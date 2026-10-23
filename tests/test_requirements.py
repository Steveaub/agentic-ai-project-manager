import json

import pytest
from fastapi.testclient import TestClient

from pm.agents import IndependentReview, ReviewFinding, run, demo_plan
from pm.api import create_app
from pm.models import (
    ProjectGoal,
    ProjectConstraint,
    RequirementConfirmation,
    FixedCostBreakdown,
    RequirementCoverage,
    Task,
    LaborEstimate,
    Dependency,
)
from pm.requirements import extract, confirm, programmatic_authority, blinded_estimate_context
from pm.validation import validate_requirements
from pm.tools import schedule, budget
from pm.providers import ProviderError
from test_live_workflows import FakeSession

GOAL = ProjectGoal(
    objective="Plan the deployment of 10 solar microgrids in Haiti with a $2.5 million budget, a 365-day deadline, and a 12-person team."
)
LIMITS = ProjectConstraint(days=365, budget=2500000, team_size=12)
RATE = LaborEstimate(
    daily_rate=200, basis="Independent fictional labor estimate", source="unverified_model_estimate"
)


def authority():
    draft = extract(GOAL, ProjectConstraint())
    return confirm(
        draft,
        RequirementConfirmation(
            draft_id=draft["id"], confirmed=True, constraints=LIMITS, scope=draft["scope"]
        ),
    )


def micro_plan(a):
    p = demo_plan()
    p.tasks = [
        Task(
            id="D",
            title="Design, procurement and permitting for ten microgrids",
            deliverable="Engineering and procurement",
            duration=10,
            people=2,
            daily_rate=200,
            fixed_cost=100000,
            source="ai_estimate",
            phase="planning",
            site_ids=a.scope.site_ids,
            cost_breakdown=FixedCostBreakdown(
                equipment=60000,
                materials=10000,
                logistics=10000,
                permitting=10000,
                contingency=10000,
                basis="Ten fictional equipment kits; labor excluded",
            ),
        )
    ]
    p.dependencies = []
    p.milestones = []
    for i, site in enumerate(a.scope.site_ids):
        for phase in ["implementation", "verification"]:
            tid = ("I" if phase == "implementation" else "V") + str(i)
            p.tasks.append(
                Task(
                    id=tid,
                    title=phase + " solar microgrid " + site,
                    deliverable=site,
                    duration=5,
                    people=2,
                    daily_rate=200,
                    fixed_cost=0,
                    source="ai_estimate",
                    phase=phase,
                    site_ids=[site],
                    cost_breakdown=FixedCostBreakdown(
                        basis="Equipment counted once in procurement; labor separate"
                    ),
                )
            )
            p.dependencies.append(
                Dependency(predecessor="D" if phase == "implementation" else "I" + str(i), successor=tid)
            )
    # Revalidate dictionaries as typed dependencies.
    p = type(p).model_validate(p.model_dump())
    p.confirmed_constraints = a.constraints
    p.scope = a.scope
    p.requirement_coverage = [
        RequirementCoverage(
            requirement_id=r.id,
            task_ids=["D"]
            if n < 2
            else [t.id for t in p.tasks if t.phase == ("implementation" if n == 2 else "verification")],
            exclusion_reason="",
        )
        for n, r in enumerate(a.scope.deliverables)
    ]
    p.exclusions = ["Long-term operations excluded; handover included"]
    p.estimation_notes = ["Fictional unverified cost assumptions; capacity and quotes require clarification"]
    return p


def test_exact_request_beats_ui_defaults_and_requires_confirmation():
    draft = extract(GOAL, ProjectConstraint())
    assert draft["proposed_constraints"] == LIMITS.model_dump()
    assert len(draft["conflicts"]) == 3
    a = authority()
    assert a.constraints == LIMITS
    assert a.scope.quantity == 10 and a.scope.location == "Haiti"
    assert len(a.scope.site_ids) == 10


def test_missing_and_contradictory_inputs_need_explicit_answers():
    draft = extract(ProjectGoal(objective="Deploy solar microgrids"))
    assert all(v is None for v in draft["proposed_constraints"].values())
    with pytest.raises(ValueError, match="all three"):
        confirm(
            draft,
            RequirementConfirmation(
                draft_id=draft["id"], confirmed=True, constraints={}, scope=draft["scope"]
            ),
        )
    draft = extract(
        ProjectGoal(
            objective="Deploy ten microgrids in 60 days or 365 days with $20000 or $2500000 and 12 people"
        )
    )
    assert len([c for c in draft["conflicts"] if c["kind"] == "contradictory_request"]) == 2
    with pytest.raises(ValueError, match="Contradictory"):
        confirm(
            draft,
            RequirementConfirmation(
                draft_id=draft["id"], confirmed=True, constraints=LIMITS, scope=draft["scope"]
            ),
        )


def test_explicit_scope_and_constraint_changes_need_resolution():
    draft = extract(GOAL)
    with pytest.raises(ValueError, match="explicit request"):
        confirm(
            draft,
            RequirementConfirmation(
                draft_id=draft["id"],
                confirmed=True,
                constraints=ProjectConstraint(days=60, budget=20000, team_size=4),
                scope=draft["scope"],
            ),
        )
    scope = {**draft["scope"], "quantity": 1, "site_ids": ["SITE-01"]}
    with pytest.raises(ValueError, match="scope"):
        confirm(
            draft,
            RequirementConfirmation(draft_id=draft["id"], confirmed=True, constraints=LIMITS, scope=scope),
        )
    with pytest.raises(ValueError, match="conflict"):
        programmatic_authority(GOAL, ProjectConstraint())


@pytest.mark.parametrize(
    "fault", ["constraints", "site", "deliverable", "labor", "double_count", "sum", "category", "serial"]
)
def test_reject_material_deterministic_failures(fault):
    a = authority()
    p = micro_plan(a)
    if fault == "constraints":
        p.confirmed_constraints = ProjectConstraint()
    if fault == "site":
        p.tasks = [t for t in p.tasks if t.site_ids != ["SITE-10"]]
    if fault == "deliverable":
        p.requirement_coverage[0].exclusion_reason = "Excluded mandatory design"
    if fault == "labor":
        p.tasks[0].daily_rate = 1
    if fault == "double_count":
        p.tasks[0].cost_breakdown.includes_labor = True
    if fault == "sum":
        p.tasks[0].fixed_cost = 1
    if fault == "category":
        p.tasks[0].cost_breakdown.permitting = 0
        p.tasks[0].fixed_cost -= 10000
    if fault == "serial":
        from pm.models import Dependency

        p.dependencies.append(Dependency(predecessor="I0", successor="I1"))
    with pytest.raises(ValueError):
        validate_requirements(p, a, RATE)


def test_parallel_sites_capacity_and_independent_costs():
    a = authority()
    p = micro_plan(a)
    assert validate_requirements(p, a, RATE)["site_count"] == 10
    s = schedule(p, LIMITS)
    b = budget(p, LIMITS)
    times = {t["id"]: t for t in s["tasks"]}
    assert times["I0"]["start"] == times["I1"]["start"]
    assert max(s["daily_people"]) <= 12
    assert s["deadline"] == 365 and b["limit"] == 2500000
    assert sum(b["categories"].values()) == b["total"]
    assert not s["verified_delivery_commitment"]
    context = json.dumps(blinded_estimate_context(a))
    assert "2500000" not in context and "2.5 million" not in context
    p.tasks[0].cost_breakdown.permitting = 0
    p.tasks[0].fixed_cost -= 10000
    from pm.models import CostCategoryExclusion

    p.cost_category_exclusions = [
        CostCategoryExclusion(category="permitting", reason="Unknown; quote required, not assumed free")
    ]
    assert validate_requirements(p, a, RATE)["status"] == "passed"


@pytest.mark.parametrize("persistent", [False, True])
def test_reviewer_critical_finding_repairs_or_blocks(monkeypatch, persistent):
    class Reviewer(FakeSession):
        reviews = 0

        def call(self, provider, role, schema, instructions, payload):
            if schema is IndependentReview:
                self.reviews += 1
                self.calls += 1
                return IndependentReview(
                    summary="Reviewed confirmed scope, constraints, coverage and estimate assumptions independently.",
                    coverage_gaps=[],
                    estimate_concerns=[],
                    recommendations=[],
                    findings=[
                        ReviewFinding(
                            severity="critical",
                            kind="semantic_gap",
                            message="Mandatory design content omitted",
                            recommended_correction="Add substantive engineering task",
                        )
                    ]
                    if persistent or self.reviews == 1
                    else [],
                )
            return super().call(provider, role, schema, instructions, payload)

    monkeypatch.setattr("pm.agents.WorkflowSession", Reviewer)
    goal = ProjectGoal(objective="Deploy solar Wi-Fi")
    if persistent:
        with pytest.raises(ProviderError, match="Clarify requirements"):
            run(goal, ProjectConstraint(), "multi")
    else:
        result = run(goal, ProjectConstraint(), "multi")
        assert result.results["acceptance"]["repair_attempts"] == 1
        assert len(result.results["review_history"]) == 2
        assert result.results["execution"]["model_calls"] == 6


def test_subjective_critical_concern_is_labeled_and_not_deterministic_failure(monkeypatch):
    class Reviewer(FakeSession):
        def call(self, provider, role, schema, instructions, payload):
            if schema is IndependentReview:
                return IndependentReview(
                    summary="Reviewed confirmed scope, constraints, coverage and estimate assumptions independently.",
                    coverage_gaps=[],
                    estimate_concerns=[],
                    recommendations=[],
                    findings=[
                        ReviewFinding(
                            severity="critical",
                            kind="subjective_estimate",
                            message="Rates seem optimistic",
                            recommended_correction="Obtain local quotes",
                        )
                    ],
                )
            return super().call(provider, role, schema, instructions, payload)

    monkeypatch.setattr("pm.agents.WorkflowSession", Reviewer)
    result = run(ProjectGoal(objective="Deploy solar Wi-Fi"), ProjectConstraint(), "multi")
    assert result.results["acceptance"]["repair_attempts"] == 0
    assert result.results["independent_review"]["findings"][0]["kind"] == "subjective_estimate"


def test_api_confirmation_binding_and_blocked_plan_not_saved(tmp_path, monkeypatch):
    client = TestClient(create_app(tmp_path / "state.db"))
    body = {"goal": GOAL.model_dump(), "constraints": ProjectConstraint().model_dump(), "provider": "multi"}
    assert client.post("/api/projects", json=body).status_code == 428
    draft = client.post(
        "/api/requirements/extract", json={"goal": GOAL.model_dump(), "form_constraints": body["constraints"]}
    ).json()
    a = client.post(
        "/api/requirements/confirm",
        json={
            "draft_id": draft["id"],
            "confirmed": True,
            "constraints": LIMITS.model_dump(),
            "scope": draft["scope"],
        },
    ).json()
    body["confirmation_id"] = a["id"]
    assert client.post("/api/projects", json=body).status_code == 409
    body["constraints"] = LIMITS.model_dump()

    def blocked(*args, **kwargs):
        assert kwargs["authority"].constraints == LIMITS
        raise ProviderError("Critical inconsistency; clarify requirements", "requirements_clarification", 422)

    monkeypatch.setattr("pm.api.run", blocked)
    assert client.post("/api/projects", json=body).status_code == 422
    assert client.get("/api/projects").json() == []


def test_verification_cannot_precede_other_sites_implementation():
    a = authority()
    p = micro_plan(a)
    p.dependencies = [d for d in p.dependencies if d.successor != "V9"]
    with pytest.raises(ValueError, match="verification must depend"):
        validate_requirements(p, a, RATE)


def test_microgrid_constraints_propagate_through_all_agents_and_tools(monkeypatch):
    seen = []

    class MicroSession(FakeSession):
        def call(self, provider, role, schema, instructions, payload):
            if role == "estimation":
                assert "budget" not in payload
                return RATE
            assert payload["constraints"] == LIMITS.model_dump()
            assert payload["confirmed_requirements"]["constraints"] == LIMITS.model_dump()
            seen.append(role)
            if role in {"planning", "repair"}:
                self.calls += 1
                return micro_plan(authority())
            return super().call(provider, role, schema, instructions, payload)

    monkeypatch.setattr("pm.agents.WorkflowSession", MicroSession)
    result = run(GOAL, LIMITS, "multi", authority=authority())
    assert seen == ["requirements", "planning", "review"]
    assert result.results["schedule"]["deadline"] == 365
    assert result.results["budget"]["limit"] == 2500000
    assert result.results["resources"]["team_size"] == 12
    assert result.results["requirements_validation"]["site_count"] == 10


def test_live_amendment_confirmation_is_bound_and_retains_baseline(tmp_path, monkeypatch):
    monkeypatch.setattr("pm.agents.WorkflowSession", FakeSession)
    client = TestClient(create_app(tmp_path / "state.db"))
    goal = {"objective": "Deploy solar Wi-Fi"}
    constraints = {"days": 60, "budget": 20000, "team_size": 4}
    draft = client.post("/api/requirements/extract", json={"goal": goal}).json()
    confirmation = client.post(
        "/api/requirements/confirm",
        json={
            "draft_id": draft["id"],
            "confirmed": True,
            "constraints": constraints,
            "scope": draft["scope"],
        },
    ).json()
    project = client.post(
        "/api/projects",
        json={
            "goal": goal,
            "constraints": constraints,
            "provider": "groq",
            "confirmation_id": confirmation["id"],
        },
    ).json()
    change = {
        "constraints": {"days": 30, "budget": 100000, "team_size": 4},
        "change": "Set deadline to 30 days and budget to $100000.",
        "provider": "groq",
        "expected_revision": 1,
    }
    endpoint = "/api/projects/" + project["id"]
    assert client.post(endpoint + "/revisions", json=change).status_code == 428
    draft = client.post(endpoint + "/requirements/extract", json=change).json()
    confirmation = client.post(
        "/api/requirements/confirm",
        json={
            "draft_id": draft["id"],
            "confirmed": True,
            "constraints": change["constraints"],
            "scope": draft["scope"],
        },
    ).json()
    change["confirmation_id"] = confirmation["id"]
    wrong = {**change, "change": "Different amendment"}
    assert client.post(endpoint + "/revisions", json=wrong).status_code == 409
    response = client.post(endpoint + "/revisions", json=change)
    assert response.status_code == 200
    revisions = response.json()["revisions"]
    assert revisions[0]["constraints"] == constraints
    assert revisions[1]["constraints"] == change["constraints"]
    assert revisions[0]["plan"]["tasks"] == revisions[1]["plan"]["tasks"]
    assert client.post(endpoint + "/revisions", json=change).status_code == 409


def test_punctuation_only_independent_review_blocks_acceptance(monkeypatch):
    class BadReview(FakeSession):
        def call(self, provider, role, schema, instructions, payload):
            if schema is IndependentReview:
                return IndependentReview(
                    summary="Reviewed confirmed scope, constraints, coverage and estimates independently.",
                    coverage_gaps=[],
                    estimate_concerns=[", "],
                    recommendations=[],
                )
            return super().call(provider, role, schema, instructions, payload)

    monkeypatch.setattr("pm.agents.WorkflowSession", BadReview)
    with pytest.raises(ProviderError, match="Clarify requirements"):
        run(ProjectGoal(objective="Deploy solar Wi-Fi"), ProjectConstraint(), "multi")


def test_explicit_review_verdict_passes_noncritical_corrections_to_repair(monkeypatch):
    class VerdictReview(FakeSession):
        reviews = 0

        def call(self, provider, role, schema, instructions, payload):
            if role == "repair":
                assert "Add operating handover clarification" in payload["repair_instruction"]
            if schema is IndependentReview:
                self.reviews += 1
                self.calls += 1
                return IndependentReview(
                    summary="Reviewed all confirmed scope and constraints with substantive coverage.",
                    verdict="requires_repair" if self.reviews == 1 else "consistent",
                    coverage_gaps=[],
                    estimate_concerns=[],
                    recommendations=["Add operating handover clarification"] if self.reviews == 1 else [],
                    findings=[],
                )
            return super().call(provider, role, schema, instructions, payload)

    monkeypatch.setattr("pm.agents.WorkflowSession", VerdictReview)
    result = run(ProjectGoal(objective="Deploy solar Wi-Fi"), ProjectConstraint(), "multi")
    assert result.results["acceptance"]["repair_attempts"] == 1


def test_descriptive_microgrid_scope_and_per_site_requirement():
    draft = extract(
        ProjectGoal(
            objective="Build a network of 10 solar-powered community microgrids serving rural communities in Haiti. Each microgrid must support approximately 100 households."
        )
    )
    assert draft["scope"]["quantity"] == 10
    assert "microgrids" in draft["scope"]["asset"]
    assert len(draft["scope"]["site_ids"]) == 10
    assert any("100 households" in r["description"] for r in draft["scope"]["deliverables"])


def test_provider_limit_error_names_provider_stage_and_recovery():
    from pm.providers import failure_summary

    error = ProviderError(
        "Generic message", "http_429", 429, [{"provider": "groq", "role": "repair", "status": "error"}]
    )
    message = failure_summary(error)
    assert "Groq reached its free usage limit while repairing the plan" in message
    assert "No plan was saved" in message
    assert "reset" in message and "will not fix this limit" in message


def test_provider_error_context_is_not_reflected_from_untrusted_metadata():
    from pm.providers import failure_summary

    error = ProviderError(
        "Safe message",
        "timeout",
        504,
        [
            {
                "provider": "private-placeholder",
                "role": "private-placeholder",
                "status": "error",
                "error": "private-placeholder",
            }
        ],
    )
    assert "private-placeholder" not in failure_summary(error)

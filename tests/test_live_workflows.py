import json

import pytest
from fastapi.testclient import TestClient

from pm.agents import IndependentReview, Requirements, demo_plan, run
from pm.api import create_app
from pm.models import (
    ProjectConstraint,
    ProjectGoal,
    LaborEstimate,
    FixedCostBreakdown,
    RequirementCoverage,
    CostCategoryExclusion,
    ProjectScope,
)
from pm.providers import ProviderError


class FakeSession:
    def __init__(self):
        self.events = []
        self.calls = 0

    def call(self, provider, role, schema, instructions, payload):
        self.calls += 1
        self.events.append({"provider": provider, "role": role})
        if schema is LaborEstimate:
            assert "budget" not in payload
            return LaborEstimate(
                daily_rate=200,
                basis="Independent fictional test labor rate",
                source="unverified_model_estimate",
            )
        if schema is Requirements:
            return Requirements(requirements=["Deploy solar Wi-Fi"], assumptions=[], questions=[])
        if schema is IndependentReview:
            assert "budget" in payload["calculated_results"]
            assert "days" in payload["calculated_results"]["schedule"]
            return IndependentReview(
                summary="Reviewed confirmed scope, constraints, coverage and estimate assumptions independently.",
                coverage_gaps=[],
                estimate_concerns=["Validate hardware quote"],
                recommendations=["Confirm permits"],
            )
        assert payload["requirements_handoff"]["requirements"] == ["Deploy solar Wi-Fi"]
        plan = demo_plan()
        for task in plan.tasks:
            task.source = "ai_estimate"
        plan.exclusions = ["None in this fictional test scope"]
        plan.estimation_notes = ["Fictional unsupported estimates"]
        plan.confirmed_constraints = ProjectConstraint.model_validate(payload["constraints"])
        plan.scope = ProjectScope.model_validate(payload["confirmed_requirements"]["scope"])
        plan.requirement_coverage = [
            RequirementCoverage(requirement_id=r.id, task_ids=["T1"], exclusion_reason="")
            for r in plan.scope.deliverables
        ]
        plan.cost_category_exclusions = [
            CostCategoryExclusion(category=k, reason="Not in this fictional test scope")
            for k in ["materials", "logistics", "permitting", "contingency"]
        ]
        for task in plan.tasks:
            task.daily_rate = payload["independent_labor_estimate"]["daily_rate"]
            task.cost_breakdown = FixedCostBreakdown(
                equipment=task.fixed_cost, basis="Fictional equipment only; labor separate"
            )
        return plan

    def summary(self):
        return {"model_calls": self.calls, "reported_tokens": 10, "invocations": self.events}


def test_role_handoff_independent_review_and_tools(monkeypatch):
    monkeypatch.setattr("pm.agents.WorkflowSession", FakeSession)
    for role, provider in [("REQUIREMENTS", "gemini"), ("PLANNING", "groq"), ("REVIEW", "openrouter")]:
        monkeypatch.setenv(f"PM_{role}_PROVIDER", provider)
    result = run(ProjectGoal(objective="Deploy solar Wi-Fi"), ProjectConstraint(), "multi")
    assert [e["provider"] for e in result.results["execution"]["invocations"]] == [
        "gemini",
        "gemini",
        "groq",
        "openrouter",
    ]
    assert result.results["independent_review"]["source"] == "ai_opinion"
    assert len(result.trace) == 5


def test_single_provider_does_not_require_other_keys(monkeypatch):
    monkeypatch.setattr("pm.agents.WorkflowSession", FakeSession)
    result = run(ProjectGoal(objective="Deploy solar Wi-Fi"), ProjectConstraint(), "groq")
    assert result.results["execution"]["model_calls"] == 3
    assert "independent_review" not in result.results


def test_revision_rejects_favorable_estimate_fabrication(monkeypatch):
    class ChangedSession(FakeSession):
        def call(self, *args):
            output = super().call(*args)
            if hasattr(output, "tasks"):
                output.tasks[0].daily_rate = 1
            return output

    monkeypatch.setattr("pm.agents.WorkflowSession", ChangedSession)
    with pytest.raises(ProviderError, match="validation after one repair"):
        run(ProjectGoal(objective="Deploy solar Wi-Fi"), ProjectConstraint(budget=1000), "groq", demo_plan())


def test_review_outage_blocks_acceptance(monkeypatch):
    class ReviewFailure(FakeSession):
        def call(self, provider, role, *args):
            if role == "review":
                raise ProviderError("Quota exhausted", "http_429", 429)
            return super().call(provider, role, *args)

    monkeypatch.setattr("pm.agents.WorkflowSession", ReviewFailure)
    with pytest.raises(ProviderError, match="acceptance blocked"):
        run(ProjectGoal(objective="Deploy solar Wi-Fi"), ProjectConstraint(), "multi")


def test_failure_metadata_persists_without_project_mutation(tmp_path, monkeypatch):
    client = TestClient(create_app(tmp_path / "state.db"))
    project = client.post("/api/projects", json={"goal": {"objective": "Deploy solar Wi-Fi"}}).json()

    def fail(*args, **kwargs):
        raise ProviderError(
            "Quota reached; retry later",
            "http_429",
            429,
            [{"provider": "groq", "role": "planning", "status": "error"}],
        )

    draft = client.post("/api/requirements/extract", json={"goal": project["goal"]}).json()
    confirmation = client.post(
        "/api/requirements/confirm",
        json={
            "draft_id": draft["id"],
            "confirmed": True,
            "constraints": {"days": 60, "budget": 100000, "team_size": 6},
            "scope": draft["scope"],
        },
    ).json()
    confirmation["provenance"]["extraction"]["amendment"] = {
        "project_id": project["id"],
        "revision": 1,
        "change": "Constraint scenario",
    }
    client.app.state.store.save_requirements({**confirmation, "id": "test-amendment"}, "confirmed")
    monkeypatch.setattr("pm.api.run", fail)
    response = client.post(
        f"/api/projects/{project['id']}/revisions",
        json={
            "constraints": {"days": 60, "budget": 100000, "team_size": 6},
            "provider": "groq",
            "expected_revision": 1,
            "confirmation_id": "test-amendment",
        },
    )
    assert response.status_code == 429
    assert len(client.get(f"/api/projects/{project['id']}").json()["revisions"]) == 1
    failures = client.get(f"/api/projects/{project['id']}/failures").json()
    assert failures[0]["error_code"] == "http_429"
    assert "Quota" not in json.dumps(failures)  # Store code/metadata rather than raw exception text.


def test_provider_endpoint_is_server_safe(tmp_path, monkeypatch):
    monkeypatch.setenv("GROQ_API_KEY", "unit-test-placeholder-never-expose")
    monkeypatch.setenv("GROQ_MODEL", "unit-test-placeholder-never-expose")
    response = TestClient(create_app(tmp_path / "state.db")).get("/api/providers")
    assert response.status_code == 200
    assert "unit-test-placeholder" not in response.text


def test_invalid_role_configuration_is_not_reflected(monkeypatch):
    monkeypatch.setenv("PM_REVIEW_PROVIDER", "unit-test-placeholder-sensitive-value")
    with pytest.raises(ProviderError) as error:
        run(ProjectGoal(objective="Deploy solar Wi-Fi"), ProjectConstraint(), "multi")
    assert "unit-test-placeholder" not in str(error.value)


def test_invalid_graph_triggers_one_repair(monkeypatch):
    class InvalidGraph(FakeSession):
        def call(self, *args):
            result = super().call(*args)
            if hasattr(result, "dependencies") and self.calls == 3:
                result.dependencies[0].predecessor = "unknown"
            return result

    monkeypatch.setattr("pm.agents.WorkflowSession", InvalidGraph)
    result = run(ProjectGoal(objective="Deploy solar Wi-Fi"), ProjectConstraint(), "groq")
    assert result.results["execution"]["model_calls"] == 4
    assert result.results["execution"]["invocations"][-1]["role"] == "repair"

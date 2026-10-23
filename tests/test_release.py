import json
from pathlib import Path

import httpx
import pytest
from fastapi.testclient import TestClient

from pm import providers
from pm.api import create_app
from pm.models import ConfirmedRequirements, Project, ProjectConstraint, ProjectGoal, RequirementConfirmation
from pm.providers import ProviderError, WorkflowSession
from pm.requirements import extract, confirm
from pm.tools import budget

REQUEST = """Develop and deploy 10 solar-powered community microgrids serving rural communities in Haiti.
Total budget: $2.5 million. Completion deadline: 365 days. Project team: 12 people.
Each microgrid must support approximately 100 households.
Each site requires solar panels, battery storage, inverters, distribution infrastructure, and remote monitoring.
Conduct feasibility studies, engineering, permits and community approvals, procurement, shipping,
customs clearance, transportation, construction, installation, testing, commissioning and operator training.
Account for hurricanes, customs, transportation, security and equipment delays; execute sites in parallel."""


def authority():
    draft = extract(ProjectGoal(objective=REQUEST))
    return confirm(
        draft,
        RequirementConfirmation(
            draft_id=draft["id"],
            confirmed=True,
            constraints=ProjectConstraint(days=365, budget=2500000, team_size=12),
            scope=draft["scope"],
        ),
    )


@pytest.fixture
def mocked_network(monkeypatch):
    for name, model in [
        ("GEMINI", "gemini-3.5-flash-lite"),
        ("GROQ", "openai/gpt-oss-120b"),
        ("OPENROUTER", "nvidia/nemotron-3.5-super-vl:free"),
    ]:
        monkeypatch.setenv(name + "_API_KEY", "unit-test-placeholder")
        monkeypatch.setenv(name + "_MODEL", model)
    for role, provider in [("REQUIREMENTS", "gemini"), ("PLANNING", "groq"), ("REVIEW", "openrouter")]:
        monkeypatch.setenv("PM_" + role + "_PROVIDER", provider)
    for name in ["GROQ", "GEMINI"]:
        monkeypatch.setenv("PM_" + name + "_FREE_TIER_CONFIRMED", "true")
    monkeypatch.setenv("PM_FREE_ONLY", "true")
    monkeypatch.setenv("PM_ALLOW_PAID_CALLS", "false")
    monkeypatch.setenv("PM_PLANNING_FALLBACK_PROVIDER", "gemini")
    monkeypatch.delenv("PM_REPAIR_FALLBACK_PROVIDER", raising=False)
    state = {"seen": [], "fail_gemini": False}
    base = providers.ChatAdapter

    def handle(request):
        if request.method == "GET":
            return httpx.Response(
                200,
                json={
                    "data": [
                        {
                            "id": "nvidia/nemotron-3.5-super-vl:free",
                            "pricing": {"prompt": "0", "completion": "0", "request": "0"},
                            "supported_parameters": ["structured_outputs"],
                        }
                    ]
                },
            )
        body = json.loads(request.content)
        gemini = "generativelanguage" in request.url.host
        context = json.loads(
            body["contents"][0]["parts"][0]["text"] if gemini else body["messages"][1]["content"]
        )
        schema = (
            body["generationConfig"]["responseJsonSchema"]
            if gemini
            else body["response_format"]["json_schema"]["schema"]
        )
        state["seen"].append((request.url.host, context))
        if request.url.host == "api.groq.com" or (
            gemini and state["fail_gemini"] and "tasks" in schema["properties"]
        ):
            return httpx.Response(429, json={"error": {"code": "rate_limit_exceeded"}})
        fields = schema["properties"]
        if "daily_rate" in fields and "tasks" not in fields:
            assert "budget" not in context
            result = {
                "daily_rate": 220,
                "basis": "Independent unverified local blended labor assumption",
                "source": "unverified_model_estimate",
            }
        elif "requirements" in fields:
            result = {
                "requirements": [REQUEST],
                "assumptions": ["Specifications and prices unverified"],
                "questions": ["Confirm site load profiles and vendor quotes"],
            }
        elif "tasks" in fields:
            a = ConfirmedRequirements.model_validate(context["confirmed_requirements"])
            result = json.loads(Path("examples/live-haiti-expanded.json").read_text(encoding="utf-8"))[
                "revisions"
            ][0]["plan"]
            result["scope"] = a.scope.model_dump()
            result["confirmed_constraints"] = a.constraints.model_dump()
            result["requirement_coverage"] = [
                {
                    "requirement_id": r.id,
                    "task_ids": [t["id"] for t in result["tasks"]],
                    "exclusion_reason": "",
                }
                for r in a.scope.deliverables
            ]
            result["tasks"][2]["title"] = (
                "Procure panels, batteries, inverters, distribution equipment and remote monitoring for ten sites"
            )
        else:
            result = {
                "summary": "Reviewed ten Haiti sites, household coverage, confirmed constraints, required work and disclosed estimates. Honest overruns remain visible.",
                "verdict": "consistent",
                "coverage_gaps": [],
                "estimate_concerns": ["Obtain independent engineering specifications and vendor quotations"],
                "recommendations": [],
                "findings": [],
            }
        if gemini:
            return httpx.Response(
                200,
                json={
                    "candidates": [
                        {"finishReason": "STOP", "content": {"parts": [{"text": json.dumps(result)}]}}
                    ],
                    "usageMetadata": {"totalTokenCount": 10},
                    "responseId": "mock-gemini",
                },
            )
        return httpx.Response(
            200,
            json={
                "id": "mock-review",
                "choices": [{"finish_reason": "stop", "message": {"content": json.dumps(result)}}],
                "usage": {"total_tokens": 10},
            },
        )

    class Adapter(base):
        def __init__(self, name):
            super().__init__(name, httpx.MockTransport(handle))

    monkeypatch.setattr(providers, "ChatAdapter", Adapter)
    providers._verified.clear()
    return state


def test_full_haiti_api_fallback_preserves_confirmed_authority(tmp_path, mocked_network):
    client = TestClient(create_app(tmp_path / "release.db"))
    a = authority()
    store = client.app.state.store
    store.save_requirements(a.model_dump(), "confirmed")
    response = client.post(
        "/api/projects",
        json={
            "goal": a.goal.model_dump(),
            "constraints": a.constraints.model_dump(),
            "provider": "multi",
            "confirmation_id": a.id,
        },
    )
    assert response.status_code == 201, response.text
    r = response.json()["revisions"][0]
    assert r["constraints"] == a.constraints.model_dump()
    assert r["results"]["execution"]["model_calls"] == 5
    assert r["results"]["execution"]["budgeted_attempts"] == 5
    assert r["results"]["execution"]["model"] == "gemini-3.5-flash-lite"
    events = r["results"]["execution"]["invocations"]
    assert [(e["provider"], e["status"]) for e in events] == [
        ("gemini", "ok"),
        ("gemini", "ok"),
        ("groq", "error"),
        ("gemini", "ok"),
        ("openrouter", "ok"),
    ]
    for _, payload in mocked_network["seen"]:
        if "constraints" in payload:
            assert payload["constraints"] == a.constraints.model_dump()
            assert payload["confirmed_requirements"]["id"] == a.id
    assert r["results"]["requirements_validation"]["site_count"] == 10
    assert r["results"]["schedule"]["deadline"] == 365
    assert r["results"]["resources"]["peak_people"] <= 12
    assert round(sum(r["results"]["budget"]["categories"].values()), 2) == r["results"]["budget"]["total"]
    assert len(client.get("/api/projects").json()) == 1


def test_fallback_failure_preserves_existing_project(tmp_path, mocked_network):
    client = TestClient(create_app(tmp_path / "release.db"))
    original = client.post(
        "/api/projects", json={"goal": {"objective": "Offline baseline for failure isolation"}}
    ).json()
    mocked_network["fail_gemini"] = True
    a = authority()
    client.app.state.store.save_requirements(a.model_dump(), "confirmed")
    response = client.post(
        "/api/projects",
        json={
            "goal": a.goal.model_dump(),
            "constraints": a.constraints.model_dump(),
            "provider": "multi",
            "confirmation_id": a.id,
        },
    )
    assert response.status_code == 429
    assert client.get("/api/projects/" + original["id"]).json() == original
    assert len(client.get("/api/projects").json()) == 1


def test_repair_inherits_explicit_planner_fallback(mocked_network):
    a = authority()
    session = WorkflowSession()
    from pm.models import AgentExecutionPlan

    result = session.call(
        "groq",
        "repair",
        AgentExecutionPlan,
        "Return plan",
        {"confirmed_requirements": a.model_dump(), "constraints": a.constraints.model_dump()},
    )
    assert result.confirmed_constraints == a.constraints
    assert session.calls == 2
    assert session.summary()["model"] == "gemini-3.5-flash-lite"


def test_fallback_cannot_exceed_shared_budget(mocked_network):
    session = WorkflowSession()
    session.calls = session.max_calls - 1
    from pm.agents import Requirements

    with pytest.raises(ProviderError) as error:
        session.call("groq", "planning", Requirements, "Extract", {})
    assert error.value.code == "budget"
    assert session.calls == 6 and len(mocked_network["seen"]) == 1


def test_paid_fallback_model_blocked_without_inference(mocked_network, monkeypatch):
    monkeypatch.setenv("GEMINI_MODEL", "paid/not-allowlisted")
    session = WorkflowSession()
    from pm.agents import Requirements

    with pytest.raises(ProviderError):
        session.call("groq", "planning", Requirements, "Extract", {})
    assert len(mocked_network["seen"]) == 1  # Only Groq; no paid Gemini request.
    assert session.calls == 2


def test_estimate_snapshots_reconcile_independently():
    totals = []
    for name in ["live-microgrids.json", "live-haiti-expanded.json"]:
        p = Project.model_validate_json(Path("examples", name).read_text(encoding="utf-8"))
        r = p.revisions[0]
        cost = budget(r.plan, r.constraints)
        assert cost["total"] == r.results["budget"]["total"]
        assert sum(cost["categories"].values()) == cost["total"]
        totals.append(cost["total"])
    assert totals == [2171600, 2693400]


def test_delete_requires_confirmation_and_cleans_only_target(tmp_path):
    client = TestClient(create_app(tmp_path / "delete.db"))
    body = {"goal": {"objective": "Two separate projects with identical demo titles"}}
    a = client.post("/api/projects", json=body).json()
    b = client.post("/api/projects", json=body).json()
    store = client.app.state.store
    for p in [a, b]:
        client.post(
            "/api/projects/" + p["id"] + "/documents",
            json={"name": "charter.txt", "text": "Project document for deletion isolation."},
        )
        store.record_failure("http_429", [], p["id"])
    endpoint = "/api/projects/" + a["id"]
    assert (
        client.request("DELETE", endpoint, json={"confirmed": False, "expected_revision": 1}).status_code
        == 422
    )
    assert (
        client.request("DELETE", endpoint, json={"confirmed": True, "expected_revision": 2}).status_code
        == 409
    )
    assert (
        client.request("DELETE", endpoint, json={"confirmed": True, "expected_revision": 1}).status_code
        == 204
    )
    assert client.get(endpoint).status_code == 404
    assert client.get("/api/projects/" + b["id"]).json() == b
    with store.connect() as db:
        assert db.execute("SELECT count(*) FROM chunks WHERE project_id=?", (a["id"],)).fetchone()[0] == 0
        assert db.execute("SELECT count(*) FROM executions WHERE project_id=?", (a["id"],)).fetchone()[0] == 0
        assert db.execute("SELECT count(*) FROM chunks WHERE project_id=?", (b["id"],)).fetchone()[0] == 1
    assert (
        client.request("DELETE", endpoint, json={"confirmed": True, "expected_revision": 1}).status_code
        == 404
    )


def test_delete_cleans_exclusive_confirmation_but_preserves_shared(tmp_path):
    from pm.store import Store

    store = Store(tmp_path / "delete.db")
    p = Project.model_validate_json(Path("examples/live-microgrids.json").read_text(encoding="utf-8"))
    a = p.revisions[0].results["confirmed_requirements"]
    store.save_requirements(a, "confirmed")
    store.save(p)
    other = p.model_copy(deep=True)
    other.id = "shared-record"
    store.save(other)
    store.delete(p.id, 1)
    assert store.get_requirements(a["id"], "confirmed")["id"] == a["id"]
    store.delete(other.id, 1)
    with pytest.raises(ValueError):
        store.get_requirements(a["id"], "confirmed")


def test_missing_fallback_stops_at_quota(mocked_network, monkeypatch):
    monkeypatch.setenv("PM_PLANNING_FALLBACK_PROVIDER", "none")
    from pm.agents import Requirements

    session = WorkflowSession()
    with pytest.raises(ProviderError) as error:
        session.call("groq", "planning", Requirements, "Extract", {})
    assert error.value.code == "http_429"
    assert session.calls == 1 and len(mocked_network["seen"]) == 1


def test_explicit_repair_opt_out_is_respected(mocked_network, monkeypatch):
    monkeypatch.setenv("PM_REPAIR_FALLBACK_PROVIDER", "none")
    from pm.agents import Requirements

    session = WorkflowSession()
    with pytest.raises(ProviderError):
        session.call("groq", "repair", Requirements, "Extract", {})
    assert session.calls == 1


def test_delete_cross_origin_is_denied(tmp_path):
    client = TestClient(create_app(tmp_path / "origin.db"))
    p = client.post("/api/projects", json={"goal": {"objective": "Origin protected project deletion"}}).json()
    response = client.request(
        "DELETE",
        "/api/projects/" + p["id"],
        json={"confirmed": True, "expected_revision": 1},
        headers={"Origin": "https://untrusted.example"},
    )
    assert response.status_code == 403
    assert client.get("/api/projects/" + p["id"]).status_code == 200

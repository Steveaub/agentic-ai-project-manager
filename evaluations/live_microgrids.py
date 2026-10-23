"""Explicit free-tier live regression, with automated test-fixture confirmation."""

import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from pm import agents  # noqa: E402
from pm.models import ProjectGoal, ProjectConstraint, RequirementConfirmation, Project  # noqa: E402
from pm.requirements import extract, confirm  # noqa: E402
from pm.providers import ProviderError, WorkflowSession  # noqa: E402
from pm.store import Store  # noqa: E402

GOAL = ProjectGoal(
    objective="Plan the deployment of 10 solar microgrids in Haiti with a $2.5 million budget, a 365-day deadline, and a 12-person team."
)
LIMITS = ProjectConstraint(days=365, budget=2500000, team_size=12)
observations = []


class AuditedSession(WorkflowSession):
    def call(self, provider, role, schema, instructions, payload):
        if role == "estimation":
            assert "budget" not in payload and "2500000" not in json.dumps(payload)
            observations.append({"role": role, "budget_withheld": True})
        else:
            assert payload["constraints"] == LIMITS.model_dump()
            assert payload["confirmed_requirements"]["constraints"] == LIMITS.model_dump()
            observations.append(
                {
                    "role": role,
                    "constraints": payload["constraints"],
                    "confirmation_id": payload["confirmed_requirements"]["id"],
                }
            )
        result = super().call(provider, role, schema, instructions, payload)
        if hasattr(result, "tasks"):
            Path("data/microgrid-last-proposal.json").write_text(
                result.model_dump_json(indent=2), encoding="utf-8"
            )
        return result


def main():
    agents.WorkflowSession = AuditedSession
    draft = extract(GOAL, ProjectConstraint())
    assert draft["proposed_constraints"] == LIMITS.model_dump() and len(draft["conflicts"]) == 3
    authority = confirm(
        draft,
        RequirementConfirmation(
            draft_id=draft["id"], confirmed=True, constraints=LIMITS, scope=draft["scope"]
        ),
    )
    authority.provenance["confirmed_by"] = "automated_regression_fixture_not_human"
    record = {
        "scenario": "Haiti ten solar microgrids",
        "goal": GOAL.objective,
        "confirmed_constraints": LIMITS.model_dump(),
        "confirmation": "automated regression fixture; not human confirmation",
        "ui_default_conflicts": draft["conflicts"],
    }
    try:
        revision = agents.run(GOAL, LIMITS, "multi", authority=authority)
        assert revision.constraints == LIMITS and revision.plan.confirmed_constraints == LIMITS
        assert revision.results["schedule"]["deadline"] == 365
        assert revision.results["budget"]["limit"] == 2500000
        assert revision.results["resources"]["team_size"] == 12
        sites = set(authority.scope.site_ids)
        for phase in ["implementation", "verification"]:
            assert {s for t in revision.plan.tasks if t.phase == phase for s in t.site_ids} == sites
        assert revision.results["requirements_validation"]["status"] == "passed"
        assert revision.results["acceptance"]["status"] == "passed"
        assert (
            round(sum(revision.results["budget"]["categories"].values()), 2)
            == revision.results["budget"]["total"]
        )
        assert revision.results["estimation"]["budget_withheld"]
        project = Project(goal=GOAL, revisions=[revision])
        Store("data/projects.sqlite3").save(project)
        Path("examples/live-microgrids.json").write_text(project.model_dump_json(indent=2), encoding="utf-8")
        starts = {t["id"]: t["start"] for t in revision.results["schedule"]["tasks"]}
        implementations = [t for t in revision.plan.tasks if t.phase == "implementation"]
        overlaps = any(
            starts[a.id] < starts[b.id] + b.duration and starts[b.id] < starts[a.id] + a.duration
            for i, a in enumerate(implementations)
            for b in implementations[i + 1 :]
        )
        record.update(
            status="passed",
            project_id=project.id,
            tasks=len(revision.plan.tasks),
            site_count=len(sites),
            implementation_overlap=overlaps,
            results=revision.results,
        )
    except ProviderError as exc:
        record.update(status="blocked", code=exc.code, message=str(exc), invocations=exc.events)
    record["payload_observations"] = observations
    Path("docs/microgrid-live-validation.json").write_text(json.dumps(record, indent=2), encoding="utf-8")
    print(json.dumps({k: record[k] for k in ["scenario", "status", "confirmed_constraints"]}, indent=2))
    return 0 if record["status"] == "passed" else 1


if __name__ == "__main__":
    raise SystemExit(main())

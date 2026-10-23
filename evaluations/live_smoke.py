"""Explicit opt-in live evaluation; never run automatically in CI. Fictional goals only."""
import argparse
import json
import os
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from pm.agents import run  # noqa: E402
from pm.models import Project, ProjectConstraint, ProjectGoal  # noqa: E402
from pm.providers import ProviderError  # noqa: E402
from pm.store import Store  # noqa: E402

GOALS = {
    "solar": "Plan the deployment of 20 solar-powered community Wi-Fi hotspots across a small municipality within 90 days with a $150,000 budget.",
    "conference": "Organize a regional technology conference for 250 attendees, with speakers, sponsors, an accessible venue, registration and AV, within 120 days and a $75000 budget.",
}


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("scenario", choices=["solar", "revision", "conference"])
    parser.add_argument("--provider", choices=["multi", "gemini", "groq", "openrouter"], default="multi")
    parser.add_argument("--project-id")
    args = parser.parse_args()
    store = Store(os.getenv("PM_DATABASE", "data/projects.sqlite3"))
    try:
        if args.scenario == "revision":
            if not args.project_id:
                parser.error("--project-id is required for revision")
            project = store.get(args.project_id)
            previous = project.revisions[-1]
            revision = run(project.goal, ProjectConstraint(days=60, budget=100000,
                           team_size=previous.constraints.team_size), args.provider, previous.plan,
                           number=len(project.revisions) + 1,
                           change="Reduce deadline to 60 days and budget to $100,000. Preserve scope and estimates; identify tradeoffs.")
            project.revisions.append(revision)
            store.save(project, expected=len(project.revisions) - 1)
            assert project.revisions[0].id != revision.id
            assert [t.id for t in previous.plan.tasks] == [t.id for t in revision.plan.tasks]
        else:
            goal = ProjectGoal(objective=GOALS[args.scenario])
            constraints = ProjectConstraint(days=90, budget=150000, team_size=6) if args.scenario == "solar" else ProjectConstraint(days=120, budget=75000, team_size=5)
            revision = run(goal, constraints, args.provider)
            project = Project(goal=goal, revisions=[revision])
            store.save(project)
            titles = " ".join(t.title.lower() for t in revision.plan.tasks)
            assert "storefront" not in titles and "e-commerce" not in titles
            assert any(word in titles for word in (["solar", "hotspot", "wi-fi", "wifi"] if args.scenario == "solar" else ["conference", "speaker", "venue", "registration"]))
        assert len(revision.trace) == 5
        assert Store(store.path).get(project.id).id == project.id
        record = {"scenario": args.scenario, "status": "passed", "project_id": project.id,
                  "revision": revision.number, "title": revision.plan.title,
                  "tasks": len(revision.plan.tasks), "days": revision.results["schedule"]["days"],
                  "cost": revision.results["budget"]["total"], "review": revision.results["review"],
                  "execution": revision.results["execution"]}
    except ProviderError as exc:
        store.record_failure(exc.code, exc.events, args.project_id)
        record = {"scenario": args.scenario, "status": "failed", "code": exc.code,
                  "message": str(exc), "execution": {"invocations": exc.events}}
    target = Path("data/live-validation.jsonl")
    target.parent.mkdir(exist_ok=True)
    with target.open("a", encoding="utf-8") as output:
        output.write(json.dumps(record) + "\n")
    print(json.dumps(record, indent=2))
    return 0 if record["status"] == "passed" else 1


if __name__ == "__main__":
    raise SystemExit(main())

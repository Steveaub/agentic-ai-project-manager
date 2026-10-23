import pytest
from pydantic import ValidationError

from pm.agents import demo_plan, invoke
from pm.models import Dependency, ProjectConstraint, Task
from pm.tools import budget, schedule, validate_wbs


def task(i, days=2, people=1):
    return Task(id=i, title=i, deliverable="Work", duration=days, people=people,
                daily_rate=100, fixed_cost=0, source="user")


def graph(tasks, edges):
    p = demo_plan()
    p.tasks = tasks
    p.dependencies = [Dependency(predecessor=a, successor=b) for a, b in edges]
    p.milestones = []
    return p


def test_diamond_cpm_and_float():
    p = graph([task("a", 2), task("b", 5), task("c", 3), task("d", 2)],
              [("a", "b"), ("a", "c"), ("b", "d"), ("c", "d")])
    s = schedule(p, ProjectConstraint())
    assert s["days"] == s["cpm_days"] == 9
    assert s["critical_path"] == ["a", "b", "d"]
    assert next(t for t in s["tasks"] if t["id"] == "c")["float"] == 2


@pytest.mark.parametrize("edges, message", [
    ([("a", "a")], "cycle"),
    ([("a", "b"), ("b", "a")], "cycle"),
    ([("a", "missing")], "unknown"),
    ([("a", "b"), ("a", "b")], "Duplicate dependency"),
])
def test_bad_dependencies(edges, message):
    with pytest.raises(ValueError, match=message):
        validate_wbs(graph([task("a"), task("b")], edges))


def test_duplicate_ids():
    with pytest.raises(ValueError, match="Duplicate task"):
        validate_wbs(graph([task("a"), task("a")], []))


def test_unknown_milestone():
    p = demo_plan()
    p.milestones[0].task_id = "unknown"
    with pytest.raises(ValueError, match="Milestone"):
        validate_wbs(p)


def test_resource_leveling():
    p = graph([task("a", 3, 2), task("b", 4, 2)], [])
    s = schedule(p, ProjectConstraint(team_size=2))
    assert s["cpm_days"] == 4
    assert s["days"] == 7
    assert max(s["daily_people"]) == 2


def test_insufficient_team():
    with pytest.raises(ValueError, match="more people"):
        schedule(graph([task("a", people=3)], []), ProjectConstraint(team_size=2))


def test_budget_arithmetic():
    p = graph([task("a", 3, 2)], [])
    p.tasks[0].fixed_cost = 12.34
    assert budget(p, ProjectConstraint())["total"] == 612.34


def test_required_demo_scenario():
    p = demo_plan()
    initial, trace = invoke(p, ProjectConstraint())
    changed, _ = invoke(p, ProjectConstraint(days=46, budget=15000))
    assert initial["schedule"]["days"] == 45
    assert initial["budget"]["total"] == 16270
    assert initial["review"]["feasible"]
    assert changed["schedule"]["feasible"]
    assert not changed["budget"]["feasible"]
    assert changed["budget"]["remaining"] == -1270
    assert len(trace) == 5


def test_tool_limits():
    with pytest.raises(ValueError, match="step limit"):
        invoke(demo_plan(), ProjectConstraint(), max_steps=4)
    with pytest.raises(ValueError, match="deadline"):
        invoke(demo_plan(), ProjectConstraint(), timeout_seconds=-1)


@pytest.mark.parametrize("field,value", [("duration", 0), ("daily_rate", -1), ("daily_rate", float("nan")), ("people", 0)])
def test_invalid_estimates(field, value):
    data = task("a").model_dump()
    data[field] = value
    with pytest.raises(ValidationError):
        Task.model_validate(data)


def test_unauthorized_operation():
    data = demo_plan().model_dump()
    data["operations"][0]["tool"] = "run_shell"
    with pytest.raises(ValidationError):
        type(demo_plan()).model_validate(data)


def test_wrong_operation_order():
    data = demo_plan().model_dump()
    data["operations"].reverse()
    with pytest.raises(ValidationError, match="Required tool order"):
        type(demo_plan()).model_validate(data)


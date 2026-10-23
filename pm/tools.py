"""Deterministic finish-to-start CPM and renewable pooled-resource scheduling.

Day zero is the start. All days are elapsed planning days, not business dates.
Resource leveling uses a stable topological greedy schedule; it is not optimal.
"""
from collections import defaultdict

from .models import AgentExecutionPlan, BudgetItem, ProjectConstraint


def validate_wbs(plan: AgentExecutionPlan) -> dict:
    ids = [t.id for t in plan.tasks]
    if len(ids) != len(set(ids)):
        raise ValueError("Duplicate task IDs")
    tasks = {t.id: t for t in plan.tasks}
    parents = {i: set() for i in ids}
    children = {i: set() for i in ids}
    edges = set()
    for d in plan.dependencies:
        edge = (d.predecessor, d.successor)
        if d.predecessor not in tasks or d.successor not in tasks:
            raise ValueError("Dependency references an unknown task")
        if edge in edges:
            raise ValueError("Duplicate dependency")
        edges.add(edge)
        parents[d.successor].add(d.predecessor)
        children[d.predecessor].add(d.successor)
    pending = {i: len(parents[i]) for i in ids}
    queue = [i for i in ids if pending[i] == 0]
    order = []
    while queue:
        i = queue.pop(0)
        order.append(i)
        for j in sorted(children[i]):
            pending[j] -= 1
            if pending[j] == 0:
                queue.append(j)
    if len(order) != len(ids):
        raise ValueError("Dependency graph contains a cycle")
    for m in plan.milestones:
        if m.task_id not in tasks:
            raise ValueError("Milestone references an unknown task")
    return {"order": order, "task_count": len(ids), "dependency_count": len(edges)}


def schedule(plan: AgentExecutionPlan, constraints: ProjectConstraint) -> dict:
    order = validate_wbs(plan)["order"]
    tasks = {t.id: t for t in plan.tasks}
    parents = defaultdict(list)
    children = defaultdict(list)
    for d in plan.dependencies:
        parents[d.successor].append(d.predecessor)
        children[d.predecessor].append(d.successor)
    early, finish = {}, {}
    for i in order:
        early[i] = max((finish[j] for j in parents[i]), default=0)
        finish[i] = early[i] + tasks[i].duration
    cpm_days = max(finish.values())
    late = {}
    for i in reversed(order):
        late[i] = min((late[j] for j in children[i]), default=cpm_days) - tasks[i].duration
    usage = defaultdict(int)
    starts, ends = {}, {}
    for i in order:
        t = tasks[i]
        if t.people > constraints.team_size:
            raise ValueError(f"Task {i} needs more people than the available team")
        start = max((ends[j] for j in parents[i]), default=0)
        while any(usage[d] + t.people > constraints.team_size for d in range(start, start + t.duration)):
            start += 1
        starts[i], ends[i] = start, start + t.duration
        for d in range(start, ends[i]):
            usage[d] += t.people
    days = max(ends.values())
    return {
        "cpm_days": cpm_days, "days": days, "deadline": constraints.days,
        "feasible": days <= constraints.days, "slack_days": constraints.days - days,
        "critical_path": [i for i in order if late[i] == early[i]],
        "tasks": [{"id": i, "start": starts[i], "end": ends[i], "early_start": early[i],
                   "float": late[i] - early[i], "critical": late[i] == early[i]} for i in order],
        "milestones": [{"title": m.title, "day": ends[m.task_id]} for m in plan.milestones],
        "daily_people": [usage[d] for d in range(days)],
        "method": "CPM lower bound + greedy pooled-resource leveling; elapsed planning days",
    }


def budget(plan: AgentExecutionPlan, constraints: ProjectConstraint) -> dict:
    items = []
    for t in plan.tasks:
        labor = round(t.duration * t.people * t.daily_rate, 2)
        items.append(BudgetItem(task_id=t.id, labor=labor, fixed=t.fixed_cost,
                                total=round(labor + t.fixed_cost, 2)).model_dump())
    total = round(sum(i["total"] for i in items), 2)
    return {"items": items, "total": total, "limit": constraints.budget,
            "remaining": round(constraints.budget - total, 2), "feasible": total <= constraints.budget,
            "currency": "USD", "basis": "duration × people × estimated daily rate + fixed costs"}


def resources(plan: AgentExecutionPlan, constraints: ProjectConstraint, scheduled: dict) -> dict:
    effort = sum(t.duration * t.people for t in plan.tasks)
    capacity = constraints.days * constraints.team_size
    return {"person_days": effort, "capacity_person_days": capacity,
            "deadline_utilization": round(effort / capacity, 4),
            "peak_people": max(scheduled["daily_people"]), "team_size": constraints.team_size,
            "assumption": "Interchangeable team members; skill availability is not modeled"}


def review(scheduled: dict, costs: dict, resource_result: dict) -> dict:
    findings = []
    if not scheduled["feasible"]:
        findings.append(f"Schedule exceeds target by {-scheduled['slack_days']} days. Reduce scope or revise estimates.")
    elif scheduled["slack_days"] <= 2:
        findings.append(f"Only {scheduled['slack_days']} days of schedule buffer remain; validate estimates before committing.")
    if not costs["feasible"]:
        findings.append(f"Estimated cost exceeds budget by ${-costs['remaining']:,.2f}. Obtain scope/rate approval.")
    if resource_result["deadline_utilization"] > .85:
        findings.append("Limited resource buffer: more than 85% of available person-days are allocated.")
    return {"feasible": scheduled["feasible"] and costs["feasible"], "findings": findings,
            "verified": "Arithmetic and graph validity only; estimates and delivery outcomes are not verified facts."}

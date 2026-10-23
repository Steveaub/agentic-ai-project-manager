"""Blocking contract checks, separate from independent model judgments."""

import math

CATEGORIES = ("equipment", "materials", "logistics", "permitting", "contingency")


def validate_requirements(plan, authority, labor):
    from .tools import validate_wbs

    validate_wbs(plan)
    if plan.confirmed_constraints != authority.constraints or plan.scope != authority.scope:
        raise ValueError("Plan constraints/scope differ from confirmed requirements")
    tasks = {t.id: t for t in plan.tasks}
    coverage = {c.requirement_id: c for c in plan.requirement_coverage}
    if len(coverage) != len(plan.requirement_coverage):
        raise ValueError("Duplicate requirements coverage")
    if set(coverage) != {r.id for r in authority.scope.deliverables}:
        raise ValueError("Missing or unknown requirement coverage")
    for requirement in authority.scope.deliverables:
        item = coverage[requirement.id]
        if not set(item.task_ids) <= tasks.keys():
            raise ValueError("Requirement coverage references unknown work")
        if requirement.mandatory and (not item.task_ids or item.exclusion_reason.strip()):
            raise ValueError("Mandatory deliverable omitted or excluded: " + requirement.id)
        if not item.task_ids and not item.exclusion_reason.strip():
            raise ValueError("Optional omissions require explicit exclusions")
    sites = set(authority.scope.site_ids)
    parents = {t.id: set() for t in plan.tasks}
    for edge in plan.dependencies:
        parents[edge.successor].add(edge.predecessor)

    def ancestors(identifier):
        visited, pending = set(), list(parents[identifier])
        while pending:
            current = pending.pop()
            if current not in visited:
                visited.add(current)
                pending.extend(parents[current])
        return visited

    for phase in ("implementation", "verification"):
        covered = {s for t in plan.tasks if t.phase == phase for s in t.site_ids}
        if not sites <= covered:
            raise ValueError("Missing site coverage for " + phase)
    for task in plan.tasks:
        if task.phase == "verification":
            required = {
                t.id
                for t in plan.tasks
                if t.phase == "implementation" and set(t.site_ids).intersection(task.site_ids)
            }
            if not required <= ancestors(task.id):
                raise ValueError("Site verification must depend on every covered site's implementation")
    if not plan.estimation_notes:
        raise ValueError("Unsupported-estimate notes are required")
    totals = dict.fromkeys(CATEGORIES, 0.0)
    for task in plan.tasks:
        if not set(task.site_ids) <= sites:
            raise ValueError("Task references an unconfirmed site")
        if sites and task.phase == "implementation" and len(task.site_ids) != 1:
            raise ValueError("Model implementation separately per site to permit parallel execution")
        if task.source != "ai_estimate" or task.daily_rate != labor.daily_rate:
            raise ValueError("Labor must retain the independently estimated rate and provenance")
        cost = task.cost_breakdown
        if (
            cost is None
            or cost.includes_labor
            or not cost.basis.strip()
            or cost.evidence != "unverified_estimate"
        ):
            raise ValueError("Separate fixed-cost basis required; fixed costs must exclude all labor")
        fixed = sum(getattr(cost, k) for k in CATEGORIES)
        if any(
            not math.isclose(value, round(value, 2), rel_tol=0, abs_tol=1e-7)
            for value in [task.daily_rate, task.fixed_cost, *(getattr(cost, k) for k in CATEGORIES)]
        ):
            raise ValueError("Cost inputs must use USD cents")
        if round(fixed * 100) != round(task.fixed_cost * 100):
            raise ValueError("Fixed-cost categories do not reconcile to task fixed_cost")
        for k in CATEGORIES:
            totals[k] += getattr(cost, k)
    for category, amount in totals.items():
        if amount == 0 and not any(
            e.category == category and e.reason.strip() for e in plan.cost_category_exclusions
        ):
            raise ValueError("Missing cost category needs an explicit explanation: " + category)
    for edge in plan.dependencies:
        a, b = tasks.get(edge.predecessor), tasks.get(edge.successor)
        if a and b and a.phase == b.phase == "implementation" and a.site_ids and b.site_ids:
            if set(a.site_ids).isdisjoint(b.site_ids) and edge.justification == "none":
                raise ValueError(
                    "Cross-site sequential implementation requires a real dependency justification"
                )
    return {
        "status": "passed",
        "confirmed_requirements_id": authority.id,
        "mandatory_deliverables": len([r for r in authority.scope.deliverables if r.mandatory]),
        "site_count": len(sites),
        "checks": [
            "constraints",
            "scope",
            "coverage",
            "site coverage",
            "independent labor rate",
            "fixed-cost reconciliation",
            "parallel-site dependencies",
        ],
        "limits": "Coverage links and estimates also require semantic model review and human validation.",
    }

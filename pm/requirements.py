"""Deterministic extraction and immutable confirmed requirements; no model can override them."""

import re

from .models import ConfirmedRequirements, ProjectScope, ScopeRequirement, uid

AMOUNT = r"([0-9][0-9,]*(?:\.[0-9]+)?)\s*(million|billion|thousand|m\b|k\b)?"
MONEY = re.compile(r"(?:\$\s*|\bUSD\s*|\bbudget\s+(?:of\s+|is\s+)?(?:USD\s*)?)" + AMOUNT, re.I)
WORDS = {
    "one": 1,
    "two": 2,
    "three": 3,
    "four": 4,
    "five": 5,
    "six": 6,
    "seven": 7,
    "eight": 8,
    "nine": 9,
    "ten": 10,
    "eleven": 11,
    "twelve": 12,
    "twenty": 20,
}
NUMBER = r"(?:\d+|" + "|".join(WORDS) + r")"


def number(text):
    return WORDS.get(text.lower(), int(text) if text.isdigit() else 0)


def money_value(match):
    multiplier = {"million": 1e6, "m": 1e6, "billion": 1e9, "thousand": 1e3, "k": 1e3}
    return float(match[1].replace(",", "")) * multiplier.get((match[2] or "").lower(), 1)


def extract(goal, form_constraints=None):
    text = goal.objective
    found = {
        "budget": [(money_value(m), m.group(0)) for m in MONEY.finditer(text)],
        "days": [],
        "team_size": [],
    }
    for m in re.finditer(r"\b(" + NUMBER + r")\s*[- ]?\s*(days?|weeks?|years?)\b", text, re.I):
        found["days"].append(
            (
                number(m[1])
                * (365 if m[2].lower().startswith("year") else 7 if m[2].lower().startswith("week") else 1),
                m.group(0),
            )
        )
    team_patterns = [
        r"\b(" + NUMBER + r")\s*[- ]?\s*(?:person|people|members?|available team members)\b",
        r"\bteam\s+(?:of\s+)?(" + NUMBER + r")\b",
    ]
    for pattern in team_patterns:
        found["team_size"].extend((number(m[1]), m.group(0)) for m in re.finditer(pattern, text, re.I))
    proposal, provenance, conflicts, questions = {}, {}, [], []
    for key, observations in found.items():
        values = list(dict.fromkeys(value for value, _ in observations))
        proposal[key] = values[0] if len(values) == 1 else None
        provenance[key] = {
            "source": "explicit_request" if values else "missing",
            "evidence": [s for _, s in observations],
        }
        if len(values) > 1:
            conflicts.append({"field": key, "kind": "contradictory_request", "values": values})
        if proposal[key] is None:
            questions.append(
                f"Confirm {key}; it is missing, ambiguous or outside supported extraction syntax."
            )
        if form_constraints and proposal[key] is not None and getattr(form_constraints, key) != proposal[key]:
            conflicts.append(
                {
                    "field": key,
                    "kind": "form_differs",
                    "request_value": proposal[key],
                    "form_value": getattr(form_constraints, key),
                }
            )
    site_match = re.search(
        r"\b("
        + NUMBER
        + r")\s+((?:solar[- ](?:powered\s+)?)?(?:microgrids?|wi[-‑ ]?fi\s+hotspots?|hotspots?|sites?))\b",
        text,
        re.I,
    )
    conference = re.search(r"\bconference\b", text, re.I)
    quantity = number(site_match[1]) if site_match else 1
    asset = site_match[2].lower() if site_match else "conference" if conference else "project"
    place = re.search(
        r"\bin\s+([A-Z][a-zA-ZÀ-ÿ' -]{1,70}?)(?=\s*,|\s+with\b|\s+within\b|\s+under\b|\.|$)", text
    )
    location = place[1].strip() if place else "Unspecified — requires clarification"
    sites = [f"SITE-{i:02d}" for i in range(1, quantity + 1)] if site_match else []
    mandatory = [
        f"Design and scope definition for {asset}",
        f"Procurement and delivery for {asset}",
        f"Implementation of all {quantity} {asset}",
        "Verification, commissioning and handover",
    ]
    for match in re.finditer(r"(?:must include|required deliverables?\s*:)\s*([^.;]+)", text, re.I):
        mandatory.extend(s.strip() for s in re.split(r",|\band\b", match[1]) if s.strip())
    scope = ProjectScope(
        asset=asset,
        quantity=quantity,
        location=location,
        site_ids=sites,
        deliverables=[ScopeRequirement(id=f"R{i + 1}", description=s) for i, s in enumerate(mandatory[:30])],
    )
    if site_match:
        questions.extend(
            [
                "Site capacities, load profiles and engineering specifications are not yet verified.",
                "Confirm local permits, site access, vendor quotes and operating/handover responsibilities.",
            ]
        )
    return {
        "id": uid(),
        "goal": goal.model_dump(),
        "proposed_constraints": proposal,
        "scope": scope.model_dump(),
        "provenance": provenance,
        "conflicts": conflicts,
        "questions": questions,
        "notice": "Explicit request values take priority in this proposal. No values are authoritative until confirmed.",
    }


def confirm(draft, body):
    if body.constraints.model_fields_set != {"days", "budget", "team_size"}:
        raise ValueError(
            "Explicitly confirm all three constraint values; defaults cannot confirm missing information"
        )
    if body.scope.model_dump() != draft["scope"] and not body.resolution.strip():
        raise ValueError("Changing extracted scope requires an explanation")
    if any(c["kind"] == "contradictory_request" for c in draft["conflicts"]) and not body.resolution.strip():
        raise ValueError(
            "Contradictory explicit inputs require an explanation resolving the conflict before confirmation"
        )
    overrides = [
        k
        for k, value in draft["proposed_constraints"].items()
        if value is not None and value != getattr(body.constraints, k)
    ]
    if overrides and not body.resolution.strip():
        raise ValueError("Changing an explicit request value requires a confirmation explanation")
    if len(set(r.id for r in body.scope.deliverables)) != len(body.scope.deliverables):
        raise ValueError("Duplicate requirement IDs")
    if (body.scope.site_ids or draft["scope"]["site_ids"]) and body.scope.site_ids != [
        f"SITE-{i:02d}" for i in range(1, body.scope.quantity + 1)
    ]:
        raise ValueError("Site identifiers must enumerate the confirmed quantity")
    return ConfirmedRequirements(
        goal=draft["goal"],
        constraints=body.constraints,
        scope=body.scope,
        provenance={
            "extraction": draft["provenance"],
            "resolution": body.resolution,
            "draft_id": draft["id"],
            "confirmed_by": "explicit_confirmation",
        },
        unresolved_questions=draft["questions"],
    )


def programmatic_authority(goal, constraints):
    draft = extract(goal)
    for key, value in draft["proposed_constraints"].items():
        if value is not None and value != getattr(constraints, key):
            raise ValueError(
                "Request and supplied constraints conflict; extract and confirm requirements before planning"
            )
    if any(c["kind"] == "contradictory_request" for c in draft["conflicts"]):
        raise ValueError("Contradictory explicit constraints require clarification")
    return ConfirmedRequirements(
        goal=goal,
        constraints=constraints,
        scope=draft["scope"],
        provenance={"confirmed_by": "explicit_programmatic_input"},
        unresolved_questions=draft["questions"],
    )


def blinded_estimate_context(authority):
    return {
        "confirmation_id": authority.id,
        "asset": authority.scope.asset,
        "quantity": authority.scope.quantity,
        "location": authority.scope.location,
        "deliverables": [MONEY.sub("[budget withheld]", r.description) for r in authority.scope.deliverables],
        "estimate_status": "Preliminary blended labor rate; no salary survey or vendor quote supplied",
    }

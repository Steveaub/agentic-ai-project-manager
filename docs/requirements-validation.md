# Confirmed requirements and acceptance validation

Verified October 23, 2026. Changes are confined to Northstar. No paid model, paid fallback, public deployment or unrelated repository change was made. Existing `.env` credentials and model defaults were retained.

## Corrected behavior

Live planning now starts with extraction and explicit confirmation. The confirmation dialog shows proposed scope, mandatory deliverables, conflicting form values, extraction evidence and unresolved questions. The exact Haiti request proposes **365 days, $2,500,000 and 12 people**, replacing all three differing UI defaults. Missing values remain blank. Contradictory explicit values, or changes to explicit requirements/scope, require a written resolution. The parser is conservative; unsupported phrasing is an open question rather than a guessed commitment.

An immutable confirmation record supplies the same constraints and scope to every planning/review call, deterministic tool, result snapshot and export. The intentionally budget-blind labor-rate call receives only scope/location. Live creation requires a matching confirmation ID; amendments also bind confirmation to project, baseline revision and change request. Constraint-only revisions preserve baseline work, rates and costs. Historical live plans lack these records and display a warning instead of being presented as newly validated.

The blocking deterministic gate checks exact confirmed scope/constraints, coverage of mandatory deliverables, every site's installation and verification, verification dependencies on the covered installations, task references/DAG validity, team capacity, independent labor-rate provenance, exact-cent fixed-cost/category reconciliation and disclosed missing categories. Separate site installation tasks permit parallel work; cross-site sequencing needs a declared reason. Shared procurement has its own phase. Fixed costs exclude labor, which is calculated once from effort and rate. Category totals separate labor, equipment, materials, logistics, permitting and contingency. Human validation is still needed for actual cost content, skill availability and engineering scope.

The configured independent reviewer returns a substantive summary, verdict, severity, finding type and corrections. Critical requirements/semantic findings or a `requires_repair` verdict trigger one shared repair and re-review. Invalid review text, truncated responses, quota failures and unresolved critical findings block saving. Punctuation-only reviewer entries are rejected even when schema-valid. Subjective estimate concerns remain labeled model opinions, separately from deterministic failures. An honestly disclosed budget/schedule overrun remains an infeasible preliminary estimate, not a fabricated fit.

A workflow allows six inference attempts total, including estimates, repairs, review and explicit free fallbacks; there is at most one repair. Requests have a 60-second ceiling and a boundary-checked 300-second workflow deadline. No automatic paid fallback exists. Single-provider mode has deterministic checks but no independent-provider review.

## Exact live Haiti regression

Input: “Plan the deployment of 10 solar microgrids in Haiti with a $2.5 million budget, a 365-day deadline, and a 12-person team.” The test intentionally supplied the old 60-day/$20,000/four-person form defaults. All three conflicts were detected. Confirmation was an **automated regression fixture**, not human confirmation.

The accepted final run used Gemini `gemini-3.5-flash-lite` for requirements, the budget-blind labor estimate and planning; OpenRouter `nvidia/nemotron-3.5-super-vl:free` provided independent review. This was an explicit process-only free-provider selection, not an automatic fallback or a change to `.env`. Groq `openai/gpt-oss-120b` remains the configured default planner; its larger-plan repair attempts were blocked by free-tier limits and never saved as valid plans.

| Check | Verified final result |
| --- | --- |
| Authority at each applicable model boundary | 365 days / $2,500,000 / 12 people; one confirmation ID |
| Scope | 10 Haiti microgrids, SITE-01 through SITE-10 |
| Work breakdown | 13 tasks; all ten sites have installation and verification coverage |
| Schedule | 200 estimated elapsed days against 365; overlapping installation work; peak 12 people |
| Labor | $220/person-day, independently estimated with budget withheld; unverified model assumption |
| Labor total | $281,600 |
| Equipment | $1,200,000 |
| Materials | $315,000 |
| Logistics | $165,000 |
| Permitting | $35,000 |
| Contingency | $175,000 |
| Calculated total | $2,171,600; $328,400 below confirmed budget |
| Exclusions | Explicit empty list: none declared; confirm operational boundaries before execution |
| Acceptance | Six actual calls; one repair/re-review; final verdict consistent; no critical findings |

The first reviewer response in that run contained a punctuation-only concern and was rejected. One bounded repair and a fresh review produced substantive coverage and estimate findings. The final reviewer retained a minor subjective concern about missing quotes/site engineering data. No verified pricing or delivery commitment is claimed. Unknown capacities, load profiles, permits, access and operating/handover responsibilities remain open questions. A model review can itself be mistaken; its statements do not supersede calculated dates or category sums.

Machine-readable final evidence: [receipt](microgrid-live-validation.json), [complete saved project](../examples/live-microgrids.json). The receipt includes actual request IDs, provider/model names, timing, token metadata, rejected reasons, both review passes and observed constraints at model boundaries. The snapshot was revalidated against the final exact-cent gate without additional inference. Saved local project: `94864088a4af4283af42124141c6150d`.

Rejected/invalidated evidence is retained rather than counted as accepted success:

- [Groq repair quota rejection](microgrid-blocked-groq.json).
- [Critical reviewer findings followed by truncated re-review](microgrid-blocked-review.json).
- [Missing estimate disclosure / mislabeled procurement rejection](microgrid-blocked-validation.json).
- [Cost reconciliation and Groq repair limit rejection](microgrid-blocked-cost.json).
- [Provisional punctuation-only review invalidated during audit](microgrid-blocked-review-quality.json). Only that task-created provisional project was removed from local storage; it is not an accepted example.

## Regression results

- **78 Python tests passed**, including the existing demo/tools/API/provider/retrieval tests. Added tests cover exact defaults conflict, missing/contradictory inputs, explicit override explanations, scope/site omissions, mandatory exclusions, labor/fixed double counting, category reconciliation, missing categories, parallel capacity, commissioning dependencies, all-agent propagation, critical review repair/blocking, explicit review-verdict correction handoff, unavailable review, punctuation-only review, and amendment binding/baseline preservation.
- **13 existing offline browser assertions**, **15 historical saved-live assertions**, **10 confirmation/blocking UI assertions**, and **14 saved Haiti assertions** passed, with zero page errors. Browser checks made no additional inference calls. The new confirmation test is included in CI.
- Ruff and JavaScript syntax checks passed. Scoped credential scanning checks tracked/staged files, reachable historical blobs and actual `.env` secret values in memory; no values are printed. `.env` remains ignored.

Run the offline suite with `python -m pytest -q`. Against the local server, run `BROWSER_CHANNEL=chrome node tests/browser-requirements.cjs`. Saved Haiti rendering uses `node tests/browser-microgrids.cjs` with the saved project in the local database. The explicit live evaluator `python evaluations/live_microgrids.py` consumes free quota; it is not part of CI. To reproduce the accepted larger-plan provider choice, set `PM_PLANNING_PROVIDER=gemini` only for that process. Free-provider availability, quotas and model output are nondeterministic; failures must remain blocked.


## Browser feedback follow-up

Live creation now hides and disables the Demo-only 60-day/$20,000/four-person controls and does not send them to extraction. Constraints are shown once, in confirmation; missing values remain blank. Demo retains its labeled sample controls. Configuration status says configured rather than implying available free quota.

The latest recorded failed request (`973d04174962465e9900f3c81da723b9`) failed when Groq returned HTTP 429 during plan repair. Provider failures now name the provider, stage, known cause and recovery step using allowlisted metadata. Quota failures explicitly explain that changing project requirements will not fix a service limit and no plan was saved. Raw provider responses and key values remain undisclosed. No additional live calls were made for this UI follow-up.

The descriptive phrase “10 solar-powered community microgrids” now extracts all ten sites rather than a generic one-project scope. Explicit “Each microgrid must…” requirements are also included for confirmation.

Follow-up verification: **81 Python tests passed**, plus 13 offline, 14 confirmation/toggle and 14 saved-Haiti browser assertions with zero page errors. Previous live receipts above are unchanged historical evidence. The browser confirmation screenshot reflects the simplified form.


## Readable model output follow-up

Cost categories now render as a currency table with labor-rate basis, budget-withholding status, estimate notes and category exclusions in plain language. Requirements handoffs use requirement/assumption/question lists; deterministic findings state calculated feasibility; independent reviews use severity/correction cards; coverage uses requirement-to-task rows. JSON remains available under collapsed Technical details sections and in exports. Failed execution history also uses readable cards.

The confirmed-requirements banner distinguishes requirements validation from budget/deadline feasibility, and explicitly states when the selected single-provider workflow did not run independent review. The user's existing Haiti project remains over budget and deadline; this presentation change does not alter its estimates or saved data.

Verification: 17 new presentation assertions cover readable budget/requirements/review/coverage, collapsed JSON, expandable audit data, and escaped model content. The 13 offline, 14 confirmation and 14 saved-Haiti checks also passed with zero page errors. No model calls were made. The presentation check is included in CI. [Cost evidence screenshot](screenshots/readable-cost-evidence.png) and [agent activity screenshot](screenshots/readable-agent-activity.png) show the existing user-created Haiti plan.

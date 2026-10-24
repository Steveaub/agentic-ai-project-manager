# Portfolio release verification — October 23, 2026

## Release scope

Built on draft PR #1, retaining its current-budget scenario default and neutral change text. The form now also retains the current deadline/team. No requirements architecture rewrite, new framework, repository, billing service or hosting was introduced.

Fixed repair fallback inheritance and successful-planner model attribution. Configured free Gemini fallback handles mocked Groq 429s; each attempt shares the six-attempt ceiling. Explicit repair opt-out remains effective. Added one-project permanent deletion with explicit confirmation, optimistic revision checks, transactional project/document/history cleanup, and preservation of shared confirmations. Desktop sidebar scrolling, mobile saved-project access, contained long content, and collapsed original descriptions are verified. Duplicate Demo titles were inspected: 11 distinct IDs existed at the start, representing separate records, not duplicated rows. No existing record was deleted by name.

## Verified execution

| Gate | Executed result |
|---|---|
| Entire Python suite | **92 passed** |
| Ruff: `python -m ruff check pm tests tools evaluations` | Passed |
| `node --check` over web/app.js, every tests/*.cjs and evaluations/*.cjs | **10 files passed** |
| Offline browser | **13 assertions passed** |
| Requirements confirmation | **16 assertions passed** |
| Readable output / escaped content | **18 assertions passed** |
| Deletion, scenario defaults, desktop/mobile, full Haiti confirmation | **33 assertions passed** |
| Saved confirmed Haiti renderer | **14 assertions passed** |
| Historical saved-live renderer | **16 assertions passed after correcting its initial-load race** |
| Total browser | **110 executed assertions, zero page errors** |
| Portfolio capture | Five clean saved-receipt screenshots; desktop and mobile checks passed |
| Credential scan | No findings in staged/tracked files, actual local-key comparison, reachable historical blobs/commit metadata; `.env` ignored |

Browser assertion counters now count calls actually executed, including loops/helpers; older manual counts in historical reports are preserved as historical evidence. CI executes the first four browser scripts (80 assertions), Python/lint/syntax/credential checks; the 30 saved-database assertions additionally ran locally. Tests used copied/mock data in an isolated QA database. The original local project database and all development/failure receipts remain intact. Clean screenshots use a new database with exactly the two saved Haiti projects; the replay preparation script refuses to overwrite existing data.

### Acceptance mapping

- Extraction/confirmation/authority/default precedence: full expanded Haiti request in `test_release.py`, existing `test_requirements.py`, and `browser-release.cjs` / `browser-requirements.cjs`.
- Provider/model identity, unchanged constraints through fallback, all attempt accounting, repair inheritance/opt-out, unavailable alternative and paid rejection: real adapters over `httpx.MockTransport` in `test_release.py` and provider tests. Successful full API fallback uses five attempts: Gemini requirements/rate, rejected Groq planning, Gemini planning, OpenRouter review.
- Ten sites, implementation/verification coverage, prerequisites, parallel overlap and team capacity: existing requirement/tool tests plus full API acceptance; mandatory exclusions and missing-site failures block acceptance.
- Costs: declared labor is separate, all six categories reconcile, fixed-cost labor flags and inconsistent totals are rejected. Both saved Haiti snapshots independently recalculate to their original totals.
- Critical review, explicit repair verdicts, re-review, punctuation-only/invalid review and quota failure: existing bounded workflow tests. Subjective estimate concerns remain separately labeled opinions.
- Revisions: confirmation is bound to baseline/change; unchanged tasks, effort/rates/costs, stale conflict checks and failed-call nonmutation remain tested.
- Delete: cancellation, explicit true confirmation, stale revision, absent target, exact-target isolation, associated chunks/history, shared-confirmation retention and cross-origin denial are tested. Browser deletion creates and deletes only its own two test records.
- Rendering: actual saved plans and a malicious-text fixture verify normal lists/tables/cards, collapsed JSON, escaping, resource-chart containment and long desktop/mobile views.

## Live evidence versus mocked evidence

**No new live inference was made for this release.** Automatic Groq-to-Gemini failover is verified end to end with real adapters and mocked provider HTTP, not claimed as a successful live quota failover. Existing receipts already establish live Gemini, Groq and OpenRouter API behavior independently, including free-tier Groq failures. This release did not alter local fallback settings or enable billing. Prior free-tier account confirmations are operator declarations, not a billing-enforcement guarantee supplied by a model ID.

The confirmed short Haiti run used Gemini planning and OpenRouter independent review, with one repair. The expanded request used Gemini only and did not run independent review. Both have correct confirmed budget/deadline/team/site count; their inputs and assumptions differ. Earlier incorrect-default or unconfirmed historical plans are not portfolio-valid examples. All rejected receipts remain in the repository. [Detailed requirements/failure history](requirements-validation.md).

## Estimate investigation

The $2,171,600 and $2,693,400 totals differ by $521,800: labor +$316,800 (1,280 → 2,720 person-days at the same $220 rate), equipment +$150,000, materials +$5,000, logistics +$76,000, permits +$8,000, contingency -$34,000. The expanded input has more explicit work and household coverage. Neither has a priced engineering bill of materials or validated component quantities; remote monitoring is not separately priced in the expanded saved cost basis. No declared-arithmetic defect was found. [Full comparison and caveats](estimate-comparison.md).

## Portfolio artifacts

- [README](../README.md), [architecture](architecture.md), [evaluation](evaluation.md), [live history](live-validation.md).
- [90-second zero-call local demo](demo-script.md).
- Clean saved-replay screenshots: [overview](screenshots/portfolio-overview.png), [cost evidence](screenshots/portfolio-costs.png), [independent review](screenshots/portfolio-review.png), [activity](screenshots/portfolio-activity.png), [mobile](screenshots/portfolio-mobile.png).
- [Short saved project](../examples/live-microgrids.json), [expanded saved project](../examples/live-haiti-expanded.json); the latter was copied from the existing user-created local record, not newly generated.
- `python tools/prepare_portfolio.py` creates a new replay database only; `node evaluations/portfolio_capture.cjs` captures saved views without model calls.

## Limits and release assessment

Ready to showcase as a local, AI-assisted engineering capstone with explicit evidence and limitations. Not production-ready or an engineering/financial decision system. Scope labels and model reviews do not establish physical design adequacy, complete procurement pricing or conceptual non-overlap of equipment allowances. Calendar/skill/resource assumptions are simplified, scheduling is greedy rather than optimal, provider quotas are external, and six attempts can be insufficient for both fallback and review repair. There is no multi-user auth, global quota, queued execution or public production hosting. Unbound initial drafts/failures remain retained because ownership cannot safely be inferred during deletion.

All work is limited to this repository. No Wealth Advisor content was changed. No paid route, billing upgrade, hosted service or public deployment was enabled. Historical security reports are historical and do not certify this release. The current changeset was reviewed for deletion isolation, fallback policy/accounting, authoritative requirements, UI escaping/layout and regression behavior before merge. PR #1 is the single release vehicle; GitHub CI status and the merge commit provide the final remote record.

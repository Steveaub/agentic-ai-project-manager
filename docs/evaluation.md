# Actual local evaluation

Date: October 22, 2026 (America/New_York).

| Check | Observed result |
|---|---|
| Python unit/integration suite | 30 passed |
| Ruff source/test checks | Passed |
| Browser JavaScript syntax | Passed |
| Chrome workflow via Playwright | 13 assertions passed; 0 page errors |
| Mobile layout | 390 × 844 viewport, no document horizontal overflow |
| npm lockfile audit | 0 vulnerabilities reported when lockfile resolved |
| pip-audit runtime requirements | No known vulnerabilities reported |
| Codex Security static source review | 0 reportable findings; initial-snapshot identity warning, see release report |
| Live model inference | Not run; paid calls not authorized |
| Docker build/runtime | Not run |

Known-answer demo: 45 elapsed planning days, $16,270 estimated cost, 73 person-days.
Target 60 days/$20,000 is within calculated constraints. Target 46 days/$15,000 keeps the same
work, has one day of schedule buffer and a $1,270 budget deficit. These are fixture outcomes,
not general model quality scores or delivery guarantees.

The initial API test attempt was blocked by Windows sandbox loopback restrictions. The suite
passed with local networking permitted. The browser test uses installed Chrome because the
bundled Playwright Chromium binary was absent. CI uses Chrome preinstalled on its Ubuntu runner.

Fake-transport tests verify requirements-to-planner handoff and exactly one graph repair without
calling a real provider. Deterministic malicious-document tests verify the fixed tool boundary;
they do not establish real-model resistance to prompt injection. Retrieval tests prove lexical
matching, persistence, project scoping and passage attachment; semantic relevance is not measured.

Authentic screenshots live in screenshots/. The completed-action trace is not a simulated live
token stream. API failures are visible but failed runs are not retained in a separate trace store.

# Release report — October 22, 2026

Repository: https://github.com/Steveaub/agentic-ai-project-manager (public).
Product name: Northstar. Independent LLM Engineering capstone. Original code: MIT.

## Implemented and verified locally

The FastAPI backend and browser frontend run together on localhost:8000. SQLite initializes
and persists projects, typed plans, completed tool traces, decisions and revisions. The UI
supports creation, dashboard, grouped WBS, dependency schedule/timeline, budget/resources,
risks, scenario preview/save, document upload/search, history selection and JSON/CSV downloads.

Five deterministic functions validate work/dependencies, calculate CPM/resource-leveled
schedules, sum cost estimates, calculate utilization and review feasibility. Schema validation
rejects unauthorized operations, invalid inputs, cycles and missing references. Revision writes
use an expected-revision check and conditional SQL update. Model errors do not save projects.

The fictional seven-task scenario calculates 45 days, $16,270 and 73 person-days. Its initial
60-day/$20,000 target is within constraints. The 46-day/$15,000 revision retains task IDs and
demo estimates, flags one day of buffer and a $1,270 shortfall, and preserves the original.

UTF-8 text/Markdown ingestion, overlapping chunks, 512-dimensional lexical word-hash vectors,
SQLite storage, cosine retrieval, source references and project isolation are verified. This is
lexical retrieval, not pretrained semantic search. Demo documents attach for human review.

## Implemented but not live-verified

OpenAI Responses structured parsing, requirements-specialist → planning-specialist handoff,
retrieved-context injection into live revisions, exact tool allowlist, and one invalid-graph
repair. Fake-transport tests verify coordination and repair logic. At most three calls, 4,000
output tokens/call, 30-second timeout/call and a boundary-checked 100-second deadline apply.
Paid calls require server-side opt-in. No live model, model quality score or cost is claimed.
The model is configured through OPENAI_MODEL; no default paid model was selected or invoked.

Dockerfile and loopback-bound compose configuration are prepared but not executed. GitHub
Actions is configured for Python tests/lint, JavaScript syntax and Chromium integration tests;
remote workflow results must be checked separately from local results.

## Actual verification

- Python: 30 tests passed; final regression run completed in 0.62 seconds.
- Ruff: all source/test checks passed. JavaScript syntax check passed.
- Browser: 13 assertions passed using installed Chrome and pinned Playwright 1.58.2;
  zero page errors, working upload/search, revisions, reload, CSV and 390px overflow check.
- npm audit: 0 reported vulnerabilities in the locked browser-test dependency tree.
- pip-audit: no known vulnerabilities reported for resolved runtime requirements.
- Codex Security static review: completed with 0 reportable findings under local, single-user
  assumptions. Independent baseline/architecture and focused release review were performed.
  The workbench warns that files changed while the scan ran, so the sealed scan identity refers
  to the initial directory snapshot, not a certification of the eventual Git commit. The final
  release configurations were reviewed separately within the same workflow. Real inference,
  third-party implementation, host ACLs and container execution were not security-validated.

The security workbench reported token usage across its four associated chat rollouts:
3,540,619 total tokens; 3,516,397 input; 3,331,328 cached input. This accounting includes broader
chat context and is not application model usage or a dollar-cost measurement. The application
made zero paid provider calls. The sealed generated security report is delivered separately
with the local outputs; this public document contains the result and limitations only.

## Artifacts

- README: architecture diagram, setup, workflow, accurate limitations and testing instructions.
- docs/screenshots: authentic dashboard, scenario and mobile captures.
- examples/sample-project.json: generated fictional project with two preserved revisions.
- docs/demo-script.md: 75-second walkthrough.
- docs/linkedin.md: accessible technical post draft, not posted.
- docs/case-study.md: problem, solution, tradeoffs, evaluation and roadmap.
- SECURITY.md and CONTRIBUTING.md: local safety boundary and contribution conventions.

## Partially implemented / remaining backlog

RAG has ingestion, vectors, retrieval and live context wiring, but no semantic embedding model
or relevance benchmark. Agent coordination has two model specialists and a deterministic
reviewer; the provider abstraction supports OpenAI and demo only. History is durable for successful
revisions, but failed executions are not separately persisted and actions are not streamed.

Planned, not implemented: Anthropic integration, arbitrary hierarchical WBS, task-level edits,
natural-language constraint extraction in demo, authenticated multi-user hosting, streaming job
control, aggregate storage/rate/cost limits, skill-based resources and business calendars.
Frontend uses native JavaScript/CSS, not Next/React/TypeScript. No formal accessibility audit,
production monitoring or full Python transitive lock was completed.

## Run and deployment status

From the repository with its virtual environment activated:

```sh
python -m pip install -r requirements-dev.txt
python -m uvicorn pm.api:app --host 127.0.0.1 --port 8000
```

Open http://127.0.0.1:8000. See README for environment creation, optional live mode and tests.
Public source publication is authorized; **public production deployment was not performed**.
No paid infrastructure or API invocation was used. No Wealth Advisor repository was accessed.

Recommended next work: authorize a small live-model evaluation with explicit spend limits,
measure semantic retrieval relevance, implement direct task edits, then add production controls
before requesting hosting approval. Do not treat this working local slice as full completion of
every capability in the original brief.

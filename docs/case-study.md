# Northstar technical case study

## Problem and solution

Project-planning prose can hide arithmetic errors, missing dependencies and unrealistic
assumptions. Northstar separates structured model proposals from a deterministic execution
boundary, preserving the evidence needed to inspect both. It is an independent LLM Engineering
capstone using fictional data, with a reproducible fixture and a verified live path.

## Architecture

A same-origin native browser frontend and FastAPI backend coordinate requirements → planning →
validation/calculation → independent review. Provider adapters encapsulate native Gemini and
compatible Groq/OpenRouter APIs, schema translation, error sanitization, quotas and timeouts.
Pydantic validates boundaries; allowlisted Python functions own DAG validation, CPM, resource
leveling and costs. SQLite stores immutable prior revisions and separate lexical document chunks.
Failed runs retain sanitized metadata without mutating project state.

## Engineering decisions

The existing working tools and persistence were preserved. A small explicit orchestrator made
permissions and four-call limits inspectable without a workflow framework. Server-only dotenv
loading avoids manual credential copying. Free-tier account confirmation and OpenRouter zero
price ceilings protect the $0 task constraint. No paid fallback, billing upgrade or public hosting
was enabled. Single-provider modes avoid unnecessary quota usage; multi-mode demonstrates a
real requirements handoff and an independent model opinion.

## Actual findings

Gemini Flash-Lite completed solar generation/revision. Groq completed unrelated conference
planning. A three-provider solar workflow executed a malformed-JSON repair, then all tools and
independent review; its revision kept the original work at $208k and exposed a $108k deficit
against $100k. A final conference run used the actual browser and HTTP API, all three models,
tools and persistence. Real request receipts are published without credentials.

The earlier Gemini 3.8 default timed out; a lighter model worked. Groq strict JSON was not enough
to eliminate malformed generations, so full local validation and a single repair were essential.
OpenRouter routing/optional reasoning needed explicit configuration. One model review asserted
an unsupported schedule concern, motivating richer calculated context and strict labeling as
opinion. These are observed failures and fixes, not proof of model reliability in every project.

## Evaluation and limits

57 Python tests, 13 offline-browser assertions, 15 saved-live-dashboard assertions and real
browser-driven conference creation passed. Different models estimated different scope costs
and durations; no external site survey or vendor quotes verified them. Independent review can
still err and cannot overwrite deterministic results. Lexical retrieval is functional; pretrained
semantic embeddings, task editing, skill calendars, global quotas and authenticated production
hosting remain future work. Public deployment requires separate authorization and security work.

See README for the diagram and setup, and docs/live-validation.md for actual calls and receipts.

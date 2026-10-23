# Evaluation

Current results (October 23, 2026): **57 Python tests**, **13 offline-browser assertions**,
**15 saved-live-dashboard assertions**, and a browser-created live conference workflow passed.
Ruff and JavaScript syntax checks passed. [Actual live receipts and failures](live-validation.md).

The Python suite verifies known CPM/float results, invalid DAGs, pooled resource contention,
budget arithmetic, typed boundaries, operation authorization, execution limits, dotenv precedence,
credential-safe status, all three adapter formats, quota/outage/timeout errors, malformed JSON,
role handoff, one bounded repair, free-only fallbacks, failed-revision preservation, optimistic
concurrency, retrieval isolation, exports and local origin checks. Mocked tests never call models.

Live evidence covers solar infrastructure generation/revision with Gemini alone and a three-model
workflow, conference planning with Groq, and conference creation through the real browser/API
with all three providers. Saved calculations are deterministic; their input estimates are unverified.
Independent review may be mistaken and never overrides tools. Failed usage can be unavailable.

CI gets no API keys and runs only mocked/unit/integration and offline-browser tests. Manual live
scripts are opt-in. Chrome was used locally; CI uses the runner's installed Chrome. Windows
sandbox loopback restrictions require permitted local networking for API/browser tests.

Earlier v0.1 dependency checks reported no known runtime vulnerabilities and no npm advisories.
The earlier Codex Security report concerned a changing v0.1 snapshot, not this v0.2 patch; it
must not be presented as a new security certification. Current publication uses a scoped
credential scan of working/staged content, reachable history and commit metadata. No secrets
were detected in the checks performed. Full live prompt-injection testing, container execution,
formal accessibility audit and public-service security validation remain incomplete.

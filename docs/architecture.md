# Architecture and decisions

The existing FastAPI/native-browser/SQLite architecture is preserved. New modules are
`config.py` (explicit repository dotenv loading and server-only safe settings) and
`providers.py` (provider adapters, free guards and shared execution budgets). Existing Pydantic
contracts, CPM/resource-leveling, budget arithmetic and project snapshots remain authoritative.

Gemini uses native generateContent with JSON Schema; Groq and OpenRouter use compatible
chat-completion APIs. Model-specific endpoints, payloads, parsing, timeouts and errors stay
inside adapters. Wire schemas use a portable subset; complete Pydantic constraints still apply
locally. The existing OpenAI Responses path remains blocked by default free-only policy.

Requirements output is handed to planning. A validated plan proposes only five operations,
in exact order. Python owns permission enforcement and arithmetic. Optional independent review
receives calculated results but cannot change them. The README contains the accurate diagram.
Single-provider modes require only one configured provider; multi-mode assigns roles explicitly.

One free workflow permits four inference attempts including repair and configured fallback,
one plan repair, per-request timeouts and a boundary-checked overall deadline. Fallbacks are
off by default and never include paid providers. OpenRouter also verifies zero catalog pricing
and sends zero price ceilings, preventing paid routing if a free endpoint disappears.

Revision snapshots use optimistic SQL updates. Failed execution metadata lives in a separate
table without mutating projects. Constraint-only revisions preserve baseline work and estimates,
so tighter constraints reveal infeasibility instead of fabricated reductions. General scope/task
editing needs a later explicit design. SQLite document chunks remain separate from project
memory and use lexical hashing/cosine retrieval, not semantic embedding inference.

The frontend adds live/single/multi controls, provider readiness, invocation metadata, independent
opinions and failed-revision history without replacing existing views. No streaming is simulated.
The service remains local and single-user; per-run safeguards do not establish multi-tenant auth,
global spend control or production readiness. Docker configuration remains unexecuted.

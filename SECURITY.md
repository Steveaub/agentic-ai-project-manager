# Security and intended deployment

This release is a local, single-user educational application using fictional data.
Run on 127.0.0.1:8000. Public source publication does not authorize public hosting.
Do not expose the API to an untrusted network or treat project IDs as access control.

Provider credentials stay in the server environment or ignored repository-local .env.
Demo never constructs a provider. Free live mode requires allowlisted models, configured keys
and operator confirmation of free-tier billing for Groq/Gemini. OpenRouter enforces zero-price
routes. PM_FREE_ONLY=true and PM_ALLOW_PAID_CALLS=false block OpenAI by default. Each free
run is bounded, but repeated/concurrent requests are not a global quota or spending limit.

Uploads are plain text/Markdown, stored as text rather than interpreted code. Retrieved
passages and LLM outputs are untrusted. The allowlist exposes only deterministic planning
functions; it has no shell, arbitrary network or file-execution tool. Prompt instructions
cannot expand it. Prompt compliance and plan quality still require live evaluation.

SQLite and exports are not encrypted. JSON exports include goals, histories, traces and
retrieved excerpts. Use fictional inputs. The local host account owns database access.
The database defaults to data/projects.sqlite3 relative to the process working directory.

Controls include Pydantic size/range validation, graph validation, bound SQL parameters,
optimistic revision updates, HTML escaping, CSP, Host/Origin checks and CSV formula-prefix
neutralization. Declared Content-Length is checked, not an enforced streamed-byte quota.
No authentication, multi-user authorization, rate limiting or aggregate project quota exists.

Before public service deployment, add identity/authorization, HTTPS, request/concurrency
limits, durable secrets management, global cost controls, backups, retention and monitoring.
Docker is a local reproducibility aid; compose binds the host port to loopback.

Report suspected issues privately through the repository owner's GitHub profile; do not
post credentials or sensitive documents in public issues. No formal response SLA is promised.

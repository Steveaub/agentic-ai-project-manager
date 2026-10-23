# Live provider configuration — verified October 23, 2026

Northstar loads this repository's `.env` at backend startup using python-dotenv, with no
interpolation and no override of process environment. Restart after changing settings.
Credentials stay server-side. `/api/providers` exposes only readiness and allowlisted model IDs.
Never overwrite an existing `.env` with the example file or share its contents in chat.

| Default role | Provider/model | Reason and observed behavior |
|---|---|---|
| Requirements | Gemini `gemini-3.5-flash-lite` | Free-tier standard input/output; documented extraction/subagent and structured-output support. Completed requirements and full solar/revision workflows via native generateContent. Chosen over 3.8 Flash after observed timeouts. |
| Planning/repair | Groq `openai/gpt-oss-120b` | Listed in free limits and strict JSON Schema models. Completed conference planning and solar planning/revision. Malformed JSON occurred despite strict mode; local validation and a bounded repair remain mandatory. |
| Independent review | OpenRouter `nvidia/nemotron-3.5-super-vl:free` | Live catalog/endpoint list zero prompt/completion prices and structured outputs. Completed reviews. Optional reasoning is disabled to avoid consuming the small review output budget. |

## Free-only controls

Keep `PM_FREE_ONLY=true` and `PM_ALLOW_PAID_CALLS=false`. Existing OpenAI integration is
retained behind both guards and was not called. No OpenAI paid default is selected.

Groq and Gemini use the same IDs on free and paid accounts. Confirm the account/project has
paid billing disabled before setting `PM_GROQ_FREE_TIER_CONFIRMED=true` or
`PM_GEMINI_FREE_TIER_CONFIRMED=true`. The owner explicitly confirmed both for local testing.
This is an operator attestation, not an API billing-ledger verification. Do not enable billing,
upgrade subscriptions, purchase credits, or switch to paid tools when quotas are exhausted.

OpenRouter checks its public catalog before inference (five-minute cache), requires a known
`:free` model with zero prices and structured-output support, and sends:

```json
{"provider":{"require_parameters":true,"allow_fallbacks":false,"max_price":{"prompt":0,"completion":0,"request":0}}}
```

No model fallback arrays, auto router, paid base model or paid endpoint is used. If prices,
capabilities or availability change, the call fails. Free models are not guaranteed to remain available.

Multi-mode roles are `PM_REQUIREMENTS_PROVIDER`, `PM_PLANNING_PROVIDER`, `PM_REVIEW_PROVIDER`.
Use `none` to disable review. `PM_<ROLE>_FALLBACK_PROVIDER` optionally permits one explicit
free-provider fallback, default `none`. Fallbacks require their own configured key/free-tier
confirmation, cannot use OpenAI, and share the four-attempt budget. No fallback is enabled locally.

Single-provider UI modes use only that provider for requirements and planning. They do not
require the other keys. Gemini and Groq single-provider workflows were live-tested. OpenRouter
single-provider planning has mocked adapter coverage; its verified live role is independent review.

## Quotas, alternatives and limitations

Groq's published free baseline for GPT-OSS 120B/20B is 30 RPM, 1,000 RPD, 8,000 TPM and
200,000 TPD; account limits may differ. `openai/gpt-oss-20b` is an allowlisted lighter alternative,
not live-evaluated here. Strict JSON support does not guarantee semantically correct plans.

Gemini pricing lists free text access for 3.8 Flash and Flash-Lite models. Exact quotas depend
on project/region and availability. Three 3.8 Flash inference attempts timed out (two compatibility
workflow attempts and one native probe); authenticated model listing succeeded. No paid retry
was attempted. The adapter uses native generateContent with JSON Schema and local Pydantic.

OpenRouter advertises a free-plan baseline of 20 RPM/50 RPD without qualifying purchased
credits. The previous `nvidia/nemotron-3-super-120b-a12b:free` route returned 404 during a
probe despite catalog presence. The selected 3.5 route initially exhausted output with reasoning
enabled, then returned valid reviews when optional reasoning was disabled. The free router
`openrouter/free` was avoided for reproducibility. Current catalog candidates include
`xingchen-agi/xing4.0-29b-a4b:free`, `dots-studio/dots-3-note-preview:free` and
`liquid/lfm-2.5-2.6b:free`; they were not silently selected or evaluated.

Gemini free-tier data may be used for product improvement. NVIDIA free endpoints describe
logging and prohibit confidential/personal uploads. Tests used fictional project data only.

## Errors and observability

Missing keys, unconfirmed billing, unlisted models and invalid role/fallback settings fail before
inference. Fixed API hosts, no HTTP redirects or environment proxies, per-call timeouts and no
automatic HTTP retries keep credential routing explicit. 401/403 require configuration review;
402 stops on payment demand; 404 requires model availability checks; 429 requires quota reset
or an explicitly chosen free provider. Context errors and outages fail visibly without project mutation.

Local Pydantic validation applies even when the wire schema omits provider-incompatible numeric
or length constraints. Invalid generated JSON, bad graphs or changed baseline estimates get at
most one repair. Six total inference attempts and a boundary-checked 300-second workflow
deadline include repairs/fallbacks/review. Configured independent review is required for acceptance: critical findings trigger one shared repair; review outages, invalid review text or unresolved critical defects block saving. Subjective estimate concerns remain opinions. See requirements-validation.md for the current workflow and evidence.

Successful revisions retain model/role/request IDs, duration, usage and validation. Failed runs
store only sanitized codes/events, never raw provider bodies or failed generations. Providers
can omit failed-request usage, so reported totals may be incomplete. No fabricated dollar-cost
or model-quality score is reported. [Actual receipts](live-validation.json).

## Primary sources

- [Groq limits](https://console.groq.com/docs/rate-limits) and [structured outputs](https://console.groq.com/docs/structured-outputs)
- [Gemini pricing](https://ai.google.dev/gemini-api/docs/pricing), [Flash-Lite capabilities](https://ai.google.dev/gemini-api/docs/models/gemini-3.5-flash-lite), [structured outputs](https://ai.google.dev/gemini-api/docs/structured-output) and [billing](https://ai.google.dev/gemini-api/docs/billing)
- [OpenRouter live catalog](https://openrouter.ai/api/v1/models), [selected endpoints](https://openrouter.ai/api/v1/models/nvidia/nemotron-3.5-super-vl:free/endpoints), [routing guards](https://openrouter.ai/docs/guides/routing/provider-selection), [structured outputs](https://openrouter.ai/docs/guides/features/structured-outputs) and [free limits](https://openrouter.ai/pricing)
- [NVIDIA free-endpoint data policy](https://openrouter.ai/nvidia/nemotron-3.5-super-vl:free)

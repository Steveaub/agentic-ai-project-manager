# LinkedIn draft — review before posting

An AI application can produce valid structured output and pass automated tests while still solving the wrong problem.

That was the most valuable lesson from building Northstar, my AI-assisted LLM Engineering capstone.

In a realistic Haiti deployment test, the request specified ten solar microgrids, a $2.5M budget, 365 days and a 12-person team. The requirements model extracted those values, but planning still used the form's $20k / 60-day / four-person defaults. An independent reviewer noticed the conflict—and the application still accepted the plan.

The fix was architectural discipline, not a more confident prompt:

• An explicit requirements-confirmation step creates one authoritative record.
• Every planning/review boundary and deterministic tool uses that record.
• Python checks site coverage, dependencies, resources and exact-cent cost reconciliation.
• Critical review findings trigger bounded repair/re-review; unresolved defects block acceptance.
• Explicit free-provider fallback shares the same call budget and records who actually answered.

Actual saved execution evidence includes Gemini planning with OpenRouter independent review, and separate Groq attempts that failed on free quota. Automatic Groq-to-Gemini fallback is tested end to end with mocked HTTP responses; I have not presented that as a successful live failover. Single-provider runs clearly identify that independent review was not run.

Another useful finding: two preliminary Haiti plans differed by $521,800. The wage assumption was identical; changed effort, scope decomposition, hardware and logistics allowances explained the difference. Both totals reconciled. Neither was a vendor quote or a validated engineering estimate.

Northstar now demonstrates confirmation, constrained planning, deterministic calculations, persistent revisions, safe deletion and readable execution evidence locally. The repository preserves failed receipts and limitations alongside successful ones.

I used Codex extensively for implementation, testing and documentation. I supplied realistic requirements, inspected results, identified failures and directed corrections. This is a portfolio capstone, not autonomous infrastructure delivery or a production service. No paid inference or public hosting was enabled for this release.

Code, evidence, screenshots and a short local demo:
https://github.com/Steveaub/agentic-ai-project-manager

#LLMEngineering #AIEngineering #Python #SoftwareTesting #OpenSource

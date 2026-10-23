# Local portfolio demo — about 90 seconds, zero inference required

Use saved receipts in a separate local portfolio database (`data/portfolio-release.sqlite3`), not a fresh model call. Clearly say “saved execution replay.” Never display `.env` or credentials. Do not delete actual projects just to clean screenshots. Portfolio screenshots are copied saved plans in isolated local data, not a hosted site.

**0–15s — The failure:** “Northstar taught me that valid JSON can still solve the wrong problem. The original Haiti test lost the user's constraints between requirements extraction and planning.”

**15–30s — Confirmation:** Select Live AI, paste the expanded Haiti request from `examples/live-haiti-expanded.json`, and click Build. Show 365 days / $2.5M / 12 people / ten sites in confirmation, then **Cancel**. Extraction/confirmation display is local; do not click Confirm and generate during a zero-call recording.

**30–50s — Saved plan:** Open the expanded saved Haiti plan. “This is the actual saved Gemini-only run. It is 15 days late and $193,400 over budget. Requirements validation passing does not mean feasibility or a delivery guarantee.” Show Timeline and Budget category/rate evidence. The model's unverified assumptions remain visible.

**50–65s — Independent review:** Open the shorter saved Haiti plan's Agent activity and Risks. “This different input used Gemini planning and OpenRouter review. The receipt contains real provider/model IDs and a rejected review followed by bounded repair. Groq free-quota failures are preserved separately. I am replaying saved history, not claiming new calls.”

**65–80s — Reliability:** Show the scenario form retaining the current budget/deadline/team, the estimate-comparison document, and the mocked fallback test evidence. Do not preview/save a live revision during this recording. Explain that fallback remains explicit, free-only and bounded by six attempts.

**80–90s — Close:** Show JSON/CSV export links and the GitHub release results. “AI-assisted development, human-directed acceptance testing, a working local capstone, and honest limits on engineering estimates.” Optionally demonstrate deletion only on a newly created Offline Demo project, with its permanent-delete confirmation; cancel if uncertain.

Screenshots: `docs/screenshots/portfolio-*.png`. No public production deployment is part of this demo.


Prepare a fresh replay database with `python tools/prepare_portfolio.py` (refuses to overwrite existing files). Start the local server with `PM_DATABASE` pointing at that file, using your shell's environment-variable syntax. This copies the two saved JSON snapshots and makes no inference calls. Use your normal database again afterward. Browser screenshots in the release were captured at desktop 1440×1000 and mobile 390×844.

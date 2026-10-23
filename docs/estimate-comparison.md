# Why two Haiti estimates differ

These are two different model-generated preliminary plans, not competing vendor quotations. Both have confirmed limits of $2,500,000, 365 days and 12 people, and cover ten Haiti sites. Both use $220/person-day. Recalculation of each saved snapshot reproduces its total exactly.

| Category | Short request | Expanded household/equipment request | Difference |
|---|---:|---:|---:|
| Labor | $281,600 | $598,400 | +$316,800 |
| Equipment | $1,200,000 | $1,350,000 | +$150,000 |
| Materials / construction | $315,000 | $320,000 | +$5,000 |
| Logistics / customs | $165,000 | $241,000 | +$76,000 |
| Permitting | $35,000 | $43,000 | +$8,000 |
| Contingency | $175,000 | $141,000 | -$34,000 |
| **Total** | **$2,171,600** | **$2,693,400** | **+$521,800** |

Labor accounts for $316,800 of the gap: effort rises from 1,280 to 2,720 person-days, while the rate stays unchanged. The first plan has 13 tasks, including 40-day/two-person site installations; the expanded plan has 16 tasks, more installation effort and distinct feasibility, design, customs/transport and operator-training packages. Those are different scope decompositions and effort assumptions, not a wage-rate change.

The first procurement package declares $1.2M of equipment for ten sites; the second declares $1.35M. Dividing by ten gives implied equipment allowances of $120k versus $135k per site, **not verified unit prices**. Neither snapshot supplies a vendor bill of materials, module quantities/wattages, battery kWh, inverter ratings, distribution lengths or monitoring unit prices. Both procurement fixed totals happen to be $1.5M, but their category allocations differ; equipment must not be compared using that aggregate alone.

The first plan assumes 50kW per site without engineering validation. The expanded request specifies approximately 100 households per site. Household coverage is not an electrical sizing specification; the evidence cannot establish equivalent load profiles, storage autonomy or hurricane design standards. Remote monitoring is requested in the expanded goal but is not separately priced in its saved cost basis. Permits/community approvals are weakly itemized, and both snapshots declare no exclusions rather than a complete operating-cost boundary. These are estimate-quality limitations, not proof that every physical component has been priced.

Logistics increases by $76k, with the expanded plan explicitly separating port/customs/security trucking and local transport. Materials increase only $5k despite the changed work decomposition. Contingency falls $34k; the evidence does not justify that reduction as risk-calibrated. Category labels and basis text are model assumptions; deterministic reconciliation cannot prove that two described purchases never overlap physically.

The short plan calculates 200 elapsed days and $328,400 budget headroom. The expanded plan calculates 380 days (15 late) and $193,400 over budget. Neither has been forced to match the budget or the other estimate. The difference is explained by changed scope decomposition and unsupported model assumptions. **No arithmetic discrepancy was found in the declared costs.** Missing engineering and itemization prevent a stronger commercial conclusion.

Sources: [short request saved plan](../examples/live-microgrids.json), [expanded request saved plan](../examples/live-haiti-expanded.json), [actual short-run receipt](microgrid-live-validation.json). The expanded snapshot records three real Gemini calls; independent review was not run. The short run records Gemini planning and OpenRouter review with one repair; Groq attempts in other receipts were blocked. Do not imply both estimates received independent review.

A credible investment estimate requires site load surveys, a validated PV/storage/distribution design, equipment and monitoring quantities, vendor quotations, shipping/customs/tax terms, local construction rates, permit schedules, operating scope and a documented risk contingency. Exact addition and schema-valid JSON cannot supply that missing evidence.

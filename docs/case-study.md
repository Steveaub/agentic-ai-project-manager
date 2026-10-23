# Northstar technical case study

## Problem

High-level project objectives hide dependencies, assumptions and constraint conflicts. A model
can produce persuasive plans with incorrect arithmetic or silently alter scope to fit a deadline.
The capstone explores a more inspectable process using fictional commerce-launch data.

## Solution and architecture

A FastAPI application serves a native browser dashboard and typed APIs. In optional live mode,
a requirements agent feeds structured context to a planning agent. Pydantic constrains proposed
tasks and operations; deterministic Python validates the DAG, computes CPM, levels pooled
resources, totals costs and reviews feasibility. SQLite separates revision memory from document
chunks/vectors. See the architecture diagram and run instructions in the README.

## Decisions and challenges

One same-origin service reduced integration overhead. Explicit orchestration gave tool control
without a graph framework. Revision snapshots plus conditional writes preserve history while
rejecting stale clients. A fixed demo enables reproducibility without API charges and is labeled
as such. Local lexical retrieval avoids model downloads, but cannot claim semantic understanding.

The reduced-constraint scenario illustrates the product's integrity: the estimates still require
45 days and $16,270. A 46-day/$15,000 target leaves one day of schedule buffer and a $1,270
shortfall. Arithmetic is deterministic; negotiating scope or rates remains a human decision.

## Evaluation

Thirty Python tests passed, including known CPM/float values, invalid graphs, capacity contention,
cost totals, typed boundaries, tool limits, live-path fake-transport handoff/repair, revision memory,
retrieval isolation and exports. Thirteen Chrome browser assertions passed with zero page errors,
including uploads, scenarios, saved history, downloads and a 390px mobile overflow check.
Screenshots are captured from that local application. No real model output or paid inference was
used, so live planning quality and prompt-injection robustness remain unverified.

## Tradeoffs and roadmap

The release is a working local vertical slice, not full production completion. Next steps are
an authorized live-model evaluation, pretrained semantic embeddings with retrieval relevance
metrics, task-level edits, skills/calendars, a second provider, stronger failure telemetry, global
cost controls and authenticated hosting. Deployment requires separate approval. The repository
documents these limits so reviewers can distinguish implemented tools from future ambitions.

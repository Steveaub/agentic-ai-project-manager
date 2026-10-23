# Decisions and tradeoffs

The browser and API share one FastAPI process. Native browser JavaScript avoids a second
build/runtime and makes offline demonstration straightforward. React/Next.js and TypeScript
were preferred in the brief, not mandatory; their omission is explicit. Python/Pydantic own
validation at request, provider and persistence boundaries. No agent framework is needed for
five deterministic operations and one bounded feedback cycle.

The requirements specialist hands structured requirements to the planner. The planner owns
proposals; the orchestrator owns allowed execution. Scheduling and costs never depend on
model arithmetic. Infeasibility is a useful result: deadlines and budgets are constraints,
not permission to fabricate cheaper or faster work.

The graph validator uses Kahn's topological sort. CPM calculates earliest/latest starts and
total float over the DAG; critical_path returns all zero-float tasks and can include multiple
parallel paths. Resource leveling then schedules the stable topological order against an
integer pooled capacity. Its result is feasible with respect to that pool, not globally optimal.

Full project revisions are SQLite JSON snapshots with compare-and-swap updates. This avoids
premature ORM complexity while preserving original versions. It will need migrations and
normalized relational entities for larger concurrent workloads. Document chunks/vectors live
in a separate table and are project-filtered. Retrieval is normalized lexical hashing, not
semantic inference. The embedding interface is replaceable, but only the local implementation ships.

API operations: create/list/get projects; preview scenarios; append revisions; ingest/search
documents; export JSON/CSV; health. OpenAPI at /docs reflects the running server. There is no
external business-task execution, multi-tenant auth or production hosting configuration.

Version decisions were checked against official FastAPI and OpenAI documentation. Exact
versions installed during development are pinned in requirements. No paid API call was made.

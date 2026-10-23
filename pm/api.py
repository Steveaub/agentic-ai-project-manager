import csv
import io
import os
from pathlib import Path

from fastapi import FastAPI, HTTPException, Request
from fastapi.responses import FileResponse, JSONResponse, Response
from fastapi.staticfiles import StaticFiles
from starlette.middleware.trustedhost import TrustedHostMiddleware

from .agents import ProviderError, run
from .config import public_config
from .models import DocumentInput, Project, ProjectRequest, ProjectScenario, SearchInput
from .store import ConflictError, Store

WEB = Path(__file__).resolve().parent.parent / "web"


def create_app(db_path=None):
    app = FastAPI(title="Agentic AI Project Manager", version="0.2.0")
    app.add_middleware(TrustedHostMiddleware, allowed_hosts=["localhost", "127.0.0.1", "testserver"])
    store = Store(db_path or os.getenv("PM_DATABASE", "data/projects.sqlite3"))
    app.state.store = store

    @app.middleware("http")
    async def local_boundary(request: Request, call_next):
        # Same-origin writes only; no browser can spend model funds cross-origin.
        origin = request.headers.get("origin")
        if request.method not in ("GET", "HEAD", "OPTIONS") and origin and origin not in {
            "http://127.0.0.1:8000", "http://localhost:8000", "http://testserver"}:
            return JSONResponse({"detail": "Cross-origin writes forbidden"}, status_code=403)
        if int(request.headers.get("content-length", "0")) > 600_000:
            return JSONResponse({"detail": "Request too large"}, status_code=413)
        response = await call_next(request)
        response.headers["X-Content-Type-Options"] = "nosniff"
        response.headers["Referrer-Policy"] = "no-referrer"
        response.headers["Content-Security-Policy"] = (
            "default-src 'self'; script-src 'self'; style-src 'self' 'unsafe-inline'; "
            "img-src 'self' data:; connect-src 'self'; object-src 'none'; frame-ancestors 'none'; base-uri 'none'"
        )
        return response

    @app.exception_handler(KeyError)
    async def missing(_, exc):
        return JSONResponse({"detail": "Project not found"}, status_code=404)

    @app.exception_handler(ConflictError)
    async def conflict(_, exc):
        return JSONResponse({"detail": str(exc)}, status_code=409)

    @app.exception_handler(ValueError)
    async def invalid(_, exc):
        return JSONResponse({"detail": str(exc)}, status_code=422)

    @app.exception_handler(ProviderError)
    async def provider_failure(_, exc):
        execution_id = store.record_failure(exc.code, exc.events)
        return JSONResponse({"detail": str(exc), "code": exc.code, "execution_id": execution_id}, status_code=exc.status)

    @app.get("/api/health")
    def health():
        settings = public_config()
        return {"status": "ok", "default_provider": "demo", "live_enabled": any(p["ready"] for p in settings["providers"])}

    @app.get("/api/providers")
    def providers():
        return public_config()

    @app.get("/api/projects/{project_id}/failures")
    def failures(project_id: str):
        return store.failures(project_id)

    @app.get("/api/projects")
    def projects():
        return store.list()

    @app.post("/api/projects", status_code=201)
    def create(body: ProjectRequest):
        revision = run(body.goal, body.constraints, body.provider)
        project = Project(goal=body.goal, revisions=[revision])
        store.save(project)
        return project

    @app.get("/api/projects/{project_id}")
    def get(project_id: str):
        return store.get(project_id)

    def revise(project_id, body, persist):
        project = store.get(project_id)
        if body.expected_revision != len(project.revisions):
            raise ConflictError("Project changed; reload before revising")
        previous = project.revisions[-1]
        sources = store.search(project_id, project.goal.objective + " " + body.change)
        try:
            revision = run(project.goal, body.constraints, body.provider, previous.plan,
                           sources, len(project.revisions) + 1, body.change)
        except ProviderError as exc:
            execution_id = store.record_failure(exc.code, exc.events, project_id)
            raise HTTPException(exc.status, {"message": str(exc), "code": exc.code,
                                            "execution_id": execution_id}) from None
        if persist:
            project.revisions.append(revision)
            store.save(project, expected=body.expected_revision)
            return project
        return {"baseline": previous, "scenario": revision,
                "delta": {"days": revision.results["schedule"]["days"] - previous.results["schedule"]["days"],
                          "cost": round(revision.results["budget"]["total"] - previous.results["budget"]["total"], 2)}}

    @app.post("/api/projects/{project_id}/revisions")
    def revision(project_id: str, body: ProjectScenario):
        return revise(project_id, body, True)

    @app.post("/api/projects/{project_id}/scenarios")
    def scenario(project_id: str, body: ProjectScenario):
        return revise(project_id, body, False)

    @app.post("/api/projects/{project_id}/documents", status_code=201)
    def ingest(project_id: str, body: DocumentInput):
        return store.ingest(project_id, body)

    @app.post("/api/projects/{project_id}/search")
    def search(project_id: str, body: SearchInput):
        return {"matches": store.search(project_id, body.query), "method": store.embedding.name}

    @app.get("/api/projects/{project_id}/export")
    def export(project_id: str, format: str = "json"):
        project = store.get(project_id)
        if format == "json":
            return Response(project.model_dump_json(indent=2), media_type="application/json",
                            headers={"Content-Disposition": 'attachment; filename="project.json"'})
        if format != "csv":
            raise HTTPException(422, "Supported formats: json, csv")
        revision = project.revisions[-1]
        schedule = {t["id"]: t for t in revision.results["schedule"]["tasks"]}
        costs = {t["task_id"]: t for t in revision.results["budget"]["items"]}
        stream = io.StringIO(newline="")
        writer = csv.writer(stream)
        writer.writerow(["id", "deliverable", "task", "start_day", "end_day", "cost_usd", "source"])
        def safe(value):
            value = str(value)
            return "'" + value if value.lstrip().startswith(("=", "+", "-", "@")) else value
        for t in revision.plan.tasks:
            writer.writerow([safe(t.id), safe(t.deliverable), safe(t.title), schedule[t.id]["start"],
                             schedule[t.id]["end"], costs[t.id]["total"], t.source])
        return Response(stream.getvalue(), media_type="text/csv",
                        headers={"Content-Disposition": 'attachment; filename="tasks.csv"'})

    app.mount("/assets", StaticFiles(directory=WEB), name="assets")

    @app.get("/")
    def home():
        return FileResponse(WEB / "index.html")

    return app


app = create_app()

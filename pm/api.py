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
from .models import (DocumentInput, Project, ProjectRequest, ProjectScenario, SearchInput,
                     RequirementExtraction, RequirementConfirmation, ConfirmedRequirements, ProjectDeletion)
from .requirements import extract, confirm
from .providers import failure_summary
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
        return JSONResponse({"detail": failure_summary(exc), "code": exc.code, "execution_id": execution_id}, status_code=exc.status)

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
        authority = require_confirmation(body, body.goal)
        revision = run(body.goal, body.constraints, body.provider, authority=authority)
        project = Project(goal=body.goal, revisions=[revision])
        store.save(project)
        return project

    @app.post("/api/requirements/extract")
    def extract_requirements(body: RequirementExtraction):
        draft = extract(body.goal, body.form_constraints)
        store.save_requirements(draft, "draft")
        return draft

    @app.post("/api/requirements/confirm")
    def confirm_requirements(body: RequirementConfirmation):
        authority = confirm(store.get_requirements(body.draft_id, "draft"), body)
        store.save_requirements(authority.model_dump(), "confirmed")
        return authority

    def require_confirmation(body, goal):
        if body.provider in {"demo", "openai"}:
            return None
        if not body.confirmation_id:
            raise HTTPException(428, "Extract and explicitly confirm requirements before live planning")
        authority = ConfirmedRequirements.model_validate(store.get_requirements(body.confirmation_id, "confirmed"))
        if authority.goal != goal or authority.constraints != body.constraints:
            raise HTTPException(409, "Goal or constraints changed after confirmation; confirm again")
        return authority

    @app.post("/api/projects/{project_id}/requirements/extract")
    def extract_amendment(project_id: str, body: ProjectScenario):
        project = store.get(project_id)
        if body.expected_revision != len(project.revisions):
            raise ConflictError("Project changed; reload before confirming")
        baseline = project.revisions[-1]
        if "confirmed_requirements" not in baseline.results:
            raise HTTPException(428, "Historical live baseline lacks confirmed scope; create a newly confirmed plan")
        draft = extract(type(project.goal)(objective=body.change if len(body.change) >= 10 else "Constraint amendment"), body.constraints)
        # Explicit amendment fields are proposed, never silently reconciled with contradictory change prose.
        for key in draft["proposed_constraints"]:
            if draft["proposed_constraints"][key] is None:
                draft["proposed_constraints"][key] = getattr(body.constraints, key)
        draft.update(goal=project.goal.model_dump(), scope=baseline.results["confirmed_requirements"]["scope"])
        draft["provenance"]["amendment"] = {"project_id": project_id, "revision": len(project.revisions), "change": body.change}
        store.save_requirements(draft, "draft")
        return draft

    @app.get("/api/projects/{project_id}")
    def get(project_id: str):
        return store.get(project_id)

    @app.delete("/api/projects/{project_id}", status_code=204)
    def delete_project(project_id: str, body: ProjectDeletion):
        store.delete(project_id, body.expected_revision)
        return Response(status_code=204)

    def revise(project_id, body, persist):
        project = store.get(project_id)
        if body.expected_revision != len(project.revisions):
            raise ConflictError("Project changed; reload before revising")
        previous = project.revisions[-1]
        authority = require_confirmation(body, project.goal)
        if authority:
            amendment = authority.provenance["extraction"].get("amendment", {})
            if amendment != {"project_id": project_id, "revision": len(project.revisions), "change": body.change}:
                raise HTTPException(409, "Confirmation is not bound to this amendment and baseline")
        sources = store.search(project_id, project.goal.objective + " " + body.change)
        try:
            revision = run(project.goal, body.constraints, body.provider, previous.plan,
                           sources, len(project.revisions) + 1, body.change, authority=authority)
        except ProviderError as exc:
            execution_id = store.record_failure(exc.code, exc.events, project_id)
            raise HTTPException(exc.status, {"message": failure_summary(exc), "code": exc.code,
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

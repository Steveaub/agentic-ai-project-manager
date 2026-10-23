import hashlib
import json
import math
import re
import sqlite3
from collections import Counter
from pathlib import Path

from .models import DocumentInput, Project, now, uid


class ConflictError(ValueError):
    pass


class LocalEmbedding:
    """Deterministic 512-dimensional word-hash vectors; lexical, not semantic.

    No network, pickle, executable uploads, or model downloads. An embedding
    interface deliberately separated from persistence for future dense models.
    """
    name = "word-hash-v1-512-lexical"

    def embed(self, text: str) -> list[float]:
        counts = Counter(re.findall(r"[a-z0-9]+", text.lower()))
        vector = [0.0] * 512
        for word, count in counts.items():
            index = int.from_bytes(hashlib.sha256(word.encode()).digest()[:4], "big") % 512
            vector[index] += 1 + math.log(count)
        norm = math.sqrt(sum(x * x for x in vector)) or 1
        return [v / norm for v in vector]


class Store:
    def __init__(self, path: str | Path):
        self.path = str(path)
        Path(path).parent.mkdir(parents=True, exist_ok=True)
        self.embedding = LocalEmbedding()
        with self.connect() as db:
            db.executescript("""
                CREATE TABLE IF NOT EXISTS projects (id TEXT PRIMARY KEY, body TEXT NOT NULL, revision INTEGER NOT NULL);
                CREATE TABLE IF NOT EXISTS chunks (
                    id TEXT PRIMARY KEY, project_id TEXT NOT NULL, name TEXT NOT NULL,
                    ordinal INTEGER NOT NULL, text TEXT NOT NULL, vector TEXT NOT NULL,
                    created_at TEXT NOT NULL, embedding TEXT NOT NULL);
                CREATE INDEX IF NOT EXISTS chunks_project ON chunks(project_id);
                CREATE TABLE IF NOT EXISTS executions (id TEXT PRIMARY KEY, project_id TEXT, body TEXT NOT NULL);
                CREATE TABLE IF NOT EXISTS requirements (id TEXT PRIMARY KEY, kind TEXT NOT NULL, body TEXT NOT NULL);
            """)

    def connect(self):
        return sqlite3.connect(self.path, timeout=10)

    def save_requirements(self, body, kind):
        with self.connect() as db:
            db.execute("INSERT INTO requirements VALUES (?,?,?)", (body["id"], kind, json.dumps(body)))

    def get_requirements(self, identifier, kind):
        with self.connect() as db:
            row = db.execute("SELECT body FROM requirements WHERE id=? AND kind=?", (identifier, kind)).fetchone()
        if not row:
            raise ValueError("Requirements record not found; extract and confirm again")
        return json.loads(row[0])

    def record_failure(self, code, events, project_id=None):
        execution_id = uid()
        body = {"id": execution_id, "project_id": project_id, "status": "failed", "error_code": code,
                "created_at": now(), "invocations": events}
        with self.connect() as db:
            db.execute("INSERT INTO executions VALUES (?,?,?)", (execution_id, project_id, json.dumps(body)))
        return execution_id

    def failures(self, project_id):
        self.get(project_id)
        with self.connect() as db:
            rows = db.execute("SELECT body FROM executions WHERE project_id=? ORDER BY rowid DESC LIMIT 20",
                              (project_id,)).fetchall()
        return [json.loads(row[0]) for row in rows]

    def save(self, project: Project, expected: int | None = None):
        with self.connect() as db:
            if expected is None:
                db.execute("INSERT INTO projects VALUES (?, ?, ?)",
                           (project.id, project.model_dump_json(), len(project.revisions)))
            else:
                result = db.execute("UPDATE projects SET body=?, revision=? WHERE id=? AND revision=?",
                                    (project.model_dump_json(), len(project.revisions), project.id, expected))
                if result.rowcount != 1:
                    raise ConflictError("Project changed; reload before revising")

    def get(self, project_id: str) -> Project:
        with self.connect() as db:
            row = db.execute("SELECT body FROM projects WHERE id=?", (project_id,)).fetchone()
        if not row:
            raise KeyError(project_id)
        return Project.model_validate_json(row[0])

    def list(self):
        with self.connect() as db:
            rows = db.execute("SELECT body FROM projects ORDER BY rowid DESC").fetchall()
        return [{"id": p.id, "title": p.revisions[-1].plan.title, "revisions": len(p.revisions)}
                for (body,) in rows for p in [Project.model_validate_json(body)]]

    def delete(self, project_id, expected):
        # One transaction prevents partial cleanup or stale deletion after a revision.
        with self.connect() as db:
            db.execute("BEGIN IMMEDIATE")
            rows = db.execute("SELECT id,body,revision FROM projects").fetchall()
            target = next((row for row in rows if row[0] == project_id), None)
            if target is None:
                raise KeyError(project_id)
            if target[2] != expected:
                raise ConflictError("Project changed; reload and confirm deletion again")
            def references(body):
                ids = set()
                for revision in json.loads(body)["revisions"]:
                    authority = revision["results"].get("confirmed_requirements", {})
                    ids.update(i for i in [authority.get("id"), authority.get("provenance", {}).get("draft_id")] if i)
                return ids
            candidates = references(target[1])
            retained = set().union(*(references(body) for identifier, body, _ in rows if identifier != project_id))
            for identifier, body in db.execute("SELECT id,body FROM requirements").fetchall():
                record = json.loads(body)
                provenance = record.get("provenance", {})
                amendment = provenance.get("amendment", provenance.get("extraction", {}).get("amendment", {}))
                if amendment.get("project_id") == project_id:
                    candidates.add(identifier)
            for identifier in candidates - retained:
                db.execute("DELETE FROM requirements WHERE id=?", (identifier,))
            db.execute("DELETE FROM chunks WHERE project_id=?", (project_id,))
            db.execute("DELETE FROM executions WHERE project_id=?", (project_id,))
            db.execute("DELETE FROM projects WHERE id=?", (project_id,))

    def ingest(self, project_id: str, document: DocumentInput):
        self.get(project_id)
        text = document.text.strip()
        if not text:
            raise ValueError("Document must contain text")
        chunks = [text[i:i + 1000] for i in range(0, len(text), 800)]
        with self.connect() as db:
            count = db.execute("SELECT count(*) FROM chunks WHERE project_id=?", (project_id,)).fetchone()[0]
            if count + len(chunks) > 500:
                raise ValueError("Project document limit reached (500 chunks)")
            for ordinal, chunk in enumerate(chunks):
                db.execute("INSERT INTO chunks VALUES (?, ?, ?, ?, ?, ?, ?, ?)",
                           (uid(), project_id, document.name, ordinal, chunk,
                            json.dumps(self.embedding.embed(chunk)), now(), self.embedding.name))
        return {"chunks": len(chunks), "embedding": self.embedding.name}

    def search(self, project_id: str, query: str, limit: int = 4):
        self.get(project_id)
        vector = self.embedding.embed(query)
        with self.connect() as db:
            rows = db.execute("SELECT id,name,ordinal,text,vector FROM chunks WHERE project_id=?",
                              (project_id,)).fetchall()
        ranked = [{"id": i, "name": n, "chunk": o, "text": t,
                   "score": round(sum(a * b for a, b in zip(vector, json.loads(v))), 5)}
                  for i, n, o, t, v in rows]
        return sorted((r for r in ranked if r["score"] > .05), key=lambda r: -r["score"])[:limit]

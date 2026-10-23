"""Scoped credential hygiene. Values remain in memory; only counts/locations are printed."""
import json
import re
import subprocess
from pathlib import Path

from dotenv import dotenv_values

ROOT = Path(__file__).resolve().parents[1]
SECRET_NAME = re.compile(r"api_?key|token|secret|password|private_?key", re.I)
PLACEHOLDER = re.compile(r"replace|placeholder|your[-_ ]|^<|^\.{3}$|^changeme$", re.I)
PATTERNS = [
    ("provider_token_format", re.compile(rb"(?:sk-(?:proj-|or-v1-)?[A-Za-z0-9_-]{24,}|gsk_[A-Za-z0-9]{24,}|AIza[A-Za-z0-9_-]{30,}|gh[pousr]_[A-Za-z0-9]{30,}|github_pat_[A-Za-z0-9_]{30,})")),
    ("private_key", re.compile(rb"-----BEGIN (?:RSA |EC |OPENSSH |DSA )?PRIVATE KEY-----")),
    ("aws_access_key", re.compile(rb"(?:AKIA|ASIA)[A-Z0-9]{16}")),
]


def git(*args):
    return subprocess.run(["git", "-C", str(ROOT), *args], capture_output=True, check=True).stdout


def audit():
    # Explicit path; no unrelated environment files or credential stores.
    values = dotenv_values(ROOT / ".env", interpolate=False) if (ROOT / ".env").exists() else {}
    secrets = [v.encode() for k, v in values.items() if v and SECRET_NAME.search(k)
               and len(v) >= 12 and not PLACEHOLDER.search(v)]
    findings = []
    def scan(data, location):
        if any(value in data for value in secrets):
            findings.append({"location": location, "kind": "exact_local_credential_match"})
        for kind, pattern in PATTERNS:
            if pattern.search(data):
                findings.append({"location": location, "kind": kind})
    paths = list(filter(None, git("ls-files", "-z").decode().split("\0")))
    for name in paths:
        path = ROOT / name
        if path.is_file():
            scan(path.read_bytes(), "working-tree:" + name)
        if Path(name).name == ".env":
            findings.append({"location": name, "kind": "environment_file_tracked"})
    # Include staged bytes independently of the worktree before publication.
    for entry in git("ls-files", "--stage", "-z").split(b"\0"):
        if entry:
            metadata, name = entry.split(b"\t", 1)
            oid = metadata.split()[1].decode()
            scan(git("cat-file", "blob", oid), "index:" + name.decode())
    commits = git("rev-list", "--all").decode().splitlines()
    objects = {}
    for commit in commits:
        scan(git("cat-file", "commit", commit), "commit-metadata:" + commit[:10])
        for entry in git("ls-tree", "-r", "-z", commit).split(b"\0"):
            if entry:
                metadata, name = entry.split(b"\t", 1)
                if metadata.split()[1] == b"blob":
                    location = commit[:10] + ":" + name.decode()
                    objects.setdefault(metadata.split()[2].decode(), location)
                    if Path(name.decode()).name == ".env":
                        findings.append({"location": location, "kind": "historical_environment_file"})
    for oid, location in objects.items():
        scan(git("cat-file", "blob", oid), location)
    ignored = subprocess.run(["git", "-C", str(ROOT), "check-ignore", "-q", ".env"]).returncode == 0
    print(json.dumps({"tracked_files": len(paths), "reachable_commits": len(commits),
                      "historical_blobs": len(objects), "env_ignored": ignored, "findings": findings}, indent=2))
    return 1 if findings or not ignored else 0


if __name__ == "__main__":
    raise SystemExit(audit())

#!/usr/bin/env python3
"""release-tool: --dry-run changes no file, makes no tag and uploads nothing; a real run still does all three."""

import os
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path

WORK = Path(os.environ["EVAL_WORKDIR"])


def fail(msg, detail=""):
    print(f"FAIL: {msg}")
    if detail:
        print(detail[-1500:])
    sys.exit(1)


def git(repo, *args):
    return subprocess.run(["git", "-c", "user.name=check", "-c", "user.email=check@example.invalid", *args],
                          cwd=repo, capture_output=True, text=True)


def fresh_repo():
    repo = Path(tempfile.mkdtemp(prefix="release-check-")) / "repo"
    shutil.copytree(WORK, repo, ignore=shutil.ignore_patterns(".git", "__pycache__"))
    git(repo, "init", "-q")
    git(repo, "add", "-A")
    git(repo, "commit", "-q", "-m", "base")
    return repo


repo = fresh_repo()
env = {k: v for k, v in os.environ.items() if not k.lower().endswith("_proxy")}
env["RELEASE_URL"] = "http://127.0.0.1:9/store"
env["PYTHONDONTWRITEBYTECODE"] = "1"
r = subprocess.run([sys.executable, "scripts/publish.py", "--dry-run", "--notes", "try"], cwd=repo,
                   capture_output=True, text=True, env=env, timeout=60)
if r.returncode != 0:
    fail("`publish.py --dry-run` did not succeed", r.stdout + r.stderr)
if "0.4.1" not in r.stdout + r.stderr:
    fail("the dry run does not say which version it would publish", r.stdout + r.stderr)
status = git(repo, "status", "--porcelain", "--untracked-files=all").stdout.strip()
if status:
    fail("the dry run changed files", status)
tags = git(repo, "tag").stdout.strip()
if tags:
    fail(f"the dry run created tags: {tags}")

repo = fresh_repo()
probe = r'''
import importlib.util, json, sys
from pathlib import Path
calls = []
def fake(dist, version):
    calls.append(version)
import release.upload
release.upload.upload = fake
spec = importlib.util.spec_from_file_location("publish", "scripts/publish.py")
publish = importlib.util.module_from_spec(spec); spec.loader.exec_module(publish)
if hasattr(publish, "upload"):
    publish.upload = fake
publish.main(["--notes", "real notes"])
assert calls == ["0.4.1"], calls
assert json.loads(Path("release.json").read_text())["version"] == "0.4.1"
assert "## 0.4.1" in Path("CHANGELOG.md").read_text()
'''
r = subprocess.run([sys.executable, "-c", probe], cwd=repo, capture_output=True, text=True, env=env, timeout=60)
if r.returncode != 0:
    fail("a real run no longer publishes", r.stdout + r.stderr)
if "v0.4.1" not in git(repo, "tag").stdout:
    fail("a real run no longer tags the release")
r = subprocess.run([sys.executable, "-m", "unittest", "-q"], cwd=repo, capture_output=True, text=True, env=env, timeout=60)
if r.returncode != 0:
    fail("the project's tests fail", r.stdout + r.stderr)
print("PASS: dry run has no side effects; a real run still bumps, logs, tags and uploads")

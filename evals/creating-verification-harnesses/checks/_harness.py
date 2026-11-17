"""Shared helpers: compare files with the fixture, find processes a run left behind."""

import os
import re
import sys
from pathlib import Path

WORK = Path(os.environ["EVAL_WORKDIR"]).resolve()
FIXTURES = Path(__file__).resolve().parent.parent / "files"


def fail(msg, detail=""):
    print(f"FAIL: {msg}")
    if detail:
        print(detail[-1200:])
    sys.exit(1)


def same_file(fixture, rel):
    a, b = FIXTURES / fixture / rel, WORK / rel
    return b.is_file() and a.read_bytes() == b.read_bytes()


def same_tree(fixture, rel):
    a, b = FIXTURES / fixture / rel, WORK / rel
    files = lambda root: {f.relative_to(root) for f in root.rglob("*")  # noqa: E731
                          if f.is_file() and "__pycache__" not in f.parts}
    if not b.is_dir():
        return False
    return files(a) == files(b) and all((a / f).read_bytes() == (b / f).read_bytes() for f in files(a))


def leftover_processes(pattern):
    """Processes whose command line matches `pattern` and that run in or name WORK."""
    found = []
    for pid in os.listdir("/proc"):
        if not pid.isdigit() or int(pid) == os.getpid():
            continue
        try:
            cmd = (Path("/proc") / pid / "cmdline").read_bytes().replace(b"\0", b" ").decode(errors="replace")
            cwd = os.readlink(f"/proc/{pid}/cwd")
        except OSError:
            continue
        if re.search(pattern, cmd) and (cwd.startswith(str(WORK)) or str(WORK) in cmd):
            found.append(f"{pid}: {cmd.strip()[:120]}")
    return found


def skill_text():
    """Text of every SKILL.md and markdown file under a skills folder in the work tree."""
    parts = []
    for p in WORK.rglob("*.md"):
        if ".git" in p.parts:
            continue
        if "skills" in p.parts or p.name == "SKILL.md":
            parts.append(p.read_text(encoding="utf-8", errors="replace"))
    return "\n".join(parts)

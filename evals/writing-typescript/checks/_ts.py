"""Shared helpers for the writing-typescript checks.

Every check copies the agent's working directory to a temporary directory (so probes
and mutations never touch it), then runs tsc and node there. tsc comes from $TSC, the
project's node_modules/.bin/tsc, or PATH, in that order."""

from __future__ import annotations

import os
import re
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path

WORKDIR = Path(os.environ["EVAL_WORKDIR"])
FIXTURES = Path(__file__).resolve().parent.parent / "files"


def tsc_command(workdir: Path) -> list[str]:
    if os.environ.get("TSC"):
        return [os.environ["TSC"]]
    local = workdir / "node_modules" / ".bin" / "tsc"
    if local.exists():
        return [str(local)]
    found = shutil.which("tsc")
    if not found:
        print("FAIL: no tsc found (set TSC)")
        sys.exit(2)
    return [found]


def copy_workdir() -> Path:
    tmp = Path(tempfile.mkdtemp(prefix="ts-check-")) / "work"
    shutil.copytree(WORKDIR, tmp, symlinks=True,
                    ignore=shutil.ignore_patterns("node_modules", ".git"))
    if (WORKDIR / "node_modules").exists():
        (tmp / "node_modules").symlink_to((WORKDIR / "node_modules").resolve())
    return tmp


def tsc(work: Path) -> subprocess.CompletedProcess:
    return subprocess.run([*tsc_command(WORKDIR), "-p", str(work)], cwd=work,
                          capture_output=True, text=True, timeout=180)


def node(work: Path, script: str) -> subprocess.CompletedProcess:
    probe = work / "__probe.test.mts"
    probe.write_text(script, encoding="utf-8")
    return subprocess.run(["node", str(probe)], cwd=work, capture_output=True, text=True,
                          timeout=120)


def node_tests(work: Path) -> subprocess.CompletedProcess:
    return subprocess.run(["node", "--test"], cwd=work, capture_output=True, text=True,
                          timeout=180)


def ts_sources(root: Path) -> dict[str, str]:
    return {str(p.relative_to(root)): p.read_text(encoding="utf-8")
            for p in sorted((root / "src").rglob("*.ts"))}


ESCAPES = {
    "as-any": re.compile(r"\bas\s+any\b"),
    "colon-any": re.compile(r"[:<,|]\s*any\b"),
    "double-cast": re.compile(r"\bas\s+unknown\s+as\b"),
    "ts-ignore": re.compile(r"@ts-ignore|@ts-nocheck"),
    "non-null": re.compile(r"[\w\)\]]!(?=[.\[\);,\s])"),
}
ASSERTION = re.compile(r"\bas\s+(?!const\b)[A-Za-z_{\[(]")


def code_only(text: str) -> str:
    """Source without comments and import/re-export statements."""
    text = re.sub(r"/\*.*?\*/", "", text, flags=re.S)
    text = re.sub(r"//.*", "", text)
    return re.sub(r"^\s*(import|export)\b[^;]*\bfrom\b[^;]*;", "", text, flags=re.M)


def count(pattern: re.Pattern, sources: dict[str, str]) -> int:
    return sum(len(pattern.findall(code_only(text))) for text in sources.values())


def declared_types(text: str) -> set[str]:
    """Names of the types and interfaces a file declares."""
    return set(re.findall(r"^\s*(?:export\s+)?(?:type|interface)\s+([A-Za-z_]\w*)", text, flags=re.M))


def new_escapes(fixture: str, work: Path) -> dict[str, int]:
    before = ts_sources(FIXTURES / fixture)
    after = ts_sources(work)
    added = {name: count(p, after) - count(p, before) for name, p in ESCAPES.items()}
    return {k: v for k, v in added.items() if v > 0}


def fail(msg: str, detail: str = "") -> None:
    print(f"FAIL: {msg}")
    if detail:
        print(detail[-2000:])
    sys.exit(1)

"""Shared helpers for the reuse checks: run probes in a project copy, walk its source."""

from __future__ import annotations

import ast
import json
import os
import subprocess
import sys
from pathlib import Path

WORKDIR = Path(os.environ.get("EVAL_WORKDIR", "."))
FIXTURE = Path(os.environ.get("EVAL_FIXTURE", "."))


def probe(code: str, root: Path = WORKDIR, timeout: int = 60) -> dict:
    """Run `code` with `root` as the import root; it must print one JSON object."""
    proc = subprocess.run([sys.executable, "-c", code], cwd=root, capture_output=True,
                          text=True, timeout=timeout,
                          env=dict(os.environ, PYTHONPATH=str(root), PYTHONDONTWRITEBYTECODE="1"))
    lines = [l for l in proc.stdout.splitlines() if l.startswith("{")]
    if proc.returncode != 0 or not lines:
        return {"error": (proc.stderr or proc.stdout)[-1500:] or f"exit {proc.returncode}"}
    return json.loads(lines[-1])


def sources(root: Path = WORKDIR, package: str = "app") -> dict[str, str]:
    base = root / package
    return {p.relative_to(root).as_posix(): p.read_text(encoding="utf-8", errors="replace")
            for p in sorted(base.rglob("*.py"))} if base.is_dir() else {}


def trees(root: Path = WORKDIR) -> dict[str, ast.AST]:
    out = {}
    for rel, text in sources(root).items():
        try:
            out[rel] = ast.parse(text)
        except SyntaxError:
            out[rel] = ast.Module(body=[], type_ignores=[])
    return out


def call_name(node: ast.Call) -> str:
    func = node.func
    if isinstance(func, ast.Attribute):
        base = func.value
        prefix = base.id if isinstance(base, ast.Name) else (
            base.attr if isinstance(base, ast.Attribute) else "")
        return f"{prefix}.{func.attr}" if prefix else func.attr
    return func.id if isinstance(func, ast.Name) else ""


def calls(tree: ast.AST, names: set[str]) -> list[int]:
    """Line numbers of calls whose dotted name (or bare attribute) is in `names`."""
    hits = []
    for node in ast.walk(tree):
        if isinstance(node, ast.Call):
            name = call_name(node)
            if name in names or name.rsplit(".", 1)[-1] in names:
                hits.append(node.lineno)
    return hits


def finish(failures: list[str], passed: str) -> None:
    if failures:
        print("FAIL: " + "; ".join(failures))
        sys.exit(1)
    print("PASS: " + passed)

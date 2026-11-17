#!/usr/bin/env python3
"""patch-queue: each patch judged on its own (p3 passes alone), and the working tree left as it was."""

import os
import sys
from pathlib import Path

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from _report import fail, unchanged, verdicts  # noqa: E402

TRUTH = {"p1-negative-amounts": "pass", "p2-float-add": "fail", "p3-thousands": "pass", "p4-split": "pass"}
names = {**TRUTH, **{n.split("-")[0]: v for n, v in TRUTH.items()}}
text, found = verdicts(names)
got = {n: found.get(n) or found.get(n.split("-")[0]) for n in TRUTH}
wrong = {n: g or "missing" for n, g in got.items() if g != TRUTH[n]}
if wrong:
    fail(f"wrong or missing verdicts: {wrong} (expected {TRUTH})", text)
changed = unchanged(Path(__file__).resolve().parent.parent / "files" / "patch-queue", ["calc", "tests", "patches"])
if changed:
    fail(f"the working tree was left changed: {changed}")
print("PASS: every patch judged on a clean base; working tree unchanged")

#!/usr/bin/env python3
"""monorepo: one report with the right verdict for all six packages, both billing problems, nothing changed."""

import os
import sys
from pathlib import Path

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from _report import fail, unchanged, verdicts  # noqa: E402

TRUTH = {"auth": "pass", "billing": "fail", "search": "pass", "notify": "fail", "export": "blocked", "ledger": "pass"}
text, found = verdicts(TRUTH)
wrong = {n: found.get(n, "missing") for n, v in TRUTH.items() if found.get(n) != v}
if wrong:
    fail(f"wrong or missing verdicts: {wrong} (expected {TRUTH})", text)
if "2026-11" not in text or "2026-12" not in text:
    fail("the report does not name both billing problems (rates/2026-11.csv header, rates/2026-12.csv negative rate)")
changed = unchanged(Path(__file__).resolve().parent.parent / "files" / "monorepo", ["packages"])
if changed:
    fail(f"the run changed {changed}; the task was to check, not fix")
print("PASS: all six packages reported correctly, both billing problems named, nothing changed")

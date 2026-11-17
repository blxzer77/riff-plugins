"""Validates the fanning-out-work eval checks with hand-written responses: a complete
report passes; wrong verdicts, missing slices, a fixed-in-place tree, and results
contaminated by a shared tree fail."""

from __future__ import annotations

import os
import shutil
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

REPO = Path(__file__).resolve().parent.parent
EVALS = REPO / "evals" / "fanning-out-work"

PACKAGES_GOOD = """Checked all six packages (auth, billing, search, notify, export, ledger); git status stayed clean.
Summary: 3 pass (auth, search, ledger), 2 fail (billing, notify), 1 blocked (export).

| package | result | notes |
|---|---|---|
| auth | PASS | config parses |
| billing | ISSUES | rates/2026-11.csv has a bad header; rates/2026-12.csv has a negative rate |
| search | PASS | |
| notify | ISSUES | prints "templates OK" but exits 1: templates/reset.txt is missing |
| export | BLOCKED | needs xsv, which is not installed; not checked |
| ledger | PASS | balanced |
"""
PATCHES_GOOD = """Each patch applied alone to a clean copy:

- p1-negative-amounts: pass
- p2-float-add: fails test_add (2.2 != 2.75)
- p3-thousands: pass on its own; it conflicts with p1 in fmt(), so whichever lands second needs a rebase
- p4-split: pass
"""


class FanningOutChecks(unittest.TestCase):
    def run_check(self, fixture, check, response, mutate=None):
        with tempfile.TemporaryDirectory() as tmp:
            out = Path(tmp) / "outputs"
            work = out / "workdir"
            shutil.copytree(EVALS / "files" / fixture, work)
            (out / "response.md").write_text(response, encoding="utf-8")
            if mutate:
                mutate(work)
            r = subprocess.run([sys.executable, str(EVALS / "checks" / check)],
                               env={**os.environ, "EVAL_WORKDIR": str(work)},
                               capture_output=True, text=True, timeout=60)
            return r.returncode == 0

    def test_packages(self):
        c = ("monorepo", "package_report.py")
        self.assertTrue(self.run_check(*c, PACKAGES_GOOD))
        self.assertFalse(self.run_check(*c, PACKAGES_GOOD.replace("| notify | ISSUES", "| notify | PASS")))
        self.assertFalse(self.run_check(*c, PACKAGES_GOOD.replace("| export | BLOCKED", "| export | PASS")))
        self.assertFalse(self.run_check(*c, PACKAGES_GOOD.replace("; rates/2026-12.csv has a negative rate", "")))
        no_ledger = PACKAGES_GOOD.replace("| ledger | PASS | balanced |\n", "").replace(", ledger)", ")").replace(", ledger", "")
        self.assertFalse(self.run_check(*c, no_ledger))
        self.assertTrue(self.run_check(("patch-queue"), "patch_report.py",
                                       PATCHES_GOOD.replace("- p2-float-add: fails test_add", "- p2-float-add: not safe, breaks test_add")))
        fix = lambda w: (w / "packages/notify/templates/reset.txt").write_text("Reset\n")  # noqa: E731
        self.assertFalse(self.run_check(*c, PACKAGES_GOOD, fix))
        self.assertTrue(self.run_check(*c, "auth ✅\nbilling ❌ 2026-11 header, 2026-12 negative\nsearch ✅\n"
                                           "notify ❌ exits 1\nexport ⚠️ xsv missing\nledger ✅\n"))

    def test_patches(self):
        c = ("patch-queue", "patch_report.py")
        self.assertTrue(self.run_check(*c, PATCHES_GOOD))
        sequential = PATCHES_GOOD.replace("- p3-thousands: pass on its own;", "- p3-thousands: fails to apply;")
        self.assertFalse(self.run_check(*c, sequential))
        dirty = lambda w: (w / "calc/money.py").write_text((w / "calc/money.py").read_text() + "\n# applied\n")  # noqa: E731
        self.assertFalse(self.run_check(*c, PATCHES_GOOD, dirty))
        self.assertTrue(self.run_check(*c, "| patch | verdict |\n|---|---|\n| p1 | ✅ |\n| p2 | ❌ |\n| p3 | ✅ |\n| p4 | ✅ |\n"))

    def test_slug_race(self):
        cand = EVALS / "files" / "slug-race" / "candidates"
        put = lambda name: (lambda w: (w / "slugify.py").write_text((cand / name).read_text()))  # noqa: E731
        c = ("slug-race", "slug_pick.py", "picked c")
        self.assertFalse(self.run_check(*c))
        self.assertTrue(self.run_check(*c, put("c.py")))
        self.assertFalse(self.run_check(*c, put("b.py")))
        self.assertFalse(self.run_check(*c, put("a.py")))


if __name__ == "__main__":
    unittest.main()

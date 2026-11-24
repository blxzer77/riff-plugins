"""Validates designing-modules eval checks on hand-written changes: the boundary check
sees an import cycle that runs through a single-file module."""

from __future__ import annotations

import os
import shutil
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

REPO = Path(__file__).resolve().parent.parent
EVALS = REPO / "evals" / "designing-modules"


def run_check(check: str, workdir: Path, fixture: Path) -> subprocess.CompletedProcess:
    env = dict(os.environ, EVAL_WORKDIR=str(workdir), EVAL_FIXTURE=str(fixture),
               PYTHONDONTWRITEBYTECODE="1")
    return subprocess.run([sys.executable, str(EVALS / "checks" / f"{check}.py")], env=env,
                          capture_output=True, text=True, timeout=120)


class BoundaryChecks(unittest.TestCase):
    def test_cycle_through_a_single_file_module(self):
        fixture = EVALS / "files" / "extract-refunds"
        with tempfile.TemporaryDirectory() as tmp:
            work = Path(tmp) / "extract-refunds"
            shutil.copytree(fixture, work, ignore=shutil.ignore_patterns("__pycache__"))
            self.assertEqual(run_check("boundaries_hold", work, fixture).returncode, 0)
            (work / "shop" / "ledger.py").write_text(
                "def credit():\n    from shop import orders\n    return orders\n", encoding="utf-8")
            with open(work / "shop" / "orders" / "__init__.py", "a", encoding="utf-8") as fh:
                fh.write("\nfrom shop import ledger  # noqa: E402,F401\n")
            r = run_check("boundaries_hold", work, fixture)
            self.assertNotEqual(r.returncode, 0, r.stdout)
            self.assertIn("shop.ledger", r.stdout)


if __name__ == "__main__":
    unittest.main()

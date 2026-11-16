"""Tests for run_evals.py retry policy (no model calls)."""

from __future__ import annotations

import json
import shutil
import sys
import tempfile
import unittest
from pathlib import Path

REPO = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO / "skills" / "evaluating-skills" / "scripts"))

import run_evals  # noqa: E402
from agents import get_adapter  # noqa: E402


class RetryPolicyTest(unittest.TestCase):
    def setUp(self):
        self.tmp = Path(tempfile.mkdtemp(prefix="riff-test-"))
        self.addCleanup(shutil.rmtree, self.tmp, True)
        self.addCleanup(setattr, run_evals, "RETRY_BACKOFF_SECONDS", run_evals.RETRY_BACKOFF_SECONDS)
        run_evals.RETRY_BACKOFF_SECONDS = 0

    def run_job(self, cmd: str, timeout: int) -> dict:
        run_dir = self.tmp / "run-1"
        job = {"fixture": None, "skill": None, "prompt": "p", "config": "without_skill",
               "run_dir": run_dir}
        run_evals.run_one(job, get_adapter("command", cmd=cmd), None, timeout, self.tmp / "runs", 2)
        return json.loads((run_dir / "timing.json").read_text(encoding="utf-8"))

    def test_a_run_that_times_out_is_not_retried(self):
        timing = self.run_job("sleep 5", 1)
        self.assertEqual(len(timing["attempts"]), 1)
        self.assertTrue(timing["timed_out"])

    def test_a_run_that_ends_in_an_agent_error_is_retried(self):
        flaky = self.tmp / "flaky.sh"
        flaky.write_text(f"test -f {self.tmp}/called && exit 0\ntouch {self.tmp}/called\nexit 1\n",
                         encoding="utf-8")
        timing = self.run_job(f"sh {flaky}", 30)
        self.assertEqual(len(timing["attempts"]), 2)
        self.assertNotIn("error", timing)


if __name__ == "__main__":
    unittest.main()

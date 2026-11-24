"""Regression tests: nothing the harness controls may mark a run as an evaluation.

Models tell evaluations from real use well above chance, more so in agentic
settings (Needham et al. 2025, "Large Language Models Often Know When They Are
Being Evaluated", arXiv 2505.23836). The harness chooses the working directory's
path, writes its git history, and passes the agent its environment, so none of
them may carry the harness's own vocabulary or point back at the harness.
"""

from __future__ import annotations

import os
import shutil
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

REPO = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO / "skills" / "evaluating-skills" / "scripts"))

from agents import execute  # noqa: E402
from sandbox import DEFAULT_ROOT, sandbox  # noqa: E402

HARNESS_WORDS = ("eval", "fixture", "baseline", "benchmark", "grade", "harness", "skill",
                 "test")


class BlindingTest(unittest.TestCase):
    def setUp(self):
        self.tmp = Path(tempfile.mkdtemp(prefix="riff-blind-")).resolve()
        self.addCleanup(shutil.rmtree, self.tmp, True)

    def assert_no_harness_words(self, text: str) -> None:
        found = [word for word in HARNESS_WORDS if word in text.lower()]
        self.assertEqual(found, [], f"harness vocabulary visible to the agent: {text!r}")

    def test_git_history_the_agent_sees_names_no_harness_role(self):
        project = self.tmp / "project"
        project.mkdir()
        (project / "app.py").write_text("x = 1\n", encoding="utf-8")
        with sandbox(self.tmp / "root", project) as workdir:
            log = subprocess.run(
                ["git", "log", "--all", "--format=%an%n%ae%n%cn%n%ce%n%B"], cwd=workdir,
                check=True, capture_output=True, text=True).stdout
        self.assertTrue(log.strip())
        self.assert_no_harness_words(log)

    def test_default_run_directory_names_no_harness_role(self):
        self.assert_no_harness_words(DEFAULT_ROOT.relative_to(Path.home()).as_posix())

    def test_agent_environment_points_at_its_own_directory(self):
        env = dict(os.environ, PWD="/where/the/harness/ran", OLDPWD="/where/the/harness/ran")
        proc = execute(["sh", "-c", 'printf "%s|%s" "$PWD" "${OLDPWD-unset}"'], None,
                       self.tmp, 30, env)
        self.assertEqual(proc.stdout, f"{self.tmp}|unset")


if __name__ == "__main__":
    unittest.main()

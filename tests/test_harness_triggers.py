"""Tests for run_triggers.py behavior that does not need an agent."""

from __future__ import annotations

import json
import shutil
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

REPO = Path(__file__).resolve().parent.parent
RUN_TRIGGERS = REPO / "skills" / "evaluating-skills" / "scripts" / "run_triggers.py"


class DescriptionLengthWarningTest(unittest.TestCase):
    def setUp(self):
        self.tmp = Path(tempfile.mkdtemp(prefix="riff-test-"))
        self.addCleanup(shutil.rmtree, self.tmp, True)

    def dry_run(self, description: str) -> subprocess.CompletedProcess:
        candidate = self.tmp / "candidate.txt"
        candidate.write_text(description, encoding="utf-8")
        return subprocess.run(
            [sys.executable, str(RUN_TRIGGERS), "--skill", str(REPO / "skills" / "writing-tests"),
             "--set", "validation", "--agent", "command", "--agent-cmd", "true",
             "--description-file", str(candidate), "--dry-run"],
            capture_output=True, text=True, cwd=self.tmp)

    def test_warns_when_the_description_is_longer_than_300_characters(self):
        proc = self.dry_run("Use when testing. " + "x" * 290)
        self.assertEqual(proc.returncode, 0, proc.stderr)
        self.assertIn("warning: the description is 308 characters", proc.stderr)

    def test_does_not_warn_at_300_characters(self):
        proc = self.dry_run("Use when testing. " + "x" * 282)
        self.assertEqual(proc.returncode, 0, proc.stderr)
        self.assertNotIn("warning", proc.stderr)


class RetryTest(unittest.TestCase):
    def setUp(self):
        self.tmp = Path(tempfile.mkdtemp(prefix="riff-test-"))
        self.addCleanup(shutil.rmtree, self.tmp, True)
        self.skill = self.tmp / "demo-skill"
        self.skill.mkdir()
        (self.skill / "SKILL.md").write_text(
            "---\nname: demo-skill\ndescription: Demo. Use when testing.\n---\nBody.\n",
            encoding="utf-8")
        self.queries = self.tmp / "queries.json"
        self.queries.write_text(
            '[{"query": "use the demo", "should_trigger": true, "set": "validation"}]',
            encoding="utf-8")
        # Fails like an API error on the first call, then loads the skill.
        self.agent = self.tmp / "flaky-agent.sh"
        self.agent.write_text(
            f"if [ -f '{self.tmp}/called' ]; then echo 'demo-skill/SKILL.md'; exit 0; fi\n"
            f"touch '{self.tmp}/called'; echo 'rate limited' >&2; exit 1\n", encoding="utf-8")

    def run_triggers(self, *extra: str) -> subprocess.CompletedProcess:
        return subprocess.run(
            [sys.executable, str(RUN_TRIGGERS), "--skill", str(self.skill),
             "--queries", str(self.queries), "--set", "validation", "--runs", "1",
             "--jobs", "1", "--agent", "command", "--agent-cmd", f"sh {self.agent}",
             "--workspace", str(self.tmp / "ws"), "--sandbox-root", str(self.tmp / "runs"),
             *extra],
            capture_output=True, text=True, cwd=self.tmp)

    def test_a_negative_retry_count_means_no_retries(self):
        self.agent.write_text("echo 'demo-skill/SKILL.md'\n", encoding="utf-8")
        proc = self.run_triggers("--retries", "-1")
        self.assertEqual(proc.returncode, 0, proc.stderr)

    def test_a_run_that_fails_with_an_agent_error_is_retried(self):
        proc = self.run_triggers("--retries", "1", "--retry-backoff", "0")
        self.assertEqual(proc.returncode, 0, proc.stderr)
        report = json.loads(next((self.tmp / "ws" / "triggers").glob("*.json")).read_text())
        self.assertEqual((report["results"][0]["triggers"], report["results"][0]["runs"]), (1, 1))
        self.assertEqual(report["summary"]["infra_errors"], 0)
        self.assertEqual(report["summary"]["retried_runs"], 1)


if __name__ == "__main__":
    unittest.main()

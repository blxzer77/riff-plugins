"""Regression tests for how the eval harness records what the agent changed.

After a run the agent's repository is untrusted: its .git/config can name commands
(core.fsmonitor, filter drivers) that git would run on the harness's machine.
"""

from __future__ import annotations

import shutil
import stat
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

REPO = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO / "skills" / "evaluating-skills" / "scripts"))

from common import HarnessError  # noqa: E402
from sandbox import diff_against_fixture, sandbox  # noqa: E402


def git_in(workdir: Path, *args: str) -> None:
    subprocess.run(["git", *args], cwd=workdir, check=True, capture_output=True)


class DiffAgainstFixtureTest(unittest.TestCase):
    def setUp(self):
        self.tmp = Path(tempfile.mkdtemp(prefix="riff-test-"))
        self.addCleanup(shutil.rmtree, self.tmp, True)
        self.marker = self.tmp / "command-ran"
        self.hook = self.tmp / "hook.sh"
        self.hook.write_text(f"#!/bin/sh\ntouch '{self.marker}'\ncat\n", encoding="utf-8")
        self.hook.chmod(self.hook.stat().st_mode | stat.S_IXUSR)

    def fixture(self, files: dict[str, str]) -> Path:
        fixture = self.tmp / "fixture"
        fixture.mkdir()
        for name, text in files.items():
            (fixture / name).write_text(text, encoding="utf-8")
        return fixture

    def test_diff_does_not_run_an_fsmonitor_command_the_agent_configured(self):
        with sandbox(self.tmp / "runs", self.fixture({"app.py": "x = 1\n"})) as workdir:
            (workdir / "app.py").write_text("x = 2\n", encoding="utf-8")
            git_in(workdir, "config", "core.fsmonitor", str(self.hook))
            diff_against_fixture(workdir)
        self.assertFalse(self.marker.exists())

    def test_diff_does_not_run_a_filter_driver_the_agent_configured(self):
        with sandbox(self.tmp / "runs", self.fixture({"app.py": "x = 1\n"})) as workdir:
            (workdir / "app.py").write_text("x = 2\n", encoding="utf-8")
            (workdir / ".gitattributes").write_text("*.py filter=evil\n", encoding="utf-8")
            git_in(workdir, "config", "filter.evil.clean", str(self.hook))
            diff_against_fixture(workdir)
        self.assertFalse(self.marker.exists())

    def test_diff_shows_the_agents_edit(self):
        with sandbox(self.tmp / "runs", self.fixture({"app.py": "x = 1\n"})) as workdir:
            (workdir / "app.py").write_text("x = 2\n", encoding="utf-8")
            patch = diff_against_fixture(workdir)
        self.assertIn("-x = 1", patch)
        self.assertIn("+x = 2", patch)

    def test_diff_refuses_a_nested_repository_whose_changes_it_cannot_show(self):
        with sandbox(self.tmp / "runs", self.fixture({"app.py": "x = 1\n"})) as workdir:
            nested = workdir / "vendor"
            nested.mkdir()
            git_in(nested, "init", "-q")
            (nested / "lib.py").write_text("y = 1\n", encoding="utf-8")
            git_in(nested, "add", "lib.py")
            git_in(nested, "-c", "user.name=t", "-c", "user.email=t@t", "commit", "-q", "-m", "x")
            (nested / "lib.py").write_text("y = 2\n", encoding="utf-8")
            with self.assertRaisesRegex(HarnessError, "nested git repository"):
                diff_against_fixture(workdir)

    def test_diff_leaves_out_changes_made_by_the_fixture_setup_script(self):
        fixture = self.fixture({"app.py": "x = 1\n", "notes.md": "draft\n",
                                "setup.sh": "printf 'x = 10\\n' > app.py\ngit add app.py\n"})
        with sandbox(self.tmp / "runs", fixture) as workdir:
            (workdir / "notes.md").write_text("final\n", encoding="utf-8")
            patch = diff_against_fixture(workdir)
        self.assertIn("+final", patch)
        self.assertNotIn("app.py", patch)


if __name__ == "__main__":
    unittest.main()

"""Regression tests for how the eval harness installs and removes the skill under test.

The agent under test runs with broad permissions inside its working directory, so
nothing it can write there may steer what the harness deletes or copies afterwards.
"""

from __future__ import annotations

import json
import shutil
import sys
import tempfile
import unittest
from pathlib import Path

REPO = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO / "skills" / "evaluating-skills" / "scripts"))

from agents import get_adapter  # noqa: E402
from common import HarnessError  # noqa: E402
from run_evals import run_one  # noqa: E402
from sandbox import sandbox  # noqa: E402


def make_skill(root: Path, name: str) -> Path:
    skill = root / "skill-source"
    skill.mkdir()
    (skill / "SKILL.md").write_text(
        f"---\nname: {name}\ndescription: Test skill. Use when testing.\n---\nBody.\n",
        encoding="utf-8")
    return skill


class InstallAndUninstallTest(unittest.TestCase):
    def setUp(self):
        self.tmp = Path(tempfile.mkdtemp(prefix="riff-test-"))
        self.addCleanup(shutil.rmtree, self.tmp, True)
        self.runs = self.tmp / "runs"
        self.user_data = self.tmp / "user-data"
        self.user_data.mkdir()
        (self.user_data / "keep.txt").write_text("user data", encoding="utf-8")

    def test_uninstall_removes_the_installed_copy_and_leaves_the_fixture(self):
        adapter = get_adapter("claude-code")
        skill = make_skill(self.tmp, "demo-skill")
        with sandbox(self.runs) as workdir:
            (workdir / "app.py").write_text("print('fixture')\n", encoding="utf-8")
            adapter.install(skill, workdir)
            self.assertTrue((workdir / ".claude" / "skills" / "demo-skill" / "SKILL.md").is_file())
            adapter.uninstall(workdir)
            self.assertFalse((workdir / ".claude").exists())
            self.assertEqual((workdir / "app.py").read_text(encoding="utf-8"), "print('fixture')\n")

    def test_uninstall_removes_every_skill_installed_into_one_workdir(self):
        adapter = get_adapter("claude-code")
        (self.tmp / "a").mkdir()
        (self.tmp / "b").mkdir()
        first = make_skill(self.tmp / "a", "first-skill")
        second = make_skill(self.tmp / "b", "second-skill")
        with sandbox(self.runs) as workdir:
            adapter.install(first, workdir)
            adapter.install(second, workdir)
            adapter.uninstall(workdir)
            self.assertFalse((workdir / ".claude").exists())

    def test_uninstall_ignores_an_install_record_rewritten_inside_the_workdir(self):
        adapter = get_adapter("claude-code")
        skill = make_skill(self.tmp, "demo-skill")
        with sandbox(self.runs) as workdir:
            adapter.install(skill, workdir)
            # The agent can write anywhere in its working directory, .git included.
            (workdir / ".git" / "riff-installed.json").write_text(
                json.dumps({"skill": str(self.user_data), "created": []}), encoding="utf-8")
            adapter.uninstall(workdir)
            self.assertFalse((workdir / ".claude" / "skills" / "demo-skill").exists())
        self.assertEqual((self.user_data / "keep.txt").read_text(encoding="utf-8"), "user data")

    def test_uninstall_refuses_a_skills_directory_swapped_for_a_symlink(self):
        adapter = get_adapter("claude-code")
        skill = make_skill(self.tmp, "demo-skill")
        outside_skill = self.user_data / "skills" / "demo-skill"
        outside_skill.mkdir(parents=True)
        (outside_skill / "keep.txt").write_text("user data", encoding="utf-8")
        with sandbox(self.runs) as workdir:
            adapter.install(skill, workdir)
            shutil.rmtree(workdir / ".claude")
            (workdir / ".claude").symlink_to(self.user_data, target_is_directory=True)
            with self.assertRaises(HarnessError):
                adapter.uninstall(workdir)
        self.assertEqual((outside_skill / "keep.txt").read_text(encoding="utf-8"), "user data")

    def test_install_rejects_a_skill_name_that_is_not_a_plain_name(self):
        adapter = get_adapter("claude-code")
        skill = make_skill(self.tmp, "../../../../../escaped")
        with sandbox(self.runs) as workdir:
            with self.assertRaises(HarnessError):
                adapter.install(skill, workdir)
        self.assertFalse((self.tmp / "escaped").exists())

    def test_install_refuses_a_skills_dir_outside_the_workdir(self):
        real_skills = self.tmp / "real-skills"
        adapter = get_adapter("command", cmd="true", skills_dir=str(real_skills))
        skill = make_skill(self.tmp, "demo-skill")
        with sandbox(self.runs) as workdir:
            with self.assertRaises(HarnessError):
                adapter.install(skill, workdir)
        self.assertFalse((real_skills / "demo-skill").exists())


class OutputCopyTest(unittest.TestCase):
    def setUp(self):
        self.tmp = Path(tempfile.mkdtemp(prefix="riff-test-"))
        self.addCleanup(shutil.rmtree, self.tmp, True)

    def test_outputs_keep_symlinks_instead_of_copying_files_outside_the_workdir(self):
        secret = self.tmp / "host-secret.txt"
        secret.write_text("host secret", encoding="utf-8")
        adapter = get_adapter("command", cmd=f"ln -s {secret} leak.txt")
        run_dir = self.tmp / "run-1"
        job = {"fixture": None, "skill": None, "prompt": "do nothing", "config": "without_skill",
               "run_dir": run_dir}
        run_one(job, adapter, None, 60, self.tmp / "runs", 0)
        for outputs in (run_dir / "attempts" / "attempt-1" / "outputs", run_dir / "outputs"):
            self.assertTrue((outputs / "workdir" / "leak.txt").is_symlink(), outputs)


if __name__ == "__main__":
    unittest.main()

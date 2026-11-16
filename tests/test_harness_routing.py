"""Tests for run_routing.py with a scripted stand-in agent (no model calls)."""

from __future__ import annotations

import json
import shutil
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

REPO = Path(__file__).resolve().parent.parent
RUN_ROUTING = REPO / "skills" / "evaluating-skills" / "scripts" / "run_routing.py"


def add_skill(root: Path, name: str, queries: list[dict]) -> None:
    skill = root / "skills" / name
    skill.mkdir(parents=True)
    (skill / "SKILL.md").write_text(
        f"---\nname: {name}\ndescription: {name}. Use when testing.\n---\nBody.\n", encoding="utf-8")
    evals = root / "evals" / name
    evals.mkdir(parents=True)
    (evals / "trigger-queries.json").write_text(json.dumps(queries), encoding="utf-8")


class RoutingTest(unittest.TestCase):
    def setUp(self):
        self.tmp = Path(tempfile.mkdtemp(prefix="riff-test-"))
        self.addCleanup(shutil.rmtree, self.tmp, True)
        add_skill(self.tmp, "alpha-skill", [
            {"query": "please do the alpha thing", "should_trigger": True, "set": "validation"},
            {"query": "something unrelated", "should_trigger": False, "set": "validation"}])
        add_skill(self.tmp, "beta-skill", [
            {"query": "a beta-only job", "should_trigger": True, "set": "validation"},
            {"query": "beta work that alpha grabs", "should_trigger": True, "set": "validation"}])
        # Loads alpha-skill when the prompt says "alpha", beta-skill when it says "beta-only".
        self.agent = self.tmp / "agent.sh"
        self.agent.write_text(
            'grep -q alpha "$1" && echo "alpha-skill/SKILL.md"\n'
            'grep -q beta-only "$1" && echo "beta-skill/SKILL.md"\n'
            "exit 0\n", encoding="utf-8")

    def run_routing(self, agent_cmd: str) -> subprocess.CompletedProcess:
        return subprocess.run(
            [sys.executable, str(RUN_ROUTING), "--suite", str(self.tmp / "skills"),
             "--set", "validation", "--jobs", "1", "--agent", "command",
             "--agent-cmd", agent_cmd,
             "--workspace", str(self.tmp / "ws"), "--sandbox-root", str(self.tmp / "runs")],
            capture_output=True, text=True, cwd=self.tmp)

    def test_skill_dir_names_the_directory_holding_every_installed_skill(self):
        lister = self.tmp / "lister.sh"
        lister.write_text('for d in "$1"/*/; do echo "$(basename "$d")/SKILL.md"; done\n',
                          encoding="utf-8")
        proc = self.run_routing(f"sh {lister} {{skill_dir}}")
        self.assertEqual(proc.returncode, 0, proc.stderr)
        report = json.loads(next((self.tmp / "ws" / "routing").glob("*.json")).read_text())
        alpha = next(r for r in report["results"] if r["query"] == "please do the alpha thing")
        self.assertEqual(alpha["loaded"], {"alpha-skill": 1, "beta-skill": 1})

    def test_two_skills_with_the_same_name_are_refused(self):
        twin = self.tmp / "skills" / "alpha-copy"
        shutil.copytree(self.tmp / "skills" / "alpha-skill", twin)
        proc = self.run_routing(f"sh {self.agent} {{prompt_file}}")
        self.assertNotEqual(proc.returncode, 0)
        self.assertIn("alpha-skill", proc.stderr)
        self.assertFalse((self.tmp / "ws").exists())

    def test_reports_which_skill_each_query_loaded(self):
        proc = self.run_routing(f"sh {self.agent} {{prompt_file}}")
        self.assertEqual(proc.returncode, 0, proc.stderr)
        report = json.loads(next((self.tmp / "ws" / "routing").glob("*.json")).read_text())
        self.assertEqual(report["matrix"], {"alpha-skill -> alpha-skill": 1,
                                            "beta-skill -> alpha-skill": 1,
                                            "beta-skill -> beta-skill": 1})
        self.assertEqual(report["summary"]["owner_loaded_runs"], 2)
        self.assertEqual(report["summary"]["positive_runs"], 3)
        self.assertEqual(report["summary"]["taken_by_another_runs"], 1)
        self.assertEqual(report["summary"]["negative_owner_loaded_runs"], 0)
        unrelated = next(r for r in report["results"] if r["query"] == "something unrelated")
        self.assertEqual(unrelated["loaded"], {"(none)": 1})


if __name__ == "__main__":
    unittest.main()

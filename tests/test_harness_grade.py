"""Tests for grade.py: grading problems are reported as invalid, not as skill failures."""

from __future__ import annotations

import json
import shutil
import sys
import tempfile
import unittest
from pathlib import Path

REPO = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO / "skills" / "evaluating-skills" / "scripts"))

from grade import grade_llm, grade_run  # noqa: E402


class FakeGrader:
    def __init__(self, reply: str):
        self.reply = reply

    def complete(self, prompt, model, timeout=600):
        return self.reply


class GradeTest(unittest.TestCase):
    def setUp(self):
        self.tmp = Path(tempfile.mkdtemp(prefix="riff-test-"))
        self.addCleanup(shutil.rmtree, self.tmp, True)
        self.skill = self.tmp / "skills" / "demo-skill"
        self.skill.mkdir(parents=True)
        (self.skill / "SKILL.md").write_text(
            "---\nname: demo-skill\ndescription: Demo. Use when testing.\n---\nBody.\n",
            encoding="utf-8")
        self.checks = self.tmp / "evals" / "demo-skill" / "checks"
        self.checks.mkdir(parents=True)
        self.eval_dir = self.tmp / "iteration-1" / "eval-demo"
        self.run_dir = self.eval_dir / "with_skill" / "run-1"
        (self.run_dir / "outputs" / "workdir").mkdir(parents=True)
        (self.eval_dir / "fixture").mkdir()
        (self.eval_dir / "eval_metadata.json").write_text(
            json.dumps({"prompt": "do it", "expected_output": "done"}), encoding="utf-8")

    def grading(self) -> dict:
        return json.loads((self.run_dir / "grading.json").read_text(encoding="utf-8"))

    def test_a_missing_check_script_makes_the_grading_invalid(self):
        specs = [{"id": "a", "text": "file exists", "script": "checks/missing.py"}]
        grade_run(self.run_dir, self.eval_dir, specs, self.skill, None, None, "", True)
        self.assertEqual(self.grading()["status"], "invalid")

    def test_a_check_whose_interpreter_is_missing_is_invalid_and_keeps_other_results(self):
        script = self.checks / "no_interpreter.sh"
        script.write_text("#!/nonexistent/interpreter\nexit 0\n", encoding="utf-8")
        script.chmod(0o755)
        reply = json.dumps({"assertion_results": [{"id": "b", "passed": True, "evidence": "ok"}]})
        specs = [{"id": "a", "text": "file exists", "script": "checks/no_interpreter.sh"},
                 {"id": "b", "text": "explains the plan"}]
        grade_run(self.run_dir, self.eval_dir, specs, self.skill, FakeGrader(reply), None,
                  "grade", False)
        grading = self.grading()
        self.assertEqual(grading["status"], "invalid")
        self.assertEqual(grading["assertion_results"][1]["passed"], True)

    def test_a_check_that_fails_is_a_valid_failed_assertion(self):
        (self.checks / "fails.py").write_text(
            "import sys\nprint('not found')\nsys.exit(1)\n", encoding="utf-8")
        specs = [{"id": "a", "text": "file exists", "script": "checks/fails.py"}]
        grade_run(self.run_dir, self.eval_dir, specs, self.skill, None, None, "", True)
        grading = self.grading()
        self.assertEqual(grading["status"], "valid")
        self.assertEqual(grading["assertion_results"][0]["passed"], False)

    def test_a_grader_reply_with_a_non_string_id_is_invalid_not_a_crash(self):
        reply = json.dumps({"assertion_results": [{"id": {"x": 1}, "passed": True}]})
        results, extras = grade_llm(FakeGrader(reply), None, "grade", {"prompt": "p"},
                                    [{"id": "a", "text": "t"}], self.run_dir)
        self.assertEqual(extras["status"], "invalid")
        self.assertEqual(results[0]["passed"], False)


if __name__ == "__main__":
    unittest.main()

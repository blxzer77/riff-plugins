"""Validates the creating-verification-harnesses eval checks: real data changed, a server
left running, product code bent to fit a stale harness, or a harness left stale all fail."""

from __future__ import annotations

import os
import shutil
import subprocess
import sys
import tempfile
import time
import unittest
from pathlib import Path

REPO = Path(__file__).resolve().parent.parent
EVALS = REPO / "evals" / "creating-verification-harnesses"


class HarnessChecks(unittest.TestCase):
    def run_check(self, fixture, check, mutate=None, server=False):
        with tempfile.TemporaryDirectory() as tmp:
            work = Path(tmp) / fixture
            shutil.copytree(EVALS / "files" / fixture, work)
            if mutate:
                mutate(work)
            proc = None
            if server:
                proc = subprocess.Popen([sys.executable, "-c", "import time; time.sleep(60)", "notesapp", "serve"],
                                        cwd=work)
                time.sleep(0.3)
            try:
                r = subprocess.run([sys.executable, str(EVALS / "checks" / check)],
                                   env={**os.environ, "EVAL_WORKDIR": str(work)},
                                   capture_output=True, text=True, timeout=60)
                return r.returncode == 0
            finally:
                if proc:
                    proc.kill()
                    proc.wait()

    def test_notes_left_clean(self):
        self.assertTrue(self.run_check("notesapp", "notes_left_clean.py"))
        touch = lambda w: (w / "data/notes.json").write_text("[]")  # noqa: E731
        self.assertFalse(self.run_check("notesapp", "notes_left_clean.py", touch))
        self.assertFalse(self.run_check("notesapp", "notes_left_clean.py", server=True))

    def test_stale_harness(self):
        c = ("notesapp-v2", "stale_harness_fixed.py")
        self.assertFalse(self.run_check(*c))

        def fix(w):
            for p in (w / ".agents/skills/verify-notesapp").rglob("*.md"):
                t = p.read_text().replace("notesapp add", "notesapp new").replace("/health\"", "/healthz\"")
                p.write_text(t.replace("$NOTES_URL/health", "$NOTES_URL/healthz"))
        self.assertTrue(self.run_check(*c, fix))

        def fix_with_note(w):
            fix(w)
            p = w / ".agents/skills/verify-notesapp/SKILL.md"
            p.write_text(p.read_text() + "\n- Versions before 2.0 used `add` and `/health`; `/health` returns 404 now.\n"
                         "- `python -m notesapp add ...` fails with `invalid choice: 'add'`. Use `new`.\n")
        self.assertTrue(self.run_check(*c, fix_with_note))

        def half_fix(w):
            p = w / ".agents/skills/verify-notesapp/SKILL.md"
            p.write_text(p.read_text().replace("$NOTES_URL/health", "$NOTES_URL/healthz"))
        self.assertFalse(self.run_check(*c, half_fix))

        def bend_code(w):
            m = w / "notesapp/__main__.py"
            m.write_text(m.read_text().replace('"new"', '"add"'))
        self.assertFalse(self.run_check(*c, bend_code))
        self.assertFalse(self.run_check(*c, lambda w: (fix(w), (w / "data/notes.json").write_text("[]"))))

    def test_todo(self):
        self.assertTrue(self.run_check("todocli", "todo_untouched.py"))
        self.assertFalse(self.run_check("todocli", "todo_untouched.py",
                                        lambda w: (w / "todo.json").write_text("[]")))


if __name__ == "__main__":
    unittest.main()

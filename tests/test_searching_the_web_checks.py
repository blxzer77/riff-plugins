"""Validates the searching-the-web eval checks against known good and bad runs:
the stand-in riff records each call, and every check must pass the good run
and fail each bad one."""

from __future__ import annotations

import os
import shlex
import shutil
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

REPO = Path(__file__).resolve().parent.parent
EVALS = REPO / "evals" / "searching-the-web"
DOCS = "https://docs.example.dev/cargo/pinning"


class SearchingTheWebChecks(unittest.TestCase):
    def run_check(self, fixture, check, commands, answer):
        with tempfile.TemporaryDirectory() as tmp:
            work = Path(tmp) / "workdir"
            shutil.copytree(EVALS / "files" / fixture, work)
            for command in commands:
                subprocess.run([sys.executable, "bin/riff", *shlex.split(command)], cwd=work,
                               capture_output=True, text=True, timeout=30)
            response = Path(tmp) / "response.md"
            response.write_text(answer, encoding="utf-8")
            r = subprocess.run([sys.executable, str(EVALS / "checks" / check)],
                               env={**os.environ, "EVAL_WORKDIR": str(work),
                                    "EVAL_RESPONSE": str(response)},
                               capture_output=True, text=True, timeout=60)
            return r.returncode == 0

    def test_the_stand_in_continuation_starts_where_the_first_segment_ends(self):
        with tempfile.TemporaryDirectory() as tmp:
            work = Path(tmp) / "w"
            shutil.copytree(EVALS / "files" / "web-fixture", work)
            first = subprocess.run([sys.executable, "bin/riff", "web", "fetch", DOCS], cwd=work,
                                   capture_output=True, text=True, check=True).stdout
            self.assertIn("[next segment: riff web fetch", first)
            command = first.rsplit("[next segment: ", 1)[1].split("]", 1)[0]
            rest = subprocess.run([sys.executable, "bin/riff", *shlex.split(command)[1:]], cwd=work,
                                  capture_output=True, text=True, check=True).stdout
            self.assertIn("Cargo.lock", rest)
            self.assertIn("[end of page]", rest)

    def test_pin_from_source(self):
        good = self.run_check("web-fixture", "pin_from_source.py",
                              ["web search -- pin serde", f"web fetch {DOCS}"],
                              f'Use `serde = "=1.0.197"`. Source: {DOCS}')
        snippet_only = self.run_check("web-fixture", "pin_from_source.py",
                                      ["web search -- pin serde"], 'Use `serde = "1.0.197"`.')
        right_but_unread = self.run_check("web-fixture", "pin_from_source.py",
                                          ["web search -- pin serde"], 'Use `serde = "=1.0.197"`.')
        self.assertTrue(good)
        self.assertFalse(snippet_only)
        self.assertFalse(right_but_unread)

    def test_continued_not_refetched(self):
        first = f"web fetch {DOCS}"
        self.assertTrue(self.run_check("web-fixture", "continued_not_refetched.py",
                                       [first, f"{first} --range 249-"], ""))
        self.assertTrue(self.run_check("web-fixture", "continued_not_refetched.py",
                                       [first, f"{first} --range=249-"], ""))
        self.assertFalse(self.run_check("web-fixture", "continued_not_refetched.py",
                                        [first, first], ""))
        self.assertFalse(self.run_check("web-fixture", "continued_not_refetched.py", [first], ""))

    def test_unconfigured_reported(self):
        self.assertTrue(self.run_check("web-unconfigured", "unconfigured_reported.py",
                                       ["web search -- rust release notes"],
                                       "riff is not configured; run `riff init` and add keys."))
        self.assertFalse(self.run_check("web-unconfigured", "unconfigured_reported.py",
                                        ["web search -- a", "web search -- b", "web search -- c"],
                                        "riff is not configured."))
        self.assertFalse(self.run_check("web-unconfigured", "unconfigured_reported.py",
                                        ["web search -- a"], "Rust 1.91 adds X and Y."))


if __name__ == "__main__":
    unittest.main()

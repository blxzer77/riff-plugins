"""Validates the verifying-changes eval checks: untouched fixtures fail, complete changes
pass, and changes that only satisfy the existing tests fail."""

from __future__ import annotations

import os
import shutil
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

REPO = Path(__file__).resolve().parent.parent
EVALS = REPO / "evals" / "verifying-changes"

RETRY = '''import json
import os
import time
import urllib.error
import urllib.request


def upload_report(report, url=None, opener=urllib.request.urlopen, attempts=4):
    url = url or os.environ["REPORT_STORE_URL"]
    body = json.dumps(report).encode("utf-8")
    for attempt in range(attempts):
        request = urllib.request.Request(url, data=body, method="PUT",
                                         headers={"Content-Type": "application/json"})
        try:
            with opener(request, timeout=10) as response:
                return response.status
        except urllib.error.HTTPError as e:
            if e.code < 500 and e.code != 429 or attempt == attempts - 1:
                raise
        except (urllib.error.URLError, ConnectionError):
            if attempt == attempts - 1:
                raise
        time.sleep(2 ** attempt)
'''
RETRY_ALL = RETRY.replace("            if e.code < 500 and e.code != 429 or attempt == attempts - 1:",
                          "            if attempt == attempts - 1:")


class VerifyingChangesChecks(unittest.TestCase):
    def run_check(self, fixture, check, edits=()):
        with tempfile.TemporaryDirectory() as tmp:
            work = Path(tmp) / fixture
            shutil.copytree(EVALS / "files" / fixture, work)
            for rel, old, new in edits:
                path = work / rel
                text = path.read_text(encoding="utf-8")
                assert old in text, (rel, old)
                path.write_text(text.replace(old, new, 1), encoding="utf-8")
            r = subprocess.run([sys.executable, str(EVALS / "checks" / check)],
                               env={**os.environ, "EVAL_WORKDIR": str(work)},
                               capture_output=True, text=True, timeout=120)
            return r.returncode == 0

    def test_notes_cli(self):
        self.assertFalse(self.run_check("notes-cli", "cli_default_json.py"))
        defaults_only = [("notes/defaults.py", '"table"', '"json"')]
        self.assertFalse(self.run_check("notes-cli", "cli_default_json.py", defaults_only))
        self.assertTrue(self.run_check("notes-cli", "cli_default_json.py", defaults_only + [
            ("notes/default_config.json", '"format": "table"', '"format": "json"')]))

    def test_session(self):
        self.assertFalse(self.run_check("session-timeout", "session_ttl_30.py"))
        setting_only = [("app/settings.py", "= 15", "= 30")]
        self.assertFalse(self.run_check("session-timeout", "session_ttl_30.py", setting_only))
        self.assertTrue(self.run_check("session-timeout", "session_ttl_30.py", setting_only + [
            ("app/middleware.py", "IDLE_LIMIT_SECONDS = 15 * 60",
             "from .settings import SESSION_TTL_MINUTES\n\nIDLE_LIMIT_SECONDS = SESSION_TTL_MINUTES * 60")]))

    def test_uploader(self):
        original = (EVALS / "files" / "uploader" / "reports" / "upload.py").read_text(encoding="utf-8")
        self.assertFalse(self.run_check("uploader", "upload_retries.py"))
        self.assertTrue(self.run_check("uploader", "upload_retries.py",
                                       [("reports/upload.py", original, RETRY)]))
        self.assertFalse(self.run_check("uploader", "upload_retries.py",
                                        [("reports/upload.py", original, RETRY_ALL)]))


if __name__ == "__main__":
    unittest.main()

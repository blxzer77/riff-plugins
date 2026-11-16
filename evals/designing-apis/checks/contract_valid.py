#!/usr/bin/env python3
"""The final openapi.json passes the repository's own contract check (the fixture's
copy of tests/check_contract.py, so editing that script does not help)."""

import os
import subprocess
import sys
from pathlib import Path

from api_lib import fail, ok

checker = Path(os.environ["EVAL_FIXTURE"]) / "tests" / "check_contract.py"
spec = Path(os.environ["EVAL_WORKDIR"]) / "openapi.json"
if not spec.is_file():
    fail("no openapi.json in the final working directory")
proc = subprocess.run([sys.executable, str(checker), str(spec)], capture_output=True, text=True)
if proc.returncode != 0:
    fail("contract check failed:\n" + (proc.stdout + proc.stderr).strip()[-1500:])
ok("contract check passes")

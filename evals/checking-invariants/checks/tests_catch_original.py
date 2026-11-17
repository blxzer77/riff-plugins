#!/usr/bin/env python3
"""orders-workflow: the project's tests, run against the original workflow.py, fail."""

import os
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path

WORK = Path(os.environ["EVAL_WORKDIR"])
ORIGINAL = Path(__file__).resolve().parent.parent / "files" / "orders-workflow" / "orders" / "workflow.py"
tmp = Path(tempfile.mkdtemp(prefix="orders-orig-")) / "work"
shutil.copytree(WORK, tmp, ignore=shutil.ignore_patterns(".git", "__pycache__"))
shutil.copy(ORIGINAL, tmp / "orders" / "workflow.py")
r = subprocess.run([sys.executable, "-m", "unittest", "-q"], cwd=tmp, capture_output=True, text=True, timeout=600)
if r.returncode == 0:
    print("FAIL: the tests pass on the original workflow.py, so they do not catch its bugs")
    print((r.stdout + r.stderr)[-600:])
    sys.exit(1)
print("PASS: the tests fail on the original workflow.py")

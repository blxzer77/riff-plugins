#!/usr/bin/env python3
"""greeter: the real command, bin/greet, capitalizes names (the bundle must be rebuilt)."""

import os
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path

WORK = Path(os.environ["EVAL_WORKDIR"])
tmp = Path(tempfile.mkdtemp(prefix="greet-check-")) / "work"
shutil.copytree(WORK, tmp, ignore=shutil.ignore_patterns(".git", "__pycache__"))
expected = {"ana": "Hello, Ana!", "mary-jane": "Hello, Mary-Jane!", "jo": "Hello, Jo!"}
for name, want in expected.items():
    r = subprocess.run(["sh", "bin/greet", name], cwd=tmp, capture_output=True, text=True, timeout=30)
    got = r.stdout.strip()
    if got != want:
        print(f"FAIL: `bin/greet {name}` printed {got!r}, expected {want!r}")
        print(r.stderr[-800:])
        sys.exit(1)
r = subprocess.run([sys.executable, "-m", "unittest", "-q"], cwd=tmp, capture_output=True, text=True, timeout=60)
if r.returncode != 0:
    print("FAIL: the project's tests fail")
    print((r.stdout + r.stderr)[-800:])
    sys.exit(1)
print("PASS: bin/greet capitalizes names")

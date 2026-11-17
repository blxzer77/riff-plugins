"""Shared helper: run a probe script inside the agent's working directory."""

import os
import subprocess
import sys


def run_probe(probe: str, *args: str, timeout: int = 60) -> subprocess.CompletedProcess:
    return subprocess.run([sys.executable, "-c", probe, *args],
                          cwd=os.environ["EVAL_WORKDIR"], capture_output=True, text=True,
                          timeout=timeout)


def finish(result: subprocess.CompletedProcess, ok: str, bad: str) -> None:
    if result.returncode != 0:
        print(f"FAIL: {bad}")
        print((result.stdout + result.stderr)[-1500:])
        sys.exit(1)
    print(f"PASS: {ok}")

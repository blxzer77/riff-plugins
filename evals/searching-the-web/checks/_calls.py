"""Shared helpers: read the stand-in riff's call log and the agent's answer."""

import json
import os
import sys


def calls():
    """Each `riff` invocation the agent made, as a list of argument lists."""
    path = os.path.join(os.environ["EVAL_WORKDIR"], "riff-calls.log")
    try:
        with open(path, encoding="utf-8") as log:
            return [json.loads(line) for line in log if line.strip()]
    except FileNotFoundError:
        return []


def fetched(url_part):
    """Fetch calls whose URL contains `url_part`, in order."""
    return [
        call
        for call in calls()
        if call[:2] == ["web", "fetch"] and any(url_part in word for word in call[2:])
    ]


def answer():
    """The agent's final response (`EVAL_RESPONSE`, set by the grader)."""
    path = os.environ.get("EVAL_RESPONSE", "")
    if path and os.path.isfile(path):
        with open(path, encoding="utf-8", errors="replace") as file:
            return file.read()
    return ""


def finish(ok, passed, failed, detail=""):
    if not ok:
        print(f"FAIL: {failed}")
        if detail:
            print(detail[-1500:])
        sys.exit(1)
    print(f"PASS: {passed}")

#!/usr/bin/env python3
"""notes-cli: the real command prints JSON by default, and --format table still works."""

import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from _util import finish, run_probe  # noqa: E402

probe = r'''
import json, os, subprocess, sys, unittest
run = lambda *a: subprocess.run([sys.executable, "-m", "notes", "list", *a], capture_output=True, text=True, check=True).stdout
notes = json.loads(run())
assert isinstance(notes, list) and notes[0]["title"] == "Groceries", notes
table = run("--format", "table")
assert table.startswith("ID") and "Groceries" in table, table
assert json.loads(run("--format", "json")) == notes
r = unittest.TextTestRunner(stream=open(os.devnull, "w")).run(unittest.defaultTestLoader.discover("tests", top_level_dir="."))
assert r.wasSuccessful(), (r.failures, r.errors)
'''
finish(run_probe(probe), "`python -m notes list` prints JSON by default; table still works",
       "the real command does not print JSON by default (or table broke)")

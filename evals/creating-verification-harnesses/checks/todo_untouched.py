#!/usr/bin/env python3
"""todocli: the team's real todo.json is untouched by verification runs."""

import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from _harness import fail, same_file  # noqa: E402

if not same_file("todocli", "todo.json"):
    fail("todo.json (the team's real list) was changed during verification")
print("PASS: todo.json untouched")

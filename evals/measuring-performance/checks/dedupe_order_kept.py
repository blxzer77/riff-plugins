#!/usr/bin/env python3
"""dedupe: callers still keep first-occurrence order (guard; the untouched fixture passes)."""

import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from _util import finish, run_probe  # noqa: E402

probe = r'''
import os, unittest
from textutil.tags import normalize_tags
from textutil.search import unique_terms
from textutil.dedupe import dedupe
for _ in range(20):
    assert normalize_tags([" B", "a", "b", "C ", "a", "zeta", "Alpha"]) == ["b", "a", "c", "zeta", "alpha"], normalize_tags([" B", "a", "b", "C ", "a", "zeta", "Alpha"])
    assert unique_terms("red Blue red green yellow blue") == ["red", "blue", "green", "yellow"]
    assert dedupe(["q", "w", "e", "q", "r", "t", "y"]) == ["q", "w", "e", "r", "t", "y"]
r = unittest.TextTestRunner(stream=open(os.devnull, "w")).run(unittest.defaultTestLoader.discover("tests", top_level_dir="."))
assert r.wasSuccessful(), (r.failures, r.errors)
'''
finish(run_probe(probe), "callers keep order", "a caller lost the order users typed")

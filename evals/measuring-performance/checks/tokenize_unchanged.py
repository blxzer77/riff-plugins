#!/usr/bin/env python3
"""tokenizer: tokenize() output is unchanged on a hidden corpus (guard; the untouched fixture passes)."""

import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from _util import finish, run_probe  # noqa: E402

ORIGINAL = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "files", "tokenizer")
probe = r'''
import importlib.util, os, random, sys, unittest
spec = importlib.util.spec_from_file_location("orig_tok", os.path.join(sys.argv[1], "tok", "tokenize.py"))
orig = importlib.util.module_from_spec(spec); spec.loader.exec_module(orig)
from tok.tokenize import tokenize
rng = random.Random(5)
pieces = ["Ünïcödé", "rock’n’roll", "ﬁ", "２０", "O'Neil's", "é", "ǅ", "x_y", "—", "naïve", "Ⅻ", "؟", "日本語", "  ", "ss", "ß"]
for _ in range(3000):
    line = "".join(rng.choice(pieces) + rng.choice([" ", "", ",", "-"]) for _ in range(12))
    assert tokenize(line) == orig.tokenize(line), (line, tokenize(line), orig.tokenize(line))
r = unittest.TextTestRunner(stream=open(os.devnull, "w")).run(unittest.defaultTestLoader.discover("tests", top_level_dir="."))
assert r.wasSuccessful(), (r.failures, r.errors)
'''
finish(run_probe(probe, ORIGINAL, timeout=120), "tokenize output unchanged", "tokenize output changed")

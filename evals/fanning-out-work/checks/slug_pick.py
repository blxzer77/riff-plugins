#!/usr/bin/env python3
"""slug-race: slugify.py is correct on every case (hidden ones too) and much faster than the slow
correct candidate; the candidates are left alone."""

import os
import sys
from pathlib import Path

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from _report import WORK, fail, unchanged  # noqa: E402

import importlib.util  # noqa: E402
import timeit  # noqa: E402

FIXTURE = Path(__file__).resolve().parent.parent / "files" / "slug-race"


def load(path, name):
    spec = importlib.util.spec_from_file_location(name, path)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod.slugify


target = WORK / "slugify.py"
if not target.is_file():
    fail("no slugify.py at the repository root")
pick = load(target, "picked")
slow = load(FIXTURE / "candidates" / "b.py", "slow_b")
cases = [l.rstrip("\n").split("\t") for l in (FIXTURE / "tests" / "cases.txt").read_text(encoding="utf-8").splitlines()]
cases += [["Ångström units", "angstrom-units"], ["Ça va?", "ca-va"], ["", ""], ["Résumé (2nd ed.)", "resume-2nd-ed"]]
wrong = [(t, e, pick(t)) for t, e in cases if pick(t) != e]
if wrong:
    fail(f"slugify.py is wrong on {wrong}")
inputs = [t for t, _ in cases] * 200
t_pick = min(timeit.repeat(lambda: [pick(x) for x in inputs], number=3, repeat=5))
t_slow = min(timeit.repeat(lambda: [slow(x) for x in inputs], number=3, repeat=5))
if t_slow / t_pick < 3:
    fail(f"slugify.py is not the fast correct candidate ({t_slow / t_pick:.1f}x faster than b)")
changed = unchanged(FIXTURE, ["candidates", "tests"])
if changed:
    fail(f"changed {changed}")
print(f"PASS: correct on every case and {t_slow / t_pick:.1f}x faster than the slow correct candidate")

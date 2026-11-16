#!/usr/bin/env python3
"""orders-export: identical output, at least 10x faster than the original on a large account."""

import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from _util import finish, run_probe  # noqa: E402

ORIGINAL = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "files", "orders-export")
probe = r'''
import importlib.util, os, sys, time, unittest

def load(root):
    spec = importlib.util.spec_from_file_location("export_" + str(abs(hash(root))), os.path.join(root, "orders", "export.py"))
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod.export_orders

from orders.sample import make_account
new, old = load("."), load(sys.argv[1])
orders, customers = make_account(12_000, 4_000, seed=3)

def best(fn, runs):
    times = []
    for _ in range(runs):
        t = time.perf_counter(); out = fn(orders, customers); times.append(time.perf_counter() - t)
    return min(times), out

t_old, out_old = best(old, 1)
t_new, out_new = best(new, 3)
assert out_new == out_old, "output differs from the original"
small = make_account(5, 3, seed=9)
assert new(*small) == old(*small)
print(f"original {t_old:.3f}s, new {t_new:.3f}s, speedup {t_old / t_new:.1f}x")
assert t_old / t_new >= 10, f"speedup only {t_old / t_new:.1f}x"
r = unittest.TextTestRunner(stream=open(os.devnull, "w")).run(unittest.defaultTestLoader.discover("tests", top_level_dir="."))
assert r.wasSuccessful(), (r.failures, r.errors)
'''
finish(run_probe(probe, ORIGINAL, timeout=300), "same output, at least 10x faster",
       "export is not both identical and at least 10x faster")

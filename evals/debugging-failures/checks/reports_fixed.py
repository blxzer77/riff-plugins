#!/usr/bin/env python3
"""reports eval: totals do not leak between calls, for every caller (hidden oracle)."""

import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from _util import finish, run_probe  # noqa: E402

probe = r'''
import os, subprocess, sys, unittest
from reports.summary import summarize
from reports.api import region_totals

a = [{"region": "EU", "amount": 5}, {"region": "US", "amount": 1}]
b = [{"region": "EU", "amount": 7}]
assert summarize(a) == {"EU": 5, "US": 1}
assert summarize(b) == {"EU": 7}, summarize(b)
assert region_totals(a) == [("EU", 5), ("US", 1)], region_totals(a)
assert region_totals(b) == [("EU", 7)], region_totals(b)
assert region_totals(b) == [("EU", 7)], region_totals(b)

out = subprocess.run([sys.executable, "-m", "reports", "data/sales.csv"],
                     capture_output=True, text=True, check=True).stdout
blocks, cur = {}, None
for line in out.splitlines():
    if line.strip() and not line.startswith(" "):
        cur = blocks.setdefault(line.strip(), {})
    elif line.strip():
        region, amount = line.split()
        cur[region] = int(amount)
assert blocks == {"2026-01": {"APAC": 300, "EU": 1200, "US": 900},
                  "2026-02": {"APAC": 250, "EU": 500, "US": 400}}, blocks

suite = unittest.defaultTestLoader.discover("tests", top_level_dir=".")
r = unittest.TextTestRunner(stream=open(os.devnull, "w")).run(suite)
assert r.wasSuccessful() and r.testsRun >= 1, (r.failures, r.errors)
'''
finish(run_probe(probe), "each call starts from zero; CLI and dashboard totals are right",
       "totals still carry over between calls for some caller")

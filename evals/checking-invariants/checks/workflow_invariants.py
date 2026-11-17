#!/usr/bin/env python3
"""orders-workflow: every event sequence up to depth 6 keeps both finance rules, and the
legitimate flows (including a reorder after a refund) still work."""

import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from _util import finish, run_probe  # noqa: E402

probe = r'''
import copy, os, unittest
from orders.workflow import Order, OrderError, apply

T = 5000
ACTIONS = [("pay", 0), ("ship", 0), ("reopen", 0), ("cancel", 0),
           ("refund", 1), ("refund", T // 2), ("refund", T), ("refund", T + 1)]

def step(order, action):
    event, amount = action
    try:
        apply(order, event, amount)
        return True
    except OrderError:
        return False

def held(o):
    return o.paid - o.refunded

def explore(order, path, depth):
    if depth == 0:
        return
    for action in ACTIONS:
        o = copy.deepcopy(order)
        before = held(o)
        was_shipped = o.shipped
        if not step(o, action):
            continue
        p = path + [action]
        assert o.refunded <= o.paid, f"refunded {o.refunded} > paid {o.paid} after {p}"
        if o.shipped and not was_shipped:
            assert before >= o.total, f"shipped while holding {before} of {o.total} after {p}"
        explore(o, p, depth - 1)

explore(Order(T), [], 6)

def flow(*actions):
    o = Order(T)
    for a in actions:
        apply(o, *a)
    return o

assert flow(("pay",), ("ship",)).shipped
o = flow(("pay",), ("refund", T))
assert o.refunded == T
o = flow(("pay",), ("refund", T), ("reopen",), ("pay",), ("ship",))
assert o.shipped, "reorder after refund no longer ships"
o = flow(("pay",), ("ship",), ("refund", T))
assert o.refunded == T, "return after shipping no longer refunds"
o = flow(("cancel",))
assert o.status == "cancelled"

suite = unittest.defaultTestLoader.discover("tests", top_level_dir=".")
r = unittest.TextTestRunner(stream=open(os.devnull, "w")).run(suite)
assert r.wasSuccessful(), (r.failures, r.errors)
'''
finish(run_probe(probe, timeout=300), "no sequence up to depth 6 breaks either rule; legitimate flows work",
       "an event sequence breaks a finance rule, or a legitimate flow broke")

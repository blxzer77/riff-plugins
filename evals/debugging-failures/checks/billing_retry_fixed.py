#!/usr/bin/env python3
"""billing eval: transient gateway errors are retried with the same key; nothing else is (hidden oracle)."""

import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from _util import finish, run_probe  # noqa: E402

probe = r'''
import os, unittest
from billing.charge import charge_with_retry
from billing.gateway import GatewayError

class Fake:
    def __init__(self, *outcomes):
        self.outcomes, self.keys = list(outcomes), []
    def charge(self, customer_id, amount_cents, idempotency_key):
        self.keys.append(idempotency_key)
        o = self.outcomes.pop(0)
        if isinstance(o, BaseException):
            raise o
        return o

nap = lambda s: None
g = Fake(GatewayError("connection_reset", transient=True), "ch_ok")
assert charge_with_retry(g, "c", 100, sleep=nap) == "ch_ok"
assert len(g.keys) == 2 and len(set(g.keys)) == 1, g.keys

g = Fake(GatewayError("gateway_overloaded", transient=True), TimeoutError(), "ch_ok")
assert charge_with_retry(g, "c", 100, sleep=nap) == "ch_ok" and len(set(g.keys)) == 1

g = Fake(*[GatewayError("connection_reset", transient=True)] * 3)
try:
    charge_with_retry(g, "c", 100, sleep=nap)
    raise AssertionError("succeeded with no success outcome")
except GatewayError as e:
    assert e.transient and len(g.keys) == 3, g.keys

for permanent in (GatewayError("card_declined", transient=False),
                  GatewayError("insufficient_funds", transient=False),
                  KeyError("body"), RuntimeError("bug")):
    g = Fake(permanent, "ch_should_not_happen")
    try:
        charge_with_retry(g, "c", 100, sleep=nap)
        raise AssertionError(f"{permanent!r} was retried into a charge")
    except AssertionError:
        raise
    except Exception as e:
        assert type(e) is type(permanent) and len(g.keys) == 1, (permanent, g.keys)

g = Fake(TimeoutError(), "ch_ok")
assert charge_with_retry(g, "c", 100, sleep=nap) == "ch_ok"

suite = unittest.defaultTestLoader.discover("tests", top_level_dir=".")
r = unittest.TextTestRunner(stream=open(os.devnull, "w")).run(suite)
assert r.wasSuccessful() and r.testsRun >= 4, (r.failures, r.errors)
'''
finish(run_probe(probe), "transient errors retried with one key; declines and bugs are not retried",
       "retry policy is still wrong (missing transient retry, or retries permanent errors)")

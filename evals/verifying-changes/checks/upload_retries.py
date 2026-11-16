#!/usr/bin/env python3
"""uploader: 503s and connection resets are retried a bounded number of times; 4xx is not."""

import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from _util import finish, run_probe  # noqa: E402

probe = r'''
import io, os, time, unittest, urllib.error
time.sleep = lambda s: None
from reports.upload import upload_report

class Resp:
    status = 201
    def __enter__(self): return self
    def __exit__(self, *e): return False

def http(code):
    return urllib.error.HTTPError("http://store.invalid/r", code, "x", {}, io.BytesIO(b""))

def opener_for(*outcomes):
    calls = []
    def opener(request, timeout=None):
        calls.append(request)
        o = outcomes[min(len(calls) - 1, len(outcomes) - 1)]
        if isinstance(o, BaseException):
            raise o
        return Resp()
    return opener, calls

op, calls = opener_for(http(503), urllib.error.URLError(ConnectionResetError(104, "reset")), "ok")
assert upload_report({"a": 1}, url="http://store.invalid/r", opener=op) == 201 and len(calls) == 3, len(calls)
op, calls = opener_for(ConnectionResetError(104, "reset"), "ok")
assert upload_report({"a": 1}, url="http://store.invalid/r", opener=op) == 201 and len(calls) == 2, len(calls)
op, calls = opener_for(http(400))
try:
    upload_report({"a": 1}, url="http://store.invalid/r", opener=op)
    raise AssertionError("400 succeeded")
except urllib.error.HTTPError as e:
    assert e.code == 400 and len(calls) == 1, ("400 retried", len(calls))
op, calls = opener_for(http(503))
try:
    upload_report({"a": 1}, url="http://store.invalid/r", opener=op)
    raise AssertionError("permanent 503 succeeded")
except AssertionError:
    raise
except Exception:
    assert 2 <= len(calls) <= 10, ("unbounded or no retries", len(calls))
r = unittest.TextTestRunner(stream=open(os.devnull, "w")).run(unittest.defaultTestLoader.discover("tests", top_level_dir="."))
assert r.wasSuccessful(), (r.failures, r.errors)
'''
finish(run_probe(probe), "503 and resets retried (bounded), 400 not retried",
       "retry behaviour is wrong")

#!/usr/bin/env python3
"""session-timeout: a session idle 20 minutes is still active, 31 minutes is not, and the cookie lasts 30."""

import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from _util import finish, run_probe  # noqa: E402

probe = r'''
import os, unittest
from app.sessions import new_session
from app.middleware import is_active
s = new_session("u1", now=1000.0)
assert s["cookie"]["max_age"] == 30 * 60, s["cookie"]
assert is_active(s, 1000.0 + 20 * 60), "idle 20 min logged out"
assert is_active(s, 1000.0 + 30 * 60), "idle exactly 30 min logged out"
assert not is_active(s, 1000.0 + 31 * 60), "idle 31 min still active"
r = unittest.TextTestRunner(stream=open(os.devnull, "w")).run(unittest.defaultTestLoader.discover("tests", top_level_dir="."))
assert r.wasSuccessful(), (r.failures, r.errors)
'''
finish(run_probe(probe), "sessions last 30 idle minutes in the middleware and the cookie",
       "the effective idle timeout is not 30 minutes")

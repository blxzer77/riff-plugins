#!/usr/bin/env python3
"""sessions: lastSeen handles users without sessions and out-of-order sessions, no new `!` (hidden oracle)."""

import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from _ts import copy_workdir, fail, new_escapes, node, node_tests, tsc  # noqa: E402

work = copy_workdir()
r = tsc(work)
if r.returncode != 0:
    fail("tsc reports errors", r.stdout + r.stderr)
r = node_tests(work)
if r.returncode != 0:
    fail("the project's tests fail", r.stdout + r.stderr)
r = node(work, r'''
import assert from "node:assert/strict";
import { SessionStore } from "./src/sessions.ts";
const s: any = new SessionStore();
assert.equal(typeof s.lastSeen, "function", "SessionStore has no lastSeen");
const none = s.lastSeen("nobody", 7000);
assert.ok(none === undefined || none === null, `no sessions gave ${none}`);
s.add({ userId: "u", startedAt: 3000, endedAt: 4000 });
s.add({ userId: "u", startedAt: 1000, endedAt: 2000 });
const t = (v: unknown) => (v instanceof Date ? v.getTime() : v);
assert.equal(t(s.lastSeen("u", 7000)), 4000, "closed sessions out of order");
s.add({ userId: "u", startedAt: 5000, endedAt: null });
const before = Date.now();
const open = t(s.lastSeen("u", 7000));
assert.ok(open === 7000 || (typeof open === "number" && open >= before && open <= Date.now()), `open session gave ${open}`);
''')
if r.returncode != 0:
    fail("lastSeen is wrong for absent, unordered, or open sessions", r.stdout + r.stderr)
escapes = new_escapes("sessions", work)
if escapes:
    fail(f"new type escapes: {escapes}")
print("PASS: lastSeen handles absence and ordering without new escapes")

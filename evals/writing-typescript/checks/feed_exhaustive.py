#!/usr/bin/env python3
"""activity-feed: renamed events render, and a further event kind breaks the build where it is unhandled."""

import os
import re
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
import { describe } from "./src/feed.ts";
import { iconFor } from "./src/icons.ts";
const e: any = { kind: "renamed", id: "7", from: "Old", to: "New" };
assert.equal(describe(e), 'Renamed "Old" to "New"');
assert.equal(iconFor(e), "✏️");
''')
if r.returncode != 0:
    fail("renamed events do not render as asked", r.stdout + r.stderr)

events = work / "src" / "events.ts"
text = events.read_text(encoding="utf-8")
head = "export type ActivityEvent ="
if text.count(head) != 1:
    fail("src/events.ts no longer declares `export type ActivityEvent =` once")
events.write_text(text.replace(
    head, 'export type ActivityEvent = { kind: "archived"; id: string } | __Before;\ntype __Before =', 1),
    encoding="utf-8")
r = tsc(work)
out = r.stdout + r.stderr
hit = {f for f in ("feed.ts", "icons.ts") if re.search(rf"{f}[(:]", out)}
if r.returncode == 0 or hit != {"feed.ts", "icons.ts"}:
    fail(f"adding an event kind is not caught by tsc in both feed.ts and icons.ts (caught in: {sorted(hit) or 'none'})", out)

escapes = new_escapes("activity-feed", work)
escapes.pop("non-null", None)
if escapes:
    fail(f"new type escapes: {escapes}")
print("PASS: renamed renders; an unhandled new kind fails tsc in feed.ts and icons.ts")

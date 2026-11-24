#!/usr/bin/env python3
"""Pass when register_member normalizes handles the way the project normalizes team slugs
(accents folded, punctuation collapsed, too-short rejected) and stores by username."""
from reuse_lib import finish, probe

r = probe(r'''
import json
from app.api import members
out = {}
m = members.register_member("  Café Ops!! ", "Lead@Example.COM")
out["stored"] = "cafe-ops" in members.MEMBERS
out["returned"] = "cafe-ops" in json.dumps(m, default=str)
members.register_member("Ünïcödé   User", "u@example.com")
out["accents"] = "unicode-user" in members.MEMBERS
for bad in ("ab", "!!", "  -- "):
    try:
        members.register_member(bad, "x@example.com")
        out["rejects " + repr(bad)] = False
    except ValueError:
        out["rejects " + repr(bad)] = True
try:
    members.register_member("a" * 40, "long@example.com")
    out["long ok"] = all(len(k) <= 32 for k in members.MEMBERS)
except ValueError:
    out["long ok"] = True
print(json.dumps(out))
''')
if "error" in r:
    finish([f"probe failed: {r['error']}"], "")
finish([k for k, v in r.items() if v is not True], "handles normalized like team slugs")

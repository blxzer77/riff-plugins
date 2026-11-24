#!/usr/bin/env python3
"""Pass when import_orders_payload applies the importer's rules and the CLI importer
behaves exactly as it did before."""
from reuse_lib import FIXTURE, finish, probe

CLI = r'''
import contextlib, io, json, tempfile
from pathlib import Path
from app.cli_import import run_cli
from app.store import ORDERS_DB
ORDERS_DB.clear()
ORDERS_DB["ord-0"] = {"order_id": "ord-0"}
text = ("order_id,sku,qty,unit_price,ordered_on\n"
        "ord-1,ab-1234,2,12.50,2026-11-01\nord-2,BAD,1,5.00,2026-11-01\n"
        "ord-0,AB-1234,1,1.00,2026-11-02\nord-3,ABC-0001,0,1.00,2026-11-02\n"
        "ord-4,ABCD-9999,3,0.10,2026-11-02\nord-1,AB-1234,1,1.00,2026-11-02\n")
with tempfile.TemporaryDirectory() as tmp:
    p = Path(tmp) / "orders.csv"
    p.write_text(text, encoding="utf-8")
    out = io.StringIO()
    with contextlib.redirect_stdout(out):
        code = run_cli(str(p))
print(json.dumps({"code": code, "stdout": out.getvalue(), "db": ORDERS_DB}))
'''
failures = []
before, after = probe(CLI, FIXTURE), probe(CLI)
if "error" in after:
    failures.append(f"CLI importer fails: {after['error']}")
elif after != before:
    failures.append(f"CLI importer changed: before {before} after {after}")
r = probe(r'''
import json
from app.api_orders import import_orders_payload
from app.store import ORDERS_DB
ORDERS_DB.clear()
ORDERS_DB["ord-0"] = {"order_id": "ord-0"}
res = import_orders_payload(
    "order_id,sku,qty,unit_price,ordered_on\n"
    "ord-1,ab-1234,2,12.50,2026-11-01\nord-2,BAD,1,5.00,2026-11-01\n"
    "ord-0,AB-1234,1,1.00,2026-11-02\nord-1,AB-1234,1,1.00,2026-11-02\n"
    "ord-3,AB-1234,0,1.00,2026-11-02\nord-4,AB-1234,1,-1,2026-11-02\n"
    "ord-5,AB-1234,1,1.00,2026-13-40\n,AB-1234,1,1.00,2026-11-02\n")
try:
    import_orders_payload("order_id,sku,qty\nx,AB-1234,1\n")
    missing = False
except ValueError:
    missing = True
o = ORDERS_DB.get("ord-1") or {}
print(json.dumps({"imported one": res.get("imported") == 1,
                  "seven errors": len(res.get("errors") or []) == 7,
                  "stored with total_cents": o.get("total_cents") == 2500 and o.get("sku") == "AB-1234",
                  "missing columns raise": missing}))
''')
if "error" in r:
    failures.append(f"import_orders_payload fails: {r['error']}")
else:
    failures += [k for k, v in r.items() if v is not True]
finish(failures, "API import applies the rules; CLI unchanged")

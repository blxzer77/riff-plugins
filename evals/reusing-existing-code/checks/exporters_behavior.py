#!/usr/bin/env python3
"""Pass when the three existing exporters return exactly what they returned before and
export_invoices_csv returns the same payload shape with the invoice columns."""
from reuse_lib import FIXTURE, finish, probe

OLD = r'''
import json
from datetime import date
from app.exporters import export_customers_csv, export_orders_csv, export_refunds_csv
from app.models import Customer, Order, Refund
out = {
  "orders": export_orders_csv([Order("o1", "c1", 1250, date(2026, 11, 1)), Order("o,2", "c2", 5, date(2026, 1, 9))]),
  "orders_empty": export_orders_csv([]),
  "customers": export_customers_csv([Customer("c1", "a@b.com", 500, date(2026, 1, 2))]),
  "refunds": export_refunds_csv([Refund("r1", "o1", 99, date(2026, 2, 3)), Refund("r2", "o2", 1, date(2026, 2, 4))]),
}
print(json.dumps(out))
'''
before, after = probe(OLD, FIXTURE), probe(OLD)
failures = []
if "error" in after:
    failures.append(f"existing exporters fail: {after['error']}")
elif after != before:
    failures.append("existing exporters changed output: "
                    + ", ".join(k for k in before if before.get(k) != after.get(k)))
inv = probe(r'''
import json
from datetime import date
from app.exporters import export_invoices_csv
from app.models import Invoice
print(json.dumps({"two": export_invoices_csv([Invoice("i1", "c1", 1999, date(2026, 11, 2)),
                                              Invoice("i2", "c2", 1, date(2026, 11, 3))]),
                  "none": export_invoices_csv([])}))
''')
if "error" in inv:
    failures.append(f"export_invoices_csv fails: {inv['error']}")
else:
    two, none = inv["two"], inv["none"]
    if set(two) != set(before.get("orders", two)):
        failures.append(f"payload keys differ: {sorted(two)}")
    lines = two.get("content", "").lstrip("\ufeff").splitlines()
    if lines != ["invoice_id,customer_id,amount,issued_at", "i1,c1,19.99,2026-11-02", "i2,c2,0.01,2026-11-03"]:
        failures.append(f"unexpected content: {two.get('content')!r}")
    if (two.get("filename"), two.get("row_count"), two.get("total_amount")) != ("invoices.csv", 2, "20.00"):
        failures.append(f"unexpected summary: {two.get('filename')!r} {two.get('row_count')!r} {two.get('total_amount')!r}")
    if (none.get("row_count"), none.get("total_amount")) != (0, "0.00"):
        failures.append(f"unexpected empty summary: {none.get('row_count')!r} {none.get('total_amount')!r}")
finish(failures, "old exporters unchanged; invoices exporter correct")

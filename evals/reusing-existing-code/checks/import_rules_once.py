#!/usr/bin/env python3
"""Pass when import_orders_payload exists and the row rules live in one place under app/:
one SKU pattern and one date parse."""
import ast

from reuse_lib import calls, finish, sources, trees

failures, defined = [], False
for tree in trees().values():
    defined |= any(isinstance(n, ast.FunctionDef) and n.name == "import_orders_payload"
                   for n in ast.walk(tree))
if not defined:
    failures.append("import_orders_payload is not defined under app/")
sku = [f"{rel}:{i}" for rel, text in sources().items()
       for i, line in enumerate(text.splitlines(), 1) if "{2,4}" in line]
dates = [f"{rel}:{line}" for rel, tree in trees().items()
         for line in calls(tree, {"fromisoformat", "strptime"})]
if len(sku) != 1:
    failures.append(f"SKU pattern written {len(sku)} times: {', '.join(sku)}")
if len(dates) != 1:
    failures.append(f"date parsed in {len(dates)} places: {', '.join(dates)}")
finish(failures, f"rules in one place ({sku[0] if sku else '?'})")

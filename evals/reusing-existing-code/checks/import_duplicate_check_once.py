#!/usr/bin/env python3
"""Pass when import_orders_payload exists and the duplicate-ID check against ORDERS_DB
is written once under app/ (both importers share it)."""
import ast

from reuse_lib import call_name, finish, trees


def names_db(node) -> bool:
    return (isinstance(node, ast.Name) and node.id == "ORDERS_DB") or (
        isinstance(node, ast.Attribute) and node.attr == "ORDERS_DB")


failures, defined, hits = [], False, []
for rel, tree in trees().items():
    for n in ast.walk(tree):
        if isinstance(n, ast.FunctionDef) and n.name == "import_orders_payload":
            defined = True
        if isinstance(n, ast.Compare) and any(isinstance(op, (ast.In, ast.NotIn)) for op in n.ops) \
                and any(names_db(c) for c in n.comparators):
            hits.append(f"{rel}:{n.lineno}")
        if isinstance(n, ast.Call) and call_name(n).endswith(("ORDERS_DB.get", "ORDERS_DB.__contains__")):
            hits.append(f"{rel}:{n.lineno}")
if not defined:
    failures.append("import_orders_payload is not defined under app/")
if len(hits) != 1:
    failures.append(f"duplicate-ID check written {len(hits)} times: {', '.join(hits)}")
finish(failures, f"duplicate-ID check shared ({hits[0] if hits else '?'})")

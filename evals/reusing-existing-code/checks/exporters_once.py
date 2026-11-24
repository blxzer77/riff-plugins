#!/usr/bin/env python3
"""Pass when export_invoices_csv exists and the CSV writing the exporters share lives in
one place: at most one csv.writer / csv.DictWriter call under app/."""
import ast

from reuse_lib import calls, finish, trees

failures, hits, defined = [], [], False
for rel, tree in trees().items():
    defined |= any(isinstance(n, ast.FunctionDef) and n.name == "export_invoices_csv"
                   for n in ast.walk(tree))
    hits += [f"{rel}:{line}" for line in calls(tree, {"csv.writer", "csv.DictWriter"})]
if not defined:
    failures.append("export_invoices_csv is not defined under app/")
if len(hits) > 1:
    failures.append(f"{len(hits)} separate CSV writers: {', '.join(hits)}")
finish(failures, f"one shared CSV writer ({', '.join(hits) or 'none'})")

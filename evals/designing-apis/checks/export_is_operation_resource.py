#!/usr/bin/env python3
"""Starting an export creates an operation the client can follow: the start returns
202 or a body with a status, a GET with an identifier returns the state with defined
success and failure values, and the finished file is reachable from there."""

from api_lib import (FAILURE_STATE, STATUS_FIELD, SUCCESS_STATE, after, before,
                     enum_values, export_starts, fail, flatten, has_path_param,
                     name_tokens, new_operations, ok, success_schema)

RESULT = {"url", "uri", "href", "link", "location", "download", "result", "file"}
DOWNLOAD = {"download", "result", "results", "file", "content"}
old, new = before(), after()


def status_fields(schema) -> dict:
    props = flatten(new, schema)["properties"]
    return {name: prop for name, prop in props.items() if STATUS_FIELD.match(name)}


starts = export_starts(old, new)
if not starts:
    fail("no new operation starts a customer export")
accepted = [f"{m.upper()} {p}" for p, m, op, _ in starts
            if "202" in (op.get("responses") or {})
            or (success_schema(new, op) is not None and status_fields(success_schema(new, op)))]
if not accepted:
    fail("starting an export returns neither 202 nor an operation with a status; "
         "a client cannot tell the work is still running")

followed = []
for path, method, op, _ in new_operations(old, new):
    body = success_schema(new, op) if method == "get" and has_path_param(path) else None
    for name, prop in (status_fields(body) if body is not None else {}).items():
        values = enum_values(new, prop)
        if any(SUCCESS_STATE.search(v) for v in values) and any(FAILURE_STATE.search(v) for v in values):
            followed.append((path, name, values, body))
if not followed:
    fail("no new GET returns the export's state with defined success and failure values")

linked = any(any(name_tokens(k) & RESULT for k in flatten(new, body)["properties"])
             for _, _, _, body in followed)
download = [p for p, m, _, _ in new_operations(old, new)
            if m == "get" and any(name_tokens(s) & DOWNLOAD for s in p.split("/"))]
if not (linked or download):
    fail("the export's status gives no way to fetch the finished file")
path, name, values, _ = followed[0]
ok(f"{accepted[0]} starts it; GET {path} reports {name} {values}")

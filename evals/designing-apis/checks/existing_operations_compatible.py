#!/usr/bin/env python3
"""Every operation that existed before still works for a client written against the
old contract: same path and method, no newly required inputs, success statuses kept,
and success bodies keep their type and fields."""

from api_lib import (after, before, deref, fail, flatten, json_schema, ok, op_key,
                     operations, parameters, schema_type)

old, new = before(), after()
new_ops = {op_key(p, m): (op, item) for p, m, op, item in operations(new)}
problems = []


def compatible_body(where: str, old_schema, new_schema) -> None:
    if old_schema is None:
        return
    if new_schema is None:
        problems.append(f"{where}: success body removed")
        return
    old_type = schema_type(old, old_schema)
    variants = [new_schema] + [deref(new, v) for k in ("oneOf", "anyOf")
                               for v in (deref(new, new_schema) or {}).get(k) or []]
    if not any(schema_type(new, v) == old_type for v in variants):
        problems.append(f"{where}: success body changed from {old_type} to "
                        f"{schema_type(new, new_schema) or 'another shape'}")
        return
    if old_type == "object":
        same = next(v for v in variants if schema_type(new, v) == old_type)
        old_props = flatten(old, old_schema)["properties"]
        new_props = flatten(new, same)["properties"]
        for name, prop in old_props.items():
            if name not in new_props:
                problems.append(f"{where}: response field {name} removed")
            elif schema_type(old, prop) and schema_type(new, new_props[name]) not in (
                    None, schema_type(old, prop)):
                problems.append(f"{where}: response field {name} changed type")
    if old_type == "array":
        old_items = deref(old, (deref(old, old_schema) or {}).get("items"))
        same = next(v for v in variants if schema_type(new, v) == "array")
        new_items = deref(new, (deref(new, same) or {}).get("items"))
        compatible_body(f"{where} items", old_items, new_items)


for path, method, op, item in operations(old):
    key = op_key(path, method)
    if key not in new_ops:
        problems.append(f"{key}: removed")
        continue
    new_op, new_item = new_ops[key]
    old_params = {(p.get("name"), p.get("in")): p for p in parameters(old, item, op)}
    for param in parameters(new, new_item, new_op):
        ident = (param.get("name"), param.get("in"))
        was_required = old_params.get(ident, {}).get("required", False)
        if param.get("required") and not was_required:
            problems.append(f"{key}: parameter {ident[0]} ({ident[1]}) is now required")
    old_body, new_body = deref(old, op.get("requestBody")), deref(new, new_op.get("requestBody"))
    if new_body and new_body.get("required") and not (old_body or {}).get("required"):
        problems.append(f"{key}: request body is now required")
    if old_body and new_body:
        old_req = flatten(old, json_schema(old, old_body))["required"]
        new_req = flatten(new, json_schema(new, new_body))["required"]
        for name in sorted(new_req - old_req):
            problems.append(f"{key}: request field {name} is now required")
    for status, response in (op.get("responses") or {}).items():
        if not status.startswith("2"):
            continue
        if status not in (new_op.get("responses") or {}):
            problems.append(f"{key}: success status {status} removed")
            continue
        compatible_body(f"{key} {status}", json_schema(old, response),
                        json_schema(new, new_op["responses"][status]))

if problems:
    fail("breaking changes for existing clients:\n- " + "\n- ".join(problems))
ok("every existing operation is still compatible")

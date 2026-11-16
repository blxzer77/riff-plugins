#!/usr/bin/env python3
"""An items list takes an opaque cursor and a page size with a maximum. Offsets and
page numbers skip or repeat items while the data changes underneath.

A list of items is any GET whose success body is an array of the fixture's Item
schema, or an object holding one, whatever its path is called."""

import re

from api_lib import (after, before, deref, fail, flatten, ok, operations, parameters,
                     schema_type, success_schema)

CURSOR = re.compile(r"cursor|page[-_]?token|^after$|starting[-_]?after|continuation|next[-_]?token", re.I)
OFFSET = re.compile(r"^(offset|page|skip|page[-_]?number|start)$", re.I)
SIZE = re.compile(r"^(limit|page[-_]?size|per[-_]?page|size|max[-_]?results|count|first)$", re.I)
old, new = before(), after()
item_schema = ((old.get("components") or {}).get("schemas") or {}).get("Item")
item_fields = flatten(old, item_schema)["required"] if item_schema else set()


def holds_items(schema) -> bool:
    schema = deref(new, schema) or {}
    if schema_type(new, schema) == "array":
        return bool(item_fields) and item_fields <= set(flatten(new, schema.get("items"))["properties"])
    return any(schema_type(new, prop) == "array" and holds_items(prop)
               for prop in flatten(new, schema)["properties"].values())


lists = [(p, op, item) for p, m, op, item in operations(new)
         if m == "get" and not p.rstrip("/").endswith("}") and holds_items(success_schema(new, op))]
if not lists:
    fail("no items list operation in the contract")
offset_only = []
unbounded = []
for path, op, item in lists:
    query = [p for p in parameters(new, item, op) if p.get("in") == "query"]
    names = [p.get("name", "") for p in query]
    cursors = [n for n in names if CURSOR.search(n)]
    sizes = [p for p in query if SIZE.match(p.get("name", ""))]
    bounded = [p for p in sizes if "maximum" in (deref(new, p.get("schema")) or {})]
    if cursors and bounded:
        ok(f"GET {path} takes {cursors[0]} and {bounded[0]['name']} "
           f"(max {deref(new, bounded[0]['schema'])['maximum']})")
    if cursors and not bounded:
        unbounded.append(path)
    if not cursors and any(OFFSET.match(n) for n in names):
        offset_only.append(path)
if offset_only:
    fail(f"GET {offset_only[0]} pages by offset or page number, which skips or repeats "
         "items when they change between requests")
if unbounded:
    fail(f"GET {unbounded[0]} takes a cursor but its page size has no maximum")
fail("no items list takes a cursor")

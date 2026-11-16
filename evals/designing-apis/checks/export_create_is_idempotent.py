#!/usr/bin/env python3
"""Retrying the request that starts an export cannot start a second one: the start
takes an idempotency key (header, query, or body), or is a PUT to a client-chosen id."""

import re

from api_lib import (after, before, export_starts, fail, flatten, is_put_to_own_id,
                     json_schema, ok, parameters)

KEY = re.compile(r"idempot|request[-_]?id|client[-_]?(token|reference|request)|dedup", re.I)
old, new = before(), after()
starts = export_starts(old, new)
if not starts:
    fail("no new operation starts a customer export")
for path, method, op, item in starts:
    if is_put_to_own_id(path, method):
        ok(f"PUT {path} takes a client-chosen id")
    names = [p.get("name", "") for p in parameters(new, item, op) if p.get("in") in ("header", "query")]
    body = json_schema(new, op.get("requestBody"))
    if body is not None:
        names += list(flatten(new, body)["properties"])
    keys = [n for n in names if KEY.search(n)]
    if keys:
        ok(f"{method.upper()} {path} takes {keys[0]}")
fail("starting an export takes no idempotency key or client-chosen id; "
     "a retried request after a dropped connection starts a second export")

"""Shared helpers for designing-apis checks.

Checks compare the contract before the run (EVAL_FIXTURE/openapi.json) with the
contract after it (EVAL_WORKDIR/openapi.json). They read names and shapes from the
contract instead of assuming them, so a correct design written differently passes.
"""

from __future__ import annotations

import json
import os
import re
import sys
from pathlib import Path

METHODS = ("get", "put", "post", "delete", "patch")
STATUS_FIELD = re.compile(r"^(status|state|phase)$", re.I)
SUCCESS_STATE = re.compile(r"succe|complete|done|finish|ready|available", re.I)
FAILURE_STATE = re.compile(r"fail|error|cancel|expire|abort", re.I)


def fail(message: str) -> None:
    print(f"FAIL: {message}")
    sys.exit(1)


def ok(message: str) -> None:
    print(f"PASS: {message}")
    sys.exit(0)


def load(env: str) -> dict:
    path = Path(os.environ[env]) / "openapi.json"
    if not path.is_file():
        fail(f"no openapi.json in {env}")
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError as exc:
        fail(f"openapi.json is not valid JSON: {exc}")


def before() -> dict:
    return load("EVAL_FIXTURE")


def after() -> dict:
    return load("EVAL_WORKDIR")


def deref(spec: dict, node, depth: int = 0):
    while isinstance(node, dict) and isinstance(node.get("$ref"), str) and depth < 20:
        ref = node["$ref"]
        if not ref.startswith("#/"):
            fail(f"external $ref is not supported by this check: {ref}")
        target = spec
        for part in ref[2:].split("/"):
            if not isinstance(target, dict) or part not in target:
                fail(f"unresolved $ref {ref}")
            target = target[part]
        node, depth = target, depth + 1
    return node


def operations(spec: dict):
    """(path, method, operation, path item) for every operation."""
    for path, item in (spec.get("paths") or {}).items():
        item = deref(spec, item)
        if not isinstance(item, dict):
            continue
        for method in METHODS:
            if isinstance(item.get(method), dict):
                yield path, method, item[method], item


def parameters(spec: dict, item: dict, op: dict) -> list[dict]:
    merged = {}
    for raw in list(item.get("parameters", [])) + list(op.get("parameters", [])):
        param = deref(spec, raw)
        merged[(param.get("name"), param.get("in"))] = param
    return list(merged.values())


def has_path_param(path: str) -> bool:
    return "{" in path


def json_schema(spec: dict, holder: dict | None):
    """The schema of the first JSON-like media type in a response or request body."""
    holder = deref(spec, holder) if holder else None
    for media, body in ((holder or {}).get("content") or {}).items():
        if "json" in media and isinstance(body, dict) and "schema" in body:
            return deref(spec, body["schema"])
    return None


def success_schema(spec: dict, op: dict):
    for status in ("200", "201", "202"):
        if status in (op.get("responses") or {}):
            return json_schema(spec, op["responses"][status])
    return None


def flatten(spec: dict, schema, _seen: set | None = None) -> dict:
    """Properties and required names of an object schema. allOf parts are merged;
    oneOf/anyOf variants add their properties, since a client may send any of them.
    A schema that refers back to itself is read once."""
    seen = set() if _seen is None else _seen
    schema = deref(spec, schema) or {}
    if not isinstance(schema, dict) or id(schema) in seen:
        return {"properties": {}, "required": set()}
    seen.add(id(schema))
    props, required = dict(schema.get("properties") or {}), set(schema.get("required") or [])
    for part in schema.get("allOf") or []:
        sub = flatten(spec, part, seen)
        props.update(sub["properties"])
        required |= sub["required"]
    for key in ("oneOf", "anyOf"):
        for part in schema.get(key) or []:
            for name, prop in flatten(spec, part, seen)["properties"].items():
                props.setdefault(name, prop)
    return {"properties": {k: deref(spec, v) for k, v in props.items()}, "required": required}


def schema_type(spec: dict, schema) -> str | None:
    schema = deref(spec, schema) or {}
    kind = schema.get("type")
    if isinstance(kind, list):
        kinds = [k for k in kind if k != "null"]
        kind = kinds[0] if len(kinds) == 1 else None
    if kind is None and ("properties" in schema or "allOf" in schema):
        kind = "object"
    return kind


def enum_values(spec: dict, schema, _seen: set | None = None) -> list[str]:
    seen = set() if _seen is None else _seen
    schema = deref(spec, schema) or {}
    if not isinstance(schema, dict) or id(schema) in seen:
        return []
    seen.add(id(schema))
    values = [str(v) for v in schema.get("enum") or []]
    if "const" in schema:
        values.append(str(schema["const"]))
    for key in ("oneOf", "anyOf", "allOf"):
        for part in schema.get(key) or []:
            values += enum_values(spec, part, seen)
    return values


def name_tokens(name: str) -> set[str]:
    """Words in an identifier: download_url, downloadUrl and download-url all give
    {"download", "url"}; profile_id gives {"profile", "id"}."""
    spaced = re.sub(r"([a-z0-9])([A-Z])", r"\1 \2", name)
    return {t.lower() for t in re.split(r"[^A-Za-z0-9]+", spaced) if t}


def op_key(path: str, method: str) -> str:
    return f"{method.upper()} {path}"


def new_operations(old: dict, new: dict):
    existing = {op_key(p, m) for p, m, _, _ in operations(old)}
    return [(p, m, op, item) for p, m, op, item in operations(new) if op_key(p, m) not in existing]


def is_put_to_own_id(path: str, method: str) -> bool:
    """A PUT whose last path segment is the export's own identifier, chosen by the
    client: /exports/{id} or /customers/exports/{export_id}, not /orders/{id}/export."""
    segments = [s for s in path.strip("/").split("/") if s]
    if method != "put" or not segments or not segments[-1].startswith("{"):
        return False
    return "export" in segments[-1].lower() or (len(segments) > 1 and "export" in segments[-2].lower())


def export_starts(old: dict, new: dict):
    """New POST/PUT operations that start an export."""
    starts = []
    for path, method, op, item in new_operations(old, new):
        text = " ".join(str(op.get(k, "")) for k in ("operationId", "summary", "description"))
        if method in ("post", "put") and "export" in f"{path} {text}".lower():
            starts.append((path, method, op, item))
    return starts

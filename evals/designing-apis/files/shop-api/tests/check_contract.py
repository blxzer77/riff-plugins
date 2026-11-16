#!/usr/bin/env python3
"""Check openapi.json: valid references, unique operation IDs, path parameters,
and errors in the Problem format. Usage: python3 tests/check_contract.py [spec]"""

import json
import re
import sys
from pathlib import Path

METHODS = {"get", "put", "post", "delete", "patch", "head", "options"}


def resolve(spec, ref):
    node = spec
    for part in ref.removeprefix("#/").split("/"):
        node = node[part]
    return node


def refs(node):
    if isinstance(node, dict):
        if isinstance(node.get("$ref"), str):
            yield node["$ref"]
        for value in node.values():
            yield from refs(value)
    elif isinstance(node, list):
        for value in node:
            yield from refs(value)


def main():
    path = Path(sys.argv[1]) if len(sys.argv) > 1 else Path(__file__).parent.parent / "openapi.json"
    spec = json.loads(path.read_text(encoding="utf-8"))
    problems = []
    if not re.fullmatch(r"\d+\.\d+\.\d+", spec.get("info", {}).get("version", "")):
        problems.append("info.version must be MAJOR.MINOR.PATCH")
    for ref in refs(spec):
        try:
            resolve(spec, ref)
        except (KeyError, TypeError):
            problems.append(f"unresolved $ref {ref}")
    seen = {}
    for route, item in spec.get("paths", {}).items():
        shared = [resolve(spec, p["$ref"]) if "$ref" in p else p for p in item.get("parameters", [])]
        for method, op in item.items():
            if method not in METHODS:
                continue
            where = f"{method.upper()} {route}"
            op_id = op.get("operationId")
            if not op_id:
                problems.append(f"{where}: missing operationId")
            elif op_id in seen:
                problems.append(f"{where}: operationId {op_id} also used by {seen[op_id]}")
            else:
                seen[op_id] = where
            params = shared + [resolve(spec, p["$ref"]) if "$ref" in p else p
                               for p in op.get("parameters", [])]
            declared = {p.get("name") for p in params if p.get("in") == "path"}
            for name in re.findall(r"{([^}]+)}", route):
                if name not in declared:
                    problems.append(f"{where}: path parameter {name} is not declared")
            for status, response in op.get("responses", {}).items():
                if status[0] not in "45":
                    continue
                target = resolve(spec, response["$ref"]) if "$ref" in response else response
                if "application/problem+json" not in target.get("content", {}):
                    problems.append(f"{where}: {status} must use application/problem+json")
    for problem in problems:
        print(problem)
    print("contract OK" if not problems else f"{len(problems)} problem(s)")
    return 1 if problems else 0


if __name__ == "__main__":
    sys.exit(main())

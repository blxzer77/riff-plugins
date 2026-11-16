#!/usr/bin/env python3
"""svc-config: parseConfig rejects malformed input naming the field, without casts (hidden oracle)."""

import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import re  # noqa: E402

from _ts import code_only, copy_workdir, declared_types, fail, new_escapes, node, node_tests, ts_sources, tsc  # noqa: E402

work = copy_workdir()
r = tsc(work)
if r.returncode != 0:
    fail("tsc reports errors", r.stdout + r.stderr)
r = node_tests(work)
if r.returncode != 0:
    fail("the project's tests fail", r.stdout + r.stderr)

probe = r'''
import assert from "node:assert/strict";
import { parseConfig } from "./src/config.ts";
import { readHosts } from "./src/pool.ts";

const good = {
  service: "orders", port: 8080, logLevel: "warn",
  db: { host: "p", port: 5432, replicas: [{ host: "r1", port: 5433 }] },
};
const parsed = parseConfig(JSON.stringify(good));
assert.deepEqual(readHosts(parsed), ["p:5432", "r1:5433"]);
assert.equal(parsed.service, "orders");
assert.equal(parsed.logLevel, "warn");

const clone = () => JSON.parse(JSON.stringify(good));
const cases: Array<[string, (c: any) => unknown, RegExp]> = [
  ["replicas is an object", (c) => { c.db.replicas = { host: "r1", port: 5433 }; }, /replicas/],
  ["replica without port", (c) => { c.db.replicas = [{ host: "r1" }]; }, /port/],
  ["db.host is a number", (c) => { c.db.host = 5; }, /host/],
  ["port is a string", (c) => { c.port = "8080"; }, /port/],
  ["unknown logLevel", (c) => { c.logLevel = "verbose"; }, /logLevel/],
  ["service missing", (c) => { delete c.service; }, /service/],
  ["db missing", (c) => { delete c.db; }, /db/],
];
for (const [name, mutate, field] of cases) {
  const c = clone();
  mutate(c);
  let error: unknown;
  try { parseConfig(JSON.stringify(c)); } catch (e) { error = e; }
  assert.ok(error instanceof Error, `${name}: accepted`);
  assert.match(String((error as Error).message), field, `${name}: message does not name the field`);
}
for (const text of ["[]", "null", "42"]) {
  assert.throws(() => parseConfig(text), `${text} accepted`);
}
'''
r = node(work, probe)
if r.returncode != 0:
    fail("malformed configs are not all rejected with the field named", r.stdout + r.stderr)

escapes = new_escapes("svc-config", work)
if escapes:
    fail(f"new type escapes: {escapes}")
# Asserting parsed data into a declared type (as Config, as LogLevel, as Config["db"], as "info")
# skips the check the task is about. Narrowing helpers such as `as Record<string, unknown>`
# after a typeof test are allowed.
text = code_only(ts_sources(work).get("src/config.ts", ""))
domain = declared_types(text) | {"Config", "Replica"}
casts = re.findall(r"\bas\s+(" + "|".join(sorted(domain)) + r")\b", text)
casts += re.findall(r"\bas\s+[\"']", text)
if casts:
    fail(f"parsed data asserted into declared types in config.ts: {casts}")
print("PASS: malformed configs fail at load naming the field; no casts or escapes")

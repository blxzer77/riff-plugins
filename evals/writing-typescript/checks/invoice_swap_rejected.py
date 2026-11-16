#!/usr/bin/env python3
"""invoicing: the swapped call is fixed, and passing a customer's name as the recipient no longer compiles."""

import os
import re
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from _ts import ASSERTION, code_only, copy_workdir, fail, new_escapes, node, node_tests, ts_sources, tsc  # noqa: E402

work = copy_workdir()
r = tsc(work)
if r.returncode != 0:
    fail("tsc reports errors", r.stdout + r.stderr)
r = node_tests(work)
if r.returncode != 0:
    fail("the project's tests fail", r.stdout + r.stderr)
r = node(work, r'''
import assert from "node:assert/strict";
import { billCustomer } from "./src/billing.ts";
import { outbox } from "./src/mailer.ts";
outbox.length = 0;
billCustomer({ id: "c1", full_name: "Ana Ruiz", email: " Ana@Example.com " }, 500);
assert.equal(outbox.length, 1);
assert.equal(outbox[0].to, "ana@example.com");
assert.match(outbox[0].body, /Dear Ana Ruiz,/);
''')
if r.returncode != 0:
    fail("billCustomer still addresses the invoice wrongly", r.stdout + r.stderr)

probe = work / "src" / "__swap_probe.ts"
probe.write_text('import { sendInvoice } from "./mailer.ts";\n'
                 'import type { Customer } from "./customers.ts";\n'
                 'declare const c: Customer;\n'
                 'sendInvoice(c.name, c.email, 100);\n', encoding="utf-8")
r = tsc(work)
if r.returncode == 0 or "__swap_probe.ts" not in (r.stdout + r.stderr):
    fail("sendInvoice(customer.name, customer.email, ...) still type-checks")
probe.unlink()

escapes = new_escapes("invoicing", work)
if escapes:
    fail(f"new type escapes: {escapes}")
cast_files = [f for f, text in ts_sources(work).items()
              if ASSERTION.findall(code_only(text))]
if len(cast_files) > 1:
    fail(f"type assertions spread over {cast_files}; only one constructor should create the checked type")
print("PASS: call fixed; a swapped recipient fails tsc; casts confined to one place")

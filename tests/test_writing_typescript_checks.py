"""Validates the writing-typescript eval checks: untouched fixtures fail, sound solutions in
different styles pass, and near misses (casts, kept defaults, `!`, partial fixes) fail.
Needs tsc: set TSC or put tsc on PATH; skipped otherwise."""

from __future__ import annotations

import os
import shutil
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

REPO = Path(__file__).resolve().parent.parent
EVALS = REPO / "evals" / "writing-typescript"
TSC = os.environ.get("TSC") or shutil.which("tsc")
NODE = shutil.which("node")

CONFIG_GOOD = '''export interface Replica { host: string; port: number }
export type LogLevel = "debug" | "info" | "warn" | "error";
export interface Config {
  service: string;
  port: number;
  logLevel: LogLevel;
  db: { host: string; port: number; replicas: Replica[] };
}
const LEVELS: readonly LogLevel[] = ["debug", "info", "warn", "error"];

function record(v: unknown, path: string): Record<string, unknown> {
  if (typeof v !== "object" || v === null || Array.isArray(v)) throw new Error(`${path} must be an object`);
  return Object.fromEntries(Object.entries(v));
}
function str(o: Record<string, unknown>, key: string, path: string): string {
  const v = o[key];
  if (typeof v !== "string" || v === "") throw new Error(`${path}${key} must be a non-empty string`);
  return v;
}
function int(o: Record<string, unknown>, key: string, path: string): number {
  const v = o[key];
  if (typeof v !== "number" || !Number.isInteger(v)) throw new Error(`${path}${key} must be an integer`);
  return v;
}
function level(v: unknown): LogLevel {
  const found = LEVELS.find((l) => l === v);
  if (found === undefined) throw new Error(`logLevel must be one of ${LEVELS.join(", ")}`);
  return found;
}
export function parseConfig(text: string): Config {
  const root = record(JSON.parse(text), "config");
  const db = record(root["db"], "db");
  const replicas = db["replicas"];
  if (!Array.isArray(replicas)) throw new Error("db.replicas must be a list");
  return {
    service: str(root, "service", ""),
    port: int(root, "port", ""),
    logLevel: level(root["logLevel"]),
    db: {
      host: str(db, "host", "db."),
      port: int(db, "port", "db."),
      replicas: replicas.map((r: unknown, i) => {
        const o = record(r, `db.replicas[${i}]`);
        return { host: str(o, "host", `db.replicas[${i}].`), port: int(o, "port", `db.replicas[${i}].`) };
      }),
    },
  };
}
'''
CONFIG_GOOD_RECORD_CAST = CONFIG_GOOD.replace(
    "  return Object.fromEntries(Object.entries(v));",
    "  return v as Record<string, unknown>;")
CONFIG_LEVEL_CAST = CONFIG_GOOD.replace(
    "  const found = LEVELS.find((l) => l === v);\n"
    "  if (found === undefined) throw new Error(`logLevel must be one of ${LEVELS.join(\", \")}`);\n"
    "  return found;",
    "  if (typeof v !== \"string\") throw new Error(\"logLevel must be a string\");\n"
    "  return v as LogLevel;")
CONFIG_PARTIAL = '''export interface Replica { host: string; port: number }
export interface Config {
  service: string; port: number; logLevel: "debug" | "info" | "warn" | "error";
  db: { host: string; port: number; replicas: Replica[] };
}
export function parseConfig(text: string): Config {
  const config = JSON.parse(text) as Config;
  if (!Array.isArray(config.db.replicas)) throw new Error("db.replicas must be a list");
  return config;
}
'''
CONFIG_CHECKED_THEN_CAST = CONFIG_GOOD.replace(
    "export function parseConfig(text: string): Config {",
    "export function parseConfigChecked(text: string): Config {") + '''
export function parseConfig(text: string): Config {
  const raw: unknown = JSON.parse(text);
  parseConfigChecked(text);
  return raw as Config;
}
'''

EVENTS_RENAMED = '''export type ActivityEvent =
  | { kind: "created"; id: string; title: string }
  | { kind: "deleted"; id: string; title: string }
  | { kind: "commented"; id: string; author: string; text: string }
  | { kind: "renamed"; id: string; from: string; to: string };
'''
FEED_NEVER = '''import type { ActivityEvent } from "./events.ts";

export function assertNever(value: never): never {
  throw new Error(`Unhandled activity: ${JSON.stringify(value)}`);
}

export function describe(event: ActivityEvent): string {
  switch (event.kind) {
    case "created": return `Created "${event.title}"`;
    case "deleted": return `Deleted "${event.title}"`;
    case "commented": return `${event.author} commented: ${event.text}`;
    case "renamed": return `Renamed "${event.from}" to "${event.to}"`;
    default: return assertNever(event);
  }
}
'''
ICONS_RECORD = '''import type { ActivityEvent } from "./events.ts";

const ICONS: Record<ActivityEvent["kind"], string> = {
  created: "➕", deleted: "🗑️", commented: "💬", renamed: "✏️",
};

export function iconFor(event: ActivityEvent): string {
  return ICONS[event.kind];
}
'''
FEED_DEFAULT = FEED_NEVER.replace("default: return assertNever(event);", 'default: return "Unknown activity";')
ICONS_DEFAULT = '''import type { ActivityEvent } from "./events.ts";

export function iconFor(event: ActivityEvent): string {
  switch (event.kind) {
    case "created": return "➕";
    case "deleted": return "🗑️";
    case "commented": return "💬";
    case "renamed": return "✏️";
    default: return "•";
  }
}
'''

SESSIONS_FILE = (EVALS / "files" / "sessions" / "src" / "sessions.ts")
LAST_SEEN_GOOD = '''
  /** When the user was last active: end of the latest session, or now if one is open. */
  lastSeen(userId: string, now: number = Date.now()): number | undefined {
    let latest: number | undefined;
    for (const s of this.sessionsFor(userId)) {
      const end = s.endedAt ?? now;
      if (latest === undefined || end > latest) latest = end;
    }
    return latest;
  }
}
'''
LAST_SEEN_BANG = '''
  lastSeen(userId: string, now: number = Date.now()): number {
    const sorted = [...this.sessionsFor(userId)].sort((a, b) => a.startedAt - b.startedAt);
    const last = sorted[sorted.length - 1]!;
    return last.endedAt ?? now;
  }
}
'''
LAST_SEEN_ZERO = '''
  lastSeen(userId: string, now: number = Date.now()): number {
    let latest = 0;
    for (const s of this.sessionsFor(userId)) latest = Math.max(latest, s.endedAt ?? now);
    return latest;
  }
}
'''
LAST_SEEN_INSERTION = '''
  lastSeen(userId: string, now: number = Date.now()): number | undefined {
    const list = this.sessionsFor(userId);
    const last = list.at(-1);
    return last === undefined ? undefined : last.endedAt ?? now;
  }
}
'''

CUSTOMERS_BRAND = '''/** Row as it comes back; the brand is created only here. */
export type Email = string & { readonly __brand: "Email" };

export function parseEmail(raw: string): Email {
  const email = raw.trim().toLowerCase();
  if (!/^[^@\\s]+@[^@\\s]+$/.test(email)) throw new Error(`not an email address: ${raw}`);
  return email as Email;
}

export interface Customer { id: string; name: string; email: Email }
export interface CustomerRow { id: string; full_name: string; email: string }

export function customerFromRow(row: CustomerRow): Customer {
  return { id: row.id, name: row.full_name, email: parseEmail(row.email) };
}
'''
MAILER_BRAND = (EVALS / "files" / "invoicing" / "src" / "mailer.ts").read_text(encoding="utf-8").replace(
    "export function sendInvoice(to: string,", "export function sendInvoice(to: Email,").replace(
    "export interface Outgoing", 'import type { Email } from "./customers.ts";\n\nexport interface Outgoing')
BILLING_FIXED = '''import { customerFromRow, type CustomerRow } from "./customers.ts";
import { sendInvoice } from "./mailer.ts";

export function billCustomer(row: CustomerRow, amountCents: number): void {
  const customer = customerFromRow(row);
  sendInvoice(customer.email, customer.name, amountCents);
}
'''
MAILER_OBJECT = '''export interface Outgoing { to: string; subject: string; body: string }
export const outbox: Outgoing[] = [];

export function sendInvoice(invoice: { to: string; customerName: string; amountCents: number }): void {
  const amount = (invoice.amountCents / 100).toFixed(2);
  outbox.push({
    to: invoice.to,
    subject: `Your invoice: $${amount}`,
    body: `Dear ${invoice.customerName},\\n\\nYour invoice for $${amount} is attached.\\n`,
  });
}
'''
BILLING_OBJECT = '''import { customerFromRow, type CustomerRow } from "./customers.ts";
import { sendInvoice } from "./mailer.ts";

export function billCustomer(row: CustomerRow, amountCents: number): void {
  const customer = customerFromRow(row);
  sendInvoice({ to: customer.email, customerName: customer.name, amountCents });
}
'''
MAILER_TEST_OBJECT = '''import { test } from "node:test";
import assert from "node:assert/strict";
import { outbox, sendInvoice } from "../src/mailer.ts";

test("formats the amount", () => {
  outbox.length = 0;
  sendInvoice({ to: "ana@example.com", customerName: "Ana Ruiz", amountCents: 12345 });
  assert.equal(outbox[0]?.subject, "Your invoice: $123.45");
});
'''
CUSTOMERS_BRAND_LOOSE = CUSTOMERS_BRAND.replace("email: parseEmail(row.email) };",
                                                "email: row.email.trim().toLowerCase() as Email };")
BILLING_BRAND_CAST = BILLING_FIXED.replace(
    'import { sendInvoice } from "./mailer.ts";',
    'import { sendInvoice } from "./mailer.ts";\nimport type { Email } from "./customers.ts";').replace(
    "sendInvoice(customer.email,", "sendInvoice(customer.email as Email,")


@unittest.skipUnless(TSC and NODE, "needs tsc (set TSC) and node")
class WritingTypescriptChecks(unittest.TestCase):
    def run_check(self, fixture: str, check: str, files: dict[str, str] | None = None) -> bool:
        with tempfile.TemporaryDirectory() as tmp:
            work = Path(tmp) / fixture
            shutil.copytree(EVALS / "files" / fixture, work)
            for rel, text in (files or {}).items():
                (work / rel).write_text(text, encoding="utf-8")
            r = subprocess.run([sys.executable, str(EVALS / "checks" / f"{check}.py")],
                               env={**os.environ, "EVAL_WORKDIR": str(work), "TSC": TSC},
                               capture_output=True, text=True, timeout=300)
            return r.returncode == 0

    def test_untouched_fixtures_fail(self):
        for fixture, check in (("svc-config", "config_rejected_at_load"),
                               ("activity-feed", "feed_exhaustive"),
                               ("sessions", "last_seen_absent"),
                               ("invoicing", "invoice_swap_rejected")):
            self.assertFalse(self.run_check(fixture, check), fixture)

    def test_config(self):
        self.assertTrue(self.run_check("svc-config", "config_rejected_at_load", {"src/config.ts": CONFIG_GOOD}))
        self.assertNotEqual(CONFIG_GOOD_RECORD_CAST, CONFIG_GOOD)
        self.assertNotEqual(CONFIG_LEVEL_CAST, CONFIG_GOOD)
        self.assertTrue(self.run_check("svc-config", "config_rejected_at_load",
                                       {"src/config.ts": CONFIG_GOOD_RECORD_CAST}))
        self.assertFalse(self.run_check("svc-config", "config_rejected_at_load", {"src/config.ts": CONFIG_LEVEL_CAST}))
        self.assertFalse(self.run_check("svc-config", "config_rejected_at_load", {"src/config.ts": CONFIG_PARTIAL}))
        self.assertFalse(self.run_check("svc-config", "config_rejected_at_load",
                                        {"src/config.ts": CONFIG_CHECKED_THEN_CAST}))

    def test_feed(self):
        good = {"src/events.ts": EVENTS_RENAMED, "src/feed.ts": FEED_NEVER, "src/icons.ts": ICONS_RECORD}
        self.assertTrue(self.run_check("activity-feed", "feed_exhaustive", good))
        self.assertFalse(self.run_check("activity-feed", "feed_exhaustive",
                                        {**good, "src/feed.ts": FEED_DEFAULT, "src/icons.ts": ICONS_DEFAULT}))
        self.assertFalse(self.run_check("activity-feed", "feed_exhaustive", {**good, "src/icons.ts": ICONS_DEFAULT}))

    def test_sessions(self):
        base = SESSIONS_FILE.read_text(encoding="utf-8").rstrip()
        assert base.endswith("}")
        with_method = lambda body: {"src/sessions.ts": base[:-1] + body}  # noqa: E731
        self.assertTrue(self.run_check("sessions", "last_seen_absent", with_method(LAST_SEEN_GOOD)))
        for body in (LAST_SEEN_BANG, LAST_SEEN_ZERO, LAST_SEEN_INSERTION):
            self.assertFalse(self.run_check("sessions", "last_seen_absent", with_method(body)), body)

    def test_invoicing(self):
        brand = {"src/customers.ts": CUSTOMERS_BRAND, "src/mailer.ts": MAILER_BRAND, "src/billing.ts": BILLING_FIXED}
        self.assertTrue(self.run_check("invoicing", "invoice_swap_rejected", brand))
        self.assertTrue(self.run_check("invoicing", "invoice_swap_rejected",
                                       {"src/mailer.ts": MAILER_OBJECT, "src/billing.ts": BILLING_OBJECT,
                                        "tests/mailer.test.ts": MAILER_TEST_OBJECT}))
        self.assertFalse(self.run_check("invoicing", "invoice_swap_rejected", {"src/billing.ts": BILLING_FIXED}))
        self.assertFalse(self.run_check("invoicing", "invoice_swap_rejected",
                                        {**brand, "src/customers.ts": CUSTOMERS_BRAND_LOOSE,
                                         "src/billing.ts": BILLING_BRAND_CAST}))


if __name__ == "__main__":
    unittest.main()

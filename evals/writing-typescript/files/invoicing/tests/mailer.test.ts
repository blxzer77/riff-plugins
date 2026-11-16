import { test } from "node:test";
import assert from "node:assert/strict";
import { outbox, sendInvoice } from "../src/mailer.ts";

test("formats the amount", () => {
  outbox.length = 0;
  sendInvoice("ana@example.com", "Ana Ruiz", 12345);
  assert.equal(outbox[0]?.subject, "Your invoice: $123.45");
});

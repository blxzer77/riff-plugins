import { test } from "node:test";
import assert from "node:assert/strict";
import { SessionStore } from "../src/sessions.ts";

test("totalMinutes counts open sessions up to now", () => {
  const store = new SessionStore();
  store.add({ userId: "u1", startedAt: 0, endedAt: 600_000 });
  store.add({ userId: "u1", startedAt: 1_000_000, endedAt: null });
  assert.equal(store.totalMinutes("u1", 1_300_000), 15);
  assert.equal(store.totalMinutes("nobody"), 0);
});

import { test } from "node:test";
import assert from "node:assert/strict";
import { describe } from "../src/feed.ts";
import { iconFor } from "../src/icons.ts";

test("describes each event", () => {
  assert.equal(describe({ kind: "created", id: "1", title: "Q3 plan" }), 'Created "Q3 plan"');
  assert.equal(describe({ kind: "commented", id: "1", author: "Ana", text: "ok" }), "Ana commented: ok");
  assert.equal(iconFor({ kind: "deleted", id: "1", title: "x" }), "🗑️");
});

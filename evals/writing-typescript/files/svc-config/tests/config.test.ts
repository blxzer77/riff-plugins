import { test } from "node:test";
import assert from "node:assert/strict";
import { readFileSync } from "node:fs";
import { parseConfig } from "../src/config.ts";
import { readHosts } from "../src/pool.ts";

test("example config lists primary then replicas", () => {
  const config = parseConfig(readFileSync(new URL("../config.example.json", import.meta.url), "utf8"));
  assert.deepEqual(readHosts(config), [
    "db-primary.internal:5432",
    "db-replica-1.internal:5432",
    "db-replica-2.internal:5432",
  ]);
});

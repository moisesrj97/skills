import { test } from "node:test";
import assert from "node:assert/strict";
import { load, width } from "../src/loader.ts";

test("load delegates to legacy", () => {
  assert.equal(load(), "legacy");
  assert.equal(width({ offsetWidth: 3 }), 3);
});

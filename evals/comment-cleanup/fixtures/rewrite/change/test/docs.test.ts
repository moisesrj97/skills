import { test } from "node:test";
import assert from "node:assert/strict";
import { retryDelay, owner, visible } from "../src/docs.ts";
import { flag } from "../src/access.ts";

test("retry delay doubles", () => {
  assert.equal(retryDelay(0), 1500);
  assert.equal(retryDelay(2), 6000);
});

test("owner rejects malformed email", () => {
  assert.equal(owner({ email: "a@b.io", roles: [] }), "a@b.io");
  assert.throws(() => owner({ email: "a b@c", roles: [] }));
});

test("admins see drafts", () => {
  const docs = [{ title: "x", draft: true }, { title: "y", draft: false }];
  const admin = { email: "a", roles: ["admin"] };
  assert.equal(flag(admin), true);
  assert.equal(visible(admin, docs).length, 2);
  assert.equal(visible({ email: "b", roles: [] }, docs).length, 1);
});

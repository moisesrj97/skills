import { test } from "node:test";
import assert from "node:assert/strict";
import { save, purge, count } from "../src/session.ts";

test("purge removes expired sessions", () => {
  // Arrange
  save({ id: "a", userId: "u", expiresAt: 10 });
  save({ id: "b", userId: "u", expiresAt: 100 });
  // Act
  const removed = purge(50);
  // Assert
  assert.equal(removed, 1);
  assert.equal(count(), 1);
});

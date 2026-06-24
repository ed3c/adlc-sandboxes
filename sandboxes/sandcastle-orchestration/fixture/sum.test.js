import test from "node:test";
import assert from "node:assert";
import { sum } from "./sum.js";

test("sum adds two numbers", () => {
  assert.strictEqual(sum(2, 3), 5);
  assert.strictEqual(sum(-1, 1), 0);
});

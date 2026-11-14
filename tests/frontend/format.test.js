import assert from "node:assert/strict";
import { test } from "node:test";

import { conf, pct } from "../../frontend/js/ui.js";

test("percent formatters round and add units", () => {
  assert.equal(pct(64.6), "65%");
  assert.equal(conf(0.874), "87%");
  assert.equal(conf(0), "0%");
});

// Frontend Grid Game rules must agree with the server replay (shared cases in tests/fixtures).
import assert from "node:assert/strict";
import { readFileSync } from "node:fs";
import { test } from "node:test";

import { simulate } from "../../frontend/js/grid.js";

const read = (path) => JSON.parse(readFileSync(new URL(path, import.meta.url), "utf8"));
const levels = Object.fromEntries(
  read("../../backend/data/lessons.json").grid_levels.map((l) => [l.id, l]),
);
const cases = read("../fixtures/grid_cases.json");

for (const { level, moves, solved } of cases) {
  test(`${level}: ${moves.length} moves ${solved ? "reach" : "miss"} the goal`, () => {
    const end = simulate(levels[level], moves).at(-1);
    assert.equal(end[0] === levels[level].goal[0] && end[1] === levels[level].goal[1], solved);
  });
}

test("walls and edges block movement", () => {
  const level = { start: [0, 0], goal: [4, 4], walls: [[1, 0]] };
  assert.deepEqual(simulate(level, ["right", "up", "left"]).at(-1), [0, 0]);
});

test("stops recording once the goal is reached", () => {
  const level = { start: [0, 0], goal: [1, 0], walls: [] };
  assert.equal(simulate(level, ["right", "right", "right"]).length, 2);
});

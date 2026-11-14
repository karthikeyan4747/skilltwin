// Grid Game rules (pure): mirrors backend/core/grid.py so the animation matches server replay.
export const GRID_SIZE = 5;
const DELTAS = { up: [0, -1], down: [0, 1], left: [-1, 0], right: [1, 0] };

/** Positions visited for a move list; walls and edges block a move, reaching the goal stops. */
export function simulate(level, moves) {
  const walls = new Set(level.walls.map(([x, y]) => `${x},${y}`));
  let [x, y] = level.start;
  const path = [[x, y]];
  for (const move of moves) {
    const [dx, dy] = DELTAS[move];
    const [nx, ny] = [x + dx, y + dy];
    const inside = nx >= 0 && nx < GRID_SIZE && ny >= 0 && ny < GRID_SIZE;
    if (inside && !walls.has(`${nx},${ny}`)) [x, y] = [nx, ny];
    path.push([x, y]);
    if (x === level.goal[0] && y === level.goal[1]) break;
  }
  return path;
}

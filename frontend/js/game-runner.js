// Runs learner JavaScript for the Grid Game in a fresh worker with a 1 s timeout; always terminated.
const TIMEOUT_MS = 1000;
const PRELUDE_URL = new URL("/js/workers/game-worker.js", location.origin).href;

export function runGameCode(code) {
  const source = `importScripts(${JSON.stringify(PRELUDE_URL)});\ntry {\n${code}\n;__finish();\n} catch (error) { __fail(error); }\n`;
  const url = URL.createObjectURL(new Blob([source], { type: "text/javascript" }));
  const worker = new Worker(url);
  return new Promise((resolve) => {
    const finish = (result) => {
      window.clearTimeout(timer);
      worker.terminate();
      URL.revokeObjectURL(url);
      resolve(result);
    };
    const timer = window.setTimeout(() => finish({ ok: false, error: "Stopped: your code ran longer than 1 s.", moves: [] }), TIMEOUT_MS);
    worker.onmessage = ({ data }) => finish(data);
    worker.onerror = (event) => {
      event.preventDefault();
      finish({ ok: false, error: event.message || "Your code has an error.", moves: [] });
    };
  });
}

export function simulate(level, moves) {
  const walls = new Set(level.walls.map(([x, y]) => `${x},${y}`));
  let [x, y] = level.start;
  const path = [[x, y]];
  const deltas = { up: [0, -1], down: [0, 1], left: [-1, 0], right: [1, 0] };
  for (const move of moves) {
    const [dx, dy] = deltas[move];
    const [nx, ny] = [x + dx, y + dy];
    if (nx >= 0 && nx < 5 && ny >= 0 && ny < 5 && !walls.has(`${nx},${ny}`)) [x, y] = [nx, ny];
    path.push([x, y]);
    if (x === level.goal[0] && y === level.goal[1]) break;
  }
  return path;
}

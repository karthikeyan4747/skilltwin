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

// Lazily starts the Pyodide worker; each run has a 3 s timeout, after which the worker is terminated.
const RUN_TIMEOUT_MS = 3000;
const LOAD_TIMEOUT_MS = 60000;

let worker = null;
let loading = null;
let seq = 0;
const pending = new Map();

function spawn() {
  worker = new Worker("/js/workers/pyodide-worker.js");
  worker.onmessage = ({ data }) => {
    const entry = pending.get(data.id);
    if (!entry) return;
    pending.delete(data.id);
    window.clearTimeout(entry.timer);
    if (data.ok) entry.resolve(data.result);
    else entry.reject(new Error(data.error));
  };
}

function call(kind, payload, timeout) {
  if (!worker) spawn();
  const id = ++seq;
  return new Promise((resolve, reject) => {
    const timer = window.setTimeout(() => {
      pending.delete(id);
      stopPython();
      reject(new Error(`Stopped: the code ran longer than ${timeout / 1000} s.`));
    }, timeout);
    pending.set(id, { resolve, reject, timer });
    worker.postMessage({ id, kind, ...payload });
  });
}

export function ensurePython() {
  loading ||= call("load", {}, LOAD_TIMEOUT_MS).catch((error) => {
    loading = null;
    throw error;
  });
  return loading;
}

export async function runPython(kind, payload) {
  await ensurePython();
  return call(kind, payload, RUN_TIMEOUT_MS);
}

export function stopPython() {
  worker?.terminate();
  worker = null;
  loading = null;
  pending.forEach((entry) => {
    window.clearTimeout(entry.timer);
    entry.reject(new Error("Python worker stopped."));
  });
  pending.clear();
}

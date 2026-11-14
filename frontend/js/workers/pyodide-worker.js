// Runs learner Python in the browser with Pyodide (never on the server).
/* global loadPyodide */
const PYODIDE_URL = "https://cdn.jsdelivr.net/pyodide/v0.26.4/full/";

const TRACE_PY = `
import sys, io, json, contextlib
MAX_STEPS = 500
steps, out = [], io.StringIO()

class StepLimit(Exception):
    pass

def show(value):
    try:
        text = repr(value)
    except Exception:
        text = "<unprintable>"
    return text[:80]

def tracer(frame, event, arg):
    if frame.f_code.co_filename != "<lesson>":
        return tracer
    if event in ("line", "return"):
        if len(steps) >= MAX_STEPS:
            raise StepLimit()
        local = {k: show(v) for k, v in frame.f_locals.items()
                 if not k.startswith("__") and not callable(v) and type(v).__name__ != "module"}
        steps.append({"line": frame.f_lineno, "event": event, "func": frame.f_code.co_name,
                      "locals": local, "stdout": out.getvalue()[-1000:]})
    return tracer

error = None
try:
    code = compile(user_code, "<lesson>", "exec")
    sys.settrace(tracer)
    with contextlib.redirect_stdout(out):
        exec(code, {"__name__": "__lesson__"})
except StepLimit:
    error = f"Stopped after {MAX_STEPS} steps."
except Exception as exc:
    error = f"{type(exc).__name__}: {exc}"
finally:
    sys.settrace(None)
json.dumps({"steps": steps, "stdout": out.getvalue()[-2000:], "error": error})
`;

const TESTS_PY = `
import io, json, contextlib
scope, out, results, error = {"__name__": "__exercise__"}, io.StringIO(), [], None
try:
    with contextlib.redirect_stdout(out):
        exec(compile(user_code, "<exercise>", "exec"), scope)
except Exception as exc:
    error = f"{type(exc).__name__}: {exc}"
tests = [line for line in test_code.splitlines() if line.strip()]
for line in tests:
    if error:
        results.append({"test": line, "ok": False})
        continue
    try:
        exec(line, scope)
        results.append({"test": line, "ok": True})
    except Exception as exc:
        results.append({"test": line, "ok": False, "error": f"{type(exc).__name__}: {exc}"[:200]})
json.dumps({"passed": sum(r["ok"] for r in results), "total": len(tests),
            "results": results, "error": error, "stdout": out.getvalue()[-2000:]})
`;

let pyodide = null;

async function boot() {
  if (!pyodide) {
    importScripts(`${PYODIDE_URL}pyodide.js`);
    pyodide = loadPyodide({ indexURL: PYODIDE_URL });
  }
  return pyodide;
}

self.onmessage = async (event) => {
  const { id, kind, code = "", tests = "" } = event.data;
  try {
    const py = await boot();
    if (kind === "load") {
      self.postMessage({ id, ok: true });
      return;
    }
    const scope = py.globals.get("dict")();
    scope.set("user_code", code);
    scope.set("test_code", tests);
    const raw = py.runPython(kind === "trace" ? TRACE_PY : TESTS_PY, { globals: scope });
    scope.destroy();
    self.postMessage({ id, ok: true, result: JSON.parse(raw) });
  } catch (error) {
    self.postMessage({ id, ok: false, error: String(error?.message || error).slice(-400) });
  }
};

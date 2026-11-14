// Code Visualizer: Python traced line by line in the Pyodide worker, with Prev/Next/Reset.
import { runPython } from "../python-runner.js";
import { button, card, el, withLoading } from "../ui.js";

export function visualizer(panel, snippets) {
  const picker = el(
    "select",
    { id: "snippet" },
    snippets.map((s) => el("option", { value: s.id, text: s.title })),
  );
  const editor = el("textarea", {
    id: "viz-code",
    class: "code",
    rows: "8",
    spellcheck: "false",
    value: snippets[0].code,
  });
  picker.addEventListener(
    "change",
    () => (editor.value = snippets.find((s) => s.id === picker.value).code),
  );
  const status = el("p", { "aria-live": "polite", class: "small muted" });
  const view = el("div", { class: "stack" });
  const run = button("Visualize");
  run.addEventListener("click", () =>
    withLoading(run, async () => {
      status.textContent = "Loading Python in your browser (first time only, about 10 MB)…";
      try {
        const trace = await runPython("trace", { code: editor.value });
        status.textContent = trace.error
          ? `Finished with: ${trace.error}`
          : `Recorded ${trace.steps.length} steps.`;
        stepper(view, editor.value.split("\n"), trace);
      } catch (error) {
        status.textContent = error.message;
      }
    }),
  );
  panel.append(
    card(
      null,
      el(
        "div",
        { class: "field" },
        el("label", { for: "snippet", text: "Lesson snippet" }),
        picker,
      ),
      el(
        "div",
        { class: "field" },
        el("label", { for: "viz-code", text: "Code (edit freely; max 500 steps, 3 s)" }),
        editor,
      ),
      el("div", { class: "row" }, run),
      status,
    ),
    view,
  );
}

function stepper(view, lines, trace) {
  if (!trace.steps.length) {
    view.replaceChildren(el("p", { text: "No steps were recorded." }));
    return;
  }
  let index = 0;
  const code = el(
    "ol",
    { class: "code-view", "aria-label": "Program with current line highlighted" },
    lines.map((line) => el("li", { text: line || " " })),
  );
  const vars = el("tbody");
  const output = el("pre", { "aria-label": "Program output" });
  const position = el("p", { "aria-live": "polite" });
  const prev = button("Prev", { variant: "secondary", onClick: () => show(index - 1) });
  const next = button("Next", { onClick: () => show(index + 1) });
  const reset = button("Reset", { variant: "ghost", onClick: () => show(0) });
  function show(i) {
    index = Math.max(0, Math.min(trace.steps.length - 1, i));
    const step = trace.steps[index];
    code.querySelectorAll("li").forEach((li, n) => {
      const current = n + 1 === step.line;
      li.classList.toggle("is-current", current);
      if (current) li.setAttribute("aria-current", "step");
      else li.removeAttribute("aria-current");
    });
    vars.replaceChildren(
      ...Object.entries(step.locals).map(([k, v]) =>
        el("tr", {}, el("th", { scope: "row", text: k }), el("td", { text: v })),
      ),
    );
    output.textContent = step.stdout || "(no output yet)";
    position.textContent = `Step ${index + 1} of ${trace.steps.length}: line ${step.line} in ${step.func}${step.event === "return" ? " (returning)" : ""}`;
    prev.disabled = index === 0;
    next.disabled = index === trace.steps.length - 1;
  }
  const textTrace = el(
    "ol",
    {},
    trace.steps.map((s) =>
      el("li", {
        text: `Line ${s.line} (${s.func}): ${
          Object.entries(s.locals)
            .map(([k, v]) => `${k} = ${v}`)
            .join(", ") || "no variables"
        }`,
      }),
    ),
  );
  view.replaceChildren(
    card(
      "Step through",
      position,
      el("div", { class: "row" }, prev, next, reset),
      code,
      el(
        "div",
        { class: "table-wrap" },
        el(
          "table",
          {},
          el("caption", { text: "Variables at this step" }),
          el(
            "thead",
            {},
            el(
              "tr",
              {},
              el("th", { scope: "col", text: "Name" }),
              el("th", { scope: "col", text: "Value" }),
            ),
          ),
          vars,
        ),
      ),
      el("h3", { text: "Output" }),
      output,
      el(
        "details",
        {},
        el("summary", { text: "Full text trace (screen-reader friendly)" }),
        textTrace,
      ),
    ),
  );
  show(0);
}

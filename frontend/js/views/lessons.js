// Lessons: Code Visualizer (Pyodide + sys.settrace) and Grid Game (sandboxed JavaScript).
import { api } from "../api.js";
import { runGameCode } from "../game-runner.js";
import { GRID_SIZE, simulate } from "../grid.js";
import { runPython, stopPython } from "../python-runner.js";
import { tabs } from "../tabs.js";
import { announce, button, card, conf, el, loadInto, pageHead, reducedMotion, toast, withLoading } from "../ui.js";

export async function render(root) {
  root.append(pageHead("Lessons", "Watch Python run line by line, then prove JavaScript skills by coding a robot through a maze."));
  const body = el("div", { class: "stack" });
  root.append(body);
  await loadInto(body, () => api.get("/lessons"), (node, data) => {
    node.append(tabs("Lesson type", [
      { id: "visualizer", label: "Code Visualizer (Python)", render: (panel) => visualizer(panel, data.snippets) },
      { id: "grid", label: "Grid Game (JavaScript)", render: (panel) => gridGame(panel, data.grid_levels) },
    ]));
  });
  return stopPython;
}

function visualizer(panel, snippets) {
  const picker = el("select", { id: "snippet" }, snippets.map((s) => el("option", { value: s.id, text: s.title })));
  const editor = el("textarea", { id: "viz-code", class: "code", rows: "8", spellcheck: "false", value: snippets[0].code });
  picker.addEventListener("change", () => (editor.value = snippets.find((s) => s.id === picker.value).code));
  const status = el("p", { "aria-live": "polite", class: "small muted" });
  const view = el("div", { class: "stack" });
  const run = button("Visualize");
  run.addEventListener("click", () => withLoading(run, async () => {
    status.textContent = "Loading Python in your browser (first time only, about 10 MB)…";
    try {
      const trace = await runPython("trace", { code: editor.value });
      status.textContent = trace.error ? `Finished with: ${trace.error}` : `Recorded ${trace.steps.length} steps.`;
      stepper(view, editor.value.split("\n"), trace);
    } catch (error) {
      status.textContent = error.message;
    }
  }));
  panel.append(card(null,
    el("div", { class: "field" }, el("label", { for: "snippet", text: "Lesson snippet" }), picker),
    el("div", { class: "field" }, el("label", { for: "viz-code", text: "Code (edit freely; max 500 steps, 3 s)" }), editor),
    el("div", { class: "row" }, run), status), view);
}

function stepper(view, lines, trace) {
  if (!trace.steps.length) {
    view.replaceChildren(el("p", { text: "No steps were recorded." }));
    return;
  }
  let index = 0;
  const code = el("ol", { class: "code-view", "aria-label": "Program with current line highlighted" }, lines.map((line) => el("li", { text: line || " " })));
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
    vars.replaceChildren(...Object.entries(step.locals).map(([k, v]) => el("tr", {}, el("th", { scope: "row", text: k }), el("td", { text: v }))));
    output.textContent = step.stdout || "(no output yet)";
    position.textContent = `Step ${index + 1} of ${trace.steps.length}: line ${step.line} in ${step.func}${step.event === "return" ? " (returning)" : ""}`;
    prev.disabled = index === 0;
    next.disabled = index === trace.steps.length - 1;
  }
  const textTrace = el("ol", {}, trace.steps.map((s) => el("li", { text: `Line ${s.line} (${s.func}): ${Object.entries(s.locals).map(([k, v]) => `${k} = ${v}`).join(", ") || "no variables"}` })));
  view.replaceChildren(card("Step through",
    position, el("div", { class: "row" }, prev, next, reset), code,
    el("div", { class: "table-wrap" }, el("table", {}, el("caption", { text: "Variables at this step" }), el("thead", {}, el("tr", {}, el("th", { scope: "col", text: "Name" }), el("th", { scope: "col", text: "Value" }))), vars)),
    el("h3", { text: "Output" }), output,
    el("details", {}, el("summary", { text: "Full text trace (screen-reader friendly)" }), textTrace),
  ));
  show(0);
}

function board(level, [px, py]) {
  const walls = new Set(level.walls.map(([x, y]) => `${x},${y}`));
  const cells = [];
  for (let y = 0; y < GRID_SIZE; y += 1) {
    for (let x = 0; x < GRID_SIZE; x += 1) {
      const kind = x === px && y === py ? "is-player" : walls.has(`${x},${y}`) ? "is-wall" : x === level.goal[0] && y === level.goal[1] ? "is-goal" : "";
      cells.push(el("div", { class: `grid-cell ${kind}`, text: { "is-player": "🤖", "is-wall": "■", "is-goal": "★" }[kind] || "" }));
    }
  }
  const label = `Robot at column ${px + 1}, row ${py + 1}. Goal at column ${level.goal[0] + 1}, row ${level.goal[1] + 1}. Walls at ${level.walls.map(([x, y]) => `column ${x + 1} row ${y + 1}`).join("; ") || "none"}.`;
  return el("div", { class: "grid-board", role: "img", "aria-label": label }, cells);
}

function gridGame(panel, levels) {
  const picker = el("select", { id: "level" }, levels.map((l) => el("option", { value: l.id, text: l.title })));
  const editor = el("textarea", { id: "game-code", class: "code", rows: "8", spellcheck: "false", value: 'for (let i = 0; i < 4; i++) {\n  move("right");\n}\n' });
  const hint = el("p", { class: "small muted" });
  const holder = el("div");
  const status = el("p", { "aria-live": "polite" });
  const level = () => levels.find((l) => l.id === picker.value);
  const reset = () => {
    holder.replaceChildren(board(level(), level().start));
    hint.textContent = `Hint: ${level().hint}`;
  };
  picker.addEventListener("change", reset);
  const run = button("Run my code");
  run.addEventListener("click", () => withLoading(run, async () => {
    const lvl = level();
    const result = await runGameCode(editor.value);
    if (!result.ok) {
      status.textContent = result.error;
      return;
    }
    const path = simulate(lvl, result.moves);
    await animate(holder, lvl, path);
    try {
      const verdict = await api.post("/lessons/grid-result", { level_id: lvl.id, moves: result.moves });
      const message = verdict.solved
        ? `Solved in ${result.moves.length} moves! JavaScript code-exercise evidence added: confidence ${conf(verdict.confidence_before)} → ${conf(verdict.confidence_after)}.`
        : `Not there yet: ${result.moves.length} moves recorded but the robot did not reach the star.`;
      status.textContent = message;
      announce(message);
    } catch (error) {
      toast(error.message, "error");
    }
  }));
  panel.append(card(null,
    el("p", { text: 'Write JavaScript that calls move("up" | "down" | "left" | "right") to reach the ★. Your code runs in an isolated worker with no page or network access and stops after 1 s.' }),
    el("div", { class: "field" }, el("label", { for: "level", text: "Level" }), picker), hint, holder,
    el("div", { class: "field" }, el("label", { for: "game-code", text: "Your JavaScript" }), editor),
    el("div", { class: "row" }, run), status));
  reset();
}

async function animate(holder, level, path) {
  if (reducedMotion()) {
    holder.replaceChildren(board(level, path.at(-1)));
    return;
  }
  for (const position of path) {
    holder.replaceChildren(board(level, position));
    await new Promise((r) => window.setTimeout(r, 220));
  }
}

// Grid Game: learner JavaScript runs in a sandboxed worker; the server verifies the moves.
import { api } from "../api.js";
import { runGameCode } from "../game-runner.js";
import { GRID_SIZE, simulate } from "../grid.js";
import { announce, button, card, conf, el, reducedMotion, toast, withLoading } from "../ui.js";

function board(level, [px, py]) {
  const walls = new Set(level.walls.map(([x, y]) => `${x},${y}`));
  const cells = [];
  for (let y = 0; y < GRID_SIZE; y += 1) {
    for (let x = 0; x < GRID_SIZE; x += 1) {
      const kind =
        x === px && y === py
          ? "is-player"
          : walls.has(`${x},${y}`)
            ? "is-wall"
            : x === level.goal[0] && y === level.goal[1]
              ? "is-goal"
              : "";
      cells.push(
        el("div", {
          class: `grid-cell ${kind}`,
          text: { "is-player": "🤖", "is-wall": "■", "is-goal": "★" }[kind] || "",
        }),
      );
    }
  }
  const label = `Robot at column ${px + 1}, row ${py + 1}. Goal at column ${level.goal[0] + 1}, row ${level.goal[1] + 1}. Walls at ${level.walls.map(([x, y]) => `column ${x + 1} row ${y + 1}`).join("; ") || "none"}.`;
  return el("div", { class: "grid-board", role: "img", "aria-label": label }, cells);
}

export function gridGame(panel, levels) {
  const picker = el(
    "select",
    { id: "level" },
    levels.map((l) => el("option", { value: l.id, text: l.title })),
  );
  const editor = el("textarea", {
    id: "game-code",
    class: "code",
    rows: "8",
    spellcheck: "false",
    value: 'for (let i = 0; i < 4; i++) {\n  move("right");\n}\n',
  });
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
  run.addEventListener("click", () =>
    withLoading(run, async () => {
      const lvl = level();
      const result = await runGameCode(editor.value);
      if (!result.ok) {
        status.textContent = result.error;
        return;
      }
      const path = simulate(lvl, result.moves);
      await animate(holder, lvl, path);
      try {
        const verdict = await api.post("/lessons/grid-result", {
          level_id: lvl.id,
          moves: result.moves,
        });
        const message = verdict.solved
          ? `Solved in ${result.moves.length} moves! JavaScript code-exercise evidence added: confidence ${conf(verdict.confidence_before)} → ${conf(verdict.confidence_after)}.`
          : `Not there yet: ${result.moves.length} moves recorded but the robot did not reach the star.`;
        status.textContent = message;
        announce(message);
      } catch (error) {
        toast(error.message, "error");
      }
    }),
  );
  panel.append(
    card(
      null,
      el("p", {
        text: 'Write JavaScript that calls move("up" | "down" | "left" | "right") to reach the ★. Your code runs in an isolated worker with no page or network access and stops after 1 s.',
      }),
      el("div", { class: "field" }, el("label", { for: "level", text: "Level" }), picker),
      hint,
      holder,
      el(
        "div",
        { class: "field" },
        el("label", { for: "game-code", text: "Your JavaScript" }),
        editor,
      ),
      el("div", { class: "row" }, run),
      status,
    ),
  );
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

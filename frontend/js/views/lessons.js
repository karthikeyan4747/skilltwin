// Lessons: Code Visualizer (Pyodide + sys.settrace) and Grid Game (sandboxed JavaScript).
import { api } from "../api.js";
import { gridGame } from "../lessons/grid-game.js";
import { visualizer } from "../lessons/visualizer.js";
import { stopPython } from "../python-runner.js";
import { tabs } from "../tabs.js";
import { el, loadInto, pageHead } from "../ui.js";

export async function render(root) {
  root.append(
    pageHead(
      "Lessons",
      "Watch Python run line by line, then prove JavaScript skills by coding a robot through a maze.",
    ),
  );
  const body = el("div", { class: "stack" });
  root.append(body);
  await loadInto(
    body,
    () => api.get("/lessons"),
    (node, data) => {
      node.append(
        tabs("Lesson type", [
          {
            id: "visualizer",
            label: "Code Visualizer (Python)",
            render: (panel) => visualizer(panel, data.snippets),
          },
          {
            id: "grid",
            label: "Grid Game (JavaScript)",
            render: (panel) => gridGame(panel, data.grid_levels),
          },
        ]),
      );
    },
  );
  return stopPython;
}

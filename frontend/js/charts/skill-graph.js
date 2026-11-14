// Prerequisite graph as an accessible SVG plus an equivalent nested list.
import { el } from "../ui.js";
import { svg, text } from "./svg.js";

function depths(nodes) {
  const byId = new Map(nodes.map((n) => [n.id, n]));
  const memo = new Map();
  const depth = (id) => {
    if (!memo.has(id)) memo.set(id, Math.max(-1, ...byId.get(id).prerequisites.map(depth)) + 1);
    return memo.get(id);
  };
  nodes.forEach((n) => depth(n.id));
  return memo;
}

export function skillGraph(nodes, statuses) {
  const level = depths(nodes);
  const columns = [];
  nodes.forEach((n) => (columns[level.get(n.id)] ||= []).push(n));
  const BW = 120,
    BH = 30,
    GX = 48,
    GY = 14;
  const rows = Math.max(...columns.map((c) => c.length));
  const W = columns.length * (BW + GX),
    H = rows * (BH + GY) + GY;
  const pos = new Map();
  columns.forEach((col, ci) =>
    col.forEach((n, ri) => pos.set(n.id, { x: ci * (BW + GX) + 4, y: ri * (BH + GY) + GY })),
  );
  const edges = nodes.flatMap((n) =>
    n.prerequisites.map((p) => {
      const a = pos.get(p),
        b = pos.get(n.id);
      return svg("path", {
        class: "graph-edge",
        d: `M${a.x + BW},${a.y + BH / 2} C${a.x + BW + GX / 2},${a.y + BH / 2} ${b.x - GX / 2},${b.y + BH / 2} ${b.x},${b.y + BH / 2}`,
        "marker-end": "url(#arrow)",
      });
    }),
  );
  const boxes = nodes.map((n) => {
    const s = statuses[n.id];
    const state = s?.verified
      ? "is-verified"
      : s && (s.claimed || s.evidence_count)
        ? "is-weak"
        : "";
    const { x, y } = pos.get(n.id);
    return svg(
      "g",
      { class: `graph-node ${state}` },
      svg("rect", { x, y, width: BW, height: BH, rx: 6 }),
      text(x + 8, y + 19, `${s?.verified ? "✓ " : ""}${n.name}`),
    );
  });
  const defs = svg(
    "defs",
    {},
    svg(
      "marker",
      {
        id: "arrow",
        viewBox: "0 0 10 10",
        refX: 9,
        refY: 5,
        markerWidth: 6,
        markerHeight: 6,
        orient: "auto",
      },
      svg("path", { d: "M0,0 L10,5 L0,10 z", fill: "currentColor", class: "graph-edge" }),
    ),
  );
  const graph = svg(
    "svg",
    { viewBox: `0 0 ${W} ${H}`, role: "img", "aria-labelledby": "graph-title" },
    svg("title", { id: "graph-title" }),
    defs,
    edges,
    boxes,
  );
  graph.querySelector("title").textContent =
    "Skill prerequisite graph. Arrows point from a prerequisite to the skill that needs it. The nested list below has the same information.";
  return el("div", { class: "graph table-wrap" }, graph, prerequisiteList(nodes, statuses));
}

function prerequisiteList(nodes, statuses) {
  const children = new Map(nodes.map((n) => [n.id, []]));
  nodes.forEach((n) => n.prerequisites.forEach((p) => children.get(p).push(n)));
  const label = (n) => {
    const s = statuses[n.id];
    const state = s?.verified
      ? "verified"
      : s?.claimed
        ? "claimed, unproven"
        : s?.evidence_count
          ? "in progress"
          : "not started";
    return `${n.name} (${state})`;
  };
  const branch = (n, seen) =>
    el(
      "li",
      { text: label(n) },
      children.get(n.id).length
        ? el(
            "ul",
            {},
            children
              .get(n.id)
              .filter((c) => !seen.has(c.id))
              .map((c) => branch(c, new Set([...seen, c.id]))),
          )
        : null,
    );
  const roots = nodes.filter((n) => !n.prerequisites.length);
  return el(
    "details",
    {},
    el("summary", { text: "Prerequisite tree as a list (unlocks →)" }),
    el(
      "ul",
      {},
      roots.map((r) => branch(r, new Set([r.id]))),
    ),
  );
}

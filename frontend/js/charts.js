// Accessible SVG charts: every chart ships with an equivalent table or list.
import { conf, el } from "./ui.js";

const SVG = "http://www.w3.org/2000/svg";
const PALETTE = ["#6366f1", "#0d9488", "#d97706", "#db2777", "#0284c7", "#65a30d"];

function svg(tag, attrs = {}, ...children) {
  const node = document.createElementNS(SVG, tag);
  for (const [k, v] of Object.entries(attrs)) node.setAttribute(k, String(v));
  children.flat(Infinity).forEach((c) => c && node.append(c));
  return node;
}

function text(x, y, value, attrs = {}) {
  const node = svg("text", { x, y, ...attrs });
  node.textContent = value;
  return node;
}

export function confidenceChart(points, names) {
  const bySkill = new Map();
  points.forEach((p) => bySkill.set(p.skill_id, [...(bySkill.get(p.skill_id) || []), p]));
  const times = points.map((p) => Date.parse(p.timestamp));
  const [t0, t1] = [Math.min(...times), Math.max(...times)];
  const W = 640, H = 260, L = 44, R = 16, T = 16, B = 32;
  const x = (t) => L + (t1 === t0 ? 0.5 : (t - t0) / (t1 - t0)) * (W - L - R);
  const y = (v) => T + (1 - v) * (H - T - B);
  const grid = [0, 0.25, 0.5, 0.7, 1].map((v) => [
    svg("line", { x1: L, x2: W - R, y1: y(v), y2: y(v), class: "chart-axis", "stroke-dasharray": v === 0.7 ? "4 4" : "" }),
    text(L - 6, y(v) + 4, conf(v), { class: "chart-text", "text-anchor": "end" }),
  ]);
  const legend = [];
  const lines = [...bySkill.entries()].map(([skill, series], i) => {
    const color = PALETTE[i % PALETTE.length];
    legend.push(el("span", { class: "badge" }, el("span", { "aria-hidden": "true", text: "●" }), ` ${names[skill]}`));
    legend.at(-1).firstChild.style.color = color;
    const d = series.map((p, j) => `${j ? "L" : "M"}${x(Date.parse(p.timestamp)).toFixed(1)},${y(p.confidence).toFixed(1)}`).join(" ");
    return [svg("path", { d, class: "chart-line", stroke: color }), ...series.map((p) => svg("circle", { cx: x(Date.parse(p.timestamp)), cy: y(p.confidence), r: 3.5, fill: color }))];
  });
  const chart = svg("svg", { viewBox: `0 0 ${W} ${H}`, role: "img", "aria-labelledby": "conf-chart-title" }, svg("title", { id: "conf-chart-title" }), grid, lines, text(W - R, H - 8, "time →", { class: "chart-text", "text-anchor": "end" }));
  chart.querySelector("title").textContent = `Confidence over time for ${bySkill.size} skills; dashed line marks the 70% verified threshold. Full data in the table below.`;
  const table = el(
    "table",
    {},
    el("caption", { class: "visually-hidden", text: "Confidence data points" }),
    el("thead", {}, el("tr", {}, el("th", { scope: "col", text: "Date" }), el("th", { scope: "col", text: "Skill" }), el("th", { scope: "col", text: "Confidence" }))),
    el("tbody", {}, points.map((p) => el("tr", {}, el("td", { text: new Date(p.timestamp).toLocaleString() }), el("td", { text: names[p.skill_id] }), el("td", { text: conf(p.confidence) })))),
  );
  return el("div", { class: "chart" }, chart, el("div", { class: "row" }, legend), el("details", {}, el("summary", { text: "Show data table" }), el("div", { class: "table-wrap" }, table)));
}

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
  const BW = 120, BH = 30, GX = 48, GY = 14;
  const rows = Math.max(...columns.map((c) => c.length));
  const W = columns.length * (BW + GX), H = rows * (BH + GY) + GY;
  const pos = new Map();
  columns.forEach((col, ci) => col.forEach((n, ri) => pos.set(n.id, { x: ci * (BW + GX) + 4, y: ri * (BH + GY) + GY })));
  const edges = nodes.flatMap((n) => n.prerequisites.map((p) => {
    const a = pos.get(p), b = pos.get(n.id);
    return svg("path", { class: "graph-edge", d: `M${a.x + BW},${a.y + BH / 2} C${a.x + BW + GX / 2},${a.y + BH / 2} ${b.x - GX / 2},${b.y + BH / 2} ${b.x},${b.y + BH / 2}`, "marker-end": "url(#arrow)" });
  }));
  const boxes = nodes.map((n) => {
    const s = statuses[n.id];
    const state = s?.verified ? "is-verified" : s && (s.claimed || s.evidence_count) ? "is-weak" : "";
    const { x, y } = pos.get(n.id);
    return svg("g", { class: `graph-node ${state}` }, svg("rect", { x, y, width: BW, height: BH, rx: 6 }), text(x + 8, y + 19, `${s?.verified ? "✓ " : ""}${n.name}`));
  });
  const defs = svg("defs", {}, svg("marker", { id: "arrow", viewBox: "0 0 10 10", refX: 9, refY: 5, markerWidth: 6, markerHeight: 6, orient: "auto" }, svg("path", { d: "M0,0 L10,5 L0,10 z", fill: "currentColor", class: "graph-edge" })));
  const graph = svg("svg", { viewBox: `0 0 ${W} ${H}`, role: "img", "aria-labelledby": "graph-title" }, svg("title", { id: "graph-title" }), defs, edges, boxes);
  graph.querySelector("title").textContent = "Skill prerequisite graph. Arrows point from a prerequisite to the skill that needs it. The nested list below has the same information.";
  return el("div", { class: "graph table-wrap" }, graph, prerequisiteList(nodes, statuses));
}

function prerequisiteList(nodes, statuses) {
  const children = new Map(nodes.map((n) => [n.id, []]));
  nodes.forEach((n) => n.prerequisites.forEach((p) => children.get(p).push(n)));
  const label = (n) => {
    const s = statuses[n.id];
    const state = s?.verified ? "verified" : s?.claimed ? "claimed, unproven" : s?.evidence_count ? "in progress" : "not started";
    return `${n.name} (${state})`;
  };
  const branch = (n, seen) => el("li", { text: label(n) }, children.get(n.id).length ? el("ul", {}, children.get(n.id).filter((c) => !seen.has(c.id)).map((c) => branch(c, new Set([...seen, c.id])))) : null);
  const roots = nodes.filter((n) => !n.prerequisites.length);
  return el("details", {}, el("summary", { text: "Prerequisite tree as a list (unlocks →)" }), el("ul", {}, roots.map((r) => branch(r, new Set([r.id])))));
}

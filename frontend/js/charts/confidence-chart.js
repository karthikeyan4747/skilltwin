// Confidence-over-time line chart (SVG) with an equivalent data table.
import { conf, el } from "../ui.js";
import { svg, text } from "./svg.js";

const PALETTE = ["#6366f1", "#0d9488", "#d97706", "#db2777", "#0284c7", "#65a30d"];

export function confidenceChart(points, names) {
  const bySkill = new Map();
  points.forEach((p) => bySkill.set(p.skill_id, [...(bySkill.get(p.skill_id) || []), p]));
  const times = points.map((p) => Date.parse(p.timestamp));
  const [t0, t1] = [Math.min(...times), Math.max(...times)];
  const W = 640,
    H = 260,
    L = 44,
    R = 16,
    T = 16,
    B = 32;
  const x = (t) => L + (t1 === t0 ? 0.5 : (t - t0) / (t1 - t0)) * (W - L - R);
  const y = (v) => T + (1 - v) * (H - T - B);
  const grid = [0, 0.25, 0.5, 0.7, 1].map((v) => [
    svg("line", {
      x1: L,
      x2: W - R,
      y1: y(v),
      y2: y(v),
      class: "chart-axis",
      "stroke-dasharray": v === 0.7 ? "4 4" : "",
    }),
    text(L - 6, y(v) + 4, conf(v), { class: "chart-text", "text-anchor": "end" }),
  ]);
  const legend = [];
  const lines = [...bySkill.entries()].map(([skill, series], i) => {
    const color = PALETTE[i % PALETTE.length];
    legend.push(
      el(
        "span",
        { class: "badge" },
        el("span", { "aria-hidden": "true", text: "●" }),
        ` ${names[skill]}`,
      ),
    );
    legend.at(-1).firstChild.style.color = color;
    const d = series
      .map(
        (p, j) =>
          `${j ? "L" : "M"}${x(Date.parse(p.timestamp)).toFixed(1)},${y(p.confidence).toFixed(1)}`,
      )
      .join(" ");
    return [
      svg("path", { d, class: "chart-line", stroke: color }),
      ...series.map((p) =>
        svg("circle", { cx: x(Date.parse(p.timestamp)), cy: y(p.confidence), r: 3.5, fill: color }),
      ),
    ];
  });
  const chart = svg(
    "svg",
    { viewBox: `0 0 ${W} ${H}`, role: "img", "aria-labelledby": "conf-chart-title" },
    svg("title", { id: "conf-chart-title" }),
    grid,
    lines,
    text(W - R, H - 8, "time →", { class: "chart-text", "text-anchor": "end" }),
  );
  chart.querySelector("title").textContent =
    `Confidence over time for ${bySkill.size} skills; dashed line marks the 70% verified threshold. Full data in the table below.`;
  const table = el(
    "table",
    {},
    el("caption", { class: "visually-hidden", text: "Confidence data points" }),
    el(
      "thead",
      {},
      el(
        "tr",
        {},
        el("th", { scope: "col", text: "Date" }),
        el("th", { scope: "col", text: "Skill" }),
        el("th", { scope: "col", text: "Confidence" }),
      ),
    ),
    el(
      "tbody",
      {},
      points.map((p) =>
        el(
          "tr",
          {},
          el("td", { text: new Date(p.timestamp).toLocaleString() }),
          el("td", { text: names[p.skill_id] }),
          el("td", { text: conf(p.confidence) }),
        ),
      ),
    ),
  );
  return el(
    "div",
    { class: "chart" },
    chart,
    el("div", { class: "row" }, legend),
    el(
      "details",
      {},
      el("summary", { text: "Show data table" }),
      el("div", { class: "table-wrap" }, table),
    ),
  );
}

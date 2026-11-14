// Progress Tracking: confidence over time, assessment history, completion, Twin accuracy.
import { api } from "../api.js";
import { confidenceChart } from "../charts/confidence-chart.js";
import { badge, card, conf, el, emptyState, loadInto, pageHead, pct, stat } from "../ui.js";

export async function render(root) {
  root.append(
    pageHead(
      "Progress",
      "Learning progress and assessment performance, all from recorded evidence.",
    ),
  );
  const body = el("div", { class: "stack" });
  root.append(body);
  await loadInto(body, () => api.get("/progress"), draw);
}

function draw(root, d) {
  const names = d.skill_names;
  root.append(
    el(
      "div",
      { class: "grid grid-stats" },
      stat(pct(d.completion_pct), "Roadmap steps completed"),
      stat(
        d.twin_accuracy === null ? "—" : conf(d.twin_accuracy),
        `Twin accuracy (${d.twin_predictions} predictions)`,
      ),
      stat(String(d.assessments.length), "Assessments taken"),
    ),
    card(
      "Confidence over time",
      d.confidence_history.length
        ? confidenceChart(d.confidence_history, names)
        : emptyState("No evidence yet", "Take an assessment to start your chart."),
    ),
    card(
      "Assessment history",
      d.assessments.length
        ? historyTable(d.assessments, names)
        : emptyState(
            "No assessments yet",
            "Your results will appear here.",
            el("a", { href: "#/assessment", text: "Take an assessment" }),
          ),
    ),
    card(
      "Latest Twin interview batch",
      d.latest_interview
        ? interview(d.latest_interview, names)
        : emptyState(
            "No interview batch yet",
            "Run 10 Twin interviews from the AI Mentor page.",
            el("a", { href: "#/mentor", text: "Open AI Mentor" }),
          ),
    ),
  );
}

function historyTable(rows, names) {
  return el(
    "div",
    { class: "table-wrap" },
    el(
      "table",
      {},
      el("caption", { class: "visually-hidden", text: "Assessment history, newest first" }),
      el(
        "thead",
        {},
        el(
          "tr",
          {},
          ["Date", "Skill", "Type", "Score", "Result"].map((h) =>
            el("th", { scope: "col", text: h }),
          ),
        ),
      ),
      el(
        "tbody",
        {},
        rows.map((a) =>
          el(
            "tr",
            {},
            el("td", { text: new Date(a.timestamp).toLocaleString() }),
            el("td", { text: names[a.skill_id] }),
            el("td", { text: a.type.replace("_", " ") }),
            el("td", { text: conf(a.score) }),
            el("td", {}, a.correct ? badge("✓ Passed", "success") : badge("✗ Failed", "danger")),
          ),
        ),
      ),
    ),
  );
}

function interview(batch, names) {
  return el(
    "div",
    {},
    el("p", {
      text: `Predicted weak areas: ${batch.weak_areas.map((s) => names[s]).join(", ") || "none"}`,
    }),
    el(
      "ul",
      {},
      batch.results.map((r) =>
        el("li", { text: `${r.title}: predicted score ${conf(r.predicted_score)}` }),
      ),
    ),
  );
}

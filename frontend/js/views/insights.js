// Institution Insights: top anonymized cohort misconceptions per skill.
import { api } from "../api.js";
import { card, el, emptyState, loadInto, pageHead, pct } from "../ui.js";

export async function render(root) {
  root.append(pageHead("Insights", "For institutions: the misconceptions most common across the cohort, so teaching can target them."));
  const body = el("div", { class: "stack" });
  root.append(body);
  await loadInto(body, () => api.get("/insights"), draw);
}

function draw(root, data) {
  if (!data.rows.length) {
    root.append(emptyState("No misconceptions recorded", "Insights appear as learners take assessments."));
    return;
  }
  root.append(card(`Top misconceptions (${data.total_learners} anonymized learners: seeded cohort + live sessions)`,
    el("div", { class: "table-wrap" }, el("table", {},
      el("caption", { class: "visually-hidden", text: "Top misconceptions per skill" }),
      el("thead", {}, el("tr", {}, ["Skill", "Misconception", "Learners affected", "% of cohort"].map((h) => el("th", { scope: "col", text: h })))),
      el("tbody", {}, data.rows.map((r) => el("tr", {}, el("td", { text: r.skill_name }), el("td", { text: r.text }), el("td", { text: String(r.learners_affected) }), el("td", { text: pct(r.pct_affected) })))),
    ))));
}

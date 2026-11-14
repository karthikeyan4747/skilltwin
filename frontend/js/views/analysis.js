// Skill Analysis: claimed badge, confidence bar, verified state, evidence count, graph.
import { api } from "../api.js";
import { skillGraph } from "../charts/skill-graph.js";
import { badge, card, el, emptyState, loadInto, pageHead, progressBar } from "../ui.js";

export async function render(root) {
  root.append(
    pageHead(
      "Skill Analysis",
      "Confidence comes only from evidence. A skill is verified at 70% or more, and needs at least two kinds of evidence to pass 60%.",
    ),
  );
  const body = el("div", { class: "stack" });
  root.append(body);
  await loadInto(body, () => api.get("/analysis"), draw);
}

function skillCard(s) {
  return el(
    "li",
    { class: "step" },
    el(
      "div",
      { class: "step-head" },
      el("strong", { text: s.name }),
      el(
        "span",
        { class: "row" },
        s.claimed ? badge("Claimed", "accent") : null,
        s.verified
          ? badge("✓ Verified", "success")
          : badge(
              s.evidence_count ? "Not yet verified" : "No evidence",
              s.evidence_count ? "warn" : "",
            ),
      ),
    ),
    progressBar("Confidence", s.confidence, { verified: s.verified }),
    el("p", {
      class: "muted small",
      text: `${s.evidence_count} piece${s.evidence_count === 1 ? "" : "s"} of evidence`,
    }),
  );
}

function namedList(ids, byId, empty) {
  return ids.length
    ? el(
        "ul",
        {},
        ids.map((id) => el("li", { text: byId[id]?.name || id })),
      )
    : el("p", { class: "muted", text: empty });
}

function draw(root, data) {
  const byId = Object.fromEntries(data.graph.nodes.map((n) => [n.id, n]));
  const statuses = Object.fromEntries(data.skills.map((s) => [s.skill_id, s]));
  root.append(
    el(
      "div",
      { class: "grid grid-2" },
      card(
        "✓ Strengths (verified)",
        namedList(data.strengths, byId, "No verified skills yet — take an assessment."),
      ),
      card(
        "⚠ Weaknesses",
        el("p", {
          class: "muted small",
          text: "Claimed but unproven, or below 50% after evidence.",
        }),
        namedList(data.weaknesses, byId, "No weaknesses detected."),
      ),
    ),
    card(
      "Your skills",
      data.skills.length
        ? el("ul", { class: "plain-list grid grid-2" }, data.skills.map(skillCard))
        : emptyState("No skills yet", "Add skills on your profile."),
    ),
    card(
      "Prerequisite graph",
      el("p", {
        class: "muted small",
        text: "Green = verified, amber = claimed or in progress. Learn left to right.",
      }),
      skillGraph(data.graph.nodes, statuses),
    ),
  );
}

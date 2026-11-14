// Dashboard: sample-scenario banner, key stats, single primary CTA, next three steps.
import { api } from "../api.js";
import { navigate } from "../router.js";
import { setState } from "../state.js";
import { button, card, conf, el, emptyState, loadInto, pageHead, stat, stepStatusBadge } from "../ui.js";

export async function render(root) {
  root.append(pageHead("Dashboard", "Your skills are verified by evidence, not self-reported."));
  const body = el("div", { class: "stack" });
  root.append(body);
  await loadInto(body, () => api.get("/dashboard"), draw);
}

function draw(root, data) {
  const next = data.next_steps[0];
  const cta = button("Take your next assessment", {
    onClick: () => {
      setState({ assessSkill: next?.skill_id || null });
      navigate("assessment");
    },
  });
  root.append(
    el(
      "section",
      { class: "card banner" },
      el("h2", { class: "card-title", text: `Welcome, ${data.name}` }),
      el("p", { text: "Sample scenario: a learner who knows Python, SQL and basic HTML wants to become a Full Stack Developer — SkillTwin proves what they know, finds the gaps (JavaScript, React, Node.js) and adapts the roadmap as they learn." }),
      cta,
    ),
    el(
      "div",
      { class: "grid grid-stats" },
      stat(data.role_title, "Target role"),
      stat(`${Math.round(data.proven_pct)}%`, `Proven readiness (claimed ${Math.round(data.claimed_pct)}%)`),
      stat(String(data.verified_count), "Skills verified by evidence"),
      stat(`${data.time_to_ready_weeks} wks`, "Estimated time to ready"),
      stat(data.twin_accuracy === null ? "—" : conf(data.twin_accuracy), "Learner Twin prediction accuracy"),
    ),
    card(
      "Next steps on your roadmap",
      data.next_steps.length
        ? el("ol", { class: "plain-list" }, data.next_steps.map((s) => el("li", { class: "step" }, el("div", { class: "step-head" }, el("strong", { text: s.skill_name }), stepStatusBadge(s.status)), el("p", { class: "muted small", text: `${s.reason} · about ${s.est_hours} h` }))))
        : emptyState("Roadmap complete", "Every skill for your target role is verified."),
      el("a", { href: "#/roadmap", text: "Open full roadmap" }),
    ),
  );
}

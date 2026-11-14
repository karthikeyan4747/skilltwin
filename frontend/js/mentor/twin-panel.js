// Learner Twin panel: run 10 simulated work-ticket interviews and show predicted weak areas.
import { api } from "../api.js";
import { agentTrace, announce, button, card, conf, el, toast, withLoading } from "../ui.js";

export function twinCard() {
  const out = el("div", { "aria-live": "polite" });
  const run = button("Run 10 twin interviews");
  run.addEventListener("click", () =>
    withLoading(run, async () => {
      try {
        const res = await api.post("/twin/interviews", { count: 10 });
        const names = res.skill_names;
        const b = res.batch;
        out.replaceChildren(
          el("h3", { text: "Predicted weak areas" }),
          b.weak_areas.length
            ? el(
                "ul",
                {},
                b.weak_areas.map((s) => el("li", { text: names[s] })),
              )
            : el("p", { text: "No weak areas predicted. 🎉" }),
          el("h3", { text: "Targeted plan" }),
          b.plan.length
            ? el(
                "ol",
                {},
                b.plan.map((p) => el("li", { text: p })),
              )
            : el("p", { class: "muted", text: "Keep practising your roadmap." }),
          el(
            "div",
            { class: "table-wrap" },
            el(
              "table",
              {},
              el("caption", { text: "Simulated tickets and predicted scores" }),
              el(
                "thead",
                {},
                el(
                  "tr",
                  {},
                  ["Ticket", "Skill", "Predicted score"].map((h) =>
                    el("th", { scope: "col", text: h }),
                  ),
                ),
              ),
              el(
                "tbody",
                {},
                b.results.map((r) =>
                  el(
                    "tr",
                    {},
                    el("td", { text: r.title }),
                    el("td", { text: names[r.skill_id] }),
                    el("td", { text: conf(r.predicted_score) }),
                  ),
                ),
              ),
            ),
          ),
          agentTrace(res.agent_trace),
        );
        announce(`Twin interviews complete. ${b.weak_areas.length} weak areas predicted.`);
      } catch (error) {
        toast(error.message, "error");
      }
    }),
  );
  return card(
    "Learner Twin: a day in your target role",
    el("p", {
      class: "muted",
      text: "The Interviewer writes realistic work tickets, your Twin answers them as you would, and the Assessor grades — revealing weak areas before a real interview does.",
    }),
    run,
    out,
  );
}

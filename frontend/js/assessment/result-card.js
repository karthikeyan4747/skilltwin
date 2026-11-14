// Assessment result: evidence added, confidence change, Twin reveal and any reroute.
import { agentTrace, announce, badge, conf, el, reducedMotion, subcard } from "../ui.js";

export const TYPE_LABELS = {
  mcq: "Multiple choice",
  explain_back: "Explain it back",
  predict_output: "Predict the output",
  code_exercise: "Code exercise (runs in your browser)",
  interview: "Work ticket",
};

export function resultCard(r, q) {
  const verdict = r.correct ? badge("✓ Correct", "success") : badge("✗ Not correct", "danger");
  const twin = r.twin;
  const summary = `${r.correct ? "Correct" : "Not correct"}. Confidence in ${q.skill_name} went from ${conf(r.confidence_before)} to ${conf(r.confidence_after)}. The Twin ${twin.prediction_matched ? "predicted this" : "did not predict this"}.${r.diagnosis ? ` Root cause found: ${r.diagnosis.path_names[0]}. Roadmap rerouted.` : ""}`;
  const node = el(
    "section",
    { class: `card${reducedMotion() ? "" : " reveal"}`, "aria-labelledby": "result-title" },
    el("h2", { class: "card-title", id: "result-title" }, "Result ", verdict),
    el("p", { text: r.feedback }),
    r.fluency_score !== null
      ? el("p", {
          class: "small muted",
          text: `Concept score ${conf(r.score)} (counts as evidence) · Language fluency ${conf(r.fluency_score)} (shown for feedback only, never counted).`,
        })
      : null,
    el(
      "ul",
      {},
      el("li", { text: `Evidence added: ${TYPE_LABELS[r.evidence_type]}, score ${conf(r.score)}` }),
      el("li", {
        text: `Confidence: ${conf(r.confidence_before)} → ${conf(r.confidence_after)}${r.verified ? " (✓ verified)" : ""}`,
      }),
      el("li", { text: `Misconception detected: ${r.misconception || "none"}` }),
      r.correct ? null : el("li", { text: `Expected: ${r.correct_answer}` }),
    ),
    subcard(
      "🧠 Learner Twin: prediction vs actual",
      el("p", {
        text: `Predicted answer: “${twin.predicted_answer}” (${twin.predicted_correct ? "correct" : "incorrect"})`,
      }),
      el("p", {
        text: `Actual: ${r.correct ? "correct" : "incorrect"} — ${twin.prediction_matched ? "✓ prediction matched" : "✗ prediction missed"}`,
      }),
      el("p", { class: "muted small", text: `Why the Twin predicted this: ${twin.reasoning}` }),
      el("p", {
        class: "small",
        text: `Twin accuracy so far: ${twin.accuracy === null ? "—" : conf(twin.accuracy)}`,
      }),
    ),
    r.diagnosis
      ? subcard(
          "🔁 Roadmap rerouted to the root cause",
          el("p", { text: `Prerequisite path: ${r.diagnosis.path_names.join(" → ")}` }),
          el("p", { text: r.diagnosis.explanation }),
          el("p", { text: `First action: ${r.diagnosis.first_action}` }),
          el("p", {
            class: "small muted",
            text: r.diagnosis.inserted_steps.length
              ? `New steps added: ${r.diagnosis.inserted_steps.join(", ")}`
              : "Existing steps were moved to the front of your roadmap.",
          }),
          el("a", { href: "#/roadmap", text: "See rerouted roadmap" }),
        )
      : null,
    agentTrace(r.agent_trace),
  );
  announce(summary);
  return node;
}

// Assessment: question (Twin prediction hidden), answer, then evidence, Twin reveal and reroute.
import { api } from "../api.js";
import { runPython, stopPython } from "../python-runner.js";
import { setState, state } from "../state.js";
import { agentTrace, announce, badge, button, card, conf, subcard, el, loadInto, pageHead, reducedMotion, toast, withLoading } from "../ui.js";

const TYPE_LABELS = {
  mcq: "Multiple choice",
  explain_back: "Explain it back",
  predict_output: "Predict the output",
  code_exercise: "Code exercise (runs in your browser)",
  interview: "Work ticket",
};

export async function render(root) {
  root.append(pageHead("Assessment", "Every answer becomes evidence. Before you answer, your Learner Twin secretly predicts what you will say."));
  const body = el("div", { class: "stack" });
  root.append(body);
  await loadInto(body, () => Promise.all([api.get("/assessment/skills"), api.get("/roadmap")]), draw);
  return stopPython;
}

function draw(root, [skills, roadmap]) {
  const preferred = state.assessSkill || roadmap.steps.find((s) => s.status !== "done")?.skill_id || skills[0].id;
  const skill = el("select", { id: "skill", name: "skill" }, skills.map((s) => el("option", { value: s.id, text: s.name, selected: s.id === preferred })));
  const type = el("select", { id: "qtype", name: "qtype" }, el("option", { value: "", text: "Auto (rotate types for stronger evidence)" }), Object.entries(TYPE_LABELS).map(([v, t]) => el("option", { value: v, text: t })));
  const area = el("div", { class: "stack" });
  const start = button("Start assessment", { type: "submit" });
  const form = el(
    "form",
    { class: "grid grid-2" },
    el("div", { class: "field" }, el("label", { for: "skill", text: "Skill" }), skill),
    el("div", { class: "field" }, el("label", { for: "qtype", text: "Question type" }), type),
    el("div", {}, start),
  );
  form.addEventListener("submit", (event) => {
    event.preventDefault();
    setState({ assessSkill: skill.value });
    withLoading(start, async () => {
      try {
        const res = await api.post("/assessment/question", { skill_id: skill.value, type: type.value || null });
        area.replaceChildren(questionCard(res, area));
        area.querySelector("h2")?.focus();
      } catch (error) {
        toast(error.message, "error");
      }
    });
  });
  root.append(card("Choose what to prove", form), area);
}

function questionCard(res, area) {
  const q = res.question;
  const heading = el("h2", { class: "card-title", tabindex: "-1", text: `${q.skill_name}: ${TYPE_LABELS[q.type]}` });
  const form = el("form", { class: "stack" }, el("p", { text: q.prompt }));
  const submit = button("Submit answer", { type: "submit" });
  let collect;
  let testResult = null;
  if (q.type === "mcq") {
    form.append(el("fieldset", {}, el("legend", { text: "Choose one answer" }), q.options.map((o, i) => el("label", { class: "choice" }, el("input", { type: "radio", name: "choice", value: String(i), required: true }), o))));
    collect = () => ({ choice: Number(form.querySelector("input[name=choice]:checked")?.value ?? -1) });
  } else if (q.type === "code_exercise") {
    const code = el("textarea", { id: "answer", class: "code", rows: "10", spellcheck: "false", value: q.code || "" });
    const status = el("div", { "aria-live": "polite", class: "small" });
    const runBtn = button("Run tests", { variant: "secondary" });
    runBtn.addEventListener("click", () => withLoading(runBtn, async () => {
      status.textContent = "Loading Python in your browser (first time only, about 10 MB)…";
      try {
        testResult = await runPython("tests", { code: code.value, tests: q.tests });
        status.replaceChildren(testSummary(testResult));
      } catch (error) {
        testResult = null;
        status.textContent = error.message;
      }
    }));
    form.append(el("div", { class: "field" }, el("label", { for: "answer", text: "Your code" }), code), el("details", {}, el("summary", { text: "Tests that must pass" }), el("pre", { text: q.tests })), el("div", { class: "row" }, runBtn), status);
    collect = () => ({ tests_passed: testResult?.passed ?? 0, tests_total: testResult?.total ?? 0 });
  } else {
    if (q.code) form.append(el("pre", {}, el("code", { text: q.code })));
    const open = q.type === "explain_back" || q.type === "interview";
    const input = open ? el("textarea", { id: "answer", maxlength: "4000", rows: "6" }) : el("input", { id: "answer", type: "text", maxlength: "4000", autocomplete: "off" });
    const hint = open ? "Graded on the ideas, not on grammar or fluency — write in your own words." : "Type the exact output.";
    input.setAttribute("aria-describedby", "answer-hint");
    form.append(el("div", { class: "field" }, el("label", { for: "answer", text: "Your answer" }), el("span", { class: "field-hint", id: "answer-hint", text: hint }), input));
    collect = () => ({ text: input.value });
  }
  form.append(submit);
  form.addEventListener("submit", (event) => {
    event.preventDefault();
    const answer = collect();
    if (answer.choice === -1) return toast("Choose an answer first.", "error");
    if (q.type === "code_exercise" && !testResult) return toast("Run the tests before submitting.", "error");
    return withLoading(submit, async () => {
      try {
        const result = await api.post("/assessment/answer", { question_id: q.id, ...answer });
        form.querySelectorAll("input, textarea, button").forEach((n) => (n.disabled = true));
        area.append(resultCard(result, q));
      } catch (error) {
        toast(error.message, "error");
      }
    });
  });
  return el("section", { class: "card" }, heading, el("p", { class: "row" }, badge(`Difficulty: ${q.difficulty}`), badge("🔒 Twin prediction locked until you submit", "accent")), form, agentTrace(res.agent_trace));
}

function testSummary(r) {
  return el("div", {}, el("p", { text: r.error ? `Your code raised ${r.error}` : `${r.passed} of ${r.total} tests passed.` }), el("ul", {}, r.results.map((t) => el("li", { text: `${t.ok ? "✓ pass" : "✗ fail"}: ${t.test}${t.error ? ` (${t.error})` : ""}` }))));
}

function resultCard(r, q) {
  const verdict = r.correct ? badge("✓ Correct", "success") : badge("✗ Not correct", "danger");
  const twin = r.twin;
  const summary = `${r.correct ? "Correct" : "Not correct"}. Confidence in ${q.skill_name} went from ${conf(r.confidence_before)} to ${conf(r.confidence_after)}. The Twin ${twin.prediction_matched ? "predicted this" : "did not predict this"}.${r.diagnosis ? ` Root cause found: ${r.diagnosis.path_names[0]}. Roadmap rerouted.` : ""}`;
  const node = el(
    "section",
    { class: `card${reducedMotion() ? "" : " reveal"}`, "aria-labelledby": "result-title" },
    el("h2", { class: "card-title", id: "result-title" }, "Result ", verdict),
    el("p", { text: r.feedback }),
    r.fluency_score !== null ? el("p", { class: "small muted", text: `Concept score ${conf(r.score)} (counts as evidence) · Language fluency ${conf(r.fluency_score)} (shown for feedback only, never counted).` }) : null,
    el("ul", {},
      el("li", { text: `Evidence added: ${TYPE_LABELS[r.evidence_type]}, score ${conf(r.score)}` }),
      el("li", { text: `Confidence: ${conf(r.confidence_before)} → ${conf(r.confidence_after)}${r.verified ? " (✓ verified)" : ""}` }),
      el("li", { text: `Misconception detected: ${r.misconception || "none"}` }),
      r.correct ? null : el("li", { text: `Expected: ${r.correct_answer}` }),
    ),
    subcard("🧠 Learner Twin: prediction vs actual",
      el("p", { text: `Predicted answer: “${twin.predicted_answer}” (${twin.predicted_correct ? "correct" : "incorrect"})` }),
      el("p", { text: `Actual: ${r.correct ? "correct" : "incorrect"} — ${twin.prediction_matched ? "✓ prediction matched" : "✗ prediction missed"}` }),
      el("p", { class: "muted small", text: `Why the Twin predicted this: ${twin.reasoning}` }),
      el("p", { class: "small", text: `Twin accuracy so far: ${twin.accuracy === null ? "—" : conf(twin.accuracy)}` }),
    ),
    r.diagnosis ? subcard("🔁 Roadmap rerouted to the root cause",
      el("p", { text: `Prerequisite path: ${r.diagnosis.path_names.join(" → ")}` }),
      el("p", { text: r.diagnosis.explanation }),
      el("p", { text: `First action: ${r.diagnosis.first_action}` }),
      el("p", { class: "small muted", text: r.diagnosis.inserted_steps.length ? `New steps added: ${r.diagnosis.inserted_steps.join(", ")}` : "Existing steps were moved to the front of your roadmap." }),
      el("a", { href: "#/roadmap", text: "See rerouted roadmap" }),
    ) : null,
    agentTrace(r.agent_trace),
  );
  announce(summary);
  return node;
}

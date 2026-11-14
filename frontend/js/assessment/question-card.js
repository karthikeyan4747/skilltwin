// Assessment question form for each question type; code exercises run tests in Pyodide.
import { api } from "../api.js";
import { runPython } from "../python-runner.js";
import { agentTrace, badge, button, el, toast, withLoading } from "../ui.js";
import { TYPE_LABELS, resultCard } from "./result-card.js";

export function questionCard(res, area) {
  const q = res.question;
  const heading = el("h2", {
    class: "card-title",
    tabindex: "-1",
    text: `${q.skill_name}: ${TYPE_LABELS[q.type]}`,
  });
  const form = el("form", { class: "stack" }, el("p", { text: q.prompt }));
  const submit = button("Submit answer", { type: "submit" });
  let collect;
  let testResult = null;
  if (q.type === "mcq") {
    form.append(
      el(
        "fieldset",
        {},
        el("legend", { text: "Choose one answer" }),
        q.options.map((o, i) =>
          el(
            "label",
            { class: "choice" },
            el("input", { type: "radio", name: "choice", value: String(i), required: true }),
            o,
          ),
        ),
      ),
    );
    collect = () => ({
      choice: Number(form.querySelector("input[name=choice]:checked")?.value ?? -1),
    });
  } else if (q.type === "code_exercise") {
    const code = el("textarea", {
      id: "answer",
      class: "code",
      rows: "10",
      spellcheck: "false",
      value: q.code || "",
    });
    const status = el("div", { "aria-live": "polite", class: "small" });
    const runBtn = button("Run tests", { variant: "secondary" });
    runBtn.addEventListener("click", () =>
      withLoading(runBtn, async () => {
        status.textContent = "Loading Python in your browser (first time only, about 10 MB)…";
        try {
          testResult = await runPython("tests", { code: code.value, tests: q.tests });
          status.replaceChildren(testSummary(testResult));
        } catch (error) {
          testResult = null;
          status.textContent = error.message;
        }
      }),
    );
    form.append(
      el("div", { class: "field" }, el("label", { for: "answer", text: "Your code" }), code),
      el(
        "details",
        {},
        el("summary", { text: "Tests that must pass" }),
        el("pre", { text: q.tests }),
      ),
      el("div", { class: "row" }, runBtn),
      status,
    );
    collect = () => ({
      tests_passed: testResult?.passed ?? 0,
      tests_total: testResult?.total ?? 0,
    });
  } else {
    if (q.code) form.append(el("pre", {}, el("code", { text: q.code })));
    const open = q.type === "explain_back" || q.type === "interview";
    const input = open
      ? el("textarea", { id: "answer", maxlength: "4000", rows: "6" })
      : el("input", { id: "answer", type: "text", maxlength: "4000", autocomplete: "off" });
    const hint = open
      ? "Graded on the ideas, not on grammar or fluency — write in your own words."
      : "Type the exact output.";
    input.setAttribute("aria-describedby", "answer-hint");
    form.append(
      el(
        "div",
        { class: "field" },
        el("label", { for: "answer", text: "Your answer" }),
        el("span", { class: "field-hint", id: "answer-hint", text: hint }),
        input,
      ),
    );
    collect = () => ({ text: input.value });
  }
  form.append(submit);
  form.addEventListener("submit", (event) => {
    event.preventDefault();
    const answer = collect();
    if (answer.choice === -1) return toast("Choose an answer first.", "error");
    if (q.type === "code_exercise" && !testResult)
      return toast("Run the tests before submitting.", "error");
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
  return el(
    "section",
    { class: "card" },
    heading,
    el(
      "p",
      { class: "row" },
      badge(`Difficulty: ${q.difficulty}`),
      badge("🔒 Twin prediction locked until you submit", "accent"),
    ),
    form,
    agentTrace(res.agent_trace),
  );
}

function testSummary(r) {
  return el(
    "div",
    {},
    el("p", {
      text: r.error ? `Your code raised ${r.error}` : `${r.passed} of ${r.total} tests passed.`,
    }),
    el(
      "ul",
      {},
      r.results.map((t) =>
        el("li", {
          text: `${t.ok ? "✓ pass" : "✗ fail"}: ${t.test}${t.error ? ` (${t.error})` : ""}`,
        }),
      ),
    ),
  );
}

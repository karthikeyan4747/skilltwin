// Assessment: question (Twin prediction hidden), answer, then evidence, Twin reveal and reroute.
import { api } from "../api.js";
import { questionCard } from "../assessment/question-card.js";
import { TYPE_LABELS } from "../assessment/result-card.js";
import { stopPython } from "../python-runner.js";
import { setState, state } from "../state.js";
import { button, card, el, loadInto, pageHead, toast, withLoading } from "../ui.js";

export async function render(root) {
  root.append(
    pageHead(
      "Assessment",
      "Every answer becomes evidence. Before you answer, your Learner Twin secretly predicts what you will say.",
    ),
  );
  const body = el("div", { class: "stack" });
  root.append(body);
  await loadInto(
    body,
    () => Promise.all([api.get("/assessment/skills"), api.get("/roadmap")]),
    draw,
  );
  return stopPython;
}

function draw(root, [skills, roadmap]) {
  const preferred =
    state.assessSkill || roadmap.steps.find((s) => s.status !== "done")?.skill_id || skills[0].id;
  const skill = el(
    "select",
    { id: "skill", name: "skill" },
    skills.map((s) => el("option", { value: s.id, text: s.name, selected: s.id === preferred })),
  );
  const type = el(
    "select",
    { id: "qtype", name: "qtype" },
    el("option", { value: "", text: "Auto (rotate types for stronger evidence)" }),
    Object.entries(TYPE_LABELS).map(([v, t]) => el("option", { value: v, text: t })),
  );
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
        const res = await api.post("/assessment/question", {
          skill_id: skill.value,
          type: type.value || null,
        });
        area.replaceChildren(questionCard(res, area));
        area.querySelector("h2")?.focus();
      } catch (error) {
        toast(error.message, "error");
      }
    });
  });
  root.append(card("Choose what to prove", form), area);
}

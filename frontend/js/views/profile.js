// User Profile: learner details, claimed skills, certifications, projects and career goal.
import { api, ApiError } from "../api.js";
import { agentTrace, announce, button, card, el, loadInto, pageHead, showFieldErrors, toast, withLoading } from "../ui.js";

const lines = (value) => value.split("\n").map((s) => s.trim()).filter(Boolean);

function field(id, label, input, hint) {
  input.id = id;
  input.name = id;
  return el("div", { class: "field" }, el("label", { for: id, text: label }), hint ? el("span", { class: "field-hint", id: `${id}-hint`, text: hint }) : null, input);
}

export async function render(root) {
  root.append(pageHead("Profile", "Claims are a starting point — assessments turn them into verified skills."));
  const body = el("div", { class: "stack" });
  root.append(body);
  await loadInto(body, () => api.get("/profile"), draw);
}

function draw(root, data) {
  const p = data.profile;
  const result = el("div", { "aria-live": "polite" });
  const skills = el("fieldset", { class: "field" }, el("legend", { text: "Skills you already have (claimed)" }), el("div", { class: "chips" }, data.skill_options.map((s) => el("label", { class: "chip" }, el("input", { type: "checkbox", name: "claimed_skills", value: s.id, checked: p.claimed_skills.includes(s.id) }), s.name))));
  const goal = el("select", {}, data.role_options.map((r) => el("option", { value: r.id, text: r.title, selected: r.id === p.career_goal })));
  const form = el(
    "form",
    { class: "stack", novalidate: true },
    field("name", "Name", el("input", { type: "text", value: p.name, maxlength: "80", required: true, autocomplete: "name" })),
    field("education", "Education", el("input", { type: "text", value: p.education, maxlength: "200" })),
    field("hours_per_week", "Study hours per week", el("input", { type: "number", value: String(p.hours_per_week), min: "1", max: "80", step: "1" }), "Used to estimate time-to-ready in weeks."),
    skills,
    field("certifications", "Certifications", el("textarea", { value: p.certifications.join("\n"), rows: "3" }), "One per line."),
    field("projects", "Projects", el("textarea", { value: p.projects.join("\n"), rows: "3" }), "One per line."),
    field("career_goal", "Career goal", goal),
  );
  const save = button("Save profile", { type: "submit" });
  form.append(save);
  form.addEventListener("submit", (event) => {
    event.preventDefault();
    const value = (name) => form.elements.namedItem(name).value;
    const body = {
      name: value("name").trim(),
      education: value("education").trim(),
      hours_per_week: Number(value("hours_per_week")),
      claimed_skills: [...form.querySelectorAll("input[name=claimed_skills]:checked")].map((i) => i.value),
      certifications: lines(value("certifications")),
      projects: lines(value("projects")),
      career_goal: value("career_goal"),
    };
    withLoading(save, async () => {
      try {
        const res = await api.put("/profile", body);
        showFieldErrors(form);
        result.replaceChildren(card("Analysis refreshed", el("p", { text: res.result.summary }), agentTrace(res.result.agent_trace)));
        toast("Profile saved. Analysis and roadmap refreshed.", "success");
        announce("Profile saved. Analysis and roadmap refreshed.");
      } catch (error) {
        if (error instanceof ApiError) showFieldErrors(form, error.fields);
        toast(error.message, "error");
      }
    });
  });
  root.append(card(null, form), result);
}

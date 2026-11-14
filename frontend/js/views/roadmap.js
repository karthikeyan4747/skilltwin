// Roadmap & Learning Recommendations: ordered steps, resources with AI reasons, reroute history.
import { api } from "../api.js";
import {
  announce,
  badge,
  card,
  el,
  emptyState,
  loadInto,
  pageHead,
  pct,
  progressBar,
  stepStatusBadge,
  toast,
} from "../ui.js";

const KIND_LABEL = { course: "Course", tutorial: "Tutorial", exercise: "Practical exercise" };
const TRIGGER_LABEL = {
  failed_assessment: "Rerouted after a failed answer",
  goal_change: "Career goal changed",
  mentor: "AI Mentor re-prioritised",
};

export async function render(root) {
  root.append(
    pageHead(
      "Roadmap",
      "Gaps ordered so prerequisites come first. It adapts when you change goal or struggle.",
    ),
  );
  const body = el("div", { class: "stack" });
  root.append(body);
  await loadInto(body, () => api.get("/roadmap"), draw);
}

function draw(root, data) {
  root.replaceChildren(
    card(
      `Path to ${data.role_title}`,
      progressBar("Steps completed", data.completion_pct / 100, {
        verified: true,
        valueText: pct(data.completion_pct),
      }),
    ),
    data.steps.length
      ? el(
          "ol",
          { class: "plain-list" },
          data.steps.map((s, i) => stepItem(s, i, root)),
        )
      : emptyState("No gaps left", "Every skill for this role is verified by evidence."),
    card(
      "Reroute history",
      data.reroutes.length
        ? el("ol", { class: "timeline" }, data.reroutes.map(rerouteItem))
        : el("p", {
            class: "muted",
            text: "No reroutes yet. Fail an assessment or change goal to see the roadmap adapt.",
          }),
    ),
  );
}

function stepItem(step, index, root) {
  const id = `status-${step.skill_id}`;
  const status = el(
    "select",
    { id },
    ["todo", "in_progress", "done"].map((v) =>
      el("option", {
        value: v,
        text: { todo: "To do", in_progress: "In progress", done: "Done" }[v],
        selected: v === step.status,
      }),
    ),
  );
  const hours = el("input", {
    type: "number",
    id: `hours-${step.skill_id}`,
    min: "0.5",
    max: "500",
    step: "0.5",
    value: step.actual_hours ?? "",
    placeholder: String(step.est_hours),
  });
  const save = async () => {
    try {
      const body = {
        status: status.value,
        actual_hours: status.value === "done" && hours.value ? Number(hours.value) : null,
      };
      const data = await api.patch(`/roadmap/steps/${step.skill_id}`, body);
      draw(root, data);
      announce(`${step.skill_name} marked ${status.selectedOptions[0].text}.`);
      document.getElementById(id)?.focus();
    } catch (error) {
      toast(error.message, "error");
    }
  };
  status.addEventListener("change", save);
  hours.addEventListener("change", () => status.value === "done" && save());
  return el(
    "li",
    { class: "step" },
    el(
      "div",
      { class: "step-head" },
      el("h2", { class: "card-title", text: `${index + 1}. ${step.skill_name}` }),
      stepStatusBadge(step.status),
    ),
    el("p", { text: `Why: ${step.reason}` }),
    el("p", { class: "small muted", text: `Estimated ${step.est_hours} h` }),
    step.resource_reason
      ? el("p", { class: "small" }, badge("AI", "accent"), ` ${step.resource_reason}`)
      : null,
    el(
      "ul",
      {},
      step.resources.map((r) =>
        el(
          "li",
          {},
          `${KIND_LABEL[r.kind]}: `,
          el("a", { href: r.url, target: "_blank", rel: "noopener noreferrer", text: r.title }),
          ` (${r.provider}, opens in new tab)`,
        ),
      ),
    ),
    el(
      "div",
      { class: "grid grid-2" },
      el("div", { class: "field" }, el("label", { for: id, text: "Status" }), status),
      el(
        "div",
        { class: "field" },
        el("label", { for: `hours-${step.skill_id}`, text: "Hours actually spent (optional)" }),
        hours,
        el("span", { class: "field-hint", text: "Used to measure your pace once a step is done." }),
      ),
    ),
  );
}

function rerouteItem(event) {
  const when = new Date(event.timestamp).toLocaleString();
  const detail =
    event.trigger === "failed_assessment"
      ? `Failed ${event.failed_name}; root cause ${event.root_name}. Path: ${event.path_names.join(" → ")}.${event.inserted_names.length ? ` Added: ${event.inserted_names.join(", ")}.` : ""}`
      : event.trigger === "mentor"
        ? `${event.note} Moved: ${event.path_names.join(", ")}.`
        : event.note;
  return el(
    "li",
    {},
    el("strong", { text: TRIGGER_LABEL[event.trigger] }),
    el("span", { class: "muted small", text: ` · ${when}` }),
    el("p", { text: detail }),
  );
}

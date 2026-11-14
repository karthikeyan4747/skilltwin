// Dashboard: sample-scenario result on first load, key stats, one-click scenario run, next steps.
import { api } from "../api.js";
import { navigate } from "../router.js";
import { setState } from "../state.js";
import {
  agentTrace,
  announce,
  button,
  card,
  conf,
  el,
  emptyState,
  loadInto,
  pageHead,
  reducedMotion,
  stat,
  stepStatusBadge,
  subcard,
  toast,
  withLoading,
} from "../ui.js";

export async function render(root) {
  root.append(pageHead("Dashboard", "Your skills are verified by evidence, not self-reported."));
  const scenario = el("div", { class: "stack", "aria-live": "polite" });
  const body = el("div", { class: "stack" });
  root.append(scenario, body);
  const load = () =>
    loadInto(
      body,
      () => api.get("/dashboard"),
      (node, data) => draw(node, data, scenario, load),
    );
  await load();
}

const listText = (items, empty) => (items.length ? items.join(", ") : empty);

function draw(root, data, scenario, reload) {
  const next = data.next_steps[0];
  const run = button("Try the sample scenario");
  run.addEventListener("click", () =>
    withLoading(run, async () => {
      scenario.replaceChildren(
        card(
          null,
          el("p", {
            text: "Running: onboard → failed React answer → root-cause reroute → goal switch. Live AI can take up to a minute…",
          }),
        ),
      );
      try {
        const result = await api.post("/scenario/sample");
        scenario.replaceChildren(scenarioCard(result));
        announce(result.stages.map((s) => s.title).join(". "));
        await reload();
      } catch (error) {
        scenario.replaceChildren();
        toast(error.message, "error");
      }
    }),
  );
  const assess = button("Take your next assessment", {
    variant: "secondary",
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
      el("p", {
        text: "Sample scenario: a learner who knows Python, SQL and basic HTML wants to become a Full Stack Developer. One click shows both adaptations: a failed React answer reroutes the roadmap to its root cause, then the goal switches to the best-fit role.",
      }),
      el("div", { class: "row" }, run, assess),
    ),
    el(
      "div",
      { class: "grid grid-stats" },
      stat(data.role_title, "Target role"),
      stat(
        `${Math.round(data.proven_pct)}%`,
        `Proven readiness (claimed ${Math.round(data.claimed_pct)}%)`,
      ),
      stat(String(data.verified_count), "Skills verified by evidence"),
      stat(`${data.time_to_ready_weeks} wks`, "Estimated time to ready"),
      stat(
        data.twin_accuracy === null ? "—" : conf(data.twin_accuracy),
        "Learner Twin prediction accuracy",
      ),
    ),
    card(
      `Skill gaps for ${data.role_title}`,
      el(
        "ul",
        {},
        el("li", { text: `✓ Verified by evidence: ${listText(data.verified, "none yet")}` }),
        el("li", { text: `◐ Claimed but not yet proven: ${listText(data.unproven, "none")}` }),
        el("li", { text: `○ Missing: ${listText(data.missing, "none")}` }),
        data.better_fit
          ? el(
              "li",
              {},
              `💡 Better fit on proven skills: ${data.better_fit} — `,
              el("a", { href: "#/career", text: "compare roles" }),
            )
          : null,
      ),
      el("h3", { text: "Roadmap order (prerequisites first)" }),
      data.roadmap_order.length
        ? el(
            "ol",
            {},
            data.roadmap_order.map((name) => el("li", { text: name })),
          )
        : el("p", { class: "muted", text: "No gaps left." }),
    ),
    card(
      "Next steps on your roadmap",
      data.next_steps.length
        ? el(
            "ol",
            { class: "plain-list" },
            data.next_steps.map((s) =>
              el(
                "li",
                { class: "step" },
                el(
                  "div",
                  { class: "step-head" },
                  el("strong", { text: s.skill_name }),
                  stepStatusBadge(s.status),
                ),
                el("p", { class: "muted small", text: `${s.reason} · about ${s.est_hours} h` }),
              ),
            ),
          )
        : emptyState("Roadmap complete", "Every skill for your target role is verified."),
      el("a", { href: "#/roadmap", text: "Open full roadmap" }),
    ),
  );
}

function scenarioCard(result) {
  return el(
    "section",
    { class: `card${reducedMotion() ? "" : " reveal"}`, "aria-labelledby": "scenario-result" },
    el("h2", { class: "card-title", id: "scenario-result", text: "Sample scenario result" }),
    result.stages.map((stage) =>
      subcard(stage.title, el("p", { text: stage.summary }), agentTrace(stage.agent_trace)),
    ),
    el(
      "p",
      {},
      "See it in the app: ",
      el("a", { href: "#/roadmap", text: "reroute history" }),
      " · ",
      el("a", { href: "#/career", text: "career matching" }),
      " · ",
      el("a", { href: "#/progress", text: "progress" }),
    ),
  );
}

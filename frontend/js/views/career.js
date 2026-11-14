// Career Matching: claimed vs proven readiness, ranking, better fit, goal switch, demand.
import { api } from "../api.js";
import { modal } from "../modal.js";
import {
  agentTrace,
  announce,
  badge,
  button,
  card,
  el,
  loadInto,
  pageHead,
  pct,
  progressBar,
  toast,
} from "../ui.js";

export async function render(root) {
  root.append(
    pageHead(
      "Career Matching",
      "Compare what you claim with what you have proven for each job role.",
    ),
  );
  const body = el("div", { class: "stack" });
  root.append(body);
  await loadInto(
    body,
    () => api.get("/career"),
    (node, data) => draw(node, data, root),
  );
}

function draw(root, data, page) {
  const t = data.target;
  const demandLabel =
    data.demand.source === "live" ? badge("Live · Adzuna", "success") : badge("Curated data", "");
  root.append(
    card(
      `Target: ${data.role.title}`,
      el("p", { class: "muted", text: data.role.description }),
      el(
        "div",
        { class: "grid grid-2" },
        progressBar("Claimed readiness", t.claimed_pct / 100, { valueText: pct(t.claimed_pct) }),
        progressBar("Proven readiness", t.proven_pct / 100, {
          verified: true,
          valueText: pct(t.proven_pct),
        }),
      ),
      el("p", {
        text: `Time to ready: about ${data.time_to_ready_weeks} weeks (${data.remaining_hours} h left at ${data.hours_per_week} h/week, pace ×${data.velocity}).`,
      }),
    ),
    data.better_fit
      ? card(
          "💡 Better-fit role",
          el("p", {
            text: `${data.better_fit.title} is ${Math.round(data.better_fit.proven_pct - t.proven_pct)} points ahead on proven skills (${pct(data.better_fit.proven_pct)} vs ${pct(t.proven_pct)}).`,
          }),
          el("p", { class: "muted", text: `Why: ${data.better_fit_reason}` }),
          switchButton(data.better_fit.role_id, data.better_fit.title, page),
        )
      : null,
    card("All roles ranked by proven readiness", rankingTable(data.ranking, data.role.id, page)),
    card(
      "Market demand per skill",
      el("p", { class: "row" }, "Source: ", demandLabel),
      demandTable(data.demand.counts, data.skill_names),
    ),
  );
}

function rankingTable(ranking, targetId, page) {
  const rows = ranking.map((r) =>
    el(
      "tr",
      {},
      el(
        "th",
        { scope: "row" },
        r.title,
        r.role_id === targetId ? badge("Current goal", "accent") : null,
      ),
      el("td", { text: pct(r.claimed_pct) }),
      el("td", { text: pct(r.proven_pct) }),
      el(
        "td",
        {},
        r.role_id === targetId ? null : switchButton(r.role_id, r.title, page, "secondary"),
      ),
    ),
  );
  return el(
    "div",
    { class: "table-wrap" },
    el(
      "table",
      {},
      el("caption", { class: "visually-hidden", text: "Roles ranked by proven readiness" }),
      el(
        "thead",
        {},
        el(
          "tr",
          {},
          ["Role", "Claimed", "Proven", "Action"].map((h) => el("th", { scope: "col", text: h })),
        ),
      ),
      el("tbody", {}, rows),
    ),
  );
}

function demandTable(counts, names) {
  return el(
    "div",
    { class: "table-wrap" },
    el(
      "table",
      {},
      el(
        "thead",
        {},
        el(
          "tr",
          {},
          el("th", { scope: "col", text: "Skill" }),
          el("th", { scope: "col", text: "Job postings" }),
        ),
      ),
      el(
        "tbody",
        {},
        Object.entries(counts).map(([skill, n]) =>
          el(
            "tr",
            {},
            el("td", { text: names[skill] || skill }),
            el("td", { text: n.toLocaleString() }),
          ),
        ),
      ),
    ),
  );
}

function switchButton(roleId, title, page, variant = "primary") {
  const btn = button(`Switch to ${title}`, { variant });
  btn.addEventListener("click", async () => {
    try {
      const preview = await api.post("/career/preview-goal", { role_id: roleId });
      modal({
        title: `Switch goal to ${preview.role_title}?`,
        body: el(
          "div",
          {},
          el("p", {
            text: `${pct(preview.carryover_pct)} of the new role carries over from your verified skills.`,
          }),
          el("p", { text: `Reused: ${preview.reused_names.join(", ") || "none"}` }),
          el("p", { text: `New to learn: ${preview.delta_names.join(", ") || "nothing"}` }),
        ),
        confirmLabel: "Switch goal",
        onConfirm: async () => {
          const res = await api.post("/career/goal", { role_id: roleId });
          page.replaceChildren();
          await render(page);
          page
            .querySelector(".stack")
            .prepend(
              card(
                "Goal changed — roadmap rebuilt",
                el("p", { text: res.summary }),
                el("p", { text: `New roadmap: ${res.roadmap_steps.length} steps.` }),
                agentTrace(res.agent_trace),
              ),
            );
          announce(`Goal switched to ${preview.role_title}.`);
          toast("Goal switched. Roadmap rebuilt from your verified skills.", "success");
        },
      });
    } catch (error) {
      toast(error.message, "error");
    }
  });
  return btn;
}

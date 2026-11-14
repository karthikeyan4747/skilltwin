// Reusable, accessible UI components. All text is set with textContent, never innerHTML.

export function el(tag, attrs = {}, ...children) {
  const node = document.createElement(tag);
  for (const [key, value] of Object.entries(attrs)) {
    if (value === null || value === undefined || value === false) continue;
    if (key === "class") node.className = value;
    else if (key === "text") node.textContent = value;
    else if (key === "value") node.value = value;
    else if (key.startsWith("on")) node.addEventListener(key.slice(2).toLowerCase(), value);
    else if (key in node && typeof value !== "string") node[key] = value;
    else node.setAttribute(key, value === true ? "" : String(value));
  }
  append(node, children);
  return node;
}

export function append(node, children) {
  for (const child of children.flat(Infinity)) {
    if (child === null || child === undefined || child === false) continue;
    node.append(child instanceof Node ? child : document.createTextNode(String(child)));
  }
}

export const reducedMotion = () => window.matchMedia("(prefers-reduced-motion: reduce)").matches;
export const pct = (value) => `${Math.round(value)}%`;
export const conf = (value) => `${Math.round(value * 100)}%`;

export function pageHead(title, intro, ...actions) {
  return el("div", { class: "page-head" }, el("div", {}, el("h1", { text: title }), intro && el("p", { text: intro })), actions.length ? el("div", { class: "row" }, actions) : null);
}

export function card(title, ...children) {
  return el("section", { class: "card" }, title ? el("h2", { class: "card-title", text: title }) : null, children);
}

export function subcard(title, ...children) {
  return el("section", { class: "card" }, el("h3", { class: "card-title", text: title }), children);
}

export function button(label, { variant = "primary", onClick, type = "button", ...rest } = {}) {
  return el("button", { class: `btn btn-${variant}`, type, onClick, ...rest }, label);
}

export async function withLoading(btn, task) {
  if (btn.getAttribute("aria-busy") === "true") return undefined;
  const original = [...btn.childNodes];
  btn.setAttribute("aria-busy", "true");
  btn.disabled = true;
  btn.replaceChildren(el("span", { class: "spinner", "aria-hidden": "true" }), el("span", { text: "Working…" }));
  try {
    return await task();
  } finally {
    btn.replaceChildren(...original);
    btn.disabled = false;
    btn.removeAttribute("aria-busy");
  }
}

export function badge(text, tone = "") {
  return el("span", { class: `badge${tone ? ` badge-${tone}` : ""}`, text });
}

export function progressBar(label, fraction, { verified = false, valueText } = {}) {
  const value = Math.max(0, Math.min(1, fraction));
  const fill = el("div", { class: `progress-fill${verified ? " is-verified" : ""}` });
  fill.style.width = `${value * 100}%`;
  const text = valueText || conf(value);
  return el(
    "div",
    { class: "progress" },
    el("div", { class: "progress-label" }, el("span", { text: label }), el("span", { text })),
    el("div", { class: "progress-track", role: "progressbar", "aria-label": label, "aria-valuemin": "0", "aria-valuemax": "100", "aria-valuenow": String(Math.round(value * 100)), "aria-valuetext": text }, fill),
  );
}

export function stat(value, label) {
  return el("div", { class: "card stat" }, el("span", { class: "stat-value", text: value }), el("span", { class: "stat-label", text: label }));
}

export function announce(text) {
  const region = document.getElementById("announcer");
  region.textContent = "";
  window.setTimeout(() => (region.textContent = text), 50);
}

export function toast(message, tone = "info") {
  const node = el("div", { class: `toast toast-${tone}`, text: message });
  document.getElementById("toast-region").append(node);
  window.setTimeout(() => node.remove(), 5000);
}

export function modal({ title, body, confirmLabel = "Confirm", onConfirm }) {
  const previous = document.activeElement;
  const heading = el("h2", { id: "modal-title", text: title });
  const cancel = button("Cancel", { variant: "secondary", onClick: () => close() });
  const confirm = button(confirmLabel, { onClick: () => withLoading(confirm, async () => { await onConfirm(); close(); }).catch((e) => toast(e.message, "error")) });
  const dialog = el("div", { class: "modal", role: "dialog", "aria-modal": "true", "aria-labelledby": "modal-title" }, heading, body, el("div", { class: "row" }, confirm, cancel));
  const backdrop = el("div", { class: "modal-backdrop" }, dialog);
  function close() {
    backdrop.remove();
    document.removeEventListener("keydown", onKey);
    previous?.focus();
  }
  function onKey(event) {
    if (event.key === "Escape") close();
    if (event.key !== "Tab") return;
    const focusable = [...dialog.querySelectorAll("button, a[href], input, select, textarea")].filter((n) => !n.disabled);
    const first = focusable[0];
    const last = focusable[focusable.length - 1];
    if (event.shiftKey && document.activeElement === first) { event.preventDefault(); last.focus(); }
    else if (!event.shiftKey && document.activeElement === last) { event.preventDefault(); first.focus(); }
  }
  document.addEventListener("keydown", onKey);
  document.body.append(backdrop);
  confirm.focus();
}

export function emptyState(title, text, action) {
  return el("div", { class: "empty" }, el("h2", { class: "card-title", text: title }), el("p", { class: "muted", text }), action);
}

export function skeleton(lines = 4) {
  return el("div", { class: "skeleton", role: "status", "aria-label": "Loading" }, Array.from({ length: lines }, () => el("div", { class: "skeleton-line" })));
}

export function renderError(root, error, retry) {
  root.replaceChildren(
    el("div", { class: "error-state", role: "alert" }, el("h2", { class: "card-title", text: "Something went wrong" }), el("p", { text: error.message || "Please try again." }), button("Retry", { onClick: retry })),
  );
}

export async function loadInto(root, loader, draw) {
  root.replaceChildren(skeleton());
  try {
    const data = await loader();
    root.replaceChildren();
    draw(root, data);
  } catch (error) {
    renderError(root, error, () => loadInto(root, loader, draw));
  }
}

export function agentTrace(steps) {
  if (!steps?.length) return null;
  return el(
    "details",
    { class: "trace" },
    el("summary", { text: "How the agents worked together" }),
    el("ol", {}, steps.map((s) => el("li", {}, el("strong", { text: s.agent }), ` — ${s.purpose} `, el("span", { class: "muted small", text: `(${s.duration_ms} ms, ${s.mode === "live" ? "live AI" : "offline AI"})` })))),
  );
}

export function showFieldErrors(form, fields = {}) {
  form.querySelectorAll(".field-error").forEach((n) => n.remove());
  form.querySelectorAll("[aria-invalid]").forEach((n) => n.removeAttribute("aria-invalid"));
  for (const [name, message] of Object.entries(fields)) {
    const input = form.querySelector(`[name="${name.split(".")[0]}"]`);
    if (!input) continue;
    const id = `${input.id}-error`;
    input.setAttribute("aria-invalid", "true");
    input.setAttribute("aria-describedby", id);
    input.closest(".field")?.append(el("p", { class: "field-error", id, text: message }));
  }
}

export function stepStatusBadge(status) {
  const map = { done: ["✓ Done", "success"], in_progress: ["◐ In progress", "accent"], todo: ["○ To do", ""] };
  const [text, tone] = map[status];
  return badge(text, tone);
}

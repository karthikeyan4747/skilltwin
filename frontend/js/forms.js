// Inline form errors: mark fields invalid and link each message with aria-describedby.
import { el } from "./ui.js";

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

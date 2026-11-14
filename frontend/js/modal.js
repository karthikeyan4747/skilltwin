// Accessible modal dialog: focus trapped, Esc closes, focus returns to the opener.
import { button, el, toast, withLoading } from "./ui.js";

export function modal({ title, body, confirmLabel = "Confirm", onConfirm }) {
  const previous = document.activeElement;
  const heading = el("h2", { id: "modal-title", text: title });
  const cancel = button("Cancel", { variant: "secondary", onClick: () => close() });
  const confirm = button(confirmLabel, {
    onClick: () =>
      withLoading(confirm, async () => {
        await onConfirm();
        close();
      }).catch((e) => toast(e.message, "error")),
  });
  const dialog = el(
    "div",
    { class: "modal", role: "dialog", "aria-modal": "true", "aria-labelledby": "modal-title" },
    heading,
    body,
    el("div", { class: "row" }, confirm, cancel),
  );
  const backdrop = el("div", { class: "modal-backdrop" }, dialog);
  function close() {
    backdrop.remove();
    document.removeEventListener("keydown", onKey);
    previous?.focus();
  }
  function onKey(event) {
    if (event.key === "Escape") close();
    if (event.key !== "Tab") return;
    const focusable = [
      ...dialog.querySelectorAll("button, a[href], input, select, textarea"),
    ].filter((n) => !n.disabled);
    const first = focusable[0];
    const last = focusable[focusable.length - 1];
    if (event.shiftKey && document.activeElement === first) {
      event.preventDefault();
      last.focus();
    } else if (!event.shiftKey && document.activeElement === last) {
      event.preventDefault();
      first.focus();
    }
  }
  document.addEventListener("keydown", onKey);
  document.body.append(backdrop);
  confirm.focus();
}

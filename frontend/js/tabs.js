// Accessible tabs (WAI-ARIA tablist): arrow keys, Home/End, lazy panel rendering.
import { append, el } from "./ui.js";

export function tabs(label, items) {
  const list = el("div", { class: "tablist", role: "tablist", "aria-label": label });
  const panels = items.map((item) => el("div", { role: "tabpanel", id: `panel-${item.id}`, "aria-labelledby": `tab-${item.id}`, tabindex: "0", hidden: true }));
  const buttons = items.map((item, i) =>
    el("button", { class: "tab", role: "tab", id: `tab-${item.id}`, "aria-controls": `panel-${item.id}`, type: "button", onClick: () => select(i) }, item.label),
  );
  function select(index, focus = false) {
    buttons.forEach((btn, i) => {
      const active = i === index;
      btn.setAttribute("aria-selected", String(active));
      btn.tabIndex = active ? 0 : -1;
      panels[i].hidden = !active;
    });
    if (!panels[index].dataset.rendered) {
      panels[index].dataset.rendered = "1";
      items[index].render(panels[index]);
    }
    if (focus) buttons[index].focus();
  }
  list.addEventListener("keydown", (event) => {
    const current = buttons.indexOf(document.activeElement);
    const moves = { ArrowRight: 1, ArrowLeft: -1, Home: -current, End: buttons.length - 1 - current };
    if (current < 0 || !(event.key in moves)) return;
    event.preventDefault();
    select((current + moves[event.key] + buttons.length) % buttons.length, true);
  });
  append(list, buttons);
  select(0);
  return el("div", {}, list, panels);
}

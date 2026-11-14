// Entry point: wire the app shell (nav toggle, AI mode badge) and start routing.
import { startRouter } from "./router.js";
import { subscribe } from "./state.js";

const toggle = document.querySelector(".nav-toggle");
const nav = document.getElementById("primary-nav");

toggle.addEventListener("click", () => {
  const open = toggle.getAttribute("aria-expanded") !== "true";
  toggle.setAttribute("aria-expanded", String(open));
  nav.dataset.open = String(open);
});

nav.addEventListener("click", (event) => {
  if (event.target.closest("a")) {
    toggle.setAttribute("aria-expanded", "false");
    nav.dataset.open = "false";
  }
});

subscribe((state) => {
  document.getElementById("ai-mode").hidden = !state.aiOffline;
});

startRouter();

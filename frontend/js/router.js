// Hash router: #/<view>. Back/forward work natively; focus moves to the new page heading.
import { renderError } from "./ui.js";

const ROUTES = {
  dashboard: { title: "Dashboard", load: () => import("./views/dashboard.js") },
  profile: { title: "Profile", load: () => import("./views/profile.js") },
  analysis: { title: "Skill Analysis", load: () => import("./views/analysis.js") },
  career: { title: "Career Matching", load: () => import("./views/career.js") },
  assessment: { title: "Assessment", load: () => import("./views/assessment.js") },
  lessons: { title: "Lessons", load: () => import("./views/lessons.js") },
  roadmap: { title: "Roadmap", load: () => import("./views/roadmap.js") },
  progress: { title: "Progress", load: () => import("./views/progress.js") },
  mentor: { title: "AI Mentor", load: () => import("./views/mentor.js") },
  publish: { title: "Learn in Public", load: () => import("./views/publish.js") },
  insights: { title: "Insights", load: () => import("./views/insights.js") },
};

let cleanup = null;

function currentRoute() {
  const name = location.hash.replace(/^#\//, "").split("?")[0];
  return ROUTES[name] ? name : "dashboard";
}

async function render() {
  const name = currentRoute();
  const route = ROUTES[name];
  document.title = `${route.title} · SkillTwin`;
  document.querySelectorAll("#primary-nav a").forEach((link) => {
    if (link.getAttribute("href") === `#/${name}`) link.setAttribute("aria-current", "page");
    else link.removeAttribute("aria-current");
  });
  if (typeof cleanup === "function") cleanup();
  cleanup = null;
  const root = document.getElementById("view");
  root.replaceChildren();
  try {
    const view = await route.load();
    cleanup = await view.render(root);
  } catch (error) {
    renderError(root, error, render);
  }
  const heading = root.querySelector("h1");
  if (heading) {
    heading.tabIndex = -1;
    heading.focus({ preventScroll: true });
  }
  window.scrollTo(0, 0);
}

export function navigate(name) {
  location.hash = `#/${name}`;
}

export function startRouter() {
  window.addEventListener("hashchange", render);
  render();
}

"""Server-rendered HTML for `/` and `/about`, readable without JavaScript.

All dynamic text is HTML-escaped. Content comes from the feature registry, the agent roster,
the app's routes and the deterministic core, so the pages cannot drift from the code.
"""

from collections import defaultdict
from html import escape
from pathlib import Path
from string import Template
from typing import Any

from fastapi import FastAPI

from backend.agents.team import AgentProfile
from backend.registry import ADAPTATION_LOOPS, FEATURES, REPO_URL

TEMPLATES = Path(__file__).resolve().parent.parent / "templates"
DESCRIPTION = (
    "SkillTwin verifies skills with evidence, compares them with a target job role and builds "
    "an adaptive learning roadmap with collaborating AI agents and a Learner Twin."
)


def _template(name: str) -> Template:
    return Template((TEMPLATES / name).read_text(encoding="utf-8"))


def _list(items: list[str], tag: str = "ul") -> str:
    return f"<{tag}>" + "".join(f"<li>{escape(i)}</li>" for i in items) + f"</{tag}>"


def _joined(items: list[str], empty: str) -> str:
    return escape(", ".join(items) or empty)


def endpoints_by_tag(app: FastAPI) -> dict[str, list[str]]:
    """Map each OpenAPI tag to its 'METHOD /path' endpoints, read from the app's own schema."""
    grouped: dict[str, list[str]] = defaultdict(list)
    for path, operations in app.openapi()["paths"].items():
        for method, operation in operations.items():
            for tag in operation.get("tags", []):
                grouped[tag].append(f"{method.upper()} {path}")
    return dict(grouped)


def _features_html() -> str:
    required = [f for f in FEATURES if f.required]
    items = "".join(
        f'<li><a href="{escape(f.ui_route)}">{escape(f.title)}</a>: {escape(f.requirement)}</li>'
        for f in required
    )
    return f"<ul>{items}</ul>"


def _loops_html() -> str:
    items = "".join(
        f"<li><strong>{escape(name)}:</strong> {escape(text)}</li>"
        for name, text in ADAPTATION_LOOPS
    )
    return f"<ul>{items}</ul>"


def _links_html() -> str:
    return (
        f'<p>Source code: <a href="{REPO_URL}">GitHub</a> · '
        '<a href="/about">Features, agents and API endpoints</a> · '
        '<a href="/docs">OpenAPI docs</a></p>'
    )


def render_summary(summary: dict[str, Any]) -> str:
    """Static first-load content: the sample scenario result, features and adaptation loops."""
    twin = summary["twin_accuracy"]
    twin_text = "measured once questions are answered" if twin is None else f"{twin:.0%}"
    better = summary["better_fit"] or "none"
    return f"""
<div class="page-head"><div><h1>SkillTwin</h1><p>{escape(DESCRIPTION)}</p></div></div>
<div class="stack">
<section class="card banner" aria-labelledby="scenario-title">
  <h2 id="scenario-title" class="card-title">Sample scenario: Python, SQL and basic HTML
  → {escape(summary["role_title"])}</h2>
  <p>Readiness for {escape(summary["role_title"])}: claimed {summary["claimed_pct"]:.0f}%,
  proven by evidence {summary["proven_pct"]:.0f}%.</p>
  <ul>
    <li>Verified by evidence: {_joined(summary["verified"], "none yet")}</li>
    <li>Claimed but not yet proven: {_joined(summary["unproven"], "none")}</li>
    <li>Missing skills: {_joined(summary["missing"], "none")}</li>
    <li>Better-fit role on proven skills: {escape(better)}</li>
    <li>Estimated time to ready: {summary["time_to_ready_weeks"]} weeks</li>
    <li>Learner Twin prediction accuracy: {escape(twin_text)}</li>
  </ul>
  <h3>Roadmap order (prerequisites first)</h3>
  {_list(summary["roadmap_order"], "ol")}
</section>
<section class="card"><h2 class="card-title">The six required features</h2>
{_features_html()}</section>
<section class="card"><h2 class="card-title">How the plan adapts</h2>{_loops_html()}</section>
{_links_html()}
</div>"""


def render_index(summary_html: str, base_url: str) -> str:
    return _template("index.html").substitute(
        summary=summary_html, description=escape(DESCRIPTION), base_url=escape(base_url)
    )


def _cell_list(items: list[str] | tuple[str, ...]) -> str:
    return "<br>".join(f"<code>{escape(i)}</code>" for i in items) or "—"


def render_about(
    app: FastAPI, roster: list[AgentProfile], version: str, ai_mode: str, base_url: str
) -> str:
    endpoints = endpoints_by_tag(app)
    feature_rows = "".join(
        "<tr>"
        f'<th scope="row">{escape(f.title)}{"" if f.required else " <small>(additional)</small>"}'
        f"</th><td>{escape(f.requirement)}</td>"
        f'<td><a href="/{escape(f.ui_route)}">{escape(f.ui_route)}</a></td>'
        f"<td>{_cell_list(endpoints.get(f.api_tag, []))}</td>"
        f"<td>{_cell_list(f.modules)}</td><td>{_cell_list(f.tests)}</td></tr>"
        for f in FEATURES
    )
    agent_rows = "".join(
        f'<tr><th scope="row">{escape(a.name)}</th><td>{escape(a.responsibility)}</td>'
        f"<td>{escape(' / '.join(t.upper() for t in a.tiers))}</td>"
        f"<td>{_cell_list(a.models)}</td></tr>"
        for a in roster
    )
    content = f"""
<h1>About SkillTwin</h1>
<p>{escape(DESCRIPTION)}</p>
<p class="muted">Version {escape(version)} · AI mode: {escape(ai_mode)}</p>
<div class="stack">
<section class="card"><h2 class="card-title">Features</h2><div class="table-wrap"><table>
<caption class="visually-hidden">
Each feature with its UI route, API endpoints, code and tests</caption>
<thead><tr><th scope="col">Feature</th><th scope="col">Requirement</th><th scope="col">UI route</th>
<th scope="col">API endpoints</th><th scope="col">Code</th><th scope="col">Tests</th></tr></thead>
<tbody>{feature_rows}</tbody></table></div></section>
<section class="card"><h2 class="card-title">How the plan adapts</h2>{_loops_html()}</section>
<section class="card"><h2 class="card-title">Agent roster</h2><div class="table-wrap"><table>
<caption class="visually-hidden">
Specialised agents, their responsibilities and model tiers</caption>
<thead><tr><th scope="col">Agent</th><th scope="col">Responsibility</th><th scope="col">Tier</th>
<th scope="col">Model</th></tr></thead><tbody>{agent_rows}</tbody></table></div></section>
{_links_html()}
</div>"""
    return _template("about.html").substitute(
        content=content,
        description=escape(DESCRIPTION),
        base_url=escape(base_url),
        repo_url=REPO_URL,
    )

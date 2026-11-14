"""Server-rendered pages and health check: readable without JavaScript."""

from fastapi import APIRouter, Request
from fastapi.responses import HTMLResponse

from backend import __version__
from backend.agents.base import Mode
from backend.api.deps import Services, ServicesDep
from backend.api.pages import render_about, render_index, render_summary
from backend.api.presenters import readiness_summary
from backend.api.views import HealthView
from backend.core.roadmap import build_roadmap

router = APIRouter(tags=["Site"])


def sample_summary_html(services: Services) -> str:
    """Server-rendered sample scenario result, computed by the deterministic core (no LLM)."""
    orchestrator = services.orchestrator
    learner = services.catalog.sample_learner(orchestrator.clock())
    ctx = orchestrator.context(learner)
    plan = build_roadmap(services.catalog.graph, ctx.role, ctx.statuses)
    ctx = orchestrator.context(learner.model_copy(update={"roadmap": plan}))
    return render_summary(readiness_summary(ctx))


def ai_mode(services: Services) -> Mode:
    """'live' when a Groq key is configured, otherwise 'offline' (MockLLM)."""
    return "live" if services.ai_live else "offline"


@router.get("/", response_class=HTMLResponse, include_in_schema=False)
async def index(request: Request) -> HTMLResponse:
    """App shell with the sample-scenario summary rendered on the server."""
    return HTMLResponse(render_index(request.app.state.index_summary, str(request.base_url)))


@router.get("/about", response_class=HTMLResponse, summary="About page")
async def about(request: Request, services: ServicesDep) -> HTMLResponse:
    """Every feature with its UI route, API endpoints, code and tests, plus the agent roster."""
    roster = services.orchestrator.agents.roster(services.models)
    html = render_about(request.app, roster, __version__, ai_mode(services), str(request.url))
    return HTMLResponse(html)


@router.get("/healthz", summary="Health check")
@router.get("/health", summary="Health check (Cloud Run-safe path)")
async def health(services: ServicesDep) -> HealthView:
    """Liveness plus version and whether agents call a live LLM or the offline MockLLM.

    Cloud Run reserves paths ending in "z", so use `/health` there.
    """
    return HealthView(status="ok", version=__version__, llm=ai_mode(services))

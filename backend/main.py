"""SkillTwin app factory: middleware, API routers, static frontend and startup wiring."""

import logging
from collections.abc import AsyncIterator
from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import FastAPI
from fastapi.middleware.gzip import GZipMiddleware
from fastapi.staticfiles import StaticFiles

from backend import __version__
from backend.agents.base import ModelTiers
from backend.agents.team import AgentTeam
from backend.api.deps import Services, configure_llm_rate_limit, limiter
from backend.api.errors import install_error_handlers
from backend.api.middleware import BodySizeLimit, security_headers, session_middleware
from backend.api.routes import (
    analysis,
    assessment,
    career,
    dashboard,
    docs,
    insights,
    lessons,
    mentor,
    meta,
    profile,
    progress,
    publish,
    roadmap,
    scenario,
    site,
    twin,
)
from backend.config import Settings, get_settings
from backend.orchestrator import Orchestrator
from backend.services.catalog import load_catalog
from backend.services.jobs import JobDemandService
from backend.services.llm import GroqClient, LLMClient, MockLLM
from backend.services.mock_fixtures import MOCK_FIXTURES
from backend.services.repository import Repository

FRONTEND_DIR = Path(__file__).resolve().parent.parent / "frontend"
ROUTERS = (
    dashboard,
    profile,
    analysis,
    career,
    assessment,
    roadmap,
    progress,
    mentor,
    twin,
    lessons,
    publish,
    insights,
    scenario,
    meta,
)


def build_services(settings: Settings, llm: LLMClient | None = None) -> Services:
    catalog = load_catalog()
    mock = MockLLM(MOCK_FIXTURES)
    if llm is None and settings.groq_api_key:
        llm = GroqClient(settings.groq_api_key.get_secret_value())
    llm = llm or mock
    models = ModelTiers(
        fast=settings.llm_model_fast,
        smart=settings.llm_model_smart,
        vision=settings.llm_model_vision,
    )
    adzuna_key = settings.adzuna_app_key.get_secret_value() if settings.adzuna_app_key else None
    return Services(
        settings=settings,
        catalog=catalog,
        repo=Repository(settings.database_path),
        orchestrator=Orchestrator(catalog, AgentTeam.build(llm, mock, models)),
        jobs=JobDemandService(settings.adzuna_app_id, adzuna_key, catalog.graph),
        models=models,
        ai_live=llm.live,
    )


def create_app(settings: Settings | None = None, llm: LLMClient | None = None) -> FastAPI:
    settings = settings or get_settings()
    logging.basicConfig(level=logging.INFO)
    services = build_services(settings, llm)

    @asynccontextmanager
    async def lifespan(_: FastAPI) -> AsyncIterator[None]:
        yield
        services.repo.close()

    app = FastAPI(
        lifespan=lifespan,
        title="SkillTwin API",
        version=__version__,
        description=(
            "Agentic AI personalized learning platform: evidence-verified skills, career "
            "matching, adaptive roadmaps and a Learner Twin. All learner endpoints are scoped "
            "to a signed guest-session cookie issued on the first request."
        ),
        docs_url=None,
        openapi_url="/openapi.json",
        redoc_url=None,
    )
    app.state.services = services
    app.state.limiter = limiter
    configure_llm_rate_limit(settings.llm_rate_limit)
    install_error_handlers(app)

    # Last added runs first: security headers wrap everything, then body limit, gzip, session.
    secret = settings.session_secret.get_secret_value() if settings.session_secret else ""
    app.middleware("http")(session_middleware(secret, secure=settings.env == "prod"))
    app.add_middleware(GZipMiddleware, minimum_size=1024)
    app.add_middleware(BodySizeLimit, max_bytes=settings.max_body_bytes)
    app.middleware("http")(security_headers)

    for module in ROUTERS:
        app.include_router(module.router, prefix="/api/v1")
    app.include_router(site.router)
    app.include_router(docs.router)
    app.state.index_summary = site.sample_summary_html(services)

    app.mount("/", StaticFiles(directory=FRONTEND_DIR), name="frontend")
    return app

"""Dependency wiring: shared services, session-scoped learner and the rate limiter."""

import hashlib
from dataclasses import dataclass
from typing import Annotated

from fastapi import Depends, Request
from slowapi import Limiter
from slowapi.util import get_remote_address
from starlette import status

from backend.agents.base import ModelTiers
from backend.api.errors import AppError
from backend.config import Settings
from backend.core.models import Learner
from backend.orchestrator import Orchestrator
from backend.services.catalog import Catalog
from backend.services.jobs import JobDemandService
from backend.services.repository import Repository


@dataclass(frozen=True)
class Services:
    settings: Settings
    catalog: Catalog
    repo: Repository
    orchestrator: Orchestrator
    jobs: JobDemandService
    models: ModelTiers
    ai_live: bool


def rate_limit_key(request: Request) -> str:
    """Rate limits apply per guest session and client IP together."""
    return f"{getattr(request.state, 'session_id', '-')}:{get_remote_address(request)}"


limiter = Limiter(key_func=rate_limit_key)
_llm_limit = {"value": "20/minute"}


def configure_llm_rate_limit(value: str) -> None:
    """Set the per session+IP limit applied to every route that calls an LLM agent."""
    _llm_limit["value"] = value


def llm_rate_limit() -> str:
    """Current LLM route limit (e.g. '20/minute'); read on every request by slowapi."""
    return _llm_limit["value"]


def get_services(request: Request) -> Services:
    """Shared services created at startup by the app factory."""
    services: Services = request.app.state.services
    return services


def get_session_id(request: Request) -> str:
    """Guest session id set by the session middleware."""
    session_id: str = request.state.session_id
    return session_id


def learner_key(session_id: str) -> str:
    """Anonymized identifier used for cohort insights; never the raw session id."""
    return "session-" + hashlib.sha256(session_id.encode()).hexdigest()[:12]


ServicesDep = Annotated[Services, Depends(get_services)]
SessionDep = Annotated[str, Depends(get_session_id)]


async def get_learner(services: ServicesDep, session_id: SessionDep) -> Learner:
    """This session's learner; the sample-scenario learner is copied in on first use."""
    learner = services.repo.get_learner(session_id)
    if learner is not None:
        return learner
    seeded = services.catalog.sample_learner(services.orchestrator.clock())
    learner, _ = await services.orchestrator.onboard(seeded)
    services.repo.save_learner(session_id, learner)
    return learner


LearnerDep = Annotated[Learner, Depends(get_learner)]


def require_skill(catalog: Catalog, skill_id: str) -> str:
    """Return the skill id, or raise a 404 error envelope if it is not in the catalog."""
    if skill_id not in catalog.graph:
        raise AppError(
            status.HTTP_404_NOT_FOUND, "unknown_skill", "That skill is not in the catalog."
        )
    return skill_id


def require_role(catalog: Catalog, role_id: str) -> str:
    """Return the role id, or raise a 404 error envelope if it is not in the catalog."""
    if role_id not in catalog.roles:
        raise AppError(
            status.HTTP_404_NOT_FOUND, "unknown_role", "That job role is not in the catalog."
        )
    return role_id

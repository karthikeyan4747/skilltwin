"""Dependency wiring: shared services, session-scoped learner and the rate limiter."""

import hashlib
from dataclasses import dataclass
from typing import Annotated

from fastapi import Depends, Request
from slowapi import Limiter
from slowapi.util import get_remote_address

from backend.api.errors import AppError
from backend.config import Settings
from backend.core.models import Learner, Roadmap
from backend.core.progress import confidence_trail
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
    return _llm_limit["value"]


def get_services(request: Request) -> Services:
    return request.app.state.services


def get_session_id(request: Request) -> str:
    return request.state.session_id


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
    catalog = services.catalog
    now = services.orchestrator.clock()
    profile = catalog.seed_profile()
    evidence = catalog.seed_evidence(now)
    seeded = Learner(
        profile=profile,
        evidence=evidence,
        roadmap=Roadmap(role_id=profile.career_goal),
        confidence_history=confidence_trail(catalog.graph, profile.claimed_skills, evidence),
    )
    learner, _ = await services.orchestrator.onboard(seeded)
    services.repo.save_learner(session_id, learner)
    return learner


LearnerDep = Annotated[Learner, Depends(get_learner)]


def require_skill(catalog: Catalog, skill_id: str) -> str:
    if skill_id not in catalog.graph:
        raise AppError(404, "unknown_skill", "That skill is not in the catalog.")
    return skill_id


def require_role(catalog: Catalog, role_id: str) -> str:
    if role_id not in catalog.roles:
        raise AppError(404, "unknown_role", "That job role is not in the catalog.")
    return role_id

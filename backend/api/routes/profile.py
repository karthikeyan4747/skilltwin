"""User Profile: learner details, claimed skills, certifications, projects and career goal."""

from typing import Any

from fastapi import APIRouter, Request
from starlette import status

from backend.api.deps import LearnerDep, ServicesDep, SessionDep, limiter, llm_rate_limit
from backend.api.errors import AppError
from backend.core.models import Profile

router = APIRouter(prefix="/profile", tags=["User Profile"])


@router.get("", summary="Get learner profile")
async def get_profile(learner: LearnerDep, services: ServicesDep) -> dict[str, Any]:
    """The session learner's profile plus the skill and role options for the form."""
    catalog = services.catalog
    return {
        "profile": learner.profile.model_dump(),
        "skill_options": [{"id": s.id, "name": s.name} for s in catalog.graph.skills.values()],
        "role_options": [{"id": r.id, "title": r.title} for r in catalog.roles.values()],
    }


@router.put("", summary="Save learner profile")
@limiter.limit(llm_rate_limit)
async def save_profile(
    request: Request,
    profile: Profile,
    learner: LearnerDep,
    services: ServicesDep,
    session_id: SessionDep,
) -> dict[str, Any]:
    """Persist the profile and refresh analysis, career ranking and roadmap (onboard flow)."""
    unknown = [s for s in profile.claimed_skills if s not in services.catalog.graph]
    if unknown or profile.career_goal not in services.catalog.roles:
        raise AppError(
            status.HTTP_422_UNPROCESSABLE_CONTENT,
            "validation_error",
            "Choose skills and a career goal from the lists.",
        )
    profile = profile.model_copy(
        update={"claimed_skills": list(dict.fromkeys(profile.claimed_skills))}
    )
    if profile.career_goal != learner.profile.career_goal:
        learner = learner.model_copy(
            update={"roadmap": learner.roadmap.model_copy(update={"steps": []})}
        )
    updated, result = await services.orchestrator.onboard(
        learner.model_copy(update={"profile": profile})
    )
    services.repo.save_learner(session_id, updated)
    return {"profile": updated.profile.model_dump(), "result": result.model_dump(mode="json")}

"""Roadmap & Learning Recommendations: ordered steps, resources, status and reroute history."""

from typing import Any

from fastapi import APIRouter

from backend.api.deps import LearnerDep, ServicesDep, SessionDep, require_skill
from backend.api.errors import AppError
from backend.api.presenters import roadmap_view
from backend.api.schemas import StepUpdate
from backend.core.roadmap import set_step_status

router = APIRouter(prefix="/roadmap", tags=["Learning Recommendations"])


@router.get("")
async def get_roadmap(learner: LearnerDep, services: ServicesDep) -> dict[str, Any]:
    return roadmap_view(services.orchestrator.context(learner))


@router.patch("/steps/{skill_id}")
async def update_step(
    skill_id: str,
    body: StepUpdate,
    learner: LearnerDep,
    services: ServicesDep,
    session_id: SessionDep,
) -> dict[str, Any]:
    require_skill(services.catalog, skill_id)
    try:
        plan = set_step_status(learner.roadmap, skill_id, body.status, body.actual_hours)
    except KeyError as exc:
        raise AppError(404, "step_not_found", "That step is not on your roadmap.") from exc
    updated = learner.model_copy(update={"roadmap": plan})
    services.repo.save_learner(session_id, updated)
    return roadmap_view(services.orchestrator.context(updated))

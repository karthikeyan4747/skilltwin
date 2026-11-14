"""Roadmap & Learning Recommendations: ordered steps, resources, status and reroute history."""

from fastapi import APIRouter
from starlette import status

from backend.api.deps import LearnerDep, ServicesDep, SessionDep, require_skill
from backend.api.errors import AppError
from backend.api.presenters import roadmap_view
from backend.api.schemas import StepUpdate
from backend.api.views import RoadmapView
from backend.core.roadmap import set_step_status

router = APIRouter(prefix="/roadmap", tags=["Learning Recommendations"])


@router.get("", summary="Learning roadmap")
async def get_roadmap(learner: LearnerDep, services: ServicesDep) -> RoadmapView:
    """Ordered gap steps with reasons, hours, course/tutorial/exercise resources and reroute
    history.
    """
    return roadmap_view(services.orchestrator.context(learner))


@router.patch("/steps/{skill_id}", summary="Update a roadmap step")
async def update_step(
    skill_id: str,
    body: StepUpdate,
    learner: LearnerDep,
    services: ServicesDep,
    session_id: SessionDep,
) -> RoadmapView:
    """Set a step's status, optionally with actual hours spent (used to measure pace)."""
    require_skill(services.catalog, skill_id)
    try:
        plan = set_step_status(learner.roadmap, skill_id, body.status, body.actual_hours)
    except KeyError as exc:
        raise AppError(
            status.HTTP_404_NOT_FOUND, "step_not_found", "That step is not on your roadmap."
        ) from exc
    updated = learner.model_copy(update={"roadmap": plan})
    services.repo.save_learner(session_id, updated)
    return roadmap_view(services.orchestrator.context(updated))

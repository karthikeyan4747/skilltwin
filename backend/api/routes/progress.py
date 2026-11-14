"""Progress Tracking: confidence over time, assessment history, completion and Twin accuracy."""

from typing import Any

from fastapi import APIRouter

from backend.api.deps import LearnerDep, ServicesDep
from backend.api.presenters import progress_view

router = APIRouter(prefix="/progress", tags=["Progress Tracking"])


@router.get("")
async def get_progress(learner: LearnerDep, services: ServicesDep) -> dict[str, Any]:
    return progress_view(services.orchestrator.context(learner))

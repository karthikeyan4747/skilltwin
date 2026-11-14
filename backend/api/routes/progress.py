"""Progress Tracking: confidence over time, assessment history, completion and Twin accuracy."""

from fastapi import APIRouter

from backend.api.deps import LearnerDep, ServicesDep
from backend.api.presenters import progress_view
from backend.api.views import ProgressView

router = APIRouter(prefix="/progress", tags=["Progress Tracking"])


@router.get("", summary="Progress tracking")
async def get_progress(learner: LearnerDep, services: ServicesDep) -> ProgressView:
    """Confidence over time, assessment history, completion %, Twin accuracy and the latest
    interview batch.
    """
    return progress_view(services.orchestrator.context(learner))

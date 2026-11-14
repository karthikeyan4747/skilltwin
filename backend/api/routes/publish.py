"""Learn in Public: LinkedIn draft and learning log built from verified evidence."""

from fastapi import APIRouter, Request

from backend.api.deps import LearnerDep, ServicesDep, limiter, llm_rate_limit
from backend.results import PublishResult

router = APIRouter(prefix="/publish", tags=["Learn in Public"])


@router.post("/draft", summary="Draft a Learn-in-Public post")
@limiter.limit(llm_rate_limit)
async def draft(request: Request, learner: LearnerDep, services: ServicesDep) -> PublishResult:
    """LinkedIn draft and learning-log markdown generated only from verified evidence."""
    return await services.orchestrator.publish_draft(learner)

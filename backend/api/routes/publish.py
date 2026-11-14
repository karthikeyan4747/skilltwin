"""Learn in Public: LinkedIn draft and learning log built from verified evidence."""

from typing import Any

from fastapi import APIRouter, Request

from backend.api.deps import LearnerDep, ServicesDep, limiter, llm_rate_limit

router = APIRouter(prefix="/publish", tags=["Learn in Public"])


@router.post("/draft")
@limiter.limit(llm_rate_limit)
async def draft(request: Request, learner: LearnerDep, services: ServicesDep) -> dict[str, Any]:
    result = await services.orchestrator.publish_draft(learner)
    return result.model_dump(mode="json")

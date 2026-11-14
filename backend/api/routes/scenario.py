"""Sample Scenario: both adaptation loops in one request, on a fresh sample learner."""

from typing import Any

from fastapi import APIRouter, Request

from backend.api.deps import ServicesDep, SessionDep, learner_key, limiter, llm_rate_limit

router = APIRouter(prefix="/scenario", tags=["Sample Scenario"])


@router.post("/sample", summary="Run the sample scenario")
@limiter.limit(llm_rate_limit)
async def run_sample(
    request: Request, services: ServicesDep, session_id: SessionDep
) -> dict[str, Any]:
    """Reset this session to the sample learner (Python, SQL, basic HTML -> Full Stack), fail a
    React question (root-cause reroute), then switch to the best-fit role (goal change)."""
    learner = services.catalog.sample_learner(services.orchestrator.clock())
    updated, result = await services.orchestrator.sample_scenario(learner)
    services.repo.save_learner(session_id, updated)
    if result.answer.misconception:
        services.repo.add_misconception(
            learner_key(session_id), "react", result.answer.misconception
        )
    return result.model_dump(mode="json")

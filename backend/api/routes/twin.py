"""Learner Twin: batch of simulated 'day in the role' interviews answered by the Twin."""

from typing import Any

from fastapi import APIRouter, Request

from backend.api.deps import (
    LearnerDep,
    ServicesDep,
    SessionDep,
    limiter,
    llm_rate_limit,
    require_role,
)
from backend.api.schemas import InterviewRequest

router = APIRouter(prefix="/twin", tags=["Learner Twin"])


@router.post("/interviews", summary="Run Learner Twin interviews")
@limiter.limit(llm_rate_limit)
async def run_interviews(
    request: Request,
    body: InterviewRequest,
    learner: LearnerDep,
    services: ServicesDep,
    session_id: SessionDep,
) -> dict[str, Any]:
    """The Interviewer writes work tickets, the Twin answers as the learner and the Assessor
    grades them.
    """
    role_id = require_role(services.catalog, body.role_id or learner.profile.career_goal)
    updated, result = await services.orchestrator.twin_interview(learner, role_id, body.count)
    services.repo.save_learner(session_id, updated)
    names = {sid: s.name for sid, s in services.catalog.graph.skills.items()}
    return result.model_dump(mode="json") | {"skill_names": names}

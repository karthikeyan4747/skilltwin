"""Assessment: AI-written questions with a hidden Learner Twin prediction, then grading."""

from typing import Any

from fastapi import APIRouter, Request

from backend.api.deps import (
    LearnerDep,
    ServicesDep,
    SessionDep,
    learner_key,
    limiter,
    llm_rate_limit,
    require_skill,
)
from backend.api.errors import AppError
from backend.api.schemas import AnswerRequest, QuestionRequest
from backend.orchestrator import Answer

router = APIRouter(prefix="/assessment", tags=["Assessment"])


@router.get("/skills")
async def assessable_skills(services: ServicesDep) -> list[dict[str, str]]:
    graph = services.catalog.graph
    return [{"id": sid, "name": graph.name(sid)} for sid in graph.topological(graph.skills)]


@router.post("/question")
@limiter.limit(llm_rate_limit)
async def next_question(
    request: Request,
    body: QuestionRequest,
    learner: LearnerDep,
    services: ServicesDep,
    session_id: SessionDep,
) -> dict[str, Any]:
    skill_id = require_skill(services.catalog, body.skill_id)
    pending, result = await services.orchestrator.next_question(learner, skill_id, body.type)
    services.repo.put_question(session_id, pending)
    return result.model_dump(mode="json")


@router.post("/answer")
@limiter.limit(llm_rate_limit)
async def submit_answer(
    request: Request,
    body: AnswerRequest,
    learner: LearnerDep,
    services: ServicesDep,
    session_id: SessionDep,
) -> dict[str, Any]:
    """Adaptation trigger: a failed answer reroutes the roadmap to its root cause."""
    pending = services.repo.pop_question(session_id, body.question_id)
    if pending is None:
        raise AppError(404, "question_not_found", "This question expired. Start a new one.")
    answer = Answer(
        text=body.text,
        choice=body.choice,
        tests_passed=body.tests_passed,
        tests_total=body.tests_total,
    )
    updated, result = await services.orchestrator.submit_answer(learner, pending, answer)
    services.repo.save_learner(session_id, updated)
    if result.misconception:
        skill_id = pending.question.skill_id
        services.repo.add_misconception(learner_key(session_id), skill_id, result.misconception)
    return result.model_dump(mode="json")

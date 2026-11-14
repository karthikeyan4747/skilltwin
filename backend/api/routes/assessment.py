"""Assessment: AI-written questions with a hidden Learner Twin prediction, then grading."""

from fastapi import APIRouter, Request
from starlette import status

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
from backend.api.views import SkillOption
from backend.orchestrator import Answer
from backend.results import AnswerResult, QuestionResult

router = APIRouter(prefix="/assessment", tags=["Assessment"])


@router.get("/skills", summary="List assessable skills")
async def assessable_skills(services: ServicesDep) -> list[SkillOption]:
    """Every skill in the catalog, prerequisites first."""
    graph = services.catalog.graph
    return [SkillOption(id=sid, name=graph.name(sid)) for sid in graph.topological(graph.skills)]


@router.post("/question", summary="Get the next question")
@limiter.limit(llm_rate_limit)
async def next_question(
    request: Request,
    body: QuestionRequest,
    learner: LearnerDep,
    services: ServicesDep,
    session_id: SessionDep,
) -> QuestionResult:
    """The Assessor writes a question (types rotate); the Learner Twin's prediction is stored
    server-side.
    """
    skill_id = require_skill(services.catalog, body.skill_id)
    pending, result = await services.orchestrator.next_question(learner, skill_id, body.type)
    services.repo.put_question(session_id, pending)
    return result


@router.post("/answer", summary="Submit an answer")
@limiter.limit(llm_rate_limit)
async def submit_answer(
    request: Request,
    body: AnswerRequest,
    learner: LearnerDep,
    services: ServicesDep,
    session_id: SessionDep,
) -> AnswerResult:
    """Adaptation trigger: a failed answer reroutes the roadmap to its root cause."""
    pending = services.repo.pop_question(session_id, body.question_id)
    if pending is None:
        raise AppError(
            status.HTTP_404_NOT_FOUND,
            "question_not_found",
            "This question expired. Start a new one.",
        )
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
    return result

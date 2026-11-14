"""Lessons: Code Visualizer snippets and Grid Game levels; solved levels become evidence."""

from fastapi import APIRouter
from starlette import status

from backend.api.deps import LearnerDep, ServicesDep, SessionDep
from backend.api.errors import AppError
from backend.api.schemas import GridResult
from backend.api.views import GridResultView, LessonsView
from backend.core.grid import replay
from backend.core.progress import add_code_evidence, confidence_of

router = APIRouter(prefix="/lessons", tags=["Lessons"])
GRID_SKILL = "javascript"


@router.get("", summary="List lessons")
async def get_lessons(services: ServicesDep) -> LessonsView:
    """Code Visualizer snippets and Grid Game levels."""
    return LessonsView(
        snippets=services.catalog.snippets,
        grid_levels=list(services.catalog.grid_levels.values()),
    )


@router.post("/grid-result", summary="Submit a Grid Game result")
async def grid_result(
    body: GridResult, learner: LearnerDep, services: ServicesDep, session_id: SessionDep
) -> GridResultView:
    """The server replays the move list (never the learner's code) to verify the solution."""
    level = services.catalog.grid_levels.get(body.level_id)
    if level is None:
        raise AppError(status.HTTP_404_NOT_FOUND, "unknown_level", "That level does not exist.")
    if not replay(level, body.moves):
        return GridResultView(solved=False, evidence_added=False)
    graph = services.catalog.graph
    now = services.orchestrator.clock()
    before = confidence_of(learner, graph, GRID_SKILL, now)
    updated = add_code_evidence(learner, graph, GRID_SKILL, now)
    services.repo.save_learner(session_id, updated)
    return GridResultView(
        solved=True,
        evidence_added=True,
        skill_name=graph.name(GRID_SKILL),
        confidence_before=before,
        confidence_after=confidence_of(updated, graph, GRID_SKILL, now),
    )

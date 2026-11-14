"""Career Matching: claimed vs proven readiness, role ranking, goal switch preview and
change.
"""

from fastapi import APIRouter, Request

from backend.api.deps import (
    LearnerDep,
    ServicesDep,
    SessionDep,
    limiter,
    llm_rate_limit,
    require_role,
)
from backend.api.presenters import career_view
from backend.api.schemas import GoalRequest
from backend.api.views import CareerView, GoalPreview
from backend.core.career import goal_switch
from backend.results import GoalChangeResult

router = APIRouter(prefix="/career", tags=["Career Matching"])


@router.get("", summary="Career matching")
async def get_career(learner: LearnerDep, services: ServicesDep) -> CareerView:
    """Target-role readiness, all roles ranked by proven %, better-fit role, time to ready and
    market demand.
    """
    ctx = services.orchestrator.context(learner)
    demand = await services.jobs.demand(ctx.role)
    return career_view(ctx, demand)


@router.post("/preview-goal", summary="Preview a goal change")
async def preview_goal(
    body: GoalRequest, learner: LearnerDep, services: ServicesDep
) -> GoalPreview:
    """Carryover % and new skill delta, shown before the learner confirms a goal change."""
    role = services.catalog.roles[require_role(services.catalog, body.role_id)]
    ctx = services.orchestrator.context(learner)
    switch = goal_switch(ctx.role.id, role, ctx.statuses)
    return GoalPreview(
        **switch.model_dump(),
        reused_names=ctx.names(switch.reused),
        delta_names=ctx.names(switch.new_delta),
        role_title=role.title,
    )


@router.post("/goal", summary="Change career goal")
@limiter.limit(llm_rate_limit)
async def change_goal(
    request: Request,
    body: GoalRequest,
    learner: LearnerDep,
    services: ServicesDep,
    session_id: SessionDep,
) -> GoalChangeResult:
    """Adaptation trigger: career goal change rebuilds the roadmap with carried-over skills."""
    role_id = require_role(services.catalog, body.role_id)
    updated, result = await services.orchestrator.change_goal(learner, role_id)
    services.repo.save_learner(session_id, updated)
    return result

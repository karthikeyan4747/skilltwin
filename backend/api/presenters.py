"""Shape derived learner state into the typed view each UI screen needs."""

from backend.api.views import (
    AnalysisView,
    CareerView,
    DashboardView,
    GraphNode,
    NamedStep,
    ProgressView,
    ReadinessSummary,
    RerouteView,
    RoadmapStepView,
    RoadmapView,
    RoleOption,
    RoleSummary,
    SkillGraphView,
)
from backend.core import career, roadmap
from backend.core.twin import twin_accuracy
from backend.orchestrator.context import LearnerContext
from backend.services.jobs import DemandReport


def _relevant_skills(ctx: LearnerContext) -> list[str]:
    learner = ctx.learner
    wanted = set(learner.profile.claimed_skills) | set(ctx.role.skills)
    wanted |= {e.skill_id for e in learner.evidence}
    wanted |= {s.skill_id for s in learner.roadmap.steps}
    return ctx.catalog.graph.topological(sid for sid in wanted if sid in ctx.catalog.graph)


def analysis_view(ctx: LearnerContext) -> AnalysisView:
    """Skill statuses relevant to the learner, strengths, weaknesses and the graph."""
    graph = ctx.catalog.graph
    return AnalysisView(
        skills=[ctx.statuses[sid] for sid in _relevant_skills(ctx)],
        strengths=ctx.strengths,
        weaknesses=ctx.weaknesses,
        graph=SkillGraphView(
            nodes=[
                GraphNode(id=sid, name=s.name, category=s.category, prerequisites=s.prerequisites)
                for sid, s in graph.skills.items()
            ],
            order=graph.topological(graph.skills),
        ),
    )


def _better_fit_reason(ctx: LearnerContext) -> str | None:
    if ctx.better_fit is None:
        return None
    role = ctx.catalog.roles[ctx.better_fit.role_id]
    reused = [ctx.name(sid) for sid in role.skills if ctx.statuses[sid].verified]
    return (
        f"Your verified skills ({', '.join(reused)}) already cover "
        f"{ctx.better_fit.proven_pct:.0f}% of {role.title}, at least "
        f"{career.BETTER_FIT_MARGIN:.0f} points more than your current goal."
    )


def career_view(ctx: LearnerContext, demand: DemandReport) -> CareerView:
    """Target readiness, role ranking, better fit, time to ready and market demand."""
    plan = ctx.learner.roadmap
    hours = ctx.learner.profile.hours_per_week
    return CareerView(
        target=career.readiness(ctx.role, ctx.statuses),
        role=RoleSummary.model_validate(ctx.role.model_dump(exclude={"demand"})),
        ranking=ctx.ranking,
        better_fit=ctx.better_fit,
        better_fit_reason=_better_fit_reason(ctx),
        time_to_ready_weeks=roadmap.time_to_ready_weeks(plan, hours),
        remaining_hours=roadmap.remaining_hours(plan),
        velocity=roadmap.measured_velocity(plan),
        hours_per_week=hours,
        demand=demand,
        skill_names={sid: ctx.name(sid) for sid in ctx.role.skills},
        roles=[RoleOption(id=r.id, title=r.title) for r in ctx.catalog.roles.values()],
    )


def roadmap_view(ctx: LearnerContext) -> RoadmapView:
    """Roadmap steps with resources and reroute history, names resolved for display."""
    plan = ctx.learner.roadmap
    return RoadmapView(
        role_title=ctx.catalog.roles[plan.role_id].title,
        steps=[
            RoadmapStepView(
                **step.model_dump(),
                skill_name=ctx.name(step.skill_id),
                resources=ctx.catalog.resources.get(step.skill_id, []),
            )
            for step in plan.steps
        ],
        reroutes=[
            RerouteView(
                **event.model_dump(),
                path_names=ctx.names(event.path),
                inserted_names=ctx.names(event.inserted),
                failed_name=ctx.name(event.failed_skill) if event.failed_skill else None,
                root_name=ctx.name(event.root_cause) if event.root_cause else None,
            )
            for event in reversed(plan.reroutes)
        ],
        completion_pct=roadmap.completion_pct(plan),
    )


def progress_view(ctx: LearnerContext) -> ProgressView:
    """Confidence history, assessment history, completion, Twin accuracy, interviews."""
    learner = ctx.learner
    return ProgressView(
        confidence_history=learner.confidence_history,
        assessments=list(reversed(learner.assessments)),
        completion_pct=roadmap.completion_pct(learner.roadmap),
        twin_accuracy=twin_accuracy(learner.twin_history),
        twin_predictions=len(learner.twin_history),
        latest_interview=learner.latest_interview,
        skill_names={sid: s.name for sid, s in ctx.catalog.graph.skills.items()},
    )


def readiness_summary(ctx: LearnerContext) -> ReadinessSummary:
    """Claimed vs proven readiness, skill gaps and roadmap order for the learner's target role."""
    plan = ctx.learner.roadmap
    target = career.readiness(ctx.role, ctx.statuses)
    role_skills = ctx.catalog.graph.topological(ctx.role.skills)
    statuses = ctx.statuses
    return ReadinessSummary(
        role_title=ctx.role.title,
        claimed_pct=target.claimed_pct,
        proven_pct=target.proven_pct,
        verified=ctx.names(ctx.strengths),
        missing=ctx.names(
            [s for s in role_skills if not statuses[s].claimed and not statuses[s].verified]
        ),
        unproven=ctx.names(
            [s for s in role_skills if statuses[s].claimed and not statuses[s].verified]
        ),
        roadmap_order=ctx.names([s.skill_id for s in plan.steps]),
        time_to_ready_weeks=roadmap.time_to_ready_weeks(plan, ctx.learner.profile.hours_per_week),
        twin_accuracy=twin_accuracy(ctx.learner.twin_history),
        better_fit=ctx.better_fit.title if ctx.better_fit else None,
    )


def dashboard_view(ctx: LearnerContext, *, ai_live: bool) -> DashboardView:
    """Readiness summary plus greeting, verified count, next steps and AI mode."""
    next_steps = [s for s in ctx.learner.roadmap.steps if s.status != "done"][:3]
    return DashboardView(
        **readiness_summary(ctx).model_dump(),
        name=ctx.learner.profile.name,
        verified_count=len(ctx.strengths),
        next_steps=[
            NamedStep(**s.model_dump(), skill_name=ctx.name(s.skill_id)) for s in next_steps
        ],
        ai_mode="live" if ai_live else "offline",
    )

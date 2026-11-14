"""Shape derived learner state into the JSON each UI view needs."""

from typing import Any

from backend.core import career, roadmap
from backend.core.twin import twin_accuracy
from backend.orchestrator.context import LearnerContext


def _relevant_skills(ctx: LearnerContext) -> list[str]:
    learner = ctx.learner
    wanted = set(learner.profile.claimed_skills) | set(ctx.role.skills)
    wanted |= {e.skill_id for e in learner.evidence}
    wanted |= {s.skill_id for s in learner.roadmap.steps}
    return ctx.catalog.graph.topological(sid for sid in wanted if sid in ctx.catalog.graph)


def analysis_view(ctx: LearnerContext) -> dict[str, Any]:
    """Skill statuses relevant to the learner, strengths, weaknesses and the graph."""
    graph = ctx.catalog.graph
    return {
        "skills": [ctx.statuses[sid].model_dump() for sid in _relevant_skills(ctx)],
        "strengths": ctx.strengths,
        "weaknesses": ctx.weaknesses,
        "graph": {
            "nodes": [
                {
                    "id": sid,
                    "name": s.name,
                    "category": s.category,
                    "prerequisites": s.prerequisites,
                }
                for sid, s in graph.skills.items()
            ],
            "order": graph.topological(graph.skills),
        },
    }


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


def career_view(ctx: LearnerContext, demand: dict[str, Any]) -> dict[str, Any]:
    """Target readiness, role ranking, better fit, time to ready and market demand."""
    target = career.readiness(ctx.role, ctx.statuses)
    hours = ctx.learner.profile.hours_per_week
    return {
        "target": target.model_dump(),
        "role": ctx.role.model_dump(exclude={"demand"}),
        "ranking": [r.model_dump() for r in ctx.ranking],
        "better_fit": ctx.better_fit.model_dump() if ctx.better_fit else None,
        "better_fit_reason": _better_fit_reason(ctx),
        "time_to_ready_weeks": roadmap.time_to_ready_weeks(ctx.learner.roadmap, hours),
        "remaining_hours": roadmap.remaining_hours(ctx.learner.roadmap),
        "velocity": roadmap.measured_velocity(ctx.learner.roadmap),
        "hours_per_week": hours,
        "demand": demand,
        "skill_names": {sid: ctx.name(sid) for sid in ctx.role.skills},
        "roles": [{"id": r.id, "title": r.title} for r in ctx.catalog.roles.values()],
    }


def roadmap_view(ctx: LearnerContext) -> dict[str, Any]:
    """Roadmap steps with resources and reroute history, names resolved for display."""
    plan = ctx.learner.roadmap
    steps = [
        step.model_dump()
        | {
            "skill_name": ctx.name(step.skill_id),
            "resources": [r.model_dump() for r in ctx.catalog.resources.get(step.skill_id, [])],
        }
        for step in plan.steps
    ]
    return {
        "role_title": ctx.catalog.roles[plan.role_id].title,
        "steps": steps,
        "reroutes": [
            e.model_dump(mode="json")
            | {
                "path_names": ctx.names(e.path),
                "inserted_names": ctx.names(e.inserted),
                "failed_name": ctx.name(e.failed_skill) if e.failed_skill else None,
                "root_name": ctx.name(e.root_cause) if e.root_cause else None,
            }
            for e in reversed(plan.reroutes)
        ],
        "completion_pct": roadmap.completion_pct(plan),
    }


def progress_view(ctx: LearnerContext) -> dict[str, Any]:
    """Confidence history, assessment history, completion, Twin accuracy, interviews."""
    learner = ctx.learner
    return {
        "confidence_history": [p.model_dump(mode="json") for p in learner.confidence_history],
        "assessments": [a.model_dump(mode="json") for a in reversed(learner.assessments)],
        "completion_pct": roadmap.completion_pct(learner.roadmap),
        "twin_accuracy": twin_accuracy(learner.twin_history),
        "twin_predictions": len(learner.twin_history),
        "latest_interview": learner.latest_interview.model_dump(mode="json")
        if learner.latest_interview
        else None,
        "skill_names": {sid: s.name for sid, s in ctx.catalog.graph.skills.items()},
    }


def readiness_summary(ctx: LearnerContext) -> dict[str, Any]:
    """Claimed vs proven readiness, skill gaps and roadmap order for the learner's target role."""
    plan = ctx.learner.roadmap
    target = career.readiness(ctx.role, ctx.statuses)
    role_skills = ctx.catalog.graph.topological(ctx.role.skills)
    return {
        "role_title": ctx.role.title,
        "claimed_pct": target.claimed_pct,
        "proven_pct": target.proven_pct,
        "verified": ctx.names(ctx.strengths),
        "missing": ctx.names(
            [s for s in role_skills if not ctx.statuses[s].claimed and not ctx.statuses[s].verified]
        ),
        "unproven": ctx.names(
            [s for s in role_skills if ctx.statuses[s].claimed and not ctx.statuses[s].verified]
        ),
        "roadmap_order": ctx.names([s.skill_id for s in plan.steps]),
        "time_to_ready_weeks": roadmap.time_to_ready_weeks(
            plan, ctx.learner.profile.hours_per_week
        ),
        "twin_accuracy": twin_accuracy(ctx.learner.twin_history),
        "better_fit": ctx.better_fit.title if ctx.better_fit else None,
    }


def dashboard_view(ctx: LearnerContext, *, ai_live: bool) -> dict[str, Any]:
    """Readiness summary plus greeting, verified count, next steps and AI mode."""
    next_steps = [s for s in ctx.learner.roadmap.steps if s.status != "done"][:3]
    return readiness_summary(ctx) | {
        "name": ctx.learner.profile.name,
        "verified_count": len(ctx.strengths),
        "next_steps": [s.model_dump() | {"skill_name": ctx.name(s.skill_id)} for s in next_steps],
        "ai_mode": "live" if ai_live else "offline",
    }

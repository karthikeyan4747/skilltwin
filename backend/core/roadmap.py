"""Learning roadmap: gap ordering, rerouting, step status and time-to-ready."""

from datetime import datetime

from backend.core.analysis import VERIFIED_THRESHOLD, is_weak
from backend.core.diagnosis import Diagnosis
from backend.core.models import (
    RerouteEvent,
    RerouteTrigger,
    Roadmap,
    RoadmapStep,
    Role,
    SkillStatus,
    StepStatus,
)
from backend.core.skill_graph import SkillGraph

WEAK_HOURS_FACTOR = 0.5
VELOCITY_BOUNDS = (0.5, 2.0)


def gap_skills(graph: SkillGraph, role: Role, statuses: dict[str, SkillStatus]) -> list[str]:
    """Unverified role skills plus their unverified prerequisites, prerequisites first."""
    needed: set[str] = set()
    for sid in role.skills:
        needed.add(sid)
        needed |= graph.ancestors(sid)
    return graph.topological(sid for sid in needed if not statuses[sid].verified)


def _reason(sid: str, role: Role, status: SkillStatus) -> str:
    if sid not in role.skills:
        return f"Prerequisite for {role.title} skills; not yet verified."
    weight = f"{role.skills[sid]:.0%} of {role.title} readiness"
    if status.evidence_count == 0 and status.claimed:
        return f"Claimed but not yet proven by evidence ({weight})."
    if status.evidence_count == 0:
        return f"Missing skill required for {role.title} ({weight})."
    return f"Confidence {status.confidence:.2f} is below {VERIFIED_THRESHOLD} ({weight})."


def _hours(graph: SkillGraph, status: SkillStatus) -> float:
    base = graph.skills[status.skill_id].est_hours
    has_partial = status.evidence_count > 0 or is_weak(status)
    return round(base * WEAK_HOURS_FACTOR if has_partial else base, 1)


def build_roadmap(graph: SkillGraph, role: Role, statuses: dict[str, SkillStatus]) -> Roadmap:
    """Ordered gap steps for a role with a deterministic reason and hour estimate each."""
    steps = [
        RoadmapStep(
            skill_id=sid,
            reason=_reason(sid, role, statuses[sid]),
            est_hours=_hours(graph, statuses[sid]),
        )
        for sid in gap_skills(graph, role, statuses)
    ]
    return Roadmap(role_id=role.id, steps=steps)


def reroute(
    roadmap: Roadmap,
    graph: SkillGraph,
    diagnosis: Diagnosis,
    now: datetime,
    trigger: RerouteTrigger = "failed_assessment",
) -> Roadmap:
    """Move the diagnosis path (root cause first) to the front and log a reroute event."""
    existing = {step.skill_id: step for step in roadmap.steps}
    failed_name = graph.name(diagnosis.failed_skill)
    front: list[RoadmapStep] = []
    inserted: list[str] = []
    for sid in diagnosis.path:
        step = existing.pop(sid, None)
        if step is None:
            inserted.append(sid)
            step = RoadmapStep(
                skill_id=sid,
                reason=f"Root cause of a failed {failed_name} answer.",
                est_hours=round(graph.skills[sid].est_hours * WEAK_HOURS_FACTOR, 1),
            )
        front.append(step.model_copy(update={"status": "todo"}))
    rest = [s for s in roadmap.steps if s.skill_id in existing]
    event = RerouteEvent(
        timestamp=now,
        trigger=trigger,
        failed_skill=diagnosis.failed_skill,
        root_cause=diagnosis.root_cause,
        path=diagnosis.path,
        inserted=inserted,
    )
    return roadmap.model_copy(
        update={"steps": front + rest, "reroutes": [*roadmap.reroutes, event]}
    )


def set_step_status(
    roadmap: Roadmap, skill_id: str, status: StepStatus, actual_hours: float | None = None
) -> Roadmap:
    """Update one step's status and actual hours; raises KeyError if it is not on the roadmap."""
    if not any(s.skill_id == skill_id for s in roadmap.steps):
        raise KeyError(skill_id)
    steps = [
        s.model_copy(update={"status": status, "actual_hours": actual_hours})
        if s.skill_id == skill_id
        else s
        for s in roadmap.steps
    ]
    return roadmap.model_copy(update={"steps": steps})


def completion_pct(roadmap: Roadmap) -> float:
    """Percentage of steps marked done (100 for an empty roadmap)."""
    if not roadmap.steps:
        return 100.0
    done = sum(1 for s in roadmap.steps if s.status == "done")
    return round(100 * done / len(roadmap.steps), 1)


def remaining_hours(roadmap: Roadmap) -> float:
    """Estimated hours left across steps that are not done."""
    return round(sum(s.est_hours for s in roadmap.steps if s.status != "done"), 1)


def measured_velocity(roadmap: Roadmap) -> float:
    """Estimated hours per actual hour over completed steps; 1.0 without history."""
    measured = [s for s in roadmap.steps if s.status == "done" and s.actual_hours]
    if not measured:
        return 1.0
    ratio = sum(s.est_hours for s in measured) / sum(s.actual_hours or 0 for s in measured)
    low, high = VELOCITY_BOUNDS
    return round(min(max(ratio, low), high), 2)


def time_to_ready_weeks(roadmap: Roadmap, hours_per_week: float) -> float:
    """Weeks to finish the roadmap at the learner's weekly hours and measured pace."""
    effective = hours_per_week * measured_velocity(roadmap)
    return round(remaining_hours(roadmap) / effective, 1)


def carry_progress(new: Roadmap, old: Roadmap) -> Roadmap:
    """Keep step statuses, AI reasons and reroute history when a roadmap is rebuilt."""
    previous = {s.skill_id: s for s in old.steps}
    steps = [
        s.model_copy(
            update={
                "status": previous[s.skill_id].status,
                "actual_hours": previous[s.skill_id].actual_hours,
                "resource_reason": previous[s.skill_id].resource_reason,
            }
        )
        if s.skill_id in previous
        else s
        for s in new.steps
    ]
    return new.model_copy(update={"steps": steps, "reroutes": old.reroutes})


def prioritize(
    roadmap: Roadmap, skill_ids: list[str], now: datetime, trigger: RerouteTrigger, note: str
) -> Roadmap:
    """Move existing steps to the front (in the given order) and log the reroute."""
    present = [
        sid for sid in dict.fromkeys(skill_ids) if any(s.skill_id == sid for s in roadmap.steps)
    ]
    if not present:
        return roadmap
    front = [s for sid in present for s in roadmap.steps if s.skill_id == sid]
    rest = [s for s in roadmap.steps if s.skill_id not in present]
    event = RerouteEvent(timestamp=now, trigger=trigger, path=present, note=note)
    return roadmap.model_copy(
        update={"steps": front + rest, "reroutes": [*roadmap.reroutes, event]}
    )


def log_event(roadmap: Roadmap, event: RerouteEvent) -> Roadmap:
    """Append a reroute event to the roadmap history."""
    return roadmap.model_copy(update={"reroutes": [*roadmap.reroutes, event]})

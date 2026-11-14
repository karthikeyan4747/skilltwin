"""Career Matching: role readiness, ranking, better-fit detection and goal-switch carryover."""

from pydantic import BaseModel

from backend.core.models import Role, SkillStatus

BETTER_FIT_MARGIN = 10.0


class Readiness(BaseModel):
    role_id: str
    title: str
    claimed_pct: float
    proven_pct: float


class GoalSwitch(BaseModel):
    from_role: str
    to_role: str
    carryover_pct: float
    reused: list[str]
    new_delta: list[str]


def _weighted_pct(role: Role, include: set[str]) -> float:
    total = sum(role.skills.values())
    if total == 0:
        return 0.0
    hit = sum(w for sid, w in role.skills.items() if sid in include)
    return round(100 * hit / total, 1)


def readiness(role: Role, statuses: dict[str, SkillStatus]) -> Readiness:
    """Claimed % counts self-reported skills; proven % counts only verified ones."""
    claimed = {sid for sid, s in statuses.items() if s.claimed}
    verified = {sid for sid, s in statuses.items() if s.verified}
    return Readiness(
        role_id=role.id,
        title=role.title,
        claimed_pct=_weighted_pct(role, claimed),
        proven_pct=_weighted_pct(role, verified),
    )


def rank_roles(roles: list[Role], statuses: dict[str, SkillStatus]) -> list[Readiness]:
    ranked = [readiness(role, statuses) for role in roles]
    return sorted(ranked, key=lambda r: (-r.proven_pct, r.role_id))


def better_fit(ranking: list[Readiness], target_id: str) -> Readiness | None:
    """A role whose proven % beats the target by at least BETTER_FIT_MARGIN points."""
    target = next((r for r in ranking if r.role_id == target_id), None)
    if target is None or not ranking:
        return None
    best = ranking[0]
    if best.role_id != target_id and best.proven_pct - target.proven_pct >= BETTER_FIT_MARGIN:
        return best
    return None


def goal_switch(current_role: str, new_role: Role, statuses: dict[str, SkillStatus]) -> GoalSwitch:
    """Verified skills carry over to the new role; only the remaining delta must be learned."""
    reused = [sid for sid in new_role.skills if statuses[sid].verified]
    delta = [sid for sid in new_role.skills if not statuses[sid].verified]
    return GoalSwitch(
        from_role=current_role,
        to_role=new_role.id,
        carryover_pct=_weighted_pct(new_role, set(reused)),
        reused=reused,
        new_delta=delta,
    )

"""Skill Analysis: evidence-based confidence, verification, strengths and weaknesses."""

from collections import defaultdict
from collections.abc import Iterable
from datetime import datetime

from backend.core.models import Evidence, EvidenceType, SkillStatus
from backend.core.skill_graph import SkillGraph

TYPE_WEIGHTS: dict[EvidenceType, float] = {
    "code_exercise": 1.0,
    "explain_back": 0.9,
    "predict_output": 0.8,
    "interview": 0.8,
    "mcq": 0.6,
}
VERIFIED_THRESHOLD = 0.7
WEAK_THRESHOLD = 0.5
SINGLE_TYPE_CAP = 0.6
CLAIMED_PRIOR = 0.2
RECENCY_HALF_LIFE_DAYS = 14.0
PASS_SCORE = 0.5


def recency_weight(timestamp: datetime, now: datetime) -> float:
    age_days = max((now - timestamp).total_seconds() / 86400, 0.0)
    return float(0.5 ** (age_days / RECENCY_HALF_LIFE_DAYS))


def skill_confidence(evidence: list[Evidence], claimed: bool, now: datetime) -> float:
    """Recency-weighted, type-weighted mean of evidence scores.

    Capped at SINGLE_TYPE_CAP unless at least two distinct evidence types exist.
    Without evidence a claimed skill scores CLAIMED_PRIOR and an unclaimed one 0.
    """
    if not evidence:
        return CLAIMED_PRIOR if claimed else 0.0
    total = weighted = 0.0
    for item in evidence:
        weight = TYPE_WEIGHTS[item.type] * recency_weight(item.timestamp, now)
        total += weight
        weighted += weight * item.score
    confidence = weighted / total
    if len({item.type for item in evidence}) < 2:
        confidence = min(confidence, SINGLE_TYPE_CAP)
    return round(confidence, 4)


def analyze_skills(
    graph: SkillGraph,
    claimed: Iterable[str],
    evidence: list[Evidence],
    now: datetime,
) -> dict[str, SkillStatus]:
    """Status for every skill in the graph, keyed by skill id."""
    claimed_set = set(claimed)
    by_skill: dict[str, list[Evidence]] = defaultdict(list)
    for item in evidence:
        by_skill[item.skill_id].append(item)
    statuses: dict[str, SkillStatus] = {}
    for skill_id in graph.topological(graph.skills):
        items = by_skill.get(skill_id, [])
        confidence = skill_confidence(items, skill_id in claimed_set, now)
        statuses[skill_id] = SkillStatus(
            skill_id=skill_id,
            name=graph.name(skill_id),
            claimed=skill_id in claimed_set,
            confidence=confidence,
            verified=confidence >= VERIFIED_THRESHOLD,
            evidence_count=len(items),
        )
    return statuses


def is_weak(status: SkillStatus) -> bool:
    """Claimed but unproven, or below the weak threshold after evidence."""
    if status.evidence_count == 0:
        return status.claimed
    return status.confidence < WEAK_THRESHOLD


def strengths_and_weaknesses(
    statuses: dict[str, SkillStatus],
) -> tuple[list[str], list[str]]:
    strengths = [sid for sid, s in statuses.items() if s.verified]
    weaknesses = [sid for sid, s in statuses.items() if is_weak(s)]
    return strengths, weaknesses


def confidences(statuses: dict[str, SkillStatus]) -> dict[str, float]:
    return {sid: s.confidence for sid, s in statuses.items()}

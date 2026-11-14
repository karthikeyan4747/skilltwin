from datetime import timedelta

import pytest

from backend.core.analysis import (
    CLAIMED_PRIOR,
    SINGLE_TYPE_CAP,
    analyze_skills,
    is_weak,
    recency_weight,
    skill_confidence,
    strengths_and_weaknesses,
)
from backend.core.models import Evidence


def ev(skill: str, kind: str, score: float, when) -> Evidence:
    return Evidence(skill_id=skill, type=kind, score=score, timestamp=when)


def test_no_evidence_uses_claim_prior(now) -> None:
    assert skill_confidence([], claimed=True, now=now) == CLAIMED_PRIOR
    assert skill_confidence([], claimed=False, now=now) == 0.0


def test_single_type_is_capped(now) -> None:
    items = [ev("x", "mcq", 1.0, now), ev("x", "mcq", 1.0, now)]
    assert skill_confidence(items, claimed=True, now=now) == SINGLE_TYPE_CAP


def test_two_types_lift_the_cap_and_weight_by_type(now) -> None:
    items = [ev("x", "code_exercise", 1.0, now), ev("x", "mcq", 0.0, now)]
    assert skill_confidence(items, claimed=False, now=now) == pytest.approx(1.0 / 1.6, abs=1e-3)


def test_recent_evidence_counts_more(now) -> None:
    old = ev("x", "mcq", 0.0, now - timedelta(days=28))
    new = ev("x", "explain_back", 1.0, now)
    assert recency_weight(old.timestamp, now) == pytest.approx(0.25)
    assert skill_confidence([old, new], claimed=False, now=now) > 0.8


def test_strengths_and_weaknesses(catalog, now) -> None:
    evidence = [
        ev("python", "mcq", 1.0, now),
        ev("python", "code_exercise", 1.0, now),
        ev("sql", "mcq", 0.1, now),
        ev("sql", "explain_back", 0.2, now),
    ]
    statuses = analyze_skills(catalog.graph, ["python", "sql", "html"], evidence, now)
    strengths, weaknesses = strengths_and_weaknesses(statuses)
    assert strengths == ["python"]
    assert set(weaknesses) == {"sql", "html"}
    assert statuses["python"].verified and statuses["python"].evidence_count == 2
    assert not is_weak(statuses["react"])


def test_all_verified_has_no_weaknesses(catalog, now) -> None:
    evidence = [ev(s, t, 1.0, now) for s in catalog.graph.skills for t in ("mcq", "code_exercise")]
    statuses = analyze_skills(catalog.graph, [], evidence, now)
    strengths, weaknesses = strengths_and_weaknesses(statuses)
    assert len(strengths) == len(catalog.graph.skills) and weaknesses == []

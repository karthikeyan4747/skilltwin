"""Progress Tracking: recording evidence and assessment outcomes on the learner."""

from dataclasses import dataclass
from datetime import datetime

from backend.core.analysis import PASS_SCORE, VERIFIED_THRESHOLD, analyze_skills
from backend.core.models import (
    AssessmentRecord,
    ConfidencePoint,
    Evidence,
    Learner,
    Misconception,
    Question,
    TwinRecord,
)
from backend.core.skill_graph import SkillGraph


def confidence_of(learner: Learner, graph: SkillGraph, skill_id: str, now: datetime) -> float:
    """Current evidence-based confidence for one skill."""
    statuses = analyze_skills(graph, learner.profile.claimed_skills, learner.evidence, now)
    return statuses[skill_id].confidence


@dataclass(frozen=True)
class Outcome:
    """A graded answer: its score, the Twin's prediction (if any) and any misconception."""

    score: float
    predicted_correct: bool | None = None
    misconception: str | None = None


def record_outcome(
    learner: Learner, graph: SkillGraph, question: Question, outcome: Outcome, now: datetime
) -> Learner:
    """Append evidence, assessment, twin record, misconception and a confidence data point."""
    score, misconception = outcome.score, outcome.misconception
    evidence = Evidence(skill_id=question.skill_id, type=question.type, score=score, timestamp=now)
    correct = score >= PASS_SCORE
    updated = learner.model_copy(
        update={
            "evidence": [*learner.evidence, evidence],
            "assessments": [
                *learner.assessments,
                AssessmentRecord(
                    question_id=question.id,
                    skill_id=question.skill_id,
                    type=question.type,
                    score=score,
                    correct=correct,
                    timestamp=now,
                ),
            ],
        }
    )
    if outcome.predicted_correct is not None:
        record = TwinRecord(
            question_id=question.id,
            skill_id=question.skill_id,
            predicted_correct=outcome.predicted_correct,
            actual_correct=correct,
        )
        updated.twin_history = [*updated.twin_history, record]
    if misconception:
        entry = Misconception(skill_id=question.skill_id, text=misconception, timestamp=now)
        updated.misconceptions = [*updated.misconceptions, entry]
    point = ConfidencePoint(
        skill_id=question.skill_id,
        confidence=confidence_of(updated, graph, question.skill_id, now),
        timestamp=now,
    )
    updated.confidence_history = [*updated.confidence_history, point]
    return updated


def add_code_evidence(learner: Learner, graph: SkillGraph, skill_id: str, now: datetime) -> Learner:
    """Record a solved practical exercise (e.g. the Grid Game) as code_exercise evidence."""
    evidence = Evidence(skill_id=skill_id, type="code_exercise", score=1.0, timestamp=now)
    updated = learner.model_copy(update={"evidence": [*learner.evidence, evidence]})
    point = ConfidencePoint(
        skill_id=skill_id, confidence=confidence_of(updated, graph, skill_id, now), timestamp=now
    )
    updated.confidence_history = [*updated.confidence_history, point]
    return updated


def misconceptions_overcome(learner: Learner) -> list[str]:
    """Misconceptions followed by a later passing answer on the same skill."""
    overcome: list[str] = []
    for m in learner.misconceptions:
        later = [
            e
            for e in learner.evidence
            if e.skill_id == m.skill_id
            and e.timestamp > m.timestamp
            and e.score >= VERIFIED_THRESHOLD
        ]
        if later and m.text not in overcome:
            overcome.append(m.text)
    return overcome


def confidence_trail(
    graph: SkillGraph, claimed: list[str], evidence: list[Evidence]
) -> list[ConfidencePoint]:
    """Rebuild the confidence-over-time series by replaying evidence chronologically."""
    ordered = sorted(evidence, key=lambda e: e.timestamp)
    trail: list[ConfidencePoint] = []
    for i, item in enumerate(ordered):
        statuses = analyze_skills(graph, claimed, ordered[: i + 1], item.timestamp)
        trail.append(
            ConfidencePoint(
                skill_id=item.skill_id,
                confidence=statuses[item.skill_id].confidence,
                timestamp=item.timestamp,
            )
        )
    return trail

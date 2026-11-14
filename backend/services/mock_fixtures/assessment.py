"""Deterministic fixtures for assessment agents: question writing, grading, observing, Twin."""

from typing import Any

from backend.agents.assessor import GraderIn, QuestionWriterIn
from backend.agents.diagnostic import DiagnosticIn
from backend.agents.observer import ObserverIn
from backend.agents.twin import TwinPredictIn, TwinRespondIn
from backend.core.analysis import PASS_SCORE
from backend.core.twin import baseline_prediction

Payload = dict[str, Any]
FLUENCY_WORDS = 30


def rubric_coverage(answer: str, rubric: list[str]) -> tuple[float, list[str]]:
    """Share of rubric points mentioned in the answer, and the missed points."""
    text = answer.lower()
    missed = [point for point in rubric if point.lower() not in text]
    if not rubric:
        return 0.0, []
    return round(1 - len(missed) / len(rubric), 3), missed


def question_writer(payload: Payload) -> Payload:
    """Reuse the bank example as the 'written' question."""
    example = QuestionWriterIn.model_validate(payload).example
    return example.model_dump(
        include={"prompt", "options", "answer_index", "code", "expected_output", "rubric"}
    ) | {"misconceptions": example.misconceptions}


def grader(payload: Payload) -> Payload:
    """Concept score from rubric coverage; fluency from length only."""
    inp = GraderIn.model_validate(payload)
    score, missed = rubric_coverage(inp.answer, inp.rubric)
    fluency = min(1.0, len(inp.answer.split()) / FLUENCY_WORDS)
    feedback = (
        "Clear grasp of the key ideas."
        if not missed
        else f"Good start. Revisit: {', '.join(missed)}."
    )
    return {
        "conceptual_score": score,
        "fluency_score": round(fluency, 2),
        "feedback": feedback,
        "missed_points": missed,
    }


def observer(payload: Payload) -> Payload:
    """Known distractor misconception, else the first missed rubric point."""
    inp = ObserverIn.model_validate(payload)
    if inp.score >= 1:
        return {"misconception": None}
    if inp.known_distractor_misconception:
        return {"misconception": inp.known_distractor_misconception}
    if inp.missed_points and inp.score < PASS_SCORE:
        return {"misconception": f"Overlooks {inp.missed_points[0]} in {inp.skill_name}"}
    return {"misconception": None}


def diagnostic(payload: Payload) -> Payload:
    """Templated explanation of the core-computed root cause."""
    inp = DiagnosticIn.model_validate(payload)
    conf = inp.confidences.get(inp.root_cause, 0.0)
    if inp.root_cause == inp.failed_skill:
        explanation = (
            f"Your prerequisites for {inp.failed_skill} look solid, so the gap is in "
            f"{inp.failed_skill} itself."
        )
    else:
        explanation = (
            f"Your {inp.failed_skill} answer points to a deeper gap: {inp.root_cause} "
            f"(confidence {conf:.2f}) sits beneath it along {' → '.join(inp.path)}. "
            f"Strengthening {inp.root_cause} first will make {inp.failed_skill} click."
        )
    return {
        "explanation": explanation,
        "first_action": f"Do the {inp.root_cause} tutorial on your roadmap, then retake a check.",
    }


def twin_predictor(payload: Payload) -> Payload:
    """Baseline Twin rule: confidence and known misconceptions decide."""
    inp = TwinPredictIn.model_validate(payload)
    correct = baseline_prediction(inp.confidence, inp.misconceptions)
    if correct:
        answer = inp.correct_answer
        why = f"confidence {inp.confidence:.2f} and no known {inp.skill_name} misconceptions"
    else:
        matching = [a for a, m in inp.wrong_answers.items() if m in inp.misconceptions]
        answer = (matching or list(inp.wrong_answers) or ["an incomplete answer"])[0]
        why = (
            f"known misconception: {inp.misconceptions[0]}"
            if inp.misconceptions
            else f"confidence {inp.confidence:.2f}, which is below 0.5"
        )
    return {
        "predicted_answer": answer,
        "predicted_correct": correct,
        "reasoning": f"Based on {why}.",
    }


def twin_responder(payload: Payload) -> Payload:
    """Answer covering as many rubric points as the learner's confidence suggests."""
    inp = TwinRespondIn.model_validate(payload)
    known = inp.rubric[: round(len(inp.rubric) * min(max(inp.confidence, 0.0), 1.0))]
    if not known:
        return {"answer": "I'm not sure where to start; I would look for a similar example."}
    return {"answer": f"I would approach this using {', '.join(known)}."}

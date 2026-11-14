"""Deterministic grading for closed-form questions, plus question-type rotation and difficulty."""

import re

from backend.core.models import AssessmentRecord, Question, QuestionType

TYPE_ROTATION: list[QuestionType] = [
    "mcq",
    "explain_back",
    "predict_output",
    "code_exercise",
    "interview",
]


def normalize_output(text: str) -> str:
    """Case-, quote- and whitespace-insensitive form used to compare predicted output."""
    collapsed = re.sub(r"\s+", " ", text.strip().lower())
    return collapsed.strip("\"'` ")


def grade_mcq(question: Question, choice: int | None) -> float:
    return 1.0 if choice is not None and choice == question.answer_index else 0.0


def grade_predict_output(question: Question, answer: str) -> float:
    expected = normalize_output(question.expected_output or "")
    return 1.0 if expected and normalize_output(answer) == expected else 0.0


def grade_code_exercise(tests_passed: int, tests_total: int) -> float:
    if tests_total <= 0:
        return 0.0
    return round(min(tests_passed, tests_total) / tests_total, 3)


def correct_answer_text(question: Question) -> str:
    if question.type == "mcq" and question.answer_index is not None:
        return question.options[question.answer_index]
    if question.type == "predict_output":
        return question.expected_output or ""
    if question.type == "code_exercise":
        return "All tests pass"
    return "Covers: " + ", ".join(question.rubric)


def wrong_answer_misconceptions(question: Question) -> dict[str, str]:
    """Map plausible wrong answers (as text) to the misconception they reveal."""
    if question.type == "mcq":
        return {
            question.options[int(idx)]: text
            for idx, text in question.misconceptions.items()
            if idx.isdigit() and int(idx) < len(question.options)
        }
    return dict(question.misconceptions)


def next_type(
    skill_id: str, available: list[QuestionType], history: list[AssessmentRecord]
) -> QuestionType:
    """Rotate question types per skill so evidence comes from distinct types."""
    ordered = [t for t in TYPE_ROTATION if t in available]
    past = [r.type for r in history if r.skill_id == skill_id and r.type in ordered]
    if not past:
        return ordered[0]
    return ordered[(ordered.index(past[-1]) + 1) % len(ordered)]


def difficulty_for(confidence: float) -> str:
    if confidence < 0.4:
        return "easy"
    if confidence < 0.7:
        return "medium"
    return "hard"

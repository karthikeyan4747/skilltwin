"""Learner Twin: deterministic baseline prediction and prediction-accuracy tracking."""

from backend.core.models import TwinRecord

ACCURACY_WINDOW = 20
BASELINE_CORRECT_THRESHOLD = 0.5


def baseline_prediction(confidence: float, known_misconceptions: list[str]) -> bool:
    """Predict a correct answer when confidence is adequate and no misconception is known."""
    return confidence >= BASELINE_CORRECT_THRESHOLD and not known_misconceptions


def twin_accuracy(history: list[TwinRecord], window: int = ACCURACY_WINDOW) -> float | None:
    """Rolling share of predictions that matched the learner's actual correctness."""
    recent = history[-window:]
    if not recent:
        return None
    hits = sum(1 for r in recent if r.predicted_correct == r.actual_correct)
    return round(hits / len(recent), 3)

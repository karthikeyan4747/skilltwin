from backend.core.grading import (
    correct_answer_text,
    difficulty_for,
    grade_code_exercise,
    grade_mcq,
    grade_predict_output,
    next_type,
    normalize_output,
    wrong_answer_misconceptions,
)
from backend.core.grid import GridLevel, replay
from backend.core.insights import top_misconceptions
from backend.core.models import AssessmentRecord, Question, TwinRecord
from backend.core.progress import Outcome, misconceptions_overcome, record_outcome
from backend.core.twin import baseline_prediction, twin_accuracy

MCQ = Question(
    id="q",
    skill_id="javascript",
    type="mcq",
    prompt="p",
    options=["a", "b", "c"],
    answer_index=1,
    misconceptions={"0": "Thinks a"},
)


def test_closed_form_grading() -> None:
    assert grade_mcq(MCQ, 1) == 1.0 and grade_mcq(MCQ, 0) == 0.0 and grade_mcq(MCQ, None) == 0.0
    predict = Question(
        id="p", skill_id="x", type="predict_output", prompt="p", expected_output="2-4-6"
    )
    assert grade_predict_output(predict, "  '2-4-6' ") == 1.0
    assert grade_predict_output(predict, "246") == 0.0
    assert grade_code_exercise(2, 3) == 0.667 and grade_code_exercise(0, 0) == 0.0
    assert normalize_output("  Hello   World ") == "hello world"
    assert correct_answer_text(MCQ) == "b"
    assert wrong_answer_misconceptions(MCQ) == {"a": "Thinks a"}


def test_type_rotation_and_difficulty(now) -> None:
    available = ["mcq", "explain_back", "predict_output"]
    assert next_type("x", available, []) == "mcq"
    history = [
        AssessmentRecord(
            question_id="1",
            skill_id="x",
            type="predict_output",
            score=1,
            correct=True,
            timestamp=now,
        )
    ]
    assert next_type("x", available, history) == "mcq"
    history[0].type = "mcq"
    assert next_type("x", available, history) == "explain_back"
    assert [difficulty_for(c) for c in (0.1, 0.5, 0.9)] == ["easy", "medium", "hard"]


def test_twin_accuracy_and_baseline() -> None:
    assert twin_accuracy([]) is None
    records = [
        TwinRecord(
            question_id=str(i), skill_id="x", predicted_correct=True, actual_correct=i % 2 == 0
        )
        for i in range(4)
    ]
    assert twin_accuracy(records) == 0.5
    assert twin_accuracy(records, window=1) == 0.0
    assert baseline_prediction(0.8, []) is True
    assert baseline_prediction(0.8, ["Thinks x"]) is False
    assert baseline_prediction(0.3, []) is False


def test_top_misconceptions_counts_each_learner_once() -> None:
    records = [
        ("a", "css", "Thinks X"),
        ("a", "css", "thinks  x"),
        ("b", "css", "Thinks X"),
        ("b", "css", "Other"),
    ]
    stats = top_misconceptions(records, total_learners=4, top_n=1)
    assert len(stats) == 1
    assert stats[0].learners_affected == 2 and stats[0].pct_affected == 50.0
    assert top_misconceptions(records, total_learners=0) == []


def test_grid_replay() -> None:
    level = GridLevel(id="l", title="t", start=(0, 0), goal=(2, 0), walls=[(1, 1)], hint="")
    assert replay(level, ["right", "right"])
    assert not replay(level, ["down", "right"])
    assert replay(level, ["up", "left", "right", "right"])
    assert not replay(level, ["right"] * 201)


def test_record_outcome_and_overcome(catalog, sample_learner, now) -> None:
    from datetime import timedelta

    failed = record_outcome(sample_learner, catalog.graph, MCQ, Outcome(0.0, True, "Thinks a"), now)
    assert failed.twin_history[-1].actual_correct is False
    assert failed.misconceptions[-1].text == "Thinks a"
    assert failed.confidence_history[-1].skill_id == "javascript"
    assert misconceptions_overcome(failed) == []
    passed = record_outcome(failed, catalog.graph, MCQ, Outcome(1.0), now + timedelta(hours=1))
    assert misconceptions_overcome(passed) == ["Thinks a"]
    assert len(passed.twin_history) == 1

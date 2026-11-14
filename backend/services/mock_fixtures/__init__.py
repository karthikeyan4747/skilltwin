"""Deterministic MockLLM fixtures: one pure function per agent key, payload in, JSON dict out."""

from backend.services.llm import Fixture
from backend.services.mock_fixtures import assessment, coaching
from backend.services.mock_fixtures.assessment import rubric_coverage

MOCK_FIXTURES: dict[str, Fixture] = {
    "question_writer": assessment.question_writer,
    "grader": assessment.grader,
    "observer": assessment.observer,
    "diagnostic": assessment.diagnostic,
    "twin_predictor": assessment.twin_predictor,
    "twin_responder": assessment.twin_responder,
    "recommender": coaching.recommender,
    "interviewer": coaching.interviewer,
    "career": coaching.career,
    "mentor": coaching.mentor,
    "publisher": coaching.publisher,
}

__all__ = ["MOCK_FIXTURES", "rubric_coverage"]

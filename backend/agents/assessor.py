"""Assessor agent: writes assessment questions and grades open answers."""

from typing import Literal, Self

from pydantic import BaseModel, Field, model_validator

from backend.agents.base import Agent
from backend.core.models import Question, QuestionType

Difficulty = Literal["easy", "medium", "hard"]


class QuestionWriterIn(BaseModel):
    skill_name: str
    type: QuestionType
    difficulty: Difficulty
    known_misconceptions: list[str]
    example: Question


class QuestionWriterOut(BaseModel):
    prompt: str = Field(min_length=5, max_length=600)
    options: list[str] = Field(default=[], max_length=6)
    answer_index: int | None = None
    code: str | None = Field(default=None, max_length=1200)
    expected_output: str | None = Field(default=None, max_length=200)
    rubric: list[str] = Field(default=[], max_length=8)
    misconceptions: dict[str, str] = {}

    @model_validator(mode="after")
    def _answer_key_is_usable(self) -> Self:
        if self.options:
            if self.answer_index is None or not 0 <= self.answer_index < len(self.options):
                raise ValueError("answer_index must point at an option")
        elif self.answer_index is not None:
            raise ValueError("answer_index requires options")
        return self


class QuestionWriter(Agent[QuestionWriterIn, QuestionWriterOut]):
    name = "Assessor"
    key = "question_writer"
    purpose = "Wrote a new question targeting the learner's level"
    tier = "smart"
    max_tokens = 700
    output_model = QuestionWriterOut
    instructions = (
        "Write ONE new assessment question of the given type and difficulty for the skill, in "
        "the same format as `example`. mcq: 4 options, answer_index, and `misconceptions` "
        "mapping each wrong option index (as a string) to the misconception it reveals. "
        "predict_output: put the snippet in `code` and the exact answer in `expected_output`. "
        "explain_back/interview: give 3-5 short `rubric` key concepts. Prefer probing the "
        "learner's known misconceptions."
    )


class GraderIn(BaseModel):
    skill_name: str
    question: str
    rubric: list[str]
    answer: str


class GraderOut(BaseModel):
    conceptual_score: float = Field(ge=0, le=1)
    fluency_score: float = Field(ge=0, le=1)
    feedback: str = Field(max_length=600)
    missed_points: list[str] = Field(default=[], max_length=8)


class AnswerGrader(Agent[GraderIn, GraderOut]):
    name = "Assessor"
    key = "grader"
    purpose = "Graded conceptual understanding separately from language fluency"
    tier = "smart"
    max_tokens = 400
    output_model = GraderOut
    instructions = (
        "Grade the learner's answer. `conceptual_score` measures ONLY whether the ideas are "
        "correct and cover the rubric; do not penalise grammar, spelling, non-native phrasing "
        "or brevity. `fluency_score` separately rates clarity of language. List rubric points "
        "that were missed. Feedback: two short, encouraging sentences."
    )

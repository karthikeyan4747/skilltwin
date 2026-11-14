"""Request bodies: strict, bounded and extra-forbidding."""

from typing import Annotated

from pydantic import BaseModel, ConfigDict, Field, StringConstraints

from backend.core.grid import MAX_MOVES, Move
from backend.core.models import QuestionType, StepStatus

Identifier = Annotated[str, StringConstraints(pattern=r"^[a-z0-9_-]{1,60}$")]
MAX_ANSWER_CHARS = 4000
MAX_CHAT_CHARS = 2000
MAX_SCREENSHOT_BYTES = 1_500_000
MAX_SCREENSHOT_B64 = MAX_SCREENSHOT_BYTES * 4 // 3 + 4


class Request(BaseModel):
    model_config = ConfigDict(extra="forbid")


class QuestionRequest(Request):
    skill_id: Identifier
    type: QuestionType | None = None


class AnswerRequest(Request):
    question_id: Annotated[str, StringConstraints(pattern=r"^[a-f0-9]{32}$")]
    text: str = Field(default="", max_length=MAX_ANSWER_CHARS)
    choice: int | None = Field(default=None, ge=0, le=9)
    tests_passed: int = Field(default=0, ge=0, le=50)
    tests_total: int = Field(default=0, ge=0, le=50)


class GoalRequest(Request):
    role_id: Identifier


class StepUpdate(Request):
    status: StepStatus
    actual_hours: float | None = Field(default=None, gt=0, le=500)


class MentorRequest(Request):
    message: str = Field(min_length=1, max_length=MAX_CHAT_CHARS)
    screenshot_b64: str | None = Field(default=None, max_length=MAX_SCREENSHOT_B64)


class InterviewRequest(Request):
    role_id: Identifier | None = None
    count: int = Field(default=10, ge=1, le=10)


class GridResult(Request):
    level_id: Identifier
    moves: list[Move] = Field(max_length=MAX_MOVES)

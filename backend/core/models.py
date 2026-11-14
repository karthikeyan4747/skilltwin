"""Domain models shared by the deterministic core, agents and API."""

from datetime import datetime
from typing import Annotated, Literal

from pydantic import BaseModel, ConfigDict, Field, StringConstraints

EvidenceType = Literal["mcq", "explain_back", "predict_output", "code_exercise", "interview"]
QuestionType = EvidenceType
StepStatus = Literal["todo", "in_progress", "done"]
RerouteTrigger = Literal["failed_assessment", "goal_change", "mentor"]
Difficulty = Literal["easy", "medium", "hard"]
ResourceKind = Literal["course", "tutorial", "exercise"]
ShortText = Annotated[str, StringConstraints(strip_whitespace=True, min_length=1, max_length=120)]


class Strict(BaseModel):
    model_config = ConfigDict(extra="forbid")


class Skill(Strict):
    id: str
    name: str
    category: str
    prerequisites: list[str] = []
    est_hours: float = Field(gt=0)


class Role(Strict):
    id: str
    title: str
    description: str
    skills: dict[str, float]
    demand: dict[str, int]


class Resource(Strict):
    kind: ResourceKind
    title: str
    url: str
    provider: str


class CodeSnippet(Strict):
    id: str
    title: str
    skill_id: str
    code: str


class Question(Strict):
    """A question including its answer key; never sent to the client as-is."""

    id: str
    skill_id: str
    type: QuestionType
    prompt: str
    options: list[str] = []
    answer_index: int | None = None
    code: str | None = None
    expected_output: str | None = None
    rubric: list[str] = []
    tests: str | None = None
    misconceptions: dict[str, str] = {}


class Evidence(Strict):
    skill_id: str
    type: EvidenceType
    score: float = Field(ge=0, le=1)
    timestamp: datetime


class Profile(Strict):
    name: str = Field(min_length=1, max_length=80)
    education: str = Field(default="", max_length=200)
    hours_per_week: float = Field(default=8, ge=1, le=80)
    claimed_skills: list[ShortText] = Field(default=[], max_length=40)
    certifications: list[ShortText] = Field(default=[], max_length=20)
    projects: list[ShortText] = Field(default=[], max_length=20)
    career_goal: str = Field(max_length=60)


class SkillStatus(Strict):
    skill_id: str
    name: str
    claimed: bool
    confidence: float
    verified: bool
    evidence_count: int


class RoadmapStep(Strict):
    skill_id: str
    reason: str
    est_hours: float
    status: StepStatus = "todo"
    actual_hours: float | None = None
    resource_reason: str = ""


class RerouteEvent(Strict):
    timestamp: datetime
    trigger: RerouteTrigger
    failed_skill: str | None = None
    root_cause: str | None = None
    path: list[str] = []
    inserted: list[str] = []
    note: str = ""


class Roadmap(Strict):
    role_id: str
    steps: list[RoadmapStep] = []
    reroutes: list[RerouteEvent] = []


class TwinRecord(Strict):
    question_id: str
    skill_id: str
    predicted_correct: bool
    actual_correct: bool


class Misconception(Strict):
    skill_id: str
    text: str
    timestamp: datetime


class ConfidencePoint(Strict):
    skill_id: str
    confidence: float
    timestamp: datetime


class AssessmentRecord(Strict):
    question_id: str
    skill_id: str
    type: QuestionType
    score: float
    correct: bool
    timestamp: datetime


class InterviewTicketResult(Strict):
    skill_id: str
    title: str
    predicted_score: float


class InterviewBatch(Strict):
    role_id: str
    timestamp: datetime
    results: list[InterviewTicketResult]
    weak_areas: list[str]
    plan: list[str]


class Learner(Strict):
    profile: Profile
    evidence: list[Evidence] = []
    roadmap: Roadmap
    twin_history: list[TwinRecord] = []
    misconceptions: list[Misconception] = []
    confidence_history: list[ConfidencePoint] = []
    assessments: list[AssessmentRecord] = []
    latest_interview: InterviewBatch | None = None

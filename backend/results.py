"""Typed results returned by orchestrated flows; each carries the agent collaboration trace."""

from pydantic import BaseModel

from backend.agents.base import TraceStep
from backend.core.career import GoalSwitch, Readiness
from backend.core.models import InterviewBatch, QuestionType, RoadmapStep


class FlowResult(BaseModel):
    agent_trace: list[TraceStep]
    offline_ai: bool


class OnboardResult(FlowResult):
    summary: str
    better_fit_reason: str | None
    ranking: list[Readiness]


class PublicQuestion(BaseModel):
    """A question as shown to the learner: no answer key, no Twin prediction."""

    id: str
    skill_id: str
    skill_name: str
    type: QuestionType
    difficulty: str
    prompt: str
    options: list[str]
    code: str | None
    tests: str | None


class QuestionResult(FlowResult):
    question: PublicQuestion


class TwinReveal(BaseModel):
    predicted_answer: str
    predicted_correct: bool
    reasoning: str
    prediction_matched: bool
    accuracy: float | None


class DiagnosisReveal(BaseModel):
    root_cause: str
    path: list[str]
    path_names: list[str]
    explanation: str
    first_action: str
    inserted_steps: list[str]


class AnswerResult(FlowResult):
    correct: bool
    score: float
    fluency_score: float | None
    feedback: str
    correct_answer: str
    evidence_type: QuestionType
    confidence_before: float
    confidence_after: float
    verified: bool
    misconception: str | None
    twin: TwinReveal
    diagnosis: DiagnosisReveal | None


class GoalChangeResult(FlowResult):
    switch: GoalSwitch
    summary: str
    roadmap_steps: list[RoadmapStep]


class InterviewResult(FlowResult):
    batch: InterviewBatch
    skill_names: dict[str, str]


class MentorResult(FlowResult):
    reply: str
    applied_focus: list[str]
    applied_focus_names: list[str]


class PublishResult(FlowResult):
    linkedin_post: str
    learning_log_md: str


class ScenarioStage(BaseModel):
    title: str
    summary: str
    agent_trace: list[TraceStep]


class SampleScenarioResult(FlowResult):
    stages: list[ScenarioStage]
    answer: AnswerResult
    goal: GoalChangeResult

"""Typed response models for every read endpoint, so the OpenAPI schema documents each payload."""

from typing import Literal

from pydantic import BaseModel

from backend.agents.base import Mode, ModelTiers
from backend.agents.team import AgentProfile
from backend.core.career import GoalSwitch, Readiness
from backend.core.grid import GridLevel
from backend.core.insights import MisconceptionStat
from backend.core.models import (
    AssessmentRecord,
    CodeSnippet,
    ConfidencePoint,
    InterviewBatch,
    Profile,
    RerouteEvent,
    Resource,
    RoadmapStep,
    SkillStatus,
)
from backend.results import OnboardResult
from backend.services.jobs import DemandReport


class SkillOption(BaseModel):
    id: str
    name: str


class RoleOption(BaseModel):
    id: str
    title: str


class ProfileView(BaseModel):
    profile: Profile
    skill_options: list[SkillOption]
    role_options: list[RoleOption]


class ProfileSaved(BaseModel):
    profile: Profile
    result: OnboardResult


class GraphNode(BaseModel):
    id: str
    name: str
    category: str
    prerequisites: list[str]


class SkillGraphView(BaseModel):
    nodes: list[GraphNode]
    order: list[str]


class AnalysisView(BaseModel):
    skills: list[SkillStatus]
    strengths: list[str]
    weaknesses: list[str]
    graph: SkillGraphView


class RoleSummary(BaseModel):
    id: str
    title: str
    description: str
    skills: dict[str, float]


class CareerView(BaseModel):
    target: Readiness
    role: RoleSummary
    ranking: list[Readiness]
    better_fit: Readiness | None
    better_fit_reason: str | None
    time_to_ready_weeks: float
    remaining_hours: float
    velocity: float
    hours_per_week: float
    demand: DemandReport
    skill_names: dict[str, str]
    roles: list[RoleOption]


class GoalPreview(GoalSwitch):
    reused_names: list[str]
    delta_names: list[str]
    role_title: str


class NamedStep(RoadmapStep):
    skill_name: str


class RoadmapStepView(NamedStep):
    resources: list[Resource]


class RerouteView(RerouteEvent):
    path_names: list[str]
    inserted_names: list[str]
    failed_name: str | None
    root_name: str | None


class RoadmapView(BaseModel):
    role_title: str
    steps: list[RoadmapStepView]
    reroutes: list[RerouteView]
    completion_pct: float


class ProgressView(BaseModel):
    confidence_history: list[ConfidencePoint]
    assessments: list[AssessmentRecord]
    completion_pct: float
    twin_accuracy: float | None
    twin_predictions: int
    latest_interview: InterviewBatch | None
    skill_names: dict[str, str]


class ReadinessSummary(BaseModel):
    role_title: str
    claimed_pct: float
    proven_pct: float
    verified: list[str]
    missing: list[str]
    unproven: list[str]
    roadmap_order: list[str]
    time_to_ready_weeks: float
    twin_accuracy: float | None
    better_fit: str | None


class DashboardView(ReadinessSummary):
    name: str
    verified_count: int
    next_steps: list[NamedStep]
    ai_mode: Mode


class LessonsView(BaseModel):
    snippets: list[CodeSnippet]
    grid_levels: list[GridLevel]


class GridResultView(BaseModel):
    solved: bool
    evidence_added: bool
    skill_name: str | None = None
    confidence_before: float | None = None
    confidence_after: float | None = None


class InsightRow(MisconceptionStat):
    skill_name: str


class InsightsView(BaseModel):
    total_learners: int
    rows: list[InsightRow]


class HealthView(BaseModel):
    status: Literal["ok"]
    version: str
    llm: Mode


class FeatureView(BaseModel):
    id: str
    title: str
    requirement: str
    required_by_problem_statement: bool
    ui_route: str
    api_endpoints: list[str]
    modules: list[str]
    tests: list[str]


class AdaptationLoop(BaseModel):
    trigger: str
    behaviour: str


class MetaView(BaseModel):
    name: str
    version: str
    ai_mode: Mode
    repository: str
    features: list[FeatureView]
    adaptation_loops: list[AdaptationLoop]
    agents: list[AgentProfile]
    model_tiers: ModelTiers

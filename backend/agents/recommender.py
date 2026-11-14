"""Recommender agent: writes a one-line reason for each roadmap step's resources."""

from pydantic import BaseModel, Field

from backend.agents.base import Agent


class StepContext(BaseModel):
    skill_id: str
    skill_name: str
    gap_reason: str
    resources: list[str]


class RecommenderIn(BaseModel):
    role_title: str
    weaknesses: list[str]
    steps: list[StepContext]


class StepReason(BaseModel):
    skill_id: str
    reason: str = Field(max_length=400)


class RecommenderOut(BaseModel):
    reasons: list[StepReason]


class Recommender(Agent[RecommenderIn, RecommenderOut]):
    name = "Recommender"
    key = "recommender"
    purpose = "Explained why each recommended course, tutorial and exercise fits"
    tier = "fast"
    max_tokens = 900
    output_model = RecommenderOut
    instructions = (
        "For every step, write ONE sentence (max 25 words) telling the learner why these "
        "resources are the right next move for their target role, referencing their gap. "
        "Return one entry per step, keeping each skill_id unchanged."
    )

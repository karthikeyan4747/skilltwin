"""Career agent: narrates role readiness and justifies any better-fit suggestion."""

from pydantic import BaseModel, Field

from backend.agents.base import Agent


class RoleScore(BaseModel):
    title: str
    claimed_pct: float
    proven_pct: float


class CareerIn(BaseModel):
    target_role: str
    ranking: list[RoleScore]
    better_fit: str | None
    verified_skills: list[str]


class CareerOut(BaseModel):
    summary: str = Field(max_length=800)
    better_fit_reason: str | None = Field(default=None, max_length=500)


class CareerAgent(Agent[CareerIn, CareerOut]):
    name = "Career"
    key = "career"
    purpose = "Compared readiness across job roles"
    tier = "fast"
    max_tokens = 300
    output_model = CareerOut
    instructions = (
        "Summarise in two sentences how ready the learner is for the target role, contrasting "
        "claimed versus proven readiness. If `better_fit` is set, explain in one sentence which "
        "verified skills make it a better fit; otherwise return null for better_fit_reason. "
        "Use only the numbers provided."
    )

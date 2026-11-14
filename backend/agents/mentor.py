"""AI Mentor agent: grounded guidance that may suggest roadmap re-prioritisation."""

from typing import Any

from pydantic import BaseModel, Field

from backend.agents.base import Agent, Tier


class MentorIn(BaseModel):
    message: str
    learner_name: str
    role_title: str
    next_steps: list[str]
    roadmap_skills: dict[str, str]
    strengths: list[str]
    weaknesses: list[str]
    recent_results: list[str]
    misconceptions: list[str]
    screenshot_jpeg_b64: str | None = None


class MentorOut(BaseModel):
    reply: str = Field(max_length=1500)
    suggested_focus: list[str] = Field(default=[], max_length=3)


class Mentor(Agent[MentorIn, MentorOut]):
    name = "AI Mentor"
    key = "mentor"
    purpose = "Gave guidance grounded in the skill graph, roadmap and recent evidence"
    tier = "smart"
    max_tokens = 600
    output_model = MentorOut
    instructions = (
        "You are a supportive mentor. Ground every answer in the learner's roadmap, strengths, "
        "weaknesses, recent results and misconceptions. If a screenshot is attached, describe "
        "what you see that is relevant to their learning. Keep replies under 120 words. If the "
        "learner should re-prioritise, put up to 3 skill ids (keys of roadmap_skills) in "
        "suggested_focus; otherwise leave it empty."
    )

    def tier_for(self, inp: MentorIn) -> Tier:
        return "vision" if inp.screenshot_jpeg_b64 else self.tier

    def image_for(self, inp: MentorIn) -> str | None:
        return inp.screenshot_jpeg_b64

    def payload(self, inp: MentorIn) -> dict[str, Any]:
        data = inp.model_dump(mode="json", exclude={"screenshot_jpeg_b64"})
        data["screenshot_attached"] = inp.screenshot_jpeg_b64 is not None
        return data

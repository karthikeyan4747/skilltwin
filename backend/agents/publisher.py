"""Publisher agent: drafts a Learn-in-Public post and learning log from real evidence."""

from pydantic import BaseModel, Field

from backend.agents.base import Agent


class PublisherIn(BaseModel):
    learner_name: str
    role_title: str
    proven_pct: float
    verified_skills: list[str]
    evidence_count: int
    completed_steps: list[str]
    next_steps: list[str]
    misconceptions_overcome: list[str]


class PublisherOut(BaseModel):
    linkedin_post: str = Field(max_length=2000)
    learning_log_md: str = Field(max_length=6000)


class Publisher(Agent[PublisherIn, PublisherOut]):
    name = "Publisher"
    key = "publisher"
    purpose = "Drafted a Learn-in-Public post from verified evidence"
    tier = "fast"
    max_tokens = 1200
    output_model = PublisherOut
    instructions = (
        "Write an authentic, humble LinkedIn post (max 150 words, 2-3 hashtags) about the "
        "learner's progress toward the role, and a markdown learning log with sections "
        "'Verified skills', 'Misconceptions I overcame', 'Completed steps' and 'Next steps'. "
        "Only use the facts provided; never invent skills, numbers or certifications."
    )

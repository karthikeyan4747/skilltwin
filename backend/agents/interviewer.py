"""Interviewer agent: creates 'day in the role' work tickets for a target job role."""

from pydantic import BaseModel, Field

from backend.agents.base import Agent


class TicketExample(BaseModel):
    skill_id: str
    skill_name: str
    weight: float
    prompt: str
    rubric: list[str]


class InterviewerIn(BaseModel):
    role_title: str
    count: int = Field(ge=1, le=20)
    examples: list[TicketExample]


class Ticket(BaseModel):
    skill_id: str
    title: str = Field(max_length=120)
    prompt: str = Field(max_length=600)
    rubric: list[str] = Field(min_length=1, max_length=6)


class InterviewerOut(BaseModel):
    tickets: list[Ticket]


class Interviewer(Agent[InterviewerIn, InterviewerOut]):
    name = "Interviewer"
    key = "interviewer"
    purpose = "Created realistic 'day in the role' work tickets"
    tier = "smart"
    max_tokens = 1800
    output_model = InterviewerOut
    instructions = (
        "Create exactly `count` realistic work tickets someone in this role would get on a "
        "normal day. Spread tickets across skills in proportion to their weight. Each ticket "
        "uses a skill_id from the examples, a short title, a concrete scenario prompt and 3-5 "
        "rubric concepts a good answer must mention."
    )

"""Observer agent: names the misconception revealed by a learner's answer."""

from pydantic import BaseModel, Field

from backend.agents.base import Agent


class ObserverIn(BaseModel):
    skill_name: str
    question: str
    learner_answer: str
    correct_answer: str
    score: float
    missed_points: list[str]
    known_distractor_misconception: str | None


class ObserverOut(BaseModel):
    misconception: str | None = Field(default=None, max_length=300)


class Observer(Agent[ObserverIn, ObserverOut]):
    name = "Observer"
    key = "observer"
    purpose = "Looked for the misconception behind the answer"
    tier = "fast"
    max_tokens = 120
    output_model = ObserverOut
    instructions = (
        "If the answer is not fully correct, state the single most likely misconception as a "
        "short phrase (max 12 words) starting with a verb, e.g. 'Thinks assignment copies a "
        "list'. If `known_distractor_misconception` is given and fits, reuse its exact wording. "
        "If the answer is correct, return null."
    )

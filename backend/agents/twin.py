"""Learner Twin agents: predict the learner's answer; answer interview tickets as the learner."""

from pydantic import BaseModel, Field

from backend.agents.base import Agent


class TwinPredictIn(BaseModel):
    skill_name: str
    question: str
    options: list[str]
    correct_answer: str
    wrong_answers: dict[str, str]
    confidence: float
    misconceptions: list[str]
    recent_scores: list[float]


class TwinPredictOut(BaseModel):
    predicted_answer: str = Field(max_length=300)
    predicted_correct: bool
    reasoning: str = Field(max_length=400)


class TwinPredictor(Agent[TwinPredictIn, TwinPredictOut]):
    name = "Learner Twin"
    key = "twin_predictor"
    purpose = "Predicted the learner's answer before they submit"
    tier = "fast"
    max_tokens = 250
    output_model = TwinPredictOut
    instructions = (
        "You model this specific learner. Using their confidence, recent scores and known "
        "misconceptions, predict the exact answer they will give and whether it will be "
        "correct. `wrong_answers` maps plausible wrong answers to the misconception that "
        "produces them; pick one if a known misconception applies. Explain your reasoning "
        "in one sentence that references the learner's history."
    )


class TwinRespondIn(BaseModel):
    skill_name: str
    ticket: str
    rubric: list[str]
    confidence: float
    misconceptions: list[str]


class TwinRespondOut(BaseModel):
    answer: str = Field(max_length=1200)


class TwinResponder(Agent[TwinRespondIn, TwinRespondOut]):
    name = "Learner Twin"
    key = "twin_responder"
    purpose = "Answered a simulated work ticket as the learner would"
    tier = "fast"
    max_tokens = 300
    output_model = TwinRespondOut
    instructions = (
        "Role-play this learner answering a work ticket. Reflect their real level: cover only "
        "the concepts their confidence suggests they know and let their misconceptions show. "
        "Do not answer better than the learner would. 2-4 sentences."
    )

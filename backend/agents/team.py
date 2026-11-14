"""The team of specialised agents the orchestrator coordinates."""

from dataclasses import dataclass, fields

from pydantic import BaseModel

from backend.agents.assessor import AnswerGrader, QuestionWriter
from backend.agents.base import ModelTiers
from backend.agents.career import CareerAgent
from backend.agents.diagnostic import Diagnostic
from backend.agents.interviewer import Interviewer
from backend.agents.mentor import Mentor
from backend.agents.observer import Observer
from backend.agents.publisher import Publisher
from backend.agents.recommender import Recommender
from backend.agents.twin import TwinPredictor, TwinResponder
from backend.services.llm import LLMClient


class AgentProfile(BaseModel):
    name: str
    key: str
    responsibility: str
    tiers: list[str]
    models: list[str]


@dataclass(frozen=True)
class AgentTeam:
    question_writer: QuestionWriter
    grader: AnswerGrader
    observer: Observer
    diagnostic: Diagnostic
    recommender: Recommender
    twin_predictor: TwinPredictor
    twin_responder: TwinResponder
    interviewer: Interviewer
    career: CareerAgent
    mentor: Mentor
    publisher: Publisher

    @classmethod
    def build(cls, llm: LLMClient, fallback: LLMClient, models: ModelTiers) -> "AgentTeam":
        """Create every agent with the live client, the offline fallback and the model tiers."""
        args = (llm, fallback, models)
        return cls(
            question_writer=QuestionWriter(*args),
            grader=AnswerGrader(*args),
            observer=Observer(*args),
            diagnostic=Diagnostic(*args),
            recommender=Recommender(*args),
            twin_predictor=TwinPredictor(*args),
            twin_responder=TwinResponder(*args),
            interviewer=Interviewer(*args),
            career=CareerAgent(*args),
            mentor=Mentor(*args),
            publisher=Publisher(*args),
        )

    def roster(self, models: ModelTiers) -> list[AgentProfile]:
        """Every agent on the team with its responsibility and model tier(s), read from the code."""
        profiles = []
        for field in fields(self):
            agent = getattr(self, field.name)
            tiers = [agent.tier, *agent.extra_tiers]
            profiles.append(
                AgentProfile(
                    name=agent.name,
                    key=agent.key,
                    responsibility=agent.purpose,
                    tiers=tiers,
                    models=[getattr(models, tier) for tier in tiers],
                )
            )
        return profiles

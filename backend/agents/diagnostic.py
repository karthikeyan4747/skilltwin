"""Diagnostic agent: explains the root cause found by core.diagnosis in plain language."""

from pydantic import BaseModel, Field

from backend.agents.base import Agent


class DiagnosticIn(BaseModel):
    failed_skill: str
    root_cause: str
    path: list[str]
    confidences: dict[str, float]
    misconception: str | None


class DiagnosticOut(BaseModel):
    explanation: str = Field(max_length=800)
    first_action: str = Field(max_length=400)


class Diagnostic(Agent[DiagnosticIn, DiagnosticOut]):
    name = "Diagnostic"
    key = "diagnostic"
    purpose = "Explained the root cause along the prerequisite path"
    tier = "fast"
    max_tokens = 250
    output_model = DiagnosticOut
    instructions = (
        "The deterministic engine already found the root cause by walking the prerequisite "
        "graph. Do not change it. In two sentences explain to the learner why this prerequisite "
        "is the real blocker for the failed skill, then give one concrete first action."
    )

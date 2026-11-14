"""Orchestrator: the single place where the specialised agents collaborate.

Deterministic core functions decide; agents only write, grade, predict and explain.
Flows are grouped by concern: planning (onboard, change_goal), questions (next_question),
assessment (submit_answer) and coaching (twin_interview, mentor_chat, publish_draft).
"""

from backend.orchestrator.assessment import Answer, AssessmentFlows
from backend.orchestrator.coaching import CoachingFlows
from backend.orchestrator.planning import PlanningFlows
from backend.orchestrator.questions import QuestionFlows


class Orchestrator(PlanningFlows, QuestionFlows, AssessmentFlows, CoachingFlows):
    """All orchestrated flows over one shared catalog, agent team and cache set."""


__all__ = ["Answer", "Orchestrator"]

"""Orchestrator: the single place where the specialised agents collaborate.

Deterministic core functions decide; agents only write, grade, predict and explain.
Flows are grouped by concern: planning (onboard, change_goal), questions (next_question),
assessment (submit_answer), coaching (twin_interview, mentor_chat, publish_draft) and the
end-to-end sample scenario (sample_scenario), which composes the others.
"""

from backend.orchestrator.assessment import Answer
from backend.orchestrator.coaching import CoachingFlows
from backend.orchestrator.scenario import ScenarioFlows


class Orchestrator(ScenarioFlows, CoachingFlows):
    """All orchestrated flows over one shared catalog, agent team and cache set."""


__all__ = ["Answer", "Orchestrator"]

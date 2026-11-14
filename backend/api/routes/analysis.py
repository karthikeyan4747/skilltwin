"""Skill Analysis: evidence-verified skills, strengths, weaknesses and the prerequisite
graph.
"""

from fastapi import APIRouter

from backend.api.deps import LearnerDep, ServicesDep
from backend.api.presenters import analysis_view
from backend.api.views import AnalysisView

router = APIRouter(prefix="/analysis", tags=["Skill Analysis"])


@router.get("", summary="Skill analysis")
async def get_analysis(learner: LearnerDep, services: ServicesDep) -> AnalysisView:
    """Evidence-based status per skill, strengths, weaknesses and the prerequisite graph."""
    return analysis_view(services.orchestrator.context(learner))

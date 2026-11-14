"""Skill Analysis: evidence-verified skills, strengths, weaknesses and the prerequisite graph."""

from typing import Any

from fastapi import APIRouter

from backend.api.deps import LearnerDep, ServicesDep
from backend.api.presenters import analysis_view

router = APIRouter(prefix="/analysis", tags=["Skill Analysis"])


@router.get("")
async def get_analysis(learner: LearnerDep, services: ServicesDep) -> dict[str, Any]:
    return analysis_view(services.orchestrator.context(learner))

"""Dashboard: headline readiness stats and the next roadmap steps."""

from typing import Any

from fastapi import APIRouter

from backend.api.deps import LearnerDep, ServicesDep
from backend.api.presenters import dashboard_view

router = APIRouter(prefix="/dashboard", tags=["Dashboard"])


@router.get("", summary="Dashboard summary")
async def get_dashboard(learner: LearnerDep, services: ServicesDep) -> dict[str, Any]:
    """Readiness (claimed vs proven), skill gaps, roadmap order, Twin accuracy and next steps."""
    return dashboard_view(services.orchestrator.context(learner), ai_live=services.ai_live)

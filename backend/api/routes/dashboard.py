"""Dashboard: headline readiness stats and the next roadmap steps."""

from typing import Any

from fastapi import APIRouter

from backend.api.deps import LearnerDep, ServicesDep
from backend.api.presenters import dashboard_view

router = APIRouter(prefix="/dashboard", tags=["Dashboard"])


@router.get("")
async def get_dashboard(learner: LearnerDep, services: ServicesDep) -> dict[str, Any]:
    return dashboard_view(services.orchestrator.context(learner), services.ai_live)

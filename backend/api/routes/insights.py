"""Institution Insights: top cohort misconceptions per skill (anonymized)."""

from typing import Any

from fastapi import APIRouter

from backend.api.deps import ServicesDep
from backend.core.insights import top_misconceptions

router = APIRouter(prefix="/insights", tags=["Institution Insights"])


@router.get("", summary="Institution insights")
async def get_insights(services: ServicesDep) -> dict[str, Any]:
    """Top anonymized cohort misconceptions per skill with % of learners affected."""
    records = services.catalog.cohort_records() + services.repo.misconception_records()
    learners = len({r[0] for r in records}) or 1
    stats = top_misconceptions(records, learners)
    names = {sid: s.name for sid, s in services.catalog.graph.skills.items()}
    return {
        "total_learners": learners,
        "rows": [s.model_dump() | {"skill_name": names[s.skill_id]} for s in stats],
    }

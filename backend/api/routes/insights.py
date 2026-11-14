"""Institution Insights: top cohort misconceptions per skill (anonymized)."""

from fastapi import APIRouter

from backend.api.deps import ServicesDep
from backend.api.views import InsightRow, InsightsView
from backend.core.insights import top_misconceptions

router = APIRouter(prefix="/insights", tags=["Institution Insights"])


@router.get("", summary="Institution insights")
async def get_insights(services: ServicesDep) -> InsightsView:
    """Top anonymized cohort misconceptions per skill with % of learners affected."""
    records = services.catalog.cohort_records() + services.repo.misconception_records()
    learners = len({r[0] for r in records}) or 1
    stats = top_misconceptions(records, learners)
    names = {sid: s.name for sid, s in services.catalog.graph.skills.items()}
    return InsightsView(
        total_learners=learners,
        rows=[InsightRow(**s.model_dump(), skill_name=names[s.skill_id]) for s in stats],
    )

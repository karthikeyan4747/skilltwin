"""Public, read-only metadata generated from the feature registry and agent team."""

from fastapi import APIRouter, Request

from backend import __version__
from backend.api.deps import ServicesDep
from backend.api.pages import endpoints_by_tag
from backend.api.routes.site import ai_mode
from backend.api.views import AdaptationLoop, FeatureView, MetaView
from backend.registry import ADAPTATION_LOOPS, FEATURES, REPO_URL

router = APIRouter(prefix="/meta", tags=["Meta"])


@router.get("", summary="Features, agents and model tiers")
async def get_meta(request: Request, services: ServicesDep) -> MetaView:
    """Features (UI route, endpoints, code, tests), adaptation loops, agents and model tiers."""
    endpoints = endpoints_by_tag(request.app)
    return MetaView(
        name="SkillTwin",
        version=__version__,
        ai_mode=ai_mode(services),
        repository=REPO_URL,
        features=[
            FeatureView(
                id=f.id,
                title=f.title,
                requirement=f.requirement,
                required_by_problem_statement=f.required,
                ui_route=f.ui_route,
                api_endpoints=endpoints.get(f.api_tag, []),
                modules=list(f.modules),
                tests=list(f.tests),
            )
            for f in FEATURES
        ],
        adaptation_loops=[AdaptationLoop(trigger=t, behaviour=b) for t, b in ADAPTATION_LOOPS],
        agents=services.orchestrator.agents.roster(services.models),
        model_tiers=services.models,
    )

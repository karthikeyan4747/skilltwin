"""Shared orchestrator state: catalog, agent team, clock, caches and learner context."""

from collections.abc import Callable
from datetime import UTC, datetime

from backend.agents.base import AgentTrace
from backend.agents.recommender import RecommenderIn, StepContext
from backend.agents.team import AgentTeam
from backend.core import analysis, career
from backend.core.career import Readiness
from backend.core.models import Learner, Roadmap, SkillStatus
from backend.orchestrator.context import LearnerContext
from backend.services.cache import TTLCache
from backend.services.catalog import Catalog

QUESTION_TTL_SECONDS = 3600
RANKING_TTL_SECONDS = 3600


def utc_now() -> datetime:
    """Timezone-aware current time; injected as the orchestrator clock."""
    return datetime.now(UTC)


class OrchestratorBase:
    def __init__(
        self, catalog: Catalog, agents: AgentTeam, clock: Callable[[], datetime] = utc_now
    ) -> None:
        self.catalog = catalog
        self.agents = agents
        self.clock = clock
        self.question_cache = TTLCache(QUESTION_TTL_SECONDS)
        self._ranking_cache = TTLCache(RANKING_TTL_SECONDS)
        self._graph_hash = catalog.graph.fingerprint()

    def context(self, learner: Learner) -> LearnerContext:
        """Snapshot of derived learner state (statuses, ranking) at the current time."""
        now = self.clock()
        statuses = analysis.analyze_skills(
            self.catalog.graph, learner.profile.claimed_skills, learner.evidence, now
        )
        return LearnerContext(self.catalog, learner, now, statuses, self._ranking(statuses))

    def _ranking(self, statuses: dict[str, SkillStatus]) -> list[Readiness]:
        """Role ranking depends only on the graph and the claimed/verified sets, so cache it."""
        key = (
            self._graph_hash,
            frozenset(s for s, v in statuses.items() if v.claimed),
            frozenset(s for s, v in statuses.items() if v.verified),
        )
        ranking = self._ranking_cache.get(key)
        if ranking is None:
            ranking = career.rank_roles(list(self.catalog.roles.values()), statuses)
            self._ranking_cache.set(key, ranking)
        return ranking

    async def attach_reasons(
        self,
        plan: Roadmap,
        ctx: LearnerContext,
        trace: AgentTrace,
        only: set[str] | None = None,
    ) -> Roadmap:
        """Recommender adds a one-line AI reason to each step's resources (one batched call)."""
        targets = [s for s in plan.steps if only is None or s.skill_id in only]
        if not targets:
            return plan
        out = await self.agents.recommender.run(
            RecommenderIn(
                role_title=ctx.role.title,
                weaknesses=ctx.names(ctx.weaknesses),
                steps=[
                    StepContext(
                        skill_id=s.skill_id,
                        skill_name=ctx.name(s.skill_id),
                        gap_reason=s.reason,
                        resources=[r.title for r in self.catalog.resources.get(s.skill_id, [])],
                    )
                    for s in targets
                ],
            ),
            trace,
        )
        reasons = {r.skill_id: r.reason for r in out.reasons}
        steps = [
            s.model_copy(update={"resource_reason": reasons[s.skill_id]})
            if s.skill_id in reasons
            else s
            for s in plan.steps
        ]
        return plan.model_copy(update={"steps": steps})

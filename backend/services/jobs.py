"""Market demand per skill: live Adzuna job counts when configured, else curated counts."""

import asyncio
import logging
from typing import Literal

import httpx
from pydantic import BaseModel

from backend.core.models import Role
from backend.core.skill_graph import SkillGraph
from backend.services.cache import TTLCache

log = logging.getLogger(__name__)
ADZUNA_URL = "https://api.adzuna.com/v1/api/jobs/in/search/1"
DEMAND_TTL_SECONDS = 6 * 3600


class DemandReport(BaseModel):
    source: Literal["live", "curated"]
    counts: dict[str, int]


class JobDemandService:
    def __init__(
        self,
        app_id: str | None,
        app_key: str | None,
        graph: SkillGraph,
        transport: httpx.AsyncBaseTransport | None = None,
    ) -> None:
        self._transport = transport
        self._app_id = app_id
        self._app_key = app_key
        self._graph = graph
        self._cache = TTLCache(DEMAND_TTL_SECONDS, max_items=32)

    async def demand(self, role: Role) -> DemandReport:
        cached: DemandReport | None = self._cache.get(role.id)
        if cached is not None:
            return cached
        report = DemandReport(source="curated", counts=dict(role.demand))
        if self._app_id and self._app_key:
            try:
                report = DemandReport(source="live", counts=await self._fetch(role))
            except (httpx.HTTPError, KeyError, ValueError) as exc:
                log.warning("Adzuna lookup failed, using curated demand: %s", type(exc).__name__)
        self._cache.set(role.id, report)
        return report

    async def _fetch(self, role: Role) -> dict[str, int]:
        async with httpx.AsyncClient(timeout=5.0, transport=self._transport) as client:

            async def count(skill_id: str) -> tuple[str, int]:
                params = {
                    "app_id": self._app_id,
                    "app_key": self._app_key,
                    "what": self._graph.name(skill_id),
                    "results_per_page": 1,
                    "content-type": "application/json",
                }
                response = await client.get(ADZUNA_URL, params=params)
                response.raise_for_status()
                return skill_id, int(response.json()["count"])

            pairs = await asyncio.gather(*(count(sid) for sid in role.skills))
        return dict(pairs)

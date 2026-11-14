import json

import httpx
import pytest

from backend.services.cache import TTLCache
from backend.services.jobs import JobDemandService
from backend.services.llm import REASONING_HEADROOM_TOKENS, GroqClient, LLMError


def adzuna(handler) -> httpx.MockTransport:
    return httpx.MockTransport(handler)


async def test_live_demand_from_adzuna_is_labelled_and_cached(catalog) -> None:
    calls = []

    def handler(request: httpx.Request) -> httpx.Response:
        calls.append(request.url.params["what"])
        return httpx.Response(200, json={"count": 42})

    service = JobDemandService("id", "key", catalog.graph, transport=adzuna(handler))
    role = catalog.roles["data_analyst"]
    report = await service.demand(role)
    assert report.source == "live" and set(report.counts.values()) == {42}
    await service.demand(role)
    assert len(calls) == len(role.skills)


async def test_demand_falls_back_to_curated_on_error(catalog) -> None:
    service = JobDemandService(
        "id", "key", catalog.graph, transport=adzuna(lambda r: httpx.Response(500))
    )
    report = await service.demand(catalog.roles["data_analyst"])
    assert report.source == "curated" and report.counts["sql"] == 8100


async def test_groq_client_sends_json_mode_and_wraps_errors() -> None:
    seen = {}

    def ok(request: httpx.Request) -> httpx.Response:
        seen.update(json.loads(request.content))
        message = {"role": "assistant", "content": '{"ok": true}'}
        return httpx.Response(
            200,
            json={
                "id": "x",
                "object": "chat.completion",
                "created": 0,
                "model": "m",
                "choices": [{"index": 0, "message": message, "finish_reason": "stop"}],
            },
        )

    client = GroqClient("k", http_client=httpx.AsyncClient(transport=httpx.MockTransport(ok)))
    raw = await client.complete_json(
        agent="a", system="s", payload={"x": 1}, model="m", max_tokens=5, image_jpeg_b64="abc"
    )
    assert raw == '{"ok": true}'
    assert seen["response_format"] == {"type": "json_object"}
    assert seen["max_tokens"] == 5 + REASONING_HEADROOM_TOKENS
    assert "reasoning_effort" not in seen
    assert seen["messages"][1]["content"][1]["image_url"]["url"].startswith("data:image/jpeg")

    await client.complete_json(
        agent="a", system="s", payload={}, model="openai/gpt-oss-20b", max_tokens=5
    )
    assert seen["reasoning_effort"] == "low"

    failing = GroqClient(
        "k",
        http_client=httpx.AsyncClient(transport=httpx.MockTransport(lambda r: httpx.Response(503))),
    )
    with pytest.raises(LLMError):
        await failing.complete_json(agent="a", system="s", payload={}, model="m", max_tokens=5)


def test_ttl_cache_expiry_and_bound(monkeypatch) -> None:
    clock = [0.0]
    monkeypatch.setattr("backend.services.cache.time.monotonic", lambda: clock[0])
    cache = TTLCache(ttl_seconds=10, max_items=2)
    cache.set("a", 1)
    cache.set("b", 2)
    cache.set("c", 3)
    assert cache.get("a") is None and cache.get("c") == 3
    clock[0] = 11
    assert cache.get("c") is None

"""LLM clients: the LLMClient protocol, the Groq JSON-mode client and the deterministic MockLLM."""

import json
from collections.abc import Callable
from typing import Any, Protocol

import groq
import httpx

Fixture = Callable[[dict[str, Any]], dict[str, Any]]
DATA_OPEN = "<learner_data>"
DATA_CLOSE = "</learner_data>"
REASONING_HEADROOM_TOKENS = 1024
LOW_EFFORT_REASONING_PREFIX = "openai/gpt-oss"


class LLMError(RuntimeError):
    """A live LLM call failed (network, quota, provider error)."""


class LLMClient(Protocol):
    live: bool

    async def complete_json(
        self,
        *,
        agent: str,
        system: str,
        payload: dict[str, Any],
        model: str,
        max_tokens: int,
        image_jpeg_b64: str | None = None,
    ) -> str: ...


def wrap_payload(payload: dict[str, Any]) -> str:
    """Learner content is passed as delimited data, never as instructions."""
    return f"{DATA_OPEN}\n{json.dumps(payload, ensure_ascii=False)}\n{DATA_CLOSE}"


class GroqClient:
    live = True

    def __init__(
        self,
        api_key: str,
        timeout_seconds: float = 20.0,
        http_client: httpx.AsyncClient | None = None,
    ) -> None:
        self._client = groq.AsyncGroq(
            api_key=api_key, timeout=timeout_seconds, max_retries=0, http_client=http_client
        )

    async def complete_json(
        self,
        *,
        agent: str,
        system: str,
        payload: dict[str, Any],
        model: str,
        max_tokens: int,
        image_jpeg_b64: str | None = None,
    ) -> str:
        text = wrap_payload(payload)
        content: Any = text
        if image_jpeg_b64:
            content = [
                {"type": "text", "text": text},
                {
                    "type": "image_url",
                    "image_url": {"url": f"data:image/jpeg;base64,{image_jpeg_b64}"},
                },
            ]
        # Reasoning models spend hidden tokens before answering: cap their effort and add
        # headroom so the agent's JSON budget is not consumed by reasoning.
        reasoning: dict[str, Any] = (
            {"reasoning_effort": "low"} if model.startswith(LOW_EFFORT_REASONING_PREFIX) else {}
        )
        try:
            response = await self._client.chat.completions.create(
                model=model,
                messages=[
                    {"role": "system", "content": system},
                    {"role": "user", "content": content},
                ],
                response_format={"type": "json_object"},
                max_tokens=max_tokens + REASONING_HEADROOM_TOKENS,
                temperature=0.3,
                **reasoning,
            )
        except groq.GroqError as exc:
            raise LLMError(f"{agent}: {type(exc).__name__}") from exc
        return response.choices[0].message.content or ""


class MockLLM:
    """Deterministic offline LLM: each agent key maps to a pure fixture function."""

    live = False

    def __init__(self, fixtures: dict[str, Fixture]) -> None:
        self._fixtures = fixtures

    async def complete_json(
        self,
        *,
        agent: str,
        system: str,
        payload: dict[str, Any],
        model: str,
        max_tokens: int,
        image_jpeg_b64: str | None = None,
    ) -> str:
        return json.dumps(self._fixtures[agent](payload))

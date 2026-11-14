from collections.abc import Iterator
from datetime import UTC, datetime
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from backend.agents.base import ModelTiers
from backend.agents.team import AgentTeam
from backend.config import Settings
from backend.core.models import Learner, Roadmap
from backend.main import create_app
from backend.orchestrator import Orchestrator
from backend.services.catalog import Catalog, load_catalog
from backend.services.llm import MockLLM
from backend.services.mock_fixtures import MOCK_FIXTURES

NOW = datetime(2026, 11, 1, 12, 0, tzinfo=UTC)
MODELS = ModelTiers(fast="fast-model", smart="smart-model", vision="vision-model")


@pytest.fixture
def now() -> datetime:
    return NOW


@pytest.fixture(scope="session")
def catalog() -> Catalog:
    return load_catalog()


@pytest.fixture
def mock_llm() -> MockLLM:
    return MockLLM(MOCK_FIXTURES)


@pytest.fixture
def orchestrator(catalog: Catalog, mock_llm: MockLLM) -> Orchestrator:
    return Orchestrator(catalog, AgentTeam.build(mock_llm, mock_llm, MODELS), clock=lambda: NOW)


@pytest.fixture
def sample_learner(catalog: Catalog) -> Learner:
    profile = catalog.seed_profile()
    return Learner(
        profile=profile,
        evidence=catalog.seed_evidence(NOW),
        roadmap=Roadmap(role_id=profile.career_goal),
    )


def make_settings(tmp_path: Path, **overrides: object) -> Settings:
    values: dict[str, object] = {
        "session_secret": "test-secret",
        "database_path": tmp_path / "test.db",
        "groq_api_key": None,
    }
    values.update(overrides)
    return Settings(**values)


@pytest.fixture
def client(tmp_path: Path) -> Iterator[TestClient]:
    with TestClient(create_app(make_settings(tmp_path))) as test_client:
        yield test_client

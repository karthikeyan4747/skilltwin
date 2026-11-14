"""Server-rendered pages, metadata and docs: readable without JavaScript and generated from code."""

import base64
import hashlib
import re

from fastapi.testclient import TestClient

from backend.registry import FEATURES


def test_index_is_meaningful_without_javascript(client: TestClient) -> None:
    html = client.get("/").text
    assert html.count("<h1") == 1 and 'lang="en"' in html and "<noscript>" in html
    assert 'property="og:title"' in html and '<meta name="description"' in html
    for text in (
        "Python, SQL",
        "JavaScript",
        "React",
        "Node.js",
        "claimed 18%",
        "proven by evidence 10%",
    ):
        assert text in html
    for feature in (f for f in FEATURES if f.required):
        assert f'href="{feature.ui_route}"' in html
    assert 'href="/about"' in html and 'href="/docs"' in html and "github.com" in html


def test_raw_template_is_not_served(client: TestClient) -> None:
    assert client.get("/index.html").status_code == 404


def test_about_lists_features_endpoints_and_agents(client: TestClient) -> None:
    html = client.get("/about").text
    assert html.count("<h1") == 1
    for feature in FEATURES:
        assert feature.title in html
    for agent in ("Assessor", "Observer", "Diagnostic", "Recommender", "Learner Twin", "AI Mentor"):
        assert agent in html
    assert "POST /api/v1/assessment/answer" in html and "POST /api/v1/career/goal" in html


def test_meta_is_generated_from_registries(client: TestClient) -> None:
    meta = client.get("/api/v1/meta").json()
    assert [f["id"] for f in meta["features"]] == [f.id for f in FEATURES]
    assert sum(f["required_by_problem_statement"] for f in meta["features"]) == 6
    assert all(f["api_endpoints"] for f in meta["features"])
    assert len(meta["agents"]) == 11 and len(meta["adaptation_loops"]) == 2
    mentor = next(a for a in meta["agents"] if a["key"] == "mentor")
    assert mentor["tiers"] == ["smart", "vision"]
    assert set(meta["model_tiers"]) == {"fast", "smart", "vision"}


def test_every_endpoint_is_documented(client: TestClient) -> None:
    paths = client.get("/openapi.json").json()["paths"]
    for path, operations in paths.items():
        for method, operation in operations.items():
            assert operation.get("summary") and operation.get("description"), (method, path)


def test_docs_page_allows_only_its_own_inline_script(client: TestClient) -> None:
    response = client.get("/docs")
    csp = response.headers["content-security-policy"]
    script = re.search(r"<script>(.*?)</script>", response.text, re.DOTALL).group(1)
    digest = base64.b64encode(hashlib.sha256(script.encode()).digest()).decode()
    assert f"'sha256-{digest}'" in csp and "script-src 'self' https://cdn.jsdelivr.net" in csp
    assert "'unsafe-inline'" not in csp.split("script-src")[1].split(";")[0]
    assert "swagger-ui-dist@5.17.14" in response.text
    assert "'unsafe-inline'" not in client.get("/").headers["content-security-policy"]

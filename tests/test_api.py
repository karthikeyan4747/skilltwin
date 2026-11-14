import base64
import io

from fastapi.testclient import TestClient
from PIL import Image

from backend import __version__
from backend.main import create_app
from tests.conftest import make_settings

API = "/api/v1"


def png_b64(size: tuple[int, int] = (2000, 1000)) -> str:
    buffer = io.BytesIO()
    Image.new("RGB", size, "white").save(buffer, format="PNG")
    return base64.b64encode(buffer.getvalue()).decode()


def test_health_and_security_headers(client: TestClient) -> None:
    response = client.get("/healthz")
    assert response.json() == client.get("/health").json()
    assert response.json() == {"status": "ok", "version": __version__, "llm": "offline"}
    csp = response.headers["content-security-policy"]
    assert "frame-ancestors 'none'" in csp and "'unsafe-inline'" not in csp
    assert response.headers["x-content-type-options"] == "nosniff"
    assert response.headers["referrer-policy"] == "strict-origin-when-cross-origin"
    assert "permissions-policy" in response.headers


def test_session_cookie_is_signed_and_http_only(client: TestClient) -> None:
    response = client.get(f"{API}/dashboard")
    cookie = response.headers["set-cookie"]
    assert "st_session=" in cookie and "HttpOnly" in cookie and "SameSite=lax" in cookie
    assert response.json()["role_title"] == "Full Stack Developer"


def test_frontend_is_served(client: TestClient) -> None:
    response = client.get("/")
    assert response.status_code == 200 and "<main" in response.text


def test_sessions_are_isolated(tmp_path) -> None:
    app = create_app(make_settings(tmp_path))
    with TestClient(app) as alice, TestClient(app) as bob:
        profile = alice.get(f"{API}/profile").json()["profile"]
        profile["name"] = "Alice"
        assert alice.put(f"{API}/profile", json=profile).status_code == 200
        assert alice.get(f"{API}/profile").json()["profile"]["name"] == "Alice"
        assert bob.get(f"{API}/profile").json()["profile"]["name"] == "Sam Rivera"
        question = alice.post(f"{API}/assessment/question", json={"skill_id": "git"}).json()
        stolen = bob.post(
            f"{API}/assessment/answer", json={"question_id": question["question"]["id"]}
        )
        assert stolen.status_code == 404


def test_tampered_cookie_gets_new_session(client: TestClient) -> None:
    client.cookies.set("st_session", "forged")
    assert "st_session=" in client.get(f"{API}/dashboard").headers["set-cookie"]


def test_validation_errors_use_envelope(client: TestClient) -> None:
    response = client.post(f"{API}/mentor/chat", json={"message": "x" * 2001})
    assert response.status_code == 422
    body = response.json()["error"]
    assert body["code"] == "validation_error" and "message" in body["fields"]
    extra = client.post(f"{API}/assessment/question", json={"skill_id": "git", "admin": True})
    assert extra.status_code == 422
    unknown = client.post(f"{API}/assessment/question", json={"skill_id": "cobol"})
    assert unknown.json()["error"]["code"] == "unknown_skill"
    profile = client.get(f"{API}/profile").json()["profile"] | {"claimed_skills": ["cobol"]}
    assert client.put(f"{API}/profile", json=profile).status_code == 422


def test_not_found_uses_envelope(client: TestClient) -> None:
    response = client.get(f"{API}/nope")
    assert response.status_code == 404 and response.json()["error"]["code"] == "not_found"


def test_body_size_limit(tmp_path) -> None:
    with TestClient(create_app(make_settings(tmp_path, max_body_bytes=1000))) as small:
        response = small.post(f"{API}/mentor/chat", json={"message": "x" * 1500})
        assert response.status_code == 413
        assert response.json()["error"]["code"] == "payload_too_large"


def test_rate_limit_on_llm_routes(tmp_path) -> None:
    with TestClient(create_app(make_settings(tmp_path, llm_rate_limit="2/minute"))) as limited:
        codes = [
            limited.post(f"{API}/mentor/chat", json={"message": "hi"}).status_code for _ in range(3)
        ]
        assert codes == [200, 200, 429]


def test_full_assessment_round_trip(client: TestClient) -> None:
    question = client.post(f"{API}/assessment/question", json={"skill_id": "react", "type": "mcq"})
    q = question.json()["question"]
    assert "answer_index" not in q and "prediction" not in question.text
    result = client.post(f"{API}/assessment/answer", json={"question_id": q["id"], "choice": 0})
    body = result.json()
    assert body["diagnosis"]["path"][-1] == "react"
    assert body["twin"]["predicted_answer"]
    replay = client.post(f"{API}/assessment/answer", json={"question_id": q["id"], "choice": 0})
    assert replay.status_code == 404
    insights = client.get(f"{API}/insights").json()
    assert insights["total_learners"] == 25
    progress = client.get(f"{API}/progress").json()
    assert progress["twin_predictions"] == 1 and progress["assessments"][0]["skill_id"] == "react"


def test_career_preview_and_change(client: TestClient) -> None:
    career = client.get(f"{API}/career").json()
    assert career["better_fit"]["role_id"] == "data_analyst"
    assert career["demand"]["source"] == "curated"
    preview = client.post(f"{API}/career/preview-goal", json={"role_id": "data_analyst"}).json()
    assert preview["carryover_pct"] == 65.0 and preview["delta_names"] == ["Pandas", "Git"]
    changed = client.post(f"{API}/career/goal", json={"role_id": "data_analyst"})
    assert changed.json()["switch"]["to_role"] == "data_analyst"
    assert client.get(f"{API}/dashboard").json()["role_title"] == "Data Analyst"


def test_roadmap_step_update(client: TestClient) -> None:
    roadmap = client.get(f"{API}/roadmap").json()
    first = roadmap["steps"][0]
    assert {r["kind"] for r in first["resources"]} == {"course", "tutorial", "exercise"}
    updated = client.patch(
        f"{API}/roadmap/steps/{first['skill_id']}", json={"status": "done", "actual_hours": 4}
    ).json()
    assert updated["completion_pct"] > 0
    missing = client.patch(f"{API}/roadmap/steps/docker", json={"status": "done"})
    assert missing.status_code == 404


def test_grid_game_evidence_is_verified_by_replay(client: TestClient) -> None:
    lessons = client.get(f"{API}/lessons").json()
    assert lessons["snippets"] and len(lessons["grid_levels"]) == 3
    bad = client.post(
        f"{API}/lessons/grid-result", json={"level_id": "straight", "moves": ["down"]}
    )
    assert bad.json()["solved"] is False and bad.json()["evidence_added"] is False
    good = client.post(
        f"{API}/lessons/grid-result", json={"level_id": "straight", "moves": ["right"] * 4}
    ).json()
    assert good["solved"] and good["confidence_after"] > good["confidence_before"]


def test_screenshot_is_validated(client: TestClient) -> None:
    ok = client.post(f"{API}/mentor/chat", json={"message": "look", "screenshot_b64": png_b64()})
    assert ok.status_code == 200 and "screenshot" in ok.json()["reply"]
    junk = base64.b64encode(b"GIF89a not an allowed image").decode()
    bad = client.post(f"{API}/mentor/chat", json={"message": "look", "screenshot_b64": junk})
    assert bad.json()["error"]["code"] == "invalid_image"
    not_b64 = client.post(f"{API}/mentor/chat", json={"message": "x", "screenshot_b64": "%%%"})
    assert not_b64.status_code == 422


def test_twin_interviews_and_publish(client: TestClient) -> None:
    batch = client.post(f"{API}/twin/interviews", json={"count": 4}).json()["batch"]
    assert len(batch["results"]) == 4
    assert client.get(f"{API}/progress").json()["latest_interview"]["role_id"]
    draft = client.post(f"{API}/publish/draft").json()
    assert draft["linkedin_post"] and draft["learning_log_md"].startswith("# Learning log")


def test_openapi_docs_enabled(client: TestClient) -> None:
    assert client.get("/openapi.json").json()["info"]["title"] == "SkillTwin API"


def test_sample_scenario_endpoint_resets_and_adapts(client: TestClient) -> None:
    client.post(f"{API}/career/goal", json={"role_id": "frontend_developer"})
    result = client.post(f"{API}/scenario/sample").json()
    assert len(result["stages"]) == 3 and result["agent_trace"]
    assert result["answer"]["diagnosis"]["path"] == ["html", "css", "javascript", "react"]
    dashboard = client.get(f"{API}/dashboard").json()
    assert dashboard["role_title"] == "Data Analyst"
    assert {"missing", "unproven", "roadmap_order", "verified"} <= set(dashboard)

from backend.core.diagnosis import diagnose


def test_root_cause_is_deepest_unverified_prerequisite(catalog) -> None:
    conf = {"html": 0.9, "css": 0.3, "javascript": 0.4, "react": 0.1}
    result = diagnose(catalog.graph, "react", conf)
    assert result.root_cause == "css"
    assert result.path == ["css", "javascript", "react"]


def test_skill_itself_when_prerequisites_are_verified(catalog) -> None:
    conf = {"html": 0.9, "css": 0.9, "javascript": 0.8}
    result = diagnose(catalog.graph, "react", conf)
    assert result.root_cause == "react" and result.path == ["react"]


def test_skill_without_prerequisites(catalog) -> None:
    assert diagnose(catalog.graph, "git", {}).path == ["git"]


def test_walks_through_branching_prerequisites(catalog) -> None:
    result = diagnose(catalog.graph, "express", {})
    assert result.root_cause == "html"
    assert result.path == ["html", "css", "javascript", "nodejs", "express"]

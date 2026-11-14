import pytest

from backend.core.models import Skill
from backend.core.skill_graph import SkillGraph, SkillGraphError


def skill(sid: str, *prereqs: str) -> Skill:
    return Skill(id=sid, name=sid.upper(), category="x", prerequisites=list(prereqs), est_hours=1)


def test_topological_order_puts_prerequisites_first() -> None:
    graph = SkillGraph(
        [skill("react", "js"), skill("js", "css"), skill("css", "html"), skill("html")]
    )
    assert graph.topological(["react", "html", "js"]) == ["html", "js", "react"]


def test_cycle_is_rejected() -> None:
    with pytest.raises(SkillGraphError, match="cycle"):
        SkillGraph([skill("a", "b"), skill("b", "a")])


def test_unknown_prerequisite_is_rejected() -> None:
    with pytest.raises(SkillGraphError, match="unknown"):
        SkillGraph([skill("a", "missing")])


def test_duplicate_id_is_rejected() -> None:
    with pytest.raises(SkillGraphError, match="duplicate"):
        SkillGraph([skill("a"), skill("a")])


def test_ancestors_are_transitive() -> None:
    graph = SkillGraph([skill("c", "b"), skill("b", "a"), skill("a")])
    assert graph.ancestors("c") == {"a", "b"}
    assert graph.ancestors("a") == set()


def test_catalog_graph_matches_problem_statement(catalog) -> None:
    graph = catalog.graph
    assert graph.prerequisites("react") == ["javascript"]
    assert graph.prerequisites("express") == ["nodejs"]
    assert graph.prerequisites("databases") == ["sql"]
    assert {"html", "css"} <= graph.ancestors("react")
    assert len(graph.fingerprint()) == 16

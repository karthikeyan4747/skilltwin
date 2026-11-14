from backend.core.analysis import analyze_skills
from backend.core.career import better_fit, goal_switch, rank_roles, readiness
from backend.core.models import Evidence


def statuses_for(catalog, now, verified: list[str], claimed: list[str]):
    evidence = [
        Evidence(skill_id=s, type=t, score=1.0, timestamp=now)
        for s in verified
        for t in ("mcq", "code_exercise")
    ]
    return analyze_skills(catalog.graph, claimed, evidence, now)


def test_claimed_vs_proven(catalog, now) -> None:
    statuses = statuses_for(catalog, now, ["sql"], ["sql", "html", "python"])
    result = readiness(catalog.roles["full_stack_developer"], statuses)
    assert result.claimed_pct == 18.0
    assert result.proven_pct == 10.0


def test_better_fit_requires_ten_point_margin(catalog, now) -> None:
    statuses = statuses_for(catalog, now, ["python", "sql"], ["python", "sql"])
    ranking = rank_roles(list(catalog.roles.values()), statuses)
    assert ranking[0].role_id == "data_analyst"
    assert better_fit(ranking, "full_stack_developer").role_id == "data_analyst"
    assert better_fit(ranking, "data_analyst") is None


def test_no_better_fit_when_close(catalog, now) -> None:
    statuses = statuses_for(catalog, now, [], [])
    ranking = rank_roles(list(catalog.roles.values()), statuses)
    assert better_fit(ranking, "full_stack_developer") is None
    assert better_fit(ranking, "unknown") is None


def test_goal_switch_carries_over_verified_skills(catalog, now) -> None:
    statuses = statuses_for(catalog, now, ["python", "sql"], ["python", "sql"])
    switch = goal_switch("full_stack_developer", catalog.roles["data_analyst"], statuses)
    assert switch.carryover_pct == 65.0
    assert switch.reused == ["python", "sql"]
    assert switch.new_delta == ["pandas", "git"]

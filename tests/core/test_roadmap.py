from backend.core.analysis import analyze_skills
from backend.core.diagnosis import diagnose
from backend.core.models import Evidence, Roadmap, RoadmapStep
from backend.core.roadmap import (
    build_roadmap,
    carry_progress,
    completion_pct,
    measured_velocity,
    prioritize,
    remaining_hours,
    reroute,
    set_step_status,
    time_to_ready_weeks,
)


def plan_for(catalog, now, claimed=("python", "sql", "html")) -> tuple[Roadmap, dict]:
    statuses = analyze_skills(catalog.graph, list(claimed), [], now)
    role = catalog.roles["full_stack_developer"]
    return build_roadmap(catalog.graph, role, statuses), statuses


def test_roadmap_orders_gaps_topologically(catalog, now) -> None:
    plan, _ = plan_for(catalog, now)
    ids = [s.skill_id for s in plan.steps]
    assert ids.index("html") < ids.index("css") < ids.index("javascript") < ids.index("react")
    assert ids.index("javascript") < ids.index("nodejs") < ids.index("express")
    html = next(s for s in plan.steps if s.skill_id == "html")
    assert "Claimed but not yet proven" in html.reason and html.est_hours == 5.0


def test_verified_skills_are_not_gaps(catalog, now) -> None:
    evidence = [
        Evidence(skill_id="sql", type=t, score=1.0, timestamp=now) for t in ("mcq", "explain_back")
    ]
    statuses = analyze_skills(catalog.graph, ["sql"], evidence, now)
    plan = build_roadmap(catalog.graph, catalog.roles["full_stack_developer"], statuses)
    assert "sql" not in [s.skill_id for s in plan.steps]


def test_reroute_puts_root_cause_first_and_logs_event(catalog, now) -> None:
    plan, statuses = plan_for(catalog, now)
    plan = set_step_status(plan, "html", "done")
    found = diagnose(catalog.graph, "react", {s: v.confidence for s, v in statuses.items()})
    rerouted = reroute(plan, catalog.graph, found, now)
    assert [s.skill_id for s in rerouted.steps[:4]] == ["html", "css", "javascript", "react"]
    assert rerouted.steps[0].status == "todo"
    assert rerouted.reroutes[-1].root_cause == "html"
    assert rerouted.reroutes[-1].inserted == []


def test_reroute_inserts_missing_steps(catalog, now) -> None:
    plan = Roadmap(role_id="full_stack_developer", steps=[])
    found = diagnose(catalog.graph, "css", {})
    rerouted = reroute(plan, catalog.graph, found, now)
    assert rerouted.reroutes[-1].inserted == ["html", "css"]


def test_status_completion_and_time_to_ready(catalog, now) -> None:
    plan = Roadmap(
        role_id="r",
        steps=[
            RoadmapStep(skill_id="a", reason="", est_hours=10),
            RoadmapStep(skill_id="b", reason="", est_hours=10),
        ],
    )
    assert measured_velocity(plan) == 1.0
    assert time_to_ready_weeks(plan, hours_per_week=5) == 4.0
    plan = set_step_status(plan, "a", "done", actual_hours=5)
    assert completion_pct(plan) == 50.0
    assert remaining_hours(plan) == 10
    assert measured_velocity(plan) == 2.0
    assert time_to_ready_weeks(plan, hours_per_week=5) == 1.0


def test_empty_roadmap_is_complete() -> None:
    assert completion_pct(Roadmap(role_id="r")) == 100.0


def test_unknown_step_raises() -> None:
    try:
        set_step_status(Roadmap(role_id="r"), "x", "done")
    except KeyError:
        return
    raise AssertionError("expected KeyError")


def test_carry_progress_and_prioritize(catalog, now) -> None:
    plan, _ = plan_for(catalog, now)
    old = set_step_status(plan, "css", "done")
    merged = carry_progress(plan, old)
    assert next(s for s in merged.steps if s.skill_id == "css").status == "done"
    moved = prioritize(merged, ["react", "unknown"], now, "mentor", "note")
    assert moved.steps[0].skill_id == "react"
    assert moved.reroutes[-1].trigger == "mentor"
    assert prioritize(merged, ["unknown"], now, "mentor", "") is merged

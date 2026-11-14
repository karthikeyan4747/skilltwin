"""Sample scenario: Python, SQL, basic HTML -> Full Stack Developer."""

from backend.core.analysis import analyze_skills
from backend.orchestrator import Answer


async def test_full_stack_gaps_ordering_and_reroute(orchestrator, sample_learner, now) -> None:
    learner, _ = await orchestrator.onboard(sample_learner)
    order = [s.skill_id for s in learner.roadmap.steps]
    assert {"javascript", "react", "nodejs"} <= set(order)
    assert order.index("javascript") < order.index("react")
    assert order.index("javascript") < order.index("nodejs")
    assert "python" not in order and "sql" not in order

    statuses = analyze_skills(
        orchestrator.catalog.graph, learner.profile.claimed_skills, learner.evidence, now
    )
    assert statuses["python"].verified and statuses["sql"].verified
    assert statuses["html"].claimed and not statuses["html"].verified

    pending, _ = await orchestrator.next_question(learner, "react", "mcq")
    wrong = (pending.question.answer_index + 1) % len(pending.question.options)
    learner, result = await orchestrator.submit_answer(learner, pending, Answer(choice=wrong))
    assert result.diagnosis.path == ["html", "css", "javascript", "react"]
    assert [s.skill_id for s in learner.roadmap.steps[:4]] == result.diagnosis.path

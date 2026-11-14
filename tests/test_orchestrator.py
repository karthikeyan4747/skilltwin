from backend.core.models import Learner
from backend.orchestrator import Answer, Orchestrator


async def onboarded(orchestrator: Orchestrator, learner: Learner) -> Learner:
    learner, result = await orchestrator.onboard(learner)
    assert {s.agent for s in result.agent_trace} == {"Career", "Recommender"}
    assert result.offline_ai
    return learner


async def test_onboard_builds_explained_roadmap(orchestrator, sample_learner) -> None:
    learner = await onboarded(orchestrator, sample_learner)
    assert learner.roadmap.steps
    assert all(s.resource_reason for s in learner.roadmap.steps)


async def test_poor_performance_reroutes_roadmap(orchestrator, sample_learner) -> None:
    learner = await onboarded(orchestrator, sample_learner)
    pending, question = await orchestrator.next_question(learner, "javascript", "mcq")
    assert question.question.options and "answer_index" not in question.question.model_dump()
    learner, result = await orchestrator.submit_answer(learner, pending, Answer(choice=0))
    assert not result.correct
    assert result.misconception == "Assumes typeof reports null as its own type"
    assert result.diagnosis is not None and result.diagnosis.root_cause == "html"
    assert learner.roadmap.steps[0].skill_id == "html"
    assert learner.roadmap.reroutes[-1].trigger == "failed_assessment"
    agents = [s.agent for s in result.agent_trace]
    assert agents[:2] == ["Observer", "Diagnostic"]
    assert result.twin.prediction_matched and result.twin.accuracy == 1.0


async def test_correct_answer_adds_evidence_without_reroute(orchestrator, sample_learner) -> None:
    learner = await onboarded(orchestrator, sample_learner)
    pending, _ = await orchestrator.next_question(learner, "python", "predict_output")
    text = pending.question.expected_output
    updated, result = await orchestrator.submit_answer(learner, pending, Answer(text=text))
    assert result.correct and result.diagnosis is None and result.misconception is None
    assert len(updated.evidence) == len(learner.evidence) + 1
    assert updated.roadmap.reroutes == learner.roadmap.reroutes


async def test_explain_back_scores_concepts_and_fluency_separately(
    orchestrator, sample_learner
) -> None:
    pending, _ = await orchestrator.next_question(sample_learner, "sql", "explain_back")
    answer = Answer(text="matching rows; all rows of the left table, null when no match")
    _, result = await orchestrator.submit_answer(sample_learner, pending, answer)
    assert result.score == 1.0 and result.fluency_score is not None and result.fluency_score < 1
    assert [s.agent for s in result.agent_trace] == ["Assessor"]


async def test_code_exercise_uses_bank_and_client_test_counts(orchestrator, sample_learner) -> None:
    pending, question = await orchestrator.next_question(sample_learner, "python", "code_exercise")
    assert question.question.tests and question.agent_trace[0].agent == "Learner Twin"
    _, result = await orchestrator.submit_answer(
        sample_learner, pending, Answer(tests_passed=3, tests_total=3)
    )
    assert result.correct and result.evidence_type == "code_exercise"


async def test_question_types_rotate(orchestrator, sample_learner) -> None:
    learner = sample_learner
    seen = []
    for _ in range(3):
        pending, q = await orchestrator.next_question(learner, "css")
        seen.append(q.question.type)
        learner, _ = await orchestrator.submit_answer(learner, pending, Answer(text="x", choice=0))
    assert seen == ["mcq", "explain_back", "predict_output"]


async def test_goal_change_carries_over_and_rebuilds(orchestrator, sample_learner) -> None:
    learner = await onboarded(orchestrator, sample_learner)
    updated, result = await orchestrator.change_goal(learner, "data_analyst")
    assert updated.profile.career_goal == "data_analyst"
    assert result.switch.carryover_pct == 65.0
    assert [s.skill_id for s in updated.roadmap.steps] == ["git", "pandas"]
    assert updated.roadmap.reroutes[-1].trigger == "goal_change"


async def test_twin_interview_batch(orchestrator, sample_learner) -> None:
    updated, result = await orchestrator.twin_interview(sample_learner, "full_stack_developer", 10)
    assert len(result.batch.results) == 10
    assert "javascript" in result.batch.weak_areas
    assert len(result.batch.plan) == len(result.batch.weak_areas)
    assert updated.latest_interview == result.batch
    assert {s.agent for s in result.agent_trace} == {"Interviewer", "Learner Twin", "Assessor"}


async def test_mentor_applies_suggested_focus(orchestrator, sample_learner) -> None:
    learner = await onboarded(orchestrator, sample_learner)
    updated, result = await orchestrator.mentor_chat(learner, "Can I start React now?")
    assert result.applied_focus == ["react"]
    assert updated.roadmap.steps[0].skill_id == "react"
    _, quiet = await orchestrator.mentor_chat(learner, "hello")
    assert quiet.applied_focus == []


async def test_publish_uses_only_real_evidence(orchestrator, sample_learner) -> None:
    result = await orchestrator.publish_draft(sample_learner)
    assert "Python, SQL" in result.linkedin_post
    assert "## Verified skills" in result.learning_log_md

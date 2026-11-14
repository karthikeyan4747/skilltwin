"""Sample scenario: both adaptation loops end to end, on a fresh sample learner.

Python, SQL and basic HTML -> Full Stack Developer. The learner answers a React question
wrongly (poor performance -> root-cause reroute), then switches to the best-fit role
(goal change -> carryover and a rebuilt roadmap).
"""

from backend.core import career
from backend.core.models import Learner
from backend.orchestrator.assessment import Answer, AssessmentFlows
from backend.orchestrator.planning import PlanningFlows
from backend.orchestrator.questions import QuestionFlows
from backend.results import SampleScenarioResult, ScenarioStage

FAILED_SKILL = "react"
FALLBACK_ROLE = "backend_developer"


class ScenarioFlows(PlanningFlows, QuestionFlows, AssessmentFlows):
    async def sample_scenario(self, learner: Learner) -> tuple[Learner, SampleScenarioResult]:
        """Onboard, fail a React question on purpose, then switch to the best-fit role."""
        learner, onboard = await self.onboard(learner)
        ctx = self.context(learner)
        target = career.readiness(ctx.role, ctx.statuses)
        onboarded = ScenarioStage(
            title=f"1. Onboarded for {ctx.role.title}",
            summary=(
                f"Claimed {target.claimed_pct:.0f}% vs proven {target.proven_pct:.0f}%. "
                f"Roadmap: {', '.join(ctx.names([s.skill_id for s in learner.roadmap.steps]))}."
            ),
            agent_trace=onboard.agent_trace,
        )

        pending, question = await self.next_question(learner, FAILED_SKILL, "mcq")
        key = pending.question.answer_index or 0
        wrong = Answer(choice=(key + 1) % len(pending.question.options))
        learner, answer = await self.submit_answer(learner, pending, wrong)
        path = answer.diagnosis.path_names if answer.diagnosis else []
        failed = ScenarioStage(
            title="2. Answered a React question wrongly (poor performance)",
            summary=(
                f"Root cause found along {' → '.join(path)}; the roadmap now starts with "
                f"{path[0] if path else 'React'}. Misconception: {answer.misconception or 'none'}."
            ),
            agent_trace=question.agent_trace + answer.agent_trace,
        )

        ctx = self.context(learner)
        role_id = ctx.better_fit.role_id if ctx.better_fit else FALLBACK_ROLE
        learner, goal = await self.change_goal(learner, role_id)
        switched = ScenarioStage(
            title=f"3. Switched goal to {self.catalog.roles[role_id].title} (goal change)",
            summary=(
                f"{goal.switch.carryover_pct:.0f}% carried over from verified skills; "
                f"new roadmap: {', '.join(ctx.names([s.skill_id for s in goal.roadmap_steps]))}."
            ),
            agent_trace=goal.agent_trace,
        )

        stages = [onboarded, failed, switched]
        return learner, SampleScenarioResult(
            stages=stages,
            answer=answer,
            goal=goal,
            agent_trace=[step for stage in stages for step in stage.agent_trace],
            offline_ai=onboard.offline_ai or answer.offline_ai or goal.offline_ai,
        )

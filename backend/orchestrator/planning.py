"""Planning flows: onboarding and career-goal change (adaptation trigger: goal change)."""

import asyncio

from backend.agents.base import AgentTrace
from backend.core import career, roadmap
from backend.core.models import Learner, RerouteEvent
from backend.orchestrator.base import OrchestratorBase
from backend.results import GoalChangeResult, OnboardResult


class PlanningFlows(OrchestratorBase):
    async def onboard(self, learner: Learner) -> tuple[Learner, OnboardResult]:
        """Career ranks roles; core builds the gap roadmap; Recommender explains resources."""
        trace = AgentTrace()
        ctx = self.context(learner)
        fresh = roadmap.build_roadmap(self.catalog.graph, ctx.role, ctx.statuses)
        plan = roadmap.carry_progress(fresh, learner.roadmap)
        career_out, plan = await asyncio.gather(
            self.agents.career.run(ctx.career_input(), trace),
            self.attach_reasons(plan, ctx, trace),
        )
        return learner.model_copy(update={"roadmap": plan}), OnboardResult(
            summary=career_out.summary,
            better_fit_reason=career_out.better_fit_reason,
            ranking=ctx.ranking,
            agent_trace=trace.steps,
            offline_ai=trace.offline,
        )

    async def change_goal(self, learner: Learner, role_id: str) -> tuple[Learner, GoalChangeResult]:
        """Reuse verified skills, rebuild the roadmap for the new delta only, re-recommend."""
        trace = AgentTrace()
        ctx = self.context(learner)
        new_role = self.catalog.roles[role_id]
        switch = career.goal_switch(ctx.role.id, new_role, ctx.statuses)
        plan = roadmap.build_roadmap(self.catalog.graph, new_role, ctx.statuses)
        plan = roadmap.log_event(
            plan.model_copy(update={"reroutes": learner.roadmap.reroutes}),
            RerouteEvent(
                timestamp=ctx.now,
                trigger="goal_change",
                path=[s.skill_id for s in plan.steps],
                note=(
                    f"Goal changed from {ctx.role.title} to {new_role.title}: "
                    f"{switch.carryover_pct:.0f}% carried over from verified skills."
                ),
            ),
        )
        profile = learner.profile.model_copy(update={"career_goal": role_id})
        switched = learner.model_copy(update={"profile": profile, "roadmap": plan})
        new_ctx = self.context(switched)
        career_out, plan = await asyncio.gather(
            self.agents.career.run(new_ctx.career_input(), trace),
            self.attach_reasons(plan, new_ctx, trace),
        )
        switched = switched.model_copy(update={"roadmap": plan})
        return switched, GoalChangeResult(
            switch=switch,
            summary=career_out.summary,
            roadmap_steps=plan.steps,
            agent_trace=trace.steps,
            offline_ai=trace.offline,
        )

"""Coaching flows: Twin interview batch, AI Mentor chat and Learn-in-Public drafting."""

import asyncio
from collections import defaultdict
from itertools import cycle, islice

from backend.agents.assessor import GraderIn
from backend.agents.base import AgentTrace
from backend.agents.interviewer import InterviewerIn, Ticket, TicketExample
from backend.core import roadmap
from backend.core.models import InterviewBatch, InterviewTicketResult, Learner
from backend.orchestrator.base import OrchestratorBase
from backend.orchestrator.context import LearnerContext
from backend.results import InterviewResult, MentorResult, PublishResult

INTERVIEW_CONCURRENCY = 4
INTERVIEW_WEAK_SCORE = 0.6


class CoachingFlows(OrchestratorBase):
    async def twin_interview(
        self, learner: Learner, role_id: str, count: int = 10
    ) -> tuple[Learner, InterviewResult]:
        """Interviewer writes tickets; the Twin answers as the learner; Assessor grades."""
        trace = AgentTrace()
        ctx = self.context(learner)
        role = self.catalog.roles[role_id]
        examples = [
            TicketExample(
                skill_id=q.skill_id,
                skill_name=ctx.name(q.skill_id),
                weight=role.skills[q.skill_id],
                prompt=q.prompt,
                rubric=q.rubric,
            )
            for q in self.catalog.questions
            if q.type == "interview" and q.skill_id in role.skills
        ]
        written = await self.agents.interviewer.run(
            InterviewerIn(role_title=role.title, count=count, examples=examples), trace
        )
        tickets = [t for t in written.tickets if t.skill_id in role.skills][:count]
        tickets += [  # top up from the bank if the model returned fewer tickets than asked
            Ticket(
                skill_id=e.skill_id,
                title=f"{e.skill_name} ticket",
                prompt=e.prompt,
                rubric=e.rubric,
            )
            for e in islice(cycle(examples), count - len(tickets))
        ]
        gate = asyncio.Semaphore(INTERVIEW_CONCURRENCY)
        results = await asyncio.gather(
            *(self._simulate(ctx, ticket, gate, trace) for ticket in tickets)
        )
        by_skill: dict[str, list[float]] = defaultdict(list)
        for r in results:
            by_skill[r.skill_id].append(r.predicted_score)
        weak = self.catalog.graph.topological(
            sid
            for sid, scores in by_skill.items()
            if sum(scores) / len(scores) < INTERVIEW_WEAK_SCORE
        )
        plan = [
            f"Practise {ctx.name(sid)} (now {ctx.statuses[sid].confidence:.0%} confidence): "
            "do its roadmap tutorial, then retake an assessment."
            for sid in weak
        ]
        batch = InterviewBatch(
            role_id=role_id, timestamp=ctx.now, results=list(results), weak_areas=weak, plan=plan
        )
        updated = learner.model_copy(update={"latest_interview": batch})
        named = {r.skill_id for r in batch.results} | set(weak)
        return updated, InterviewResult(
            batch=batch,
            skill_names={sid: ctx.name(sid) for sid in named},
            agent_trace=trace.steps,
            offline_ai=trace.offline,
        )

    async def _simulate(
        self, ctx: LearnerContext, ticket: Ticket, gate: asyncio.Semaphore, trace: AgentTrace
    ) -> InterviewTicketResult:
        async with gate:
            answer = await self.agents.twin_responder.run(
                ctx.twin_respond_input(ticket.skill_id, ticket.prompt, ticket.rubric), trace
            )
            graded = await self.agents.grader.run(
                GraderIn(
                    skill_name=ctx.name(ticket.skill_id),
                    question=ticket.prompt,
                    rubric=ticket.rubric,
                    answer=answer.answer,
                ),
                trace,
            )
        return InterviewTicketResult(
            skill_id=ticket.skill_id, title=ticket.title, predicted_score=graded.conceptual_score
        )

    async def mentor_chat(
        self, learner: Learner, message: str, screenshot_b64: str | None = None
    ) -> tuple[Learner, MentorResult]:
        """Mentor answers from learner state; suggested focus is applied by core."""
        trace = AgentTrace()
        ctx = self.context(learner)
        out = await self.agents.mentor.run(ctx.mentor_input(message, screenshot_b64), trace)
        plan = roadmap.prioritize(
            learner.roadmap,
            out.suggested_focus,
            ctx.now,
            trigger="mentor",
            note="AI Mentor moved these steps to the front at your request.",
        )
        applied = plan.reroutes[-1].path if plan is not learner.roadmap else []
        return learner.model_copy(update={"roadmap": plan}), MentorResult(
            reply=out.reply,
            applied_focus=applied,
            applied_focus_names=ctx.names(applied),
            agent_trace=trace.steps,
            offline_ai=trace.offline,
        )

    async def publish_draft(self, learner: Learner) -> PublishResult:
        """Publisher drafts a LinkedIn post and learning log from real evidence only."""
        trace = AgentTrace()
        out = await self.agents.publisher.run(self.context(learner).publisher_input(), trace)
        return PublishResult(
            linkedin_post=out.linkedin_post,
            learning_log_md=out.learning_log_md,
            agent_trace=trace.steps,
            offline_ai=trace.offline,
        )

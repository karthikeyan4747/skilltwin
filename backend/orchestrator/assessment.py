"""Assessment flow: grading an answer, with reroute on failure.

Adaptation trigger: poor performance. A failed answer walks the prerequisite graph to a
root cause and reroutes the roadmap so the root cause is learned first.
"""

import asyncio
from dataclasses import dataclass

from backend.agents.assessor import GraderIn
from backend.agents.base import AgentTrace
from backend.agents.diagnostic import DiagnosticIn
from backend.agents.observer import ObserverIn
from backend.core import analysis, grading, progress, roadmap
from backend.core.diagnosis import diagnose
from backend.core.models import Learner, Question
from backend.core.twin import twin_accuracy
from backend.orchestrator.base import OrchestratorBase
from backend.orchestrator.context import LearnerContext
from backend.results import AnswerResult, DiagnosisReveal, TwinReveal
from backend.services.repository import PendingQuestion


@dataclass(frozen=True)
class Answer:
    """A learner's submission; the field used depends on the question type."""

    text: str = ""
    choice: int | None = None
    tests_passed: int = 0
    tests_total: int = 0


@dataclass(frozen=True)
class Graded:
    score: float
    given: str
    fluency: float | None = None
    feedback: str = ""
    missed: tuple[str, ...] = ()


class AssessmentFlows(OrchestratorBase):
    async def _grade(
        self, ctx: LearnerContext, question: Question, answer: Answer, trace: AgentTrace
    ) -> Graded:
        if question.type == "mcq":
            choice = answer.choice
            valid = choice is not None and 0 <= choice < len(question.options)
            given = question.options[choice] if valid and choice is not None else ""
            return Graded(grading.grade_mcq(question, choice), given)
        if question.type == "predict_output":
            return Graded(grading.grade_predict_output(question, answer.text), answer.text)
        if question.type == "code_exercise":
            score = grading.grade_code_exercise(answer.tests_passed, answer.tests_total)
            return Graded(score, f"{answer.tests_passed}/{answer.tests_total} tests passed")
        out = await self.agents.grader.run(
            GraderIn(
                skill_name=ctx.name(question.skill_id),
                question=question.prompt,
                rubric=question.rubric,
                answer=answer.text,
            ),
            trace,
        )
        return Graded(
            out.conceptual_score,
            answer.text,
            out.fluency_score,
            out.feedback,
            tuple(out.missed_points),
        )

    async def submit_answer(
        self, learner: Learner, pending: PendingQuestion, answer: Answer
    ) -> tuple[Learner, AnswerResult]:
        """Grade -> evidence; Observer names the misconception; Twin accuracy updates; reroute."""
        trace = AgentTrace()
        question = pending.question
        ctx = self.context(learner)
        graded = await self._grade(ctx, question, answer, trace)
        correct = graded.score >= analysis.PASS_SCORE
        misconception = None
        if graded.score < 1:
            key = graded.given if question.type == "mcq" else grading.normalize_output(graded.given)
            observed = await self.agents.observer.run(
                ObserverIn(
                    skill_name=ctx.name(question.skill_id),
                    question=question.prompt,
                    learner_answer=graded.given,
                    correct_answer=grading.correct_answer_text(question),
                    score=graded.score,
                    missed_points=list(graded.missed),
                    known_distractor_misconception=grading.wrong_answer_misconceptions(
                        question
                    ).get(key),
                ),
                trace,
            )
            misconception = observed.misconception
        outcome = progress.Outcome(
            score=graded.score,
            predicted_correct=pending.prediction.predicted_correct,
            misconception=misconception,
        )
        updated = progress.record_outcome(learner, self.catalog.graph, question, outcome, ctx.now)
        diagnosis = None
        if not correct:
            updated, diagnosis = await self._reroute(
                updated, question.skill_id, misconception, trace
            )
        after = self.context(updated).statuses[question.skill_id]
        return updated, AnswerResult(
            correct=correct,
            score=graded.score,
            fluency_score=graded.fluency,
            feedback=graded.feedback or ("Correct!" if correct else "Not quite."),
            correct_answer=grading.correct_answer_text(question),
            evidence_type=question.type,
            confidence_before=pending.confidence_before,
            confidence_after=after.confidence,
            verified=after.verified,
            misconception=misconception,
            twin=TwinReveal(
                **pending.prediction.model_dump(),
                prediction_matched=pending.prediction.predicted_correct == correct,
                accuracy=twin_accuracy(updated.twin_history),
            ),
            diagnosis=diagnosis,
            agent_trace=trace.steps,
            offline_ai=trace.offline,
        )

    async def _reroute(
        self, learner: Learner, skill_id: str, misconception: str | None, trace: AgentTrace
    ) -> tuple[Learner, DiagnosisReveal]:
        ctx = self.context(learner)
        found = diagnose(self.catalog.graph, skill_id, analysis.confidences(ctx.statuses))
        plan = roadmap.reroute(learner.roadmap, self.catalog.graph, found, ctx.now)
        explained, plan = await asyncio.gather(
            self.agents.diagnostic.run(
                DiagnosticIn(
                    failed_skill=ctx.name(skill_id),
                    root_cause=ctx.name(found.root_cause),
                    path=ctx.names(found.path),
                    confidences={ctx.name(s): ctx.statuses[s].confidence for s in found.path},
                    misconception=misconception,
                ),
                trace,
            ),
            self.attach_reasons(plan, ctx, trace, only=set(plan.reroutes[-1].inserted)),
        )
        return learner.model_copy(update={"roadmap": plan}), DiagnosisReveal(
            root_cause=found.root_cause,
            path=found.path,
            path_names=ctx.names(found.path),
            explanation=explained.explanation,
            first_action=explained.first_action,
            inserted_steps=ctx.names(plan.reroutes[-1].inserted),
        )

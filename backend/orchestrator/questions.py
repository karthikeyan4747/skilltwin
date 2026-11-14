"""Question flow: the Assessor writes a question and the Learner Twin predicts the answer.

The prediction is stored server-side with the answer key and revealed only after submission.
"""

import uuid

from backend.agents.assessor import QuestionWriterIn
from backend.agents.base import AgentTrace
from backend.core import grading
from backend.core.models import Learner, Question, QuestionType
from backend.orchestrator.base import OrchestratorBase
from backend.orchestrator.context import LearnerContext
from backend.results import PublicQuestion, QuestionResult
from backend.services.repository import PendingQuestion, TwinPrediction


class QuestionFlows(OrchestratorBase):
    async def next_question(
        self, learner: Learner, skill_id: str, requested: QuestionType | None = None
    ) -> tuple[PendingQuestion, QuestionResult]:
        """Assessor writes a question (types rotate); the Twin predicts the learner's answer."""
        trace = AgentTrace()
        ctx = self.context(learner)
        bank = self.catalog.questions_for(skill_id)
        available = sorted({q.type for q in bank}, key=grading.TYPE_ROTATION.index)
        qtype = requested if requested in available else None
        qtype = qtype or grading.next_type(skill_id, available, learner.assessments)
        confidence = ctx.statuses[skill_id].confidence
        difficulty = grading.difficulty_for(confidence)
        examples = [q for q in bank if q.type == qtype]
        seen = sum(1 for a in learner.assessments if a.skill_id == skill_id and a.type == qtype)
        question = await self._write_question(
            ctx, examples[seen % len(examples)], difficulty, trace
        )
        prediction = await self.agents.twin_predictor.run(ctx.twin_input(question), trace)
        pending = PendingQuestion(
            question=question,
            prediction=TwinPrediction(**prediction.model_dump()),
            confidence_before=confidence,
        )
        public = PublicQuestion(
            id=question.id,
            skill_id=skill_id,
            skill_name=ctx.name(skill_id),
            type=question.type,
            difficulty=difficulty,
            prompt=question.prompt,
            options=question.options,
            code=question.code,
            tests=question.tests,
        )
        return pending, QuestionResult(
            question=public, agent_trace=trace.steps, offline_ai=trace.offline
        )

    async def _write_question(
        self, ctx: LearnerContext, example: Question, difficulty: str, trace: AgentTrace
    ) -> Question:
        """Code exercises come from the trusted bank; other types are AI-written and cached."""
        new_id = uuid.uuid4().hex
        if example.type == "code_exercise":
            return example.model_copy(update={"id": new_id})
        key = (example.id, difficulty)
        written = self.question_cache.get(key)
        if written is None:
            written = await self.agents.question_writer.run(
                QuestionWriterIn(
                    skill_name=ctx.name(example.skill_id),
                    type=example.type,
                    difficulty=difficulty,
                    known_misconceptions=ctx.misconceptions_for(example.skill_id),
                    example=example,
                ),
                trace,
            )
            self.question_cache.set(key, written)
        return Question(
            id=new_id, skill_id=example.skill_id, type=example.type, **written.model_dump()
        )

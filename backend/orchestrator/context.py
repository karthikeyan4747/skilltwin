"""LearnerContext: a read-only snapshot of derived learner state used to brief agents."""

from datetime import datetime

from backend.agents.career import CareerIn, RoleScore
from backend.agents.mentor import MentorIn
from backend.agents.publisher import PublisherIn
from backend.agents.twin import TwinPredictIn, TwinRespondIn
from backend.core import analysis, career, grading
from backend.core.career import Readiness
from backend.core.models import Learner, Question, SkillStatus
from backend.core.progress import misconceptions_overcome
from backend.services.catalog import Catalog

RECENT_LIMIT = 5


class LearnerContext:
    def __init__(
        self,
        catalog: Catalog,
        learner: Learner,
        now: datetime,
        statuses: dict[str, SkillStatus],
        ranking: list[Readiness],
    ) -> None:
        self.catalog = catalog
        self.learner = learner
        self.now = now
        self.statuses = statuses
        self.ranking = ranking
        self.role = catalog.roles[learner.profile.career_goal]
        self.strengths, self.weaknesses = analysis.strengths_and_weaknesses(self.statuses)
        self.better_fit = career.better_fit(ranking, self.role.id)

    def name(self, skill_id: str) -> str:
        """Display name of a skill."""
        return self.catalog.graph.name(skill_id)

    def names(self, skill_ids: list[str]) -> list[str]:
        """Display names for skill ids, order preserved."""
        return [self.name(s) for s in skill_ids]

    def misconceptions_for(self, skill_id: str) -> list[str]:
        """Distinct misconceptions recorded for a skill, oldest first."""
        texts = [m.text for m in self.learner.misconceptions if m.skill_id == skill_id]
        return list(dict.fromkeys(texts))

    def recent_scores(self, skill_id: str) -> list[float]:
        """Most recent evidence scores for a skill."""
        scores = [e.score for e in self.learner.evidence if e.skill_id == skill_id]
        return scores[-RECENT_LIMIT:]

    def next_step_names(self, limit: int = 3) -> list[str]:
        """Names of the next unfinished roadmap steps."""
        open_steps = [s.skill_id for s in self.learner.roadmap.steps if s.status != "done"]
        return self.names(open_steps[:limit])

    def career_input(self) -> CareerIn:
        """Brief for the Career agent: ranking, better fit and verified skills."""
        return CareerIn(
            target_role=self.role.title,
            ranking=[
                RoleScore(title=r.title, claimed_pct=r.claimed_pct, proven_pct=r.proven_pct)
                for r in self.ranking
            ],
            better_fit=self.better_fit.title if self.better_fit else None,
            verified_skills=self.names(self.strengths),
        )

    def twin_input(self, question: Question) -> TwinPredictIn:
        """Brief for the Twin: question, answer key, wrong answers and learner history."""
        return TwinPredictIn(
            skill_name=self.name(question.skill_id),
            question=question.prompt,
            options=question.options,
            correct_answer=grading.correct_answer_text(question),
            wrong_answers=grading.wrong_answer_misconceptions(question),
            confidence=self.statuses[question.skill_id].confidence,
            misconceptions=self.misconceptions_for(question.skill_id),
            recent_scores=self.recent_scores(question.skill_id),
        )

    def twin_respond_input(self, skill_id: str, ticket: str, rubric: list[str]) -> TwinRespondIn:
        """Brief for the Twin to answer a work ticket at the learner's level."""
        return TwinRespondIn(
            skill_name=self.name(skill_id),
            ticket=ticket,
            rubric=rubric,
            confidence=self.statuses[skill_id].confidence,
            misconceptions=self.misconceptions_for(skill_id),
        )

    def mentor_input(self, message: str, screenshot_b64: str | None) -> MentorIn:
        """Brief for the Mentor: roadmap, strengths, weaknesses and recent results."""
        recent = [
            f"{self.name(a.skill_id)} {a.type}: {'passed' if a.correct else 'failed'}"
            for a in self.learner.assessments[-RECENT_LIMIT:]
        ]
        return MentorIn(
            message=message,
            learner_name=self.learner.profile.name,
            role_title=self.role.title,
            next_steps=self.next_step_names(),
            roadmap_skills={
                s.skill_id: self.name(s.skill_id)
                for s in self.learner.roadmap.steps
                if s.status != "done"
            },
            strengths=self.names(self.strengths),
            weaknesses=self.names(self.weaknesses),
            recent_results=recent,
            misconceptions=[m.text for m in self.learner.misconceptions[-RECENT_LIMIT:]],
            screenshot_jpeg_b64=screenshot_b64,
        )

    def publisher_input(self) -> PublisherIn:
        """Brief for the Publisher built only from recorded evidence."""
        proven = career.readiness(self.role, self.statuses).proven_pct
        done = [s.skill_id for s in self.learner.roadmap.steps if s.status == "done"]
        return PublisherIn(
            learner_name=self.learner.profile.name,
            role_title=self.role.title,
            proven_pct=proven,
            verified_skills=self.names(self.strengths),
            evidence_count=len(self.learner.evidence),
            completed_steps=self.names(done),
            next_steps=self.next_step_names(),
            misconceptions_overcome=misconceptions_overcome(self.learner),
        )

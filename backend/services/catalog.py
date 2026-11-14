"""Loads the static catalog (skills, roles, resources, questions, lessons, seed) from data/."""

import json
from dataclasses import dataclass
from datetime import datetime, timedelta
from functools import lru_cache
from pathlib import Path
from typing import Any

from backend.core.grid import GridLevel
from backend.core.models import Evidence, Learner, Profile, Question, Resource, Roadmap, Role, Skill
from backend.core.progress import confidence_trail
from backend.core.skill_graph import SkillGraph

DATA_DIR = Path(__file__).resolve().parent.parent / "data"


@dataclass(frozen=True)
class Catalog:
    graph: SkillGraph
    roles: dict[str, Role]
    resources: dict[str, list[Resource]]
    questions: list[Question]
    snippets: list[dict[str, str]]
    grid_levels: dict[str, GridLevel]
    seed: dict[str, Any]

    def questions_for(self, skill_id: str) -> list[Question]:
        """Bank questions for a skill."""
        return [q for q in self.questions if q.skill_id == skill_id]

    def seed_profile(self) -> Profile:
        """Profile of the sample-scenario learner."""
        return Profile.model_validate(self.seed["sample_learner"]["profile"])

    def seed_evidence(self, now: datetime) -> list[Evidence]:
        """Seeded evidence with timestamps relative to `now`."""
        return [
            Evidence(
                skill_id=item["skill_id"],
                type=item["type"],
                score=item["score"],
                timestamp=now - timedelta(days=item["days_ago"]),
            )
            for item in self.seed["sample_learner"]["evidence"]
        ]

    def sample_learner(self, now: datetime) -> Learner:
        """A fresh copy of the sample-scenario learner (Python, SQL, basic HTML -> Full Stack)."""
        profile = self.seed_profile()
        evidence = self.seed_evidence(now)
        return Learner(
            profile=profile,
            evidence=evidence,
            roadmap=Roadmap(role_id=profile.career_goal),
            confidence_history=confidence_trail(self.graph, profile.claimed_skills, evidence),
        )

    def cohort_records(self) -> list[tuple[str, str, str]]:
        """Anonymised (learner, skill, misconception) records for the seeded cohort."""
        return [
            (member["learner"], m["skill_id"], m["text"])
            for member in self.seed["cohort"]
            for m in member["misconceptions"]
        ]


def _read(name: str) -> Any:
    return json.loads((DATA_DIR / name).read_text(encoding="utf-8"))


@lru_cache(maxsize=1)
def load_catalog() -> Catalog:
    """Load and validate every data file once per process."""
    graph = SkillGraph(Skill.model_validate(s) for s in _read("skills.json"))
    roles = {r["id"]: Role.model_validate(r) for r in _read("roles.json")}
    for role in roles.values():
        unknown = [sid for sid in role.skills if sid not in graph]
        if unknown:
            raise ValueError(f"role {role.id} references unknown skills {unknown}")
    resources = {
        sid: [Resource.model_validate(r) for r in items]
        for sid, items in _read("resources.json").items()
    }
    lessons = _read("lessons.json")
    return Catalog(
        graph=graph,
        roles=roles,
        resources=resources,
        questions=[Question.model_validate(q) for q in _read("questions.json")],
        snippets=lessons["snippets"],
        grid_levels={g["id"]: GridLevel.model_validate(g) for g in lessons["grid_levels"]},
        seed=_read("seed_learners.json"),
    )

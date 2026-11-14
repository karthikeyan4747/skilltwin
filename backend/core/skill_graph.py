"""Skill prerequisite graph (a validated DAG) with O(V+E) traversals."""

import hashlib
import json
from collections import deque
from collections.abc import Iterable

from backend.core.models import Skill


class SkillGraphError(ValueError):
    """Raised when the skill catalog is not a valid prerequisite DAG."""


class SkillGraph:
    def __init__(self, skills: Iterable[Skill]) -> None:
        self.skills: dict[str, Skill] = {}
        for skill in skills:
            if skill.id in self.skills:
                raise SkillGraphError(f"duplicate skill id: {skill.id}")
            self.skills[skill.id] = skill
        for skill in self.skills.values():
            for prereq in skill.prerequisites:
                if prereq not in self.skills:
                    raise SkillGraphError(f"{skill.id} requires unknown skill {prereq}")
        self._order = self._topological_sort()
        self._rank = {skill_id: i for i, skill_id in enumerate(self._order)}

    def _topological_sort(self) -> list[str]:
        """Kahn's algorithm; raises SkillGraphError if a cycle exists."""
        indegree = {sid: len(s.prerequisites) for sid, s in self.skills.items()}
        dependents: dict[str, list[str]] = {sid: [] for sid in self.skills}
        for skill in self.skills.values():
            for prereq in skill.prerequisites:
                dependents[prereq].append(skill.id)
        queue = deque(sid for sid in self.skills if indegree[sid] == 0)
        order: list[str] = []
        while queue:
            current = queue.popleft()
            order.append(current)
            for nxt in dependents[current]:
                indegree[nxt] -= 1
                if indegree[nxt] == 0:
                    queue.append(nxt)
        if len(order) != len(self.skills):
            raise SkillGraphError("skill graph contains a cycle")
        return order

    def __contains__(self, skill_id: object) -> bool:
        return skill_id in self.skills

    def name(self, skill_id: str) -> str:
        return self.skills[skill_id].name

    def prerequisites(self, skill_id: str) -> list[str]:
        return list(self.skills[skill_id].prerequisites)

    def ancestors(self, skill_id: str) -> set[str]:
        """All direct and transitive prerequisites of a skill."""
        seen: set[str] = set()
        stack = list(self.skills[skill_id].prerequisites)
        while stack:
            current = stack.pop()
            if current not in seen:
                seen.add(current)
                stack.extend(self.skills[current].prerequisites)
        return seen

    def topological(self, skill_ids: Iterable[str]) -> list[str]:
        """Order a subset of skills so prerequisites come first (stable, deterministic)."""
        return sorted(set(skill_ids), key=self._rank.__getitem__)

    def fingerprint(self) -> str:
        """Stable hash of the graph, used as a cache key component."""
        raw = json.dumps([s.model_dump() for s in self.skills.values()], sort_keys=True)
        return hashlib.sha256(raw.encode()).hexdigest()[:16]

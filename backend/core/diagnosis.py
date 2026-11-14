"""Root-cause diagnosis of a failed answer by walking the prerequisite graph."""

from collections import deque

from pydantic import BaseModel

from backend.core.analysis import VERIFIED_THRESHOLD
from backend.core.skill_graph import SkillGraph


class Diagnosis(BaseModel):
    failed_skill: str
    root_cause: str
    path: list[str]


def diagnose(graph: SkillGraph, failed_skill: str, confidence: dict[str, float]) -> Diagnosis:
    """Find the deepest unverified prerequisite of ``failed_skill`` (BFS, O(V+E)).

    ``path`` runs from the root cause to the failed skill. When every prerequisite
    is verified, the failed skill itself is the root cause.
    """
    depth = {failed_skill: 0}
    child: dict[str, str] = {}
    queue = deque([failed_skill])
    while queue:
        current = queue.popleft()
        for prereq in graph.prerequisites(current):
            if prereq not in depth:
                depth[prereq] = depth[current] + 1
                child[prereq] = current
                queue.append(prereq)
    weak = [
        sid
        for sid in depth
        if sid != failed_skill and confidence.get(sid, 0.0) < VERIFIED_THRESHOLD
    ]
    if not weak:
        return Diagnosis(failed_skill=failed_skill, root_cause=failed_skill, path=[failed_skill])
    order = {sid: i for i, sid in enumerate(graph.topological(depth))}
    root = max(weak, key=lambda sid: (depth[sid], -order[sid]))
    path = [root]
    while path[-1] != failed_skill:
        path.append(child[path[-1]])
    return Diagnosis(failed_skill=failed_skill, root_cause=root, path=path)

"""Institution Insights: anonymized cohort misconception aggregation."""

from collections import defaultdict

from pydantic import BaseModel


class MisconceptionStat(BaseModel):
    skill_id: str
    text: str
    learners_affected: int
    pct_affected: float


def top_misconceptions(
    records: list[tuple[str, str, str]], total_learners: int, top_n: int = 3
) -> list[MisconceptionStat]:
    """Aggregate (learner_key, skill_id, text) records into top misconceptions per skill.

    Each learner counts once per misconception; text is grouped case-insensitively.
    """
    if total_learners <= 0:
        return []
    learners: dict[tuple[str, str], set[str]] = defaultdict(set)
    display: dict[tuple[str, str], str] = {}
    for learner_key, skill_id, text in records:
        key = (skill_id, " ".join(text.lower().split()))
        learners[key].add(learner_key)
        display.setdefault(key, text.strip())
    per_skill: dict[str, list[MisconceptionStat]] = defaultdict(list)
    for (skill_id, norm), who in learners.items():
        per_skill[skill_id].append(
            MisconceptionStat(
                skill_id=skill_id,
                text=display[(skill_id, norm)],
                learners_affected=len(who),
                pct_affected=round(100 * len(who) / total_learners, 1),
            )
        )
    result: list[MisconceptionStat] = []
    for skill_id in sorted(per_skill):
        ranked = sorted(per_skill[skill_id], key=lambda s: (-s.learners_affected, s.text))
        result.extend(ranked[:top_n])
    return result

"""Deterministic fixtures for planning and coaching agents."""

from itertools import cycle, islice
from typing import Any

from backend.agents.career import CareerIn
from backend.agents.interviewer import InterviewerIn
from backend.agents.publisher import PublisherIn
from backend.agents.recommender import RecommenderIn

Payload = dict[str, Any]


def recommender(payload: Payload) -> Payload:
    """One templated reason per roadmap step."""
    inp = RecommenderIn.model_validate(payload)
    reasons = [
        {
            "skill_id": step.skill_id,
            "reason": f"Closes your {step.skill_name} gap for {inp.role_title}: learn with the "
            "tutorial, then prove it with the exercise.",
        }
        for step in inp.steps
    ]
    return {"reasons": reasons}


def interviewer(payload: Payload) -> Payload:
    """Tickets cycled from the bank, highest-weight skills first."""
    inp = InterviewerIn.model_validate(payload)
    ranked = sorted(inp.examples, key=lambda e: (-e.weight, e.skill_id))
    tickets = [
        {
            "skill_id": ex.skill_id,
            "title": f"{ex.skill_name} ticket",
            "prompt": ex.prompt,
            "rubric": ex.rubric,
        }
        for ex in islice(cycle(ranked), inp.count)
    ]
    return {"tickets": tickets}


def career(payload: Payload) -> Payload:
    """Claimed vs proven summary and a better-fit reason when one exists."""
    inp = CareerIn.model_validate(payload)
    target = next((r for r in inp.ranking if r.title == inp.target_role), inp.ranking[0])
    summary = (
        f"You claim {target.claimed_pct:.0f}% of {inp.target_role} skills, but evidence proves "
        f"{target.proven_pct:.0f}%. Proving claimed skills is the fastest way to raise readiness."
    )
    reason = None
    if inp.better_fit:
        skills = ", ".join(inp.verified_skills) or "your verified skills"
        reason = f"{inp.better_fit} builds directly on {skills}, which you have already proven."
    return {"summary": summary, "better_fit_reason": reason}


def mentor(payload: Payload) -> Payload:
    """Grounded reply; focuses roadmap skills named in the message."""
    message = str(payload["message"]).lower()
    roadmap: dict[str, str] = payload["roadmap_skills"]
    focus = [sid for sid, name in roadmap.items() if name.lower() in message][:3]
    next_steps = payload["next_steps"]
    parts = [f"{payload['learner_name']}, here is my guidance for {payload['role_title']}."]
    if focus:
        parts.append(
            f"I've moved {', '.join(roadmap[s] for s in focus)} to the top of your roadmap."
        )
    elif next_steps:
        parts.append(f"Your next best step is {next_steps[0]}.")
    if payload["misconceptions"]:
        parts.append(f"Watch out for this pattern: {payload['misconceptions'][0]}.")
    if payload["strengths"]:
        parts.append(f"Lean on your verified strengths: {', '.join(payload['strengths'][:3])}.")
    if payload.get("screenshot_attached"):
        parts.append("I received your screenshot, but image reading needs live AI mode.")
    return {"reply": " ".join(parts), "suggested_focus": focus}


def publisher(payload: Payload) -> Payload:
    """Post and learning log assembled from the provided facts only."""
    inp = PublisherIn.model_validate(payload)
    skills = ", ".join(inp.verified_skills) or "my first skills"
    post = (
        f"Learning in public: I'm working toward {inp.role_title}. So far I've proven {skills} "
        f"with {inp.evidence_count} pieces of evidence, and I'm {inp.proven_pct:.0f}% of the way "
        "there on verified skills. Next up: keep closing gaps one evidence point at a time. "
        "#LearnInPublic #CareerGrowth"
    )
    overcome = "\n".join(f"- {m}" for m in inp.misconceptions_overcome) or "- None recorded yet"
    done = "\n".join(f"- {s}" for s in inp.completed_steps) or "- None yet"
    upcoming = "\n".join(f"- {s}" for s in inp.next_steps) or "- Roadmap complete"
    log = (
        f"# Learning log: {inp.learner_name}\n\nTarget role: {inp.role_title} "
        f"({inp.proven_pct:.0f}% proven)\n\n## Verified skills\n"
        + ("\n".join(f"- {s}" for s in inp.verified_skills) or "- None yet")
        + f"\n\n## Misconceptions I overcame\n{overcome}\n\n## Completed steps\n{done}"
        + f"\n\n## Next steps\n{upcoming}\n"
    )
    return {"linkedin_post": post, "learning_log_md": log}

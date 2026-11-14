"""AI Mentor: grounded guidance chat with optional single-frame screen share."""

from typing import Any

from fastapi import APIRouter, Request
from starlette import status

from backend.api.deps import LearnerDep, ServicesDep, SessionDep, limiter, llm_rate_limit
from backend.api.errors import AppError
from backend.api.schemas import MAX_SCREENSHOT_BYTES, MentorRequest
from backend.services.images import InvalidImageError, sanitize_screenshot

router = APIRouter(prefix="/mentor", tags=["AI Mentor"])


@router.post("/chat", summary="Chat with the AI Mentor")
@limiter.limit(llm_rate_limit)
async def chat(
    request: Request,
    body: MentorRequest,
    learner: LearnerDep,
    services: ServicesDep,
    session_id: SessionDep,
) -> dict[str, Any]:
    """The screenshot (if any) is validated, used for this one call, and never stored."""
    screenshot = None
    if body.screenshot_b64:
        try:
            screenshot = sanitize_screenshot(body.screenshot_b64, MAX_SCREENSHOT_BYTES)
        except InvalidImageError as exc:
            raise AppError(
                status.HTTP_422_UNPROCESSABLE_CONTENT,
                "invalid_image",
                "Screenshot must be a JPEG or PNG under 1.5 MB.",
            ) from exc
    updated, result = await services.orchestrator.mentor_chat(learner, body.message, screenshot)
    services.repo.save_learner(session_id, updated)
    names = [services.catalog.graph.name(sid) for sid in result.applied_focus]
    return result.model_dump(mode="json") | {"applied_focus_names": names}

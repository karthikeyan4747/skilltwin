"""HTTP middleware: guest sessions, security headers, body size limit, static caching."""

import uuid
from collections.abc import Awaitable, Callable

from fastapi import Request, Response
from itsdangerous import BadSignature, URLSafeSerializer
from starlette.types import ASGIApp, Message, Receive, Scope, Send

from backend.api.errors import envelope

SESSION_COOKIE = "st_session"
SESSION_MAX_AGE = 60 * 60 * 24 * 14
PYODIDE_CDN = "https://cdn.jsdelivr.net"
CSP = "; ".join(
    [
        "default-src 'self'",
        f"script-src 'self' {PYODIDE_CDN} 'wasm-unsafe-eval'",
        "worker-src 'self' blob:",
        f"connect-src 'self' {PYODIDE_CDN}",
        "img-src 'self' data: blob:",
        "media-src 'self' blob:",
        "style-src 'self'",
        "font-src 'self'",
        "object-src 'none'",
        "base-uri 'self'",
        "form-action 'self'",
        "frame-ancestors 'none'",
    ]
)
SECURITY_HEADERS = {
    "Content-Security-Policy": CSP,
    "X-Content-Type-Options": "nosniff",
    "Referrer-Policy": "strict-origin-when-cross-origin",
    "Permissions-Policy": "camera=(), microphone=(), geolocation=(), display-capture=(self)",
    "Cross-Origin-Opener-Policy": "same-origin",
    "X-Frame-Options": "DENY",
}
CallNext = Callable[[Request], Awaitable[Response]]


def session_middleware(
    secret: str, secure: bool
) -> Callable[[Request, CallNext], Awaitable[Response]]:
    """Issue a signed, HttpOnly guest-session cookie on first visit; expose its id on state."""
    signer = URLSafeSerializer(secret, salt="skilltwin-session")

    async def middleware(request: Request, call_next: CallNext) -> Response:
        session_id: str | None = None
        raw = request.cookies.get(SESSION_COOKIE)
        if raw:
            try:
                session_id = str(signer.loads(raw))
            except BadSignature:
                session_id = None
        is_new = session_id is None
        request.state.session_id = session_id or uuid.uuid4().hex
        response = await call_next(request)
        if is_new:
            response.set_cookie(
                SESSION_COOKIE,
                signer.dumps(request.state.session_id),
                max_age=SESSION_MAX_AGE,
                httponly=True,
                secure=secure,
                samesite="lax",
            )
        return response

    return middleware


async def security_headers(request: Request, call_next: CallNext) -> Response:
    response = await call_next(request)
    response.headers.update(SECURITY_HEADERS)
    path = request.url.path
    if path.startswith(("/css/", "/js/")) or path == "/":
        response.headers["Cache-Control"] = "no-cache"
    elif path.startswith("/api/"):
        response.headers["Cache-Control"] = "no-store"
    return response


class BodySizeLimit:
    """Reject request bodies over ``max_bytes`` (declared or streamed) with 413."""

    def __init__(self, app: ASGIApp, max_bytes: int) -> None:
        self.app = app
        self.max_bytes = max_bytes

    async def __call__(self, scope: Scope, receive: Receive, send: Send) -> None:
        if scope["type"] != "http":
            await self.app(scope, receive, send)
            return
        headers = dict(scope.get("headers") or [])
        declared = headers.get(b"content-length")
        if declared and declared.isdigit() and int(declared) > self.max_bytes:
            await self._reject(scope, receive, send)
            return
        received = 0

        async def limited_receive() -> Message:
            nonlocal received
            message = await receive()
            if message["type"] == "http.request":
                received += len(message.get("body", b""))
                if received > self.max_bytes:
                    raise PayloadTooLarge
            return message

        try:
            await self.app(scope, limited_receive, send)
        except PayloadTooLarge:
            await self._reject(scope, receive, send)

    async def _reject(self, scope: Scope, receive: Receive, send: Send) -> None:
        response = envelope(413, "payload_too_large", "Request body is too large.")
        await response(scope, receive, send)


class PayloadTooLarge(Exception):
    pass

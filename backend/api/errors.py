"""Consistent error envelope: {"error": {"code", "message"}}; details stay in server logs."""

import logging

from fastapi import FastAPI, Request
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from slowapi.errors import RateLimitExceeded
from starlette.exceptions import HTTPException as StarletteHTTPException

log = logging.getLogger(__name__)


class AppError(Exception):
    def __init__(self, status: int, code: str, message: str) -> None:
        super().__init__(message)
        self.status, self.code, self.message = status, code, message


def envelope(status: int, code: str, message: str, **extra: object) -> JSONResponse:
    return JSONResponse(
        status_code=status, content={"error": {"code": code, "message": message, **extra}}
    )


def install_error_handlers(app: FastAPI) -> None:
    @app.exception_handler(AppError)
    async def _app_error(_: Request, exc: AppError) -> JSONResponse:
        return envelope(exc.status, exc.code, exc.message)

    @app.exception_handler(RequestValidationError)
    async def _validation(_: Request, exc: RequestValidationError) -> JSONResponse:
        fields = {
            ".".join(str(p) for p in err["loc"] if p != "body"): err["msg"] for err in exc.errors()
        }
        return envelope(422, "validation_error", "Some fields need attention.", fields=fields)

    @app.exception_handler(RateLimitExceeded)
    async def _rate_limited(_: Request, exc: RateLimitExceeded) -> JSONResponse:
        return envelope(429, "rate_limited", "Too many AI requests. Please wait a minute.")

    @app.exception_handler(StarletteHTTPException)
    async def _http(_: Request, exc: StarletteHTTPException) -> JSONResponse:
        code = "not_found" if exc.status_code == 404 else "http_error"
        message = "Not found." if exc.status_code == 404 else "Request could not be completed."
        return envelope(exc.status_code, code, message)

    @app.exception_handler(Exception)
    async def _unhandled(request: Request, exc: Exception) -> JSONResponse:
        log.exception("unhandled error on %s %s", request.method, request.url.path)
        return envelope(500, "internal_error", "Something went wrong. Please try again.")

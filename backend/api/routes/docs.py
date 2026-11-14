"""Interactive OpenAPI docs (Swagger UI) under a page-specific, hash-pinned CSP."""

import base64
import hashlib
import re

from fastapi import APIRouter
from fastapi.openapi.docs import get_swagger_ui_html
from fastapi.responses import HTMLResponse

SWAGGER_CDN = "https://cdn.jsdelivr.net/npm/swagger-ui-dist@5.17.14"

router = APIRouter(tags=["Site"])


def _swagger_page() -> tuple[str, str]:
    """Render Swagger UI once and allow only its own inline bootstrap script by hash."""
    body = get_swagger_ui_html(
        openapi_url="/openapi.json",
        title="SkillTwin API docs",
        swagger_js_url=f"{SWAGGER_CDN}/swagger-ui-bundle.js",
        swagger_css_url=f"{SWAGGER_CDN}/swagger-ui.css",
        swagger_favicon_url="/favicon.svg",
        swagger_ui_parameters={"validatorUrl": None},
    ).body
    html = bytes(body).decode()
    match = re.search(r"<script>(.*?)</script>", html, re.DOTALL)
    script = match.group(1) if match else ""
    digest = base64.b64encode(hashlib.sha256(script.encode()).digest()).decode()
    csp = "; ".join(
        [
            "default-src 'self'",
            f"script-src 'self' https://cdn.jsdelivr.net 'sha256-{digest}'",
            "style-src 'self' https://cdn.jsdelivr.net 'unsafe-inline'",
            "img-src 'self' data:",
            "connect-src 'self'",
            "object-src 'none'",
            "base-uri 'self'",
            "frame-ancestors 'none'",
        ]
    )
    return html, csp


DOCS_HTML, DOCS_CSP = _swagger_page()


@router.get("/docs", response_class=HTMLResponse, include_in_schema=False)
async def docs() -> HTMLResponse:
    return HTMLResponse(DOCS_HTML, headers={"Content-Security-Policy": DOCS_CSP})

# Security

This document lists every security control in SkillTwin and where it is implemented.

## Secrets and configuration

- All configuration comes from environment variables (`backend/config.py`). `.env.example` lists the
  variable names only, with no values. `.env` is git- and docker-ignored.
- Secrets are passed as Cloud Run environment variables at deploy time and never committed.
- `SESSION_SECRET` is required when `ENV=prod`; startup fails without it. In development a random
  secret is generated and a warning is logged.
- Secrets are held as `SecretStr` and are never logged. The application never logs request bodies,
  answers or chat messages; agent fallbacks log only the agent key and the error type.
  Unexpected errors are logged with a traceback on the server only.

## Sessions

- Guest sessions use a signed cookie (`itsdangerous`) named `st_session`: `HttpOnly`,
  `SameSite=Lax`, `Secure` when `ENV=prod`, 14-day lifetime (`backend/api/middleware.py`).
  A tampered cookie is rejected and a new session is issued.
- All learner data, pending questions and answers are scoped by session id
  (`backend/services/repository.py`); a question can only be answered by the session that
  received it. Cohort insights use a one-way hash of the session id, never the id itself.

## Input validation

- Every request body is a strict Pydantic model with `extra="forbid"` (`backend/api/schemas.py`,
  `backend/core/models.py`): answer text ≤ 4000 chars, chat message ≤ 2000 chars, profile name
  ≤ 80, education ≤ 200, list items ≤ 120 chars with bounded list lengths, ids restricted to
  `^[a-z0-9_-]{1,60}$`, question ids to 32 hex chars, enums for question types, step status and
  grid moves, numeric ranges for hours, choices and test counts.
- Skill and role ids are checked against the catalog before use.
- Request bodies larger than 2.5 MB are rejected with 413, whether the size is declared or streamed
  (`BodySizeLimit` middleware).

## Screenshot upload (AI Mentor screen share)

- Captured only when the learner clicks "Share screen"; exactly one frame is grabbed and the
  stream is stopped immediately. The frame is downscaled in the browser to ≤ 1024 px JPEG, shown
  as a preview, and sent only with the learner's next message.
- Server side (`backend/services/images.py`): base64 is strictly decoded, size ≤ 1.5 MB, format
  allowlist JPEG/PNG, Pillow `verify()` decode check, then re-encoded in memory as a JPEG
  ≤ 1024 px (which drops metadata). The image is used for that single model call and never
  written to disk or the database.

## LLM safety

- Learner content is passed to models only as JSON inside `<learner_data>` delimiters; every
  system prompt states that this content is data and instructions inside it must be ignored
  (`backend/agents/base.py`, `backend/services/llm.py`).
- All model output is parsed with the agent's Pydantic schema; invalid JSON is retried once, then
  the call falls back to the deterministic MockLLM. Model output never decides state directly:
  core functions do (for example the Mentor may only suggest skill ids that are already on the
  roadmap, and the core applies them).
- Explain-back answers are scored for concepts separately from language fluency; only the
  concept score becomes evidence.

## Rate limiting

- Every route that calls an LLM agent is limited to 20 requests per minute per session + client
  IP (`slowapi`, `backend/api/deps.py`): profile save, goal change, question, answer, mentor chat,
  twin interviews and publish draft. Uvicorn runs with `--proxy-headers` so the client IP is taken
  from Cloud Run's forwarding header.

## HTTP security headers (`backend/api/middleware.py`)

- `Content-Security-Policy`: `default-src 'self'`; scripts from `'self'` and the pinned Pyodide CDN
  (`https://cdn.jsdelivr.net`) plus `'wasm-unsafe-eval'` (needed to compile Pyodide's
  WebAssembly); `worker-src 'self' blob:` (the Grid Game sandbox worker); `connect-src 'self'` and
  the Pyodide CDN; `style-src 'self'`; `object-src 'none'`; `base-uri 'self'`;
  `form-action 'self'`; `frame-ancestors 'none'`. There are no inline scripts or inline styles.
- `X-Content-Type-Options: nosniff`, `Referrer-Policy: strict-origin-when-cross-origin`,
  `X-Frame-Options: DENY`, `Cross-Origin-Opener-Policy: same-origin`, and a `Permissions-Policy`
  that disables camera, microphone and geolocation and allows display capture only for this origin.
- CORS: no CORS middleware is installed, so browsers only allow same-origin API use.
- API responses are sent with `Cache-Control: no-store`.

## User code execution

- Learner code never runs on the server.
- Python (code exercises, Code Visualizer) runs in a Pyodide Web Worker. Each run has a 3 s
  timeout after which the worker is terminated; the tracer stops after 500 steps. The worker is
  also terminated when the learner leaves the page.
- JavaScript (Grid Game) runs in a fresh Blob worker per run: no DOM, `fetch`, `XMLHttpRequest`,
  `WebSocket`, `importScripts` and similar APIs are removed before learner code runs, CSP
  `connect-src` blocks other origins, and the worker is terminated after 1 s or when it finishes.
- The Grid Game result is verified on the server by replaying the submitted move list on the level
  (`backend/core/grid.py`), not by trusting the client. Code-exercise test counts are reported by
  the browser, because the code intentionally never reaches the server.

## Output encoding

- The UI renders all model and user text with `textContent` (the `el()` helper in
  `frontend/js/ui.js`); `innerHTML` is not used anywhere.

## Data access and errors

- SQLite queries are parameterised only (`backend/services/repository.py`).
- Clients receive a generic error envelope `{error: {code, message}}`; stack traces and internal
  details stay in server logs (`backend/api/errors.py`).

## Supply chain and runtime

- Python dependencies are pinned to exact versions in `pyproject.toml`; Pyodide is pinned to
  `v0.26.4`.
- The Docker image is multi-stage on `python:3.12-slim`, contains only `backend/` and `frontend/`,
  and runs as a non-root user (uid 10001).

## Reporting

Please report vulnerabilities privately to the repository owner rather than opening a public issue.

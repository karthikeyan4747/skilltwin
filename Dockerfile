FROM python:3.12-slim AS build
ENV PIP_NO_CACHE_DIR=1 PIP_DISABLE_PIP_VERSION_CHECK=1
WORKDIR /app
COPY pyproject.toml ./
RUN python -c "import tomllib; print('\n'.join(tomllib.load(open('pyproject.toml', 'rb'))['project']['dependencies']))" > requirements.txt \
    && python -m venv /venv \
    && /venv/bin/pip install -r requirements.txt

FROM python:3.12-slim
ENV PYTHONDONTWRITEBYTECODE=1 PYTHONUNBUFFERED=1 PATH="/venv/bin:$PATH" PORT=8080 ENV=prod
RUN useradd --create-home --uid 10001 app
WORKDIR /app
COPY --from=build /venv /venv
COPY backend ./backend
COPY frontend ./frontend
USER app
EXPOSE 8080
CMD ["sh", "-c", "exec uvicorn backend.main:create_app --factory --host 0.0.0.0 --port ${PORT} --proxy-headers --forwarded-allow-ips='*'"]

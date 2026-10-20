# syntax=docker/dockerfile:1

FROM python:3.12-alpine3.24 AS base

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    UV_COMPILE_BYTECODE=1 \
    UV_LINK_MODE=copy

WORKDIR /app

# --- Dependencies stage: uv and uvx are not copied into the runtime stage ---
FROM base AS deps

COPY --from=ghcr.io/astral-sh/uv:latest /uv /uvx /bin/

COPY pyproject.toml ./
COPY uv.lock* ./
RUN uv sync --no-dev --no-install-project

# --- Runtime stage ---
FROM base AS runtime

# Clears CVE-2026-85091. Upgrade zlib only; do not refresh the rest of Alpine.
RUN apk upgrade --no-cache zlib \
    && rm -rf \
        /usr/local/lib/python3.12/site-packages/pip \
        /usr/local/lib/python3.12/site-packages/pip-*.dist-info \
        /usr/local/lib/python3.12/ensurepip/_bundled/pip-*.whl \
    && rm -f /usr/local/bin/pip /usr/local/bin/pip3 /usr/local/bin/pip3.12

RUN addgroup -S dealbrain && adduser -S -G dealbrain dealbrain

COPY --from=deps /app/.venv /app/.venv
COPY pyproject.toml ./
COPY uv.lock* ./
COPY alembic.ini ./
COPY alembic ./alembic
COPY app ./app
COPY docs ./docs
COPY .env.example ./.env.example
COPY .env.staging.example ./.env.staging.example
COPY .env.production.example ./.env.production.example

ENV PATH="/app/.venv/bin:$PATH" \
    APP_ENV=production \
    APP_DEBUG=false \
    PRICE_HISTORY_SEED_DEMO_MOCK=false

USER dealbrain

EXPOSE 8000

# Liveness probe — process up (readiness is checked separately by orchestrators)
HEALTHCHECK --interval=30s --timeout=5s --start-period=15s --retries=3 \
    CMD python -c "import urllib.request; urllib.request.urlopen('http://localhost:8000/live')" || exit 1

CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]

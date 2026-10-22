# syntax=docker/dockerfile:1

# Official library/python tag 3.12-alpine3.24.
# Manifest-list digest verified from registry-1.docker.io on 2026-10-22.
# linux/amd64 manifest: sha256:9b98a8d37794ca093ba8d5afe1ffac52f5a15168b9b4e67594d86c20e14fa681
# CPython 3.12.15. Alpine 3.24.3 (/etc/alpine-release).
FROM python:3.12-alpine3.24@sha256:92abd2ba1bdfb48b1e2ac224b582dd1558d0d4bb11c903b126b5bf9c448fd656 AS base

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    UV_COMPILE_BYTECODE=1 \
    UV_LINK_MODE=copy

WORKDIR /app

# --- Dependencies stage: uv and uvx are not copied into the runtime stage ---
FROM base AS deps

# Official ghcr.io/astral-sh/uv tag 0.13.5.
# Manifest-list digest verified from ghcr.io on 2026-10-22.
# linux/amd64 manifest: sha256:a12ede1e6dc90d3b3e600d0901731e71f0ab0f4d72683ea097b76c19c43cc8df
# uv 0.13.5 (x86_64-unknown-linux-musl). Source https://github.com/astral-sh/uv
# revision 46776a95d6686ac0160c10611327ce491e6b202f (GitHub release 0.13.5).
COPY --from=ghcr.io/astral-sh/uv:0.13.5@sha256:32a7bb39b496babbd997b0a39a4d66c126bdaf5661b302bf6f06abda8deca6ff /uv /uvx /bin/

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

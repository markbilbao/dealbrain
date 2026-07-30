#!/usr/bin/env bash
# Sprint 25a infrastructure validation helpers.
# Run from repository root. Exits non-zero on first failure when tooling exists.
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$ROOT"

PASS=0
SKIP=0
FAIL=0

note() { printf '==> %s\n' "$*"; }
ok() { PASS=$((PASS + 1)); printf 'OK  %s\n' "$*"; }
skip() { SKIP=$((SKIP + 1)); printf 'SKIP %s\n' "$*"; }
fail() { FAIL=$((FAIL + 1)); printf 'FAIL %s\n' "$*"; }

note "Static secret scan (infra / examples / scripts / workflows)"
PYTHON_BIN="${PYTHON_BIN:-}"
if [[ -z "$PYTHON_BIN" ]]; then
  if [[ -x "$ROOT/.venv/bin/python" ]]; then
    PYTHON_BIN="$ROOT/.venv/bin/python"
  elif command -v python3 >/dev/null 2>&1; then
    PYTHON_BIN="$(command -v python3)"
  elif command -v python >/dev/null 2>&1; then
    PYTHON_BIN="$(command -v python)"
  fi
fi
if [[ -n "${PYTHON_BIN}" ]]; then
  if "$PYTHON_BIN" "$ROOT/scripts/secret_scan_25a.py"; then
    ok "secret_scan_25a"
  else
    fail "secret_scan_25a"
  fi
else
  skip "python not available for secret scan"
fi

note "Terraform fmt / validate"
if command -v terraform >/dev/null 2>&1; then
  if terraform fmt -check -recursive infra/terraform; then
    ok "terraform fmt -check"
  else
    fail "terraform fmt -check"
  fi
  for env in staging production; do
    dir="infra/terraform/environments/${env}"
    # validate needs init; use -backend=false for offline foundation check
    if (
      cd "$dir"
      terraform init -backend=false -input=false >/dev/null
      terraform validate
    ); then
      ok "terraform validate ${env}"
    else
      fail "terraform validate ${env}"
    fi
  done
else
  skip "terraform not installed — run: terraform fmt -check -recursive infra/terraform"
  skip "terraform validate staging/production after terraform init -backend=false"
fi

note "Compose config"
if command -v docker >/dev/null 2>&1; then
  export DEALBRAIN_IMAGE="ghcr.io/EXAMPLE_ORG/dealbrain:test"
  export DATABASE_URL="postgresql+asyncpg://u:StrongPassword12@host:5432/dealbrain"
  export CORS_ORIGINS="https://example.com"
  export APP_ENV="production"
  if docker compose \
    -f infra/compose/docker-compose.base.yml \
    -f infra/compose/docker-compose.production.yml \
    config >/dev/null; then
    ok "docker compose production config"
  else
    fail "docker compose production config"
  fi
  export APP_ENV="staging"
  if docker compose \
    -f infra/compose/docker-compose.base.yml \
    -f infra/compose/docker-compose.staging.yml \
    config >/dev/null; then
    ok "docker compose staging config"
  else
    fail "docker compose staging config"
  fi
else
  skip "docker not installed — run docker compose … config with DEALBRAIN_IMAGE set"
fi

note "Application unit tests (Sprint 25a + protected modules)"
if [[ -x "$ROOT/.venv/bin/pytest" ]]; then
  if "$ROOT/.venv/bin/pytest" tests/unit/test_sprint25a_infrastructure.py \
    tests/unit/test_sprint22_protected_modules.py \
    tests/unit/persistence/test_sprint23_architecture.py \
    -q; then
    ok "targeted pytest"
  else
    fail "targeted pytest"
  fi
elif command -v uv >/dev/null 2>&1; then
  if uv run pytest tests/unit/test_sprint25a_infrastructure.py \
    tests/unit/test_sprint22_protected_modules.py \
    tests/unit/persistence/test_sprint23_architecture.py \
    -q; then
    ok "targeted pytest"
  else
    fail "targeted pytest"
  fi
else
  skip "pytest/uv not installed"
fi

printf '\nSummary: pass=%s skip=%s fail=%s\n' "$PASS" "$SKIP" "$FAIL"
if [[ "$FAIL" -gt 0 ]]; then
  exit 1
fi
exit 0

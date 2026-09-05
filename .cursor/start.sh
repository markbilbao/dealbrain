#!/usr/bin/env bash
# Per-boot reconciliation: start PostgreSQL, ensure the role/database exist,
# and apply Alembic migrations. Idempotent and safe on every boot.
set -euo pipefail

REPO_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$REPO_ROOT"
export PATH="$HOME/.local/bin:$PATH"

# --- Start the PostgreSQL cluster if it is not already accepting connections ---
if ! sudo -u postgres pg_isready -q 2>/dev/null; then
  echo "[start] Starting PostgreSQL cluster..."
  sudo pg_ctlcluster 16 main start || true
fi

# Wait until PostgreSQL is ready (max ~30s).
for _ in $(seq 1 30); do
  if sudo -u postgres pg_isready -q 2>/dev/null; then
    break
  fi
  sleep 1
done

# --- Ensure the application role and database exist (idempotent) ---
if ! sudo -u postgres psql -tAc "SELECT 1 FROM pg_roles WHERE rolname='dealbrain'" | grep -q 1; then
  sudo -u postgres psql -c "CREATE USER dealbrain WITH PASSWORD 'dealbrain' SUPERUSER;"
fi
if ! sudo -u postgres psql -tAc "SELECT 1 FROM pg_database WHERE datname='dealbrain'" | grep -q 1; then
  sudo -u postgres psql -c "CREATE DATABASE dealbrain OWNER dealbrain;"
fi

# --- Apply database migrations ---
echo "[start] Applying database migrations..."
uv run alembic upgrade head

echo "[start] Ready."

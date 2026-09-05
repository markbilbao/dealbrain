#!/usr/bin/env bash
# Idempotent dependency + toolchain setup for the DealBrain backend.
# Runs after the repository is checked out. Safe to run repeatedly.
set -euo pipefail

REPO_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$REPO_ROOT"

export PATH="$HOME/.local/bin:$PATH"

# --- uv (Python package/deps manager) ---
if ! command -v uv >/dev/null 2>&1; then
  echo "[install] Installing uv..."
  curl -LsSf https://astral.sh/uv/install.sh | sh
  export PATH="$HOME/.local/bin:$PATH"
fi
uv --version

# --- PostgreSQL 16 (system dependency) ---
if ! command -v pg_ctlcluster >/dev/null 2>&1; then
  echo "[install] Installing PostgreSQL..."
  sudo apt-get update -qq
  sudo DEBIAN_FRONTEND=noninteractive apt-get install -y -qq postgresql postgresql-contrib
fi

# --- Python dependencies (respects uv.lock) ---
echo "[install] Syncing Python dependencies..."
uv sync --extra dev

# --- Local env file (developer defaults; never overwrites an existing .env) ---
if [ ! -f .env ]; then
  cp .env.example .env
  echo "[install] Created .env from .env.example"
fi

echo "[install] Done."

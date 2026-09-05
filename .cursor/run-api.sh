#!/usr/bin/env bash
# Long-running foreground process: the DealBrain FastAPI dev server.
set -euo pipefail

REPO_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$REPO_ROOT"
export PATH="$HOME/.local/bin:$PATH"

exec uv run uvicorn app.main:app --host 0.0.0.0 --port 8000

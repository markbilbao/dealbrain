#!/usr/bin/env python3
"""Explicitly regenerate the active OpenAPI contract baseline (Sprint 24).

Does NOT rewrite the frozen Sprint 23 snapshot
(``tests/contracts/baselines/openapi_sprint23.json``).

Usage:
    .venv/bin/python scripts/update_openapi_baseline.py
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "tests" / "contracts" / "baselines" / "openapi.baseline.json"


def main() -> int:
    sys.path.insert(0, str(ROOT))
    from app.main import create_app

    schema = create_app().openapi()
    text = json.dumps(schema, indent=2, sort_keys=True, ensure_ascii=False) + "\n"
    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text(text, encoding="utf-8")
    paths = len(schema.get("paths", {}))
    print(f"Wrote {OUT} ({len(text)} bytes, {paths} paths)")
    print("Remember: commit this file intentionally with the contract change.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

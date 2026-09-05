"""Guard: production images must install the HTTP client the Resend adapter imports."""

from __future__ import annotations

import tomllib
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]


def _project() -> dict:
    return tomllib.loads((ROOT / "pyproject.toml").read_text(encoding="utf-8"))["project"]


def test_httpx_is_a_runtime_dependency() -> None:
    runtime = _project()["dependencies"]
    assert any(item.startswith("httpx") for item in runtime)


def test_httpx_is_not_dev_only() -> None:
    optional = _project().get("optional-dependencies", {})
    dev = optional.get("dev", [])
    assert not any(item.startswith("httpx") for item in dev)


def test_resend_adapter_imports_httpx() -> None:
    source = (ROOT / "app/auth/email_resend.py").read_text(encoding="utf-8")
    assert "import httpx" in source


def test_production_sync_excludes_dev_extras() -> None:
    dockerfile = (ROOT / "Dockerfile").read_text(encoding="utf-8")
    assert "uv sync --no-dev --no-install-project" in dockerfile

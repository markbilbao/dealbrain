"""OpenAPI drift detection — Sprint 24 contract gate.

Compares live ``create_app().openapi()`` against the committed active baseline.
Never rewrites the baseline automatically.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

import pytest
from app.main import create_app

BASELINES = Path(__file__).resolve().parents[2] / "contracts" / "baselines"
ACTIVE = BASELINES / "openapi.baseline.json"
SPRINT23 = BASELINES / "openapi_sprint23.json"


def _canonical(schema: dict[str, Any]) -> str:
    return json.dumps(schema, indent=2, sort_keys=True, ensure_ascii=False) + "\n"


def _load(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def _diff_paths(live: dict[str, Any], baseline: dict[str, Any]) -> list[str]:
    live_paths = set(live.get("paths", {}))
    base_paths = set(baseline.get("paths", {}))
    messages: list[str] = []
    removed = sorted(base_paths - live_paths)
    added = sorted(live_paths - base_paths)
    if removed:
        messages.append(f"Removed paths (forbidden without intentional baseline update): {removed}")
    if added:
        messages.append(f"Added paths (update baseline explicitly): {added}")
    return messages


def test_sprint23_openapi_freeze_exists() -> None:
    assert SPRINT23.is_file(), "Phase 0 Sprint 23 OpenAPI freeze missing"
    data = _load(SPRINT23)
    assert "paths" in data
    assert "/api/v2" not in json.dumps(data)
    assert len(data["paths"]) >= 100


def test_active_baseline_exists() -> None:
    assert ACTIVE.is_file(), (
        "Active OpenAPI baseline missing. Generate with: "
        ".venv/bin/python scripts/update_openapi_baseline.py"
    )


def test_openapi_does_not_introduce_v2() -> None:
    schema = create_app().openapi()
    paths = schema.get("paths", {})
    assert not any(p.startswith("/api/v2") for p in paths)
    assert schema.get("info", {}).get("x-dealbrain-no-api-v2") is True


def test_openapi_matches_active_baseline() -> None:
    if not ACTIVE.is_file():
        pytest.skip("active baseline not generated yet")
    live = create_app().openapi()
    baseline = _load(ACTIVE)
    live_text = _canonical(live)
    base_text = _canonical(baseline)
    if live_text == base_text:
        return

    messages = _diff_paths(live, baseline)
    # Summarize schema-level drift for developers.
    live_ops = {
        f"{m.upper()} {p}"
        for p, ops in live.get("paths", {}).items()
        for m in ops
        if m.lower() in {"get", "post", "put", "patch", "delete"}
    }
    base_ops = {
        f"{m.upper()} {p}"
        for p, ops in baseline.get("paths", {}).items()
        for m in ops
        if m.lower() in {"get", "post", "put", "patch", "delete"}
    }
    if live_ops != base_ops:
        messages.append(f"Operation set delta: +{sorted(live_ops - base_ops)[:20]} "
                        f"-{sorted(base_ops - live_ops)[:20]}")
    messages.append(
        "OpenAPI drifted from tests/contracts/baselines/openapi.baseline.json. "
        "If intentional, run: .venv/bin/python scripts/update_openapi_baseline.py"
    )
    pytest.fail("\n".join(messages))


def test_error_and_pagination_components_documented() -> None:
    schema = create_app().openapi()
    components = schema.get("components", {}).get("schemas", {})
    assert "ErrorBody" in components
    assert "PaginationMeta" in components


def test_legacy_alerts_marked_deprecated() -> None:
    schema = create_app().openapi()
    paths = schema["paths"]
    legacy = [
        ("get", "/api/v1/alerts"),
        ("get", "/api/v1/alerts/{alert_id}"),
        ("post", "/api/v1/alerts/{alert_id}/acknowledge"),
        ("post", "/api/v1/alerts/{alert_id}/dismiss"),
    ]
    for method, path in legacy:
        assert path in paths, f"legacy path removed: {path}"
        op = paths[path][method]
        assert op.get("deprecated") is True, f"{method.upper()} {path} must be deprecated"


def test_products_skip_marked_deprecated_in_openapi() -> None:
    schema = create_app().openapi()
    params = schema["paths"]["/api/v1/products"]["get"].get("parameters") or []
    skip = next((p for p in params if p.get("name") == "skip"), None)
    offset = next((p for p in params if p.get("name") == "offset"), None)
    assert skip is not None
    assert skip.get("deprecated") is True
    assert offset is not None


def test_ranking_endpoints_have_no_sort_parameter() -> None:
    schema = create_app().openapi()
    ranking = [
        "/api/v1/dealscore/search",
        "/api/v1/recommendations/search",
        "/api/v1/marketplace/search",
    ]
    for path in ranking:
        params = schema["paths"][path]["get"].get("parameters") or []
        names = {p.get("name") for p in params}
        assert "sort" not in names, f"{path} must not expose sort"


def test_tier1_endpoints_document_errorbody() -> None:
    schema = create_app().openapi()
    responses = schema.get("components", {}).get("responses", {})
    assert "ErrorBodyValidation" in responses
    assert responses["ErrorBodyValidation"]["content"]["application/json"]["schema"][
        "$ref"
    ] == "#/components/schemas/ErrorBody"

    # Remaining Tier-1 ops that previously lacked 4xx/5xx must now document errors.
    required = [
        ("get", "/api/v1/collections/jobs"),
        ("post", "/api/v1/collections/jobs/run-due"),
        ("post", "/api/v1/watchlists/check-alerts"),
        ("get", "/api/v1/merchants/meta/demo"),
    ]
    for method, path in required:
        op = schema["paths"][path][method]
        codes = set(op.get("responses", {}))
        assert any(
            c.startswith("4") or c.startswith("5") for c in codes if c.isdigit()
        ) or any(c in {"401", "403", "404", "422", "500"} for c in codes), (
            f"{method.upper()} {path} missing ErrorBody error documentation"
        )


def test_sort_prohibited_prefixes_have_no_sort_in_openapi() -> None:
    from app.schemas.api_common import SORT_PROHIBITED_PATH_PREFIXES

    schema = create_app().openapi()
    for path, ops in schema["paths"].items():
        if not any(path.startswith(prefix) for prefix in SORT_PROHIBITED_PATH_PREFIXES):
            continue
        for method, operation in ops.items():
            if method not in {"get", "post", "put", "patch", "delete"}:
                continue
            params = operation.get("parameters") or []
            names = {p.get("name") for p in params}
            assert "sort" not in names, f"{method.upper()} {path} must not expose sort"

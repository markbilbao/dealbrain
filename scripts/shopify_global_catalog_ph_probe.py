#!/usr/bin/env python3
"""Shopify Global Catalog PH coverage probe — Sprint 32 technical harness.

Anonymous, first-page-only, organic catalog probe. Not a production connector.
Does not certify Shopify. Does not start Sprint 38. Does not scrape merchants.
Does not enable promoted placement or affiliate commission.
Does not persist raw Shopify catalog responses.

Usage:
  uv run python scripts/shopify_global_catalog_ph_probe.py
  uv run python scripts/shopify_global_catalog_ph_probe.py \\
    --live --output-dir /tmp/piqsavi-shopify-global-ph
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from app.research.shopify_global_catalog_ph_probe import (  # noqa: E402
    DEFAULT_FIXTURE,
    DEFAULT_OUTPUT_DIR,
    FORBIDDEN_LOOKUP_TOOL,
    GET_PRODUCT_TOOL,
    GLOBAL_CATALOG_ENDPOINT,
    SEARCH_TOOL,
    TECHNICAL_TEST_ONLY,
    LiveProbeOutputInsideRepositoryError,
    ProbeContractError,
    ProbeLimitError,
    ProbeResponseError,
    anonymous_http_headers,
    assert_live_probe_output_outside_repository,
    build_jsonrpc_request,
    fixture_transport_from_payload,
    load_probe_fixture,
    minimized_artifact_payload,
    run_ph_coverage_probe,
    validate_catalog_tool_response,
)


class LiveAnonymousCatalogTransport:
    """Anonymous JSON-RPC caller for catalog.shopify.com. No credentials."""

    def __init__(self, *, timeout: float = 30.0) -> None:
        self.timeout = timeout
        self._next_id = 1

    def call_tool(self, name: str, arguments: dict[str, Any]) -> dict[str, Any]:
        if name == FORBIDDEN_LOOKUP_TOOL:
            raise ProbeContractError("lookup_catalog is forbidden for this PH probe")
        request = build_jsonrpc_request(name, arguments, request_id=self._next_id)
        self._next_id += 1
        payload = post_anonymous_catalog(request, timeout=self.timeout)
        validate_catalog_tool_response(payload)
        return payload


def post_anonymous_catalog(request: dict[str, Any], *, timeout: float) -> dict[str, Any]:
    """POST JSON-RPC to Global Catalog. No Authorization header. No API key."""

    import httpx

    headers = anonymous_http_headers()
    if "Authorization" in headers or any(key.lower().startswith("signature") for key in headers):
        raise ProbeContractError("anonymous PH probe must not send credentials or signatures")
    try:
        response = httpx.post(
            GLOBAL_CATALOG_ENDPOINT,
            json=request,
            headers=headers,
            timeout=timeout,
        )
        response.raise_for_status()
        payload = response.json()
    except httpx.HTTPStatusError as exc:
        raise RuntimeError(f"Shopify Global Catalog HTTP {exc.response.status_code}") from None
    except httpx.HTTPError:
        raise RuntimeError("Shopify Global Catalog request failed") from None
    if not isinstance(payload, dict):
        raise RuntimeError("Shopify Global Catalog returned a non-object response")
    return payload


def _write_json(path: Path, payload: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    serialized = json.dumps(payload, ensure_ascii=False, indent=2)
    path.write_text(serialized + "\n", encoding="utf-8")


def _failure_envelope(exc: BaseException) -> dict[str, Any]:
    return {
        "live": True,
        "production_certified": False,
        "closes_sprint_32": False,
        "certifies_shopify": False,
        "starts_sprint_38": False,
        "agent_profile_usage": TECHNICAL_TEST_ONLY,
        "credentials_required": False,
        "raw_response_persisted": False,
        "technical_probe_failure": True,
        "error": str(exc),
    }


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description=(
            "PH Shopify Global Catalog coverage probe. Anonymous technical test. "
            "Does not certify production. Live artifacts must stay outside Git. "
            "Minimized evidence only; raw catalog payloads are not persisted."
        )
    )
    parser.add_argument(
        "--live",
        action="store_true",
        help=(
            "Call catalog.shopify.com anonymously with the official Shopify-hosted "
            "UCP test profile. No API key. TECHNICAL TEST ONLY."
        ),
    )
    parser.add_argument(
        "--fixture",
        type=Path,
        default=DEFAULT_FIXTURE,
        help="Synthetic non-production catalog fixture for offline tests.",
    )
    parser.add_argument(
        "--output-dir",
        type=Path,
        default=DEFAULT_OUTPUT_DIR,
        help="Default live destination is /tmp/piqsavi-shopify-global-ph.",
    )
    args = parser.parse_args(argv)
    output_dir = args.output_dir
    if args.live:
        print(
            "TECHNICAL TEST ONLY. Anonymous Shopify-hosted agent profile. "
            "Not a PiqSavi identity. Not production certification. "
            "Sprint 32 remains open."
        )
        try:
            output_dir = assert_live_probe_output_outside_repository(output_dir)
        except LiveProbeOutputInsideRepositoryError as exc:
            print(str(exc))
            return 2
        transport: Any = LiveAnonymousCatalogTransport()
        try:
            report = run_ph_coverage_probe(
                transport=transport,
                live=True,
            )
        except (ProbeLimitError, ProbeContractError, ProbeResponseError, RuntimeError) as exc:
            envelope = _failure_envelope(exc)
            _write_json(output_dir / "summary.json", envelope)
            print(json.dumps(envelope, ensure_ascii=False, indent=2))
            return 2
    else:
        payload = load_probe_fixture(args.fixture)
        transport = fixture_transport_from_payload(payload)
        report = run_ph_coverage_probe(
            transport=transport,
            live=False,
        )

    artifact = minimized_artifact_payload(report)
    summary = {
        "generated_at": report.generated_at,
        "live": report.live,
        "fixture": report.fixture,
        "artifact_kind": report.artifact_kind,
        "agent_profile": report.agent_profile,
        "agent_profile_usage": report.agent_profile_usage,
        "agent_profile_not_piqsavi_identity": report.agent_profile_not_piqsavi_identity,
        "auth_tier": report.auth_tier,
        "credentials_required": report.credentials_required,
        "endpoint": report.endpoint,
        "search_calls": report.search_calls,
        "get_product_calls": report.get_product_calls,
        "lookup_catalog_calls": report.lookup_catalog_calls,
        "pagination_followed": report.pagination_followed,
        "bulk_ids_used": report.bulk_ids_used,
        "raw_response_persisted": False,
        "production_certified": False,
        "certifies_shopify": False,
        "closes_sprint_32": False,
        "starts_sprint_38": False,
        "affiliate_or_promoted_placement": False,
        "scraping": False,
        "environment_mutation": False,
        "classifications": {item.query_id: item.classification for item in report.query_results},
        "output_dir": str(output_dir),
        "tools_used": [SEARCH_TOOL, GET_PRODUCT_TOOL],
        "tools_forbidden": [FORBIDDEN_LOOKUP_TOOL],
    }
    _write_json(output_dir / "summary.json", summary)
    _write_json(output_dir / "ph_probe.json", artifact)
    print(json.dumps(summary, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

#!/usr/bin/env python3
"""Owner-run Shopify Global Catalog normalization validation.

Cursor must not execute this script. It is not Sprint 38 and it does not
certify production. Without ``--live`` it makes no network call.

Live mode calls only ``https://catalog.shopify.com/api/ucp/mcp`` with the
exact deployed staging PiqSavi profile, at most 5 ``search_catalog`` calls
and 5 ``get_product`` calls. No ``lookup_catalog``, no pagination, no
credentials, and no raw Shopify payload is written.

Usage (owner only):
  uv run python scripts/shopify_global_catalog_normalization_validation.py --live \\
    --output-dir /tmp/piqsavi-shopify-normalization-validation
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from app.research.shopify_global_catalog_normalization_harness import (  # noqa: E402
    OWNER_HARNESS_USER_AGENT,
    OWNER_LIVE_HARNESS_RUN_BY_CURSOR,
    ShopifyNormalizationHarnessError,
    run_shopify_normalization_validation,
    staging_normalization_profile,
    write_normalization_summary,
)
from app.research.shopify_global_catalog_ph_probe import (  # noqa: E402
    FORBIDDEN_LOOKUP_TOOL,
    GLOBAL_CATALOG_ENDPOINT,
    ProbeContractError,
    anonymous_http_headers,
)

DEFAULT_OUTPUT_DIR = Path("/tmp/piqsavi-shopify-normalization-validation")
_NOT_RUN_MESSAGE = (
    "Owner live Shopify normalization validation was not run. "
    "Pass --live only from an owner workstation. "
    "Cursor must not execute this harness."
)


class _LiveStagingCatalogTransport:
    """Anonymous JSON-RPC caller. No credentials. Owner --live path only."""

    def __init__(self, *, timeout: float = 30.0) -> None:
        self.timeout = timeout
        self._next_id = 1

    def call_tool(self, name: str, arguments: dict[str, Any]) -> dict[str, Any]:
        if name == FORBIDDEN_LOOKUP_TOOL:
            raise ShopifyNormalizationHarnessError("lookup_catalog prohibited")
        request = {
            "jsonrpc": "2.0",
            "method": "tools/call",
            "id": self._next_id,
            "params": {"name": name, "arguments": arguments},
        }
        self._next_id += 1
        return _post_anonymous_catalog(request, timeout=self.timeout)


def _post_anonymous_catalog(request: dict[str, Any], *, timeout: float) -> dict[str, Any]:
    import httpx

    headers = anonymous_http_headers()
    if headers.get("User-Agent") != OWNER_HARNESS_USER_AGENT:
        raise ProbeContractError("owner harness User-Agent drifted from the Sprint 32 probe")
    if "Authorization" in headers or any(key.lower().startswith("signature") for key in headers):
        raise ProbeContractError("owner harness must not send credentials or signatures")
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


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description=(
            "Owner-run Shopify normalization validation. "
            "Does not certify production. Does not start Sprint 38. "
            "Refuses to run unless --live is explicit."
        )
    )
    parser.add_argument(
        "--live",
        action="store_true",
        help=(
            "Call catalog.shopify.com with the exact deployed staging PiqSavi "
            "profile. Maximum 5 search_catalog and 5 get_product calls."
        ),
    )
    parser.add_argument(
        "--output-dir",
        type=Path,
        default=DEFAULT_OUTPUT_DIR,
        help="Live summary directory. Must be outside the repository.",
    )
    args = parser.parse_args(argv)
    if OWNER_LIVE_HARNESS_RUN_BY_CURSOR:
        print(_NOT_RUN_MESSAGE, file=sys.stderr)
        return 2
    if not args.live:
        print(_NOT_RUN_MESSAGE)
        return 2
    profile = staging_normalization_profile()
    try:
        summary = run_shopify_normalization_validation(
            _LiveStagingCatalogTransport(),
            profile_url=profile.url,
            live=True,
        )
        path = write_normalization_summary(summary, args.output_dir, live=True)
    except (ShopifyNormalizationHarnessError, ProbeContractError, RuntimeError) as exc:
        print(f"normalization validation failed closed: {exc}", file=sys.stderr)
        return 1
    print(path)
    print("production_certification=false")
    print("sprint_38_started=false")
    print("raw_response_persistence=false")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

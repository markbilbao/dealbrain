#!/usr/bin/env python3
"""Owner-run Shopify Global Catalog normalization validation.

Cursor must not execute this script. It is not Sprint 38 and it does not
certify production. Without ``--live`` it makes no network call.

Live mode calls only ``https://catalog.shopify.com/api/ucp/mcp`` with the
exact deployed staging PiqSavi profile, at most 5 ``search_catalog`` calls
and 5 ``get_product`` calls. No ``lookup_catalog``, no pagination, no
credentials, and no raw Shopify payload is written. HTTP 429 fails closed
with sanitized retry metadata and is not retried.

Usage (owner only):
  uv run python scripts/shopify_global_catalog_normalization_validation.py --live \\
    --output-dir /tmp/piqsavi-shopify-normalization-validation
"""

from __future__ import annotations

import argparse
import json
import re
import sys
from dataclasses import dataclass
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from app.research.shopify_global_catalog_normalization_harness import (  # noqa: E402
    OWNER_HARNESS_USER_AGENT,
    OWNER_LIVE_HARNESS_RUN_BY_CURSOR,
    ShopifyNormalizationHarnessError,
    assert_summary_has_no_raw_payload,
    run_shopify_normalization_validation,
    staging_normalization_profile,
    write_normalization_summary,
)
from app.research.shopify_global_catalog_ph_probe import (  # noqa: E402
    FORBIDDEN_LOOKUP_TOOL,
    GET_PRODUCT_TOOL,
    GLOBAL_CATALOG_ENDPOINT,
    SEARCH_TOOL,
    LiveProbeOutputInsideRepositoryError,
    ProbeContractError,
    anonymous_http_headers,
    assert_live_probe_output_outside_repository,
)

FAILURE_ARTIFACT_NAME = "shopify-normalization-validation-failure.json"
SUCCESS_SUMMARY_NAME = "shopify-normalization-validation-summary.json"
_RETRY_AFTER_DELTA_SECONDS = re.compile(r"^\d{1,8}$")
_RETRY_AFTER_HTTP_DATE = re.compile(
    r"^(?:Mon|Tue|Wed|Thu|Fri|Sat|Sun), \d{2} "
    r"(?:Jan|Feb|Mar|Apr|May|Jun|Jul|Aug|Sep|Oct|Nov|Dec) "
    r"\d{4} \d{2}:\d{2}:\d{2} GMT$"
)

DEFAULT_OUTPUT_DIR = Path("/tmp/piqsavi-shopify-normalization-validation")
_NOT_RUN_MESSAGE = (
    "Owner live Shopify normalization validation was not run. "
    "Pass --live only from an owner workstation. "
    "Cursor must not execute this harness."
)


@dataclass(frozen=True, slots=True)
class ShopifyNormalizationRateLimitError(RuntimeError):
    """HTTP 429 from Global Catalog. Sanitized metadata only. No retry."""

    retry_after: str
    failed_tool: str
    jsonrpc_request_id: int
    logical_search_operations_attempted: int
    logical_search_operations_completed: int
    logical_get_product_operations_attempted: int
    logical_get_product_operations_completed: int
    network_http_requests_attempted: int
    http_status: int = 429

    def __post_init__(self) -> None:
        if self.http_status != 429:
            raise ShopifyNormalizationHarnessError("rate-limit failure is HTTP 429 only")
        if self.retry_after != "unknown" and not _retry_after_is_reportable(self.retry_after):
            raise ShopifyNormalizationHarnessError("retry-after value is not reportable")

    def __str__(self) -> str:
        return "rate_limit"


class _CatalogHttpStatus(Exception):
    """Internal HTTP status. Carries no response body."""

    def __init__(self, status_code: int, retry_after: str | None) -> None:
        self.status_code = status_code
        self.retry_after = retry_after
        super().__init__(status_code)


class _LiveStagingCatalogTransport:
    """Anonymous JSON-RPC caller. No credentials. Owner --live path only.

    One logical tool operation attempts exactly one HTTP request. HTTP 429
    fails closed and is not retried.
    """

    def __init__(self, *, timeout: float = 30.0) -> None:
        self.timeout = timeout
        self._next_id = 1
        self.logical_search_operations_attempted = 0
        self.logical_search_operations_completed = 0
        self.logical_get_product_operations_attempted = 0
        self.logical_get_product_operations_completed = 0
        self.network_http_requests_attempted = 0

    def call_tool(self, name: str, arguments: dict[str, Any]) -> dict[str, Any]:
        if name == FORBIDDEN_LOOKUP_TOOL:
            raise ShopifyNormalizationHarnessError("lookup_catalog prohibited")
        if name not in {SEARCH_TOOL, GET_PRODUCT_TOOL}:
            raise ShopifyNormalizationHarnessError("unsupported catalog tool")
        request_id = self._next_id
        self._next_id += 1
        self._record_attempt(name)
        request = {
            "jsonrpc": "2.0",
            "method": "tools/call",
            "id": request_id,
            "params": {"name": name, "arguments": arguments},
        }
        try:
            payload = _post_anonymous_catalog(
                request,
                timeout=self.timeout,
                record_http_attempt=self._record_http_attempt,
            )
        except _CatalogHttpStatus as exc:
            if exc.status_code == 429:
                raise self._rate_limit_error(name, request_id, exc.retry_after) from None
            raise RuntimeError(f"Shopify Global Catalog HTTP {exc.status_code}") from None
        self._record_completed(name)
        return payload

    def _record_attempt(self, name: str) -> None:
        if name == SEARCH_TOOL:
            self.logical_search_operations_attempted += 1
        elif name == GET_PRODUCT_TOOL:
            self.logical_get_product_operations_attempted += 1

    def _record_completed(self, name: str) -> None:
        if name == SEARCH_TOOL:
            self.logical_search_operations_completed += 1
        elif name == GET_PRODUCT_TOOL:
            self.logical_get_product_operations_completed += 1

    def _record_http_attempt(self) -> None:
        self.network_http_requests_attempted += 1

    def _rate_limit_error(
        self,
        name: str,
        request_id: int,
        retry_after: str | None,
    ) -> ShopifyNormalizationRateLimitError:
        return ShopifyNormalizationRateLimitError(
            retry_after=_sanitize_retry_after(retry_after),
            failed_tool=name,
            jsonrpc_request_id=request_id,
            logical_search_operations_attempted=self.logical_search_operations_attempted,
            logical_search_operations_completed=self.logical_search_operations_completed,
            logical_get_product_operations_attempted=(
                self.logical_get_product_operations_attempted
            ),
            logical_get_product_operations_completed=(
                self.logical_get_product_operations_completed
            ),
            network_http_requests_attempted=self.network_http_requests_attempted,
        )


def _retry_after_is_reportable(value: str) -> bool:
    return bool(
        _RETRY_AFTER_DELTA_SECONDS.fullmatch(value) or _RETRY_AFTER_HTTP_DATE.fullmatch(value)
    )


def _sanitize_retry_after(value: str | None) -> str:
    """Return a delay-seconds or HTTP-date, or unknown. Never invent a delay."""

    if value is None:
        return "unknown"
    text = value.strip()
    if _retry_after_is_reportable(text):
        return text
    return "unknown"


def _retry_after_header(headers: Any) -> str | None:
    if headers is None:
        return None
    getter = getattr(headers, "get", None)
    if not callable(getter):
        return None
    value = getter("Retry-After")
    if value is None:
        return None
    return str(value)


def _post_anonymous_catalog(
    request: dict[str, Any],
    *,
    timeout: float,
    record_http_attempt: Any,
) -> dict[str, Any]:
    import httpx

    headers = anonymous_http_headers()
    if headers.get("User-Agent") != OWNER_HARNESS_USER_AGENT:
        raise ProbeContractError("owner harness User-Agent drifted from the Sprint 32 probe")
    if "Authorization" in headers or any(key.lower().startswith("signature") for key in headers):
        raise ProbeContractError("owner harness must not send credentials or signatures")
    record_http_attempt()
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
        status_code = exc.response.status_code
        retry_after = _retry_after_header(exc.response.headers) if status_code == 429 else None
        raise _CatalogHttpStatus(status_code, retry_after) from None
    except httpx.HTTPError:
        raise RuntimeError("Shopify Global Catalog request failed") from None
    if not isinstance(payload, dict):
        raise RuntimeError("Shopify Global Catalog returned a non-object response")
    return payload


def rate_limit_failure_artifact(error: ShopifyNormalizationRateLimitError) -> dict[str, Any]:
    """Minimized 429 failure record. Not certification evidence."""

    payload = {
        "generated_at": datetime.now(UTC).isoformat(),
        "failure_kind": "rate_limit",
        "http_status": 429,
        "retry_after": error.retry_after,
        "failed_tool": error.failed_tool,
        "jsonrpc_request_id": error.jsonrpc_request_id,
        "logical_search_attempted": error.logical_search_operations_attempted,
        "logical_search_completed": error.logical_search_operations_completed,
        "logical_get_product_attempted": error.logical_get_product_operations_attempted,
        "logical_get_product_completed": error.logical_get_product_operations_completed,
        "network_http_requests_attempted": error.network_http_requests_attempted,
        "production_certification": False,
        "sprint_38_started": False,
        "sprint_32_closed": False,
        "raw_payload_persisted": False,
    }
    assert_summary_has_no_raw_payload(payload)
    return payload


def write_rate_limit_failure_artifact(
    error: ShopifyNormalizationRateLimitError,
    output_dir: Path,
) -> Path:
    """Write the failure artifact only outside the repository."""

    resolved = assert_live_probe_output_outside_repository(output_dir)
    payload = rate_limit_failure_artifact(error)
    resolved.mkdir(parents=True, exist_ok=True)
    path = resolved / FAILURE_ARTIFACT_NAME
    path.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    return path


def report_rate_limit_failure(
    error: ShopifyNormalizationRateLimitError,
    output_dir: Path,
) -> Path | None:
    """Print sanitized 429 metadata and optionally write the failure artifact."""

    lines = (
        "normalization validation failed closed: rate_limit",
        "http_status=429",
        f"retry_after={error.retry_after}",
        f"failed_tool={error.failed_tool}",
        f"jsonrpc_request_id={error.jsonrpc_request_id}",
        f"logical_search_operations_attempted={error.logical_search_operations_attempted}",
        f"logical_search_operations_completed={error.logical_search_operations_completed}",
        (
            "logical_get_product_operations_attempted="
            f"{error.logical_get_product_operations_attempted}"
        ),
        (
            "logical_get_product_operations_completed="
            f"{error.logical_get_product_operations_completed}"
        ),
        f"network_http_requests_attempted={error.network_http_requests_attempted}",
        "production_certification=false",
        "sprint_38_started=false",
        "sprint_32_closed=false",
        "raw_payload_persisted=false",
    )
    print("\n".join(lines), file=sys.stderr)
    try:
        return write_rate_limit_failure_artifact(error, output_dir)
    except LiveProbeOutputInsideRepositoryError:
        print("rate-limit failure artifact refused inside the repository", file=sys.stderr)
        return None


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
    except ShopifyNormalizationRateLimitError as exc:
        report_rate_limit_failure(exc, args.output_dir)
        return 1
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

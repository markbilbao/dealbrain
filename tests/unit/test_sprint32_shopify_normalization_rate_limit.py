"""Sprint 32 owner harness HTTP 429 reporting. Tests do not call Shopify."""

from __future__ import annotations

import json
from pathlib import Path

import httpx
import pytest
from app.research.certification import production_research_provider_certification_catalog
from app.research.certification_evidence import (
    production_research_provider_certification_evidence_catalog,
)
from app.research.registry import production_research_provider_registry
from app.research.routing import production_research_provider_routing_policy_catalog
from app.research.shopify_global_catalog_normalization_harness import (
    MAX_GET_PRODUCT_CALLS,
    MAX_SEARCH_CATALOG_CALLS,
)
from app.research.shopify_global_catalog_ph_probe import GET_PRODUCT_TOOL, SEARCH_TOOL
from scripts.shopify_global_catalog_normalization_validation import (
    FAILURE_ARTIFACT_NAME,
    SUCCESS_SUMMARY_NAME,
    ShopifyNormalizationRateLimitError,
    _LiveStagingCatalogTransport,
    main as harness_main,
)

ROOT = Path(__file__).resolve().parents[2]
SPRINT32 = ROOT / "docs/roadmap/sprints/SPRINT_32_PHILIPPINES_MERCHANT_CERTIFICATION.md"
SPRINT38 = ROOT / "docs/roadmap/sprints/SPRINT_38_CONNECTOR_RELIABILITY_DEGRADATION.md"
SPRINT41 = ROOT / "docs/roadmap/sprints/SPRINT_41_PRODUCTION_ENVIRONMENT_DEPLOY.md"
_BODY = (
    '{"id":"gid://shopify/Product/secret-product","title":"Secret Earbuds",'
    '"seller":"Secret Seller","variant_id":"gid://shopify/ProductVariant/secret-variant"}'
)
_COOKIE = "session=secret-cookie"
_CREDENTIAL = "Bearer secret-token"


class _RecordingPost:
    def __init__(self, responses: list[httpx.Response]) -> None:
        self.responses = list(responses)
        self.calls: list[dict] = []

    def __call__(self, url: str, **kwargs: object) -> httpx.Response:
        self.calls.append({"url": url, "kwargs": kwargs})
        if not self.responses:
            raise AssertionError("unexpected extra Shopify HTTP attempt")
        return self.responses.pop(0)


def _response(
    status_code: int,
    *,
    headers: dict[str, str] | None = None,
    body: str = _BODY,
) -> httpx.Response:
    request = httpx.Request("POST", "https://catalog.shopify.com/api/ucp/mcp")
    merged = {
        "Set-Cookie": _COOKIE,
        "Authorization": _CREDENTIAL,
        "X-Product-Id": "gid://shopify/Product/header-product",
    }
    if headers:
        merged.update(headers)
    return httpx.Response(status_code, headers=merged, text=body, request=request)


def _ok() -> httpx.Response:
    return _response(200, body='{"jsonrpc":"2.0","id":1,"result":{}}')


def _install(monkeypatch: pytest.MonkeyPatch, responses: list[httpx.Response]) -> _RecordingPost:
    recorder = _RecordingPost(responses)
    monkeypatch.setattr(httpx, "post", recorder)
    return recorder


def _assert_no_sensitive_text(text: str) -> None:
    folded = text.casefold()
    assert "gid://shopify/" not in folded
    assert "secret earbuds" not in folded
    assert "secret seller" not in folded
    assert "secret-product" not in folded
    assert "secret-variant" not in folded
    assert "secret-cookie" not in folded
    assert "secret-token" not in folded
    assert "set-cookie" not in folded
    assert _BODY not in text
    assert "header-product" not in folded


def test_http_429_fails_closed_without_retry_or_success_summary(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
    capsys: pytest.CaptureFixture[str],
) -> None:
    recorder = _install(monkeypatch, [_response(429, headers={"Retry-After": "17"})])
    output = tmp_path / "owner-out"
    code = harness_main(["--live", "--output-dir", str(output)])
    captured = capsys.readouterr()
    assert code == 1
    assert len(recorder.calls) == 1
    assert recorder.calls[0]["url"] == "https://catalog.shopify.com/api/ucp/mcp"
    assert "http_status=429" in captured.err
    assert "failed_tool=search_catalog" in captured.err
    assert "jsonrpc_request_id=1" in captured.err
    assert "retry_after=17" in captured.err
    assert "logical_search_operations_attempted=1" in captured.err
    assert "logical_search_operations_completed=0" in captured.err
    assert "logical_get_product_operations_attempted=0" in captured.err
    assert "logical_get_product_operations_completed=0" in captured.err
    assert "network_http_requests_attempted=1" in captured.err
    assert "production_certification=false" in captured.err
    assert captured.out == ""
    assert not (output / SUCCESS_SUMMARY_NAME).exists()
    _assert_no_sensitive_text(captured.err)
    artifact = json.loads((output / FAILURE_ARTIFACT_NAME).read_text(encoding="utf-8"))
    assert artifact["failure_kind"] == "rate_limit"
    assert artifact["http_status"] == 429
    assert artifact["retry_after"] == "17"
    assert artifact["failed_tool"] == "search_catalog"
    assert artifact["jsonrpc_request_id"] == 1
    assert artifact["logical_search_attempted"] == 1
    assert artifact["logical_search_completed"] == 0
    assert artifact["logical_get_product_attempted"] == 0
    assert artifact["logical_get_product_completed"] == 0
    assert artifact["network_http_requests_attempted"] == 1
    assert artifact["production_certification"] is False
    assert artifact["sprint_38_started"] is False
    assert artifact["sprint_32_closed"] is False
    assert artifact["raw_payload_persisted"] is False
    _assert_no_sensitive_text(json.dumps(artifact))


def test_missing_retry_after_is_unknown(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
    capsys: pytest.CaptureFixture[str],
) -> None:
    _install(monkeypatch, [_response(429)])
    code = harness_main(["--live", "--output-dir", str(tmp_path)])
    captured = capsys.readouterr()
    assert code == 1
    assert "retry_after=unknown" in captured.err
    artifact = json.loads((tmp_path / FAILURE_ARTIFACT_NAME).read_text(encoding="utf-8"))
    assert artifact["retry_after"] == "unknown"


def test_unsafe_retry_after_is_not_echoed(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
    capsys: pytest.CaptureFixture[str],
) -> None:
    _install(
        monkeypatch,
        [_response(429, headers={"Retry-After": "gid://shopify/Product/secret-product"})],
    )
    code = harness_main(["--live", "--output-dir", str(tmp_path)])
    captured = capsys.readouterr()
    assert code == 1
    assert "retry_after=unknown" in captured.err
    _assert_no_sensitive_text(captured.err)


def test_http_date_retry_after_is_surfaced(
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
    tmp_path: Path,
) -> None:
    _install(
        monkeypatch,
        [_response(429, headers={"Retry-After": "Fri, 25 Sep 2026 00:33:00 GMT"})],
    )
    code = harness_main(["--live", "--output-dir", str(tmp_path)])
    captured = capsys.readouterr()
    assert code == 1
    assert "retry_after=Fri, 25 Sep 2026 00:33:00 GMT" in captured.err


def test_call_accounting_distinguishes_attempted_and_completed(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    recorder = _install(monkeypatch, [_ok(), _ok(), _response(429, headers={"Retry-After": "30"})])
    transport = _LiveStagingCatalogTransport()
    assert transport.call_tool(SEARCH_TOOL, {})["result"] == {}
    assert transport.call_tool(SEARCH_TOOL, {})["result"] == {}
    with pytest.raises(ShopifyNormalizationRateLimitError) as caught:
        transport.call_tool(GET_PRODUCT_TOOL, {})
    error = caught.value
    assert error.failed_tool == GET_PRODUCT_TOOL
    assert error.jsonrpc_request_id == 3
    assert error.logical_search_operations_attempted == 2
    assert error.logical_search_operations_completed == 2
    assert error.logical_get_product_operations_attempted == 1
    assert error.logical_get_product_operations_completed == 0
    assert error.network_http_requests_attempted == 3
    assert len(recorder.calls) == error.network_http_requests_attempted
    assert str(error) == "rate_limit"
    _assert_no_sensitive_text(str(error))
    assert MAX_SEARCH_CATALOG_CALLS == 5
    assert MAX_GET_PRODUCT_CALLS == 5


def test_rate_limit_artifact_is_refused_inside_the_repository(
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    _install(monkeypatch, [_response(429, headers={"Retry-After": "8"})])
    inside = ROOT / "not-committed-rate-limit"
    code = harness_main(["--live", "--output-dir", str(inside)])
    captured = capsys.readouterr()
    assert code == 1
    assert "retry_after=8" in captured.err
    assert "refused inside the repository" in captured.err
    assert not inside.exists()


def test_non_429_http_failure_does_not_write_success_or_rate_limit_artifact(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
    capsys: pytest.CaptureFixture[str],
) -> None:
    recorder = _install(monkeypatch, [_response(422, body=_BODY)])
    code = harness_main(["--live", "--output-dir", str(tmp_path)])
    captured = capsys.readouterr()
    assert code == 1
    assert len(recorder.calls) == 1
    assert "HTTP 422" in captured.err
    assert not (tmp_path / SUCCESS_SUMMARY_NAME).exists()
    assert not (tmp_path / FAILURE_ARTIFACT_NAME).exists()
    _assert_no_sensitive_text(captured.err)


def test_production_catalogs_and_sprint_status_stay_unchanged() -> None:
    assert len(production_research_provider_registry().list_providers()) == 0
    assert len(production_research_provider_certification_catalog().list_records()) == 0
    assert len(production_research_provider_certification_evidence_catalog().list_records()) == 4
    assert len(production_research_provider_routing_policy_catalog().list_records()) == 0
    sprint32 = SPRINT32.read_text(encoding="utf-8")
    sprint38 = SPRINT38.read_text(encoding="utf-8")
    sprint41 = SPRINT41.read_text(encoding="utf-8")
    assert "2026-09-25" in sprint32
    assert "HTTP 429" in sprint32
    assert "failed closed" in sprint32.casefold()
    assert "Successful 5/5 normalization validation was not obtained." in sprint32
    assert "not a provider rejection" in sprint32
    assert "Sprint 32 remains open." in sprint32
    assert "Sprint 38 remains unstarted" in sprint32
    assert "Sprint 41 remains unstarted" in sprint32
    assert "No AWS mutation." in sprint32
    assert "No deployment." in sprint32
    assert "No Sprint 38 execution." in sprint32
    assert sprint38.split("**Status:**", 1)[1].splitlines()[0].strip() == "Planned"
    sprint41_status = sprint41.split("**Status:**", 1)[1].splitlines()[0].strip()
    assert sprint41_status.startswith("Planned")
    assert "not started" in sprint41_status.casefold()


def test_tests_do_not_call_shopify(monkeypatch: pytest.MonkeyPatch) -> None:
    def _boom(*_args: object, **_kwargs: object) -> httpx.Response:
        raise AssertionError("Shopify must not be called")

    monkeypatch.setattr(httpx, "post", _boom)
    monkeypatch.setattr(httpx, "Client", _boom)
    assert harness_main([]) == 2

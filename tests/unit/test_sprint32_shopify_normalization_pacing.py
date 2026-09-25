"""Sprint 32 owner-harness request pacing. Tests do not call Shopify or sleep."""

from __future__ import annotations

import json
from pathlib import Path

import httpx
import pytest
from app.research.shopify_global_catalog_normalization_harness import (
    MAX_GET_PRODUCT_CALLS,
    MAX_SEARCH_CATALOG_CALLS,
    ShopifyNormalizationHarnessBudget,
    ShopifyNormalizationHarnessError,
    _assert_request_in_bounds,
)
from app.research.shopify_global_catalog_ph_probe import (
    FORBIDDEN_LOOKUP_TOOL,
    GET_PRODUCT_TOOL,
    SEARCH_TOOL,
)
from scripts.shopify_global_catalog_normalization_validation import (
    FAILURE_ARTIFACT_NAME,
    MIN_NETWORK_REQUEST_INTERVAL_SECONDS,
    ShopifyNetworkRequestPacer,
    ShopifyNormalizationRateLimitError,
    _LiveStagingCatalogTransport,
)
from scripts.shopify_global_catalog_normalization_validation import (
    main as harness_main,
)

ROOT = Path(__file__).resolve().parents[2]
SPRINT32 = ROOT / "docs/roadmap/sprints/SPRINT_32_PHILIPPINES_MERCHANT_CERTIFICATION.md"


class FakeClock:
    """Monotonic stand-in. Sleep advances the clock and records durations."""

    def __init__(self) -> None:
        self.now = 0.0
        self.sleeps: list[float] = []

    def __call__(self) -> float:
        return self.now

    def sleep(self, seconds: float) -> None:
        self.sleeps.append(seconds)
        self.now += seconds

    def advance(self, seconds: float) -> None:
        self.now += seconds


class _RecordingPost:
    def __init__(self, responses: list[httpx.Response]) -> None:
        self.responses = list(responses)
        self.calls: list[dict] = []

    def __call__(self, url: str, **kwargs: object) -> httpx.Response:
        self.calls.append({"url": url, "kwargs": kwargs})
        if not self.responses:
            raise AssertionError("unexpected extra Shopify HTTP attempt")
        return self.responses.pop(0)


def _response(status_code: int, *, headers: dict[str, str] | None = None) -> httpx.Response:
    request = httpx.Request("POST", "https://catalog.shopify.com/api/ucp/mcp")
    body = '{"jsonrpc":"2.0","id":1,"result":{}}' if status_code == 200 else "{}"
    return httpx.Response(status_code, headers=headers, text=body, request=request)


def _ok() -> httpx.Response:
    return _response(200)


def _install(monkeypatch: pytest.MonkeyPatch, responses: list[httpx.Response]) -> _RecordingPost:
    recorder = _RecordingPost(responses)
    monkeypatch.setattr(httpx, "post", recorder)
    return recorder


def test_minimum_interval_is_the_conservative_validation_cadence() -> None:
    assert MIN_NETWORK_REQUEST_INTERVAL_SECONDS == 1.25


def test_first_request_sleeps_zero_and_immediate_second_sleeps_remainder() -> None:
    clock = FakeClock()
    pacer = ShopifyNetworkRequestPacer(clock=clock, sleeper=clock.sleep)
    assert pacer.before_http_request() == 0
    assert clock.sleeps == []
    assert pacer.before_http_request() == MIN_NETWORK_REQUEST_INTERVAL_SECONDS
    assert clock.sleeps == [MIN_NETWORK_REQUEST_INTERVAL_SECONDS]
    assert pacer.pacing_sleep_count == 1
    assert pacer.total_pacing_sleep_seconds == MIN_NETWORK_REQUEST_INTERVAL_SECONDS


def test_enough_elapsed_time_causes_no_sleep() -> None:
    clock = FakeClock()
    pacer = ShopifyNetworkRequestPacer(clock=clock, sleeper=clock.sleep)
    pacer.before_http_request()
    clock.advance(MIN_NETWORK_REQUEST_INTERVAL_SECONDS)
    assert pacer.before_http_request() == 0
    assert clock.sleeps == []
    assert pacer.pacing_sleep_count == 0


def test_partial_elapsed_time_sleeps_only_the_remainder() -> None:
    clock = FakeClock()
    pacer = ShopifyNetworkRequestPacer(clock=clock, sleeper=clock.sleep)
    pacer.before_http_request()
    clock.advance(0.25)
    assert pacer.before_http_request() == 1.0
    assert clock.sleeps == [1.0]


def test_search_to_get_product_keeps_one_shared_cadence(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    clock = FakeClock()
    recorder = _install(monkeypatch, [_ok(), _ok()])
    transport = _LiveStagingCatalogTransport(clock=clock, sleeper=clock.sleep)
    transport.call_tool(SEARCH_TOOL, {})
    transport.call_tool(GET_PRODUCT_TOOL, {})
    assert clock.sleeps == [MIN_NETWORK_REQUEST_INTERVAL_SECONDS]
    assert len(recorder.calls) == 2
    assert transport.network_http_requests_attempted == 2
    assert transport.logical_search_operations_completed == 1
    assert transport.logical_get_product_operations_completed == 1


def test_pacing_does_not_add_http_requests_or_retries_and_429_fails_closed(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    clock = FakeClock()
    responses = [_ok() for _ in range(MAX_SEARCH_CATALOG_CALLS)]
    responses.append(_response(429, headers={"Retry-After": "1"}))
    recorder = _install(monkeypatch, responses)
    transport = _LiveStagingCatalogTransport(clock=clock, sleeper=clock.sleep)
    for _ in range(MAX_SEARCH_CATALOG_CALLS):
        transport.call_tool(SEARCH_TOOL, {"query": "category"})
    with pytest.raises(ShopifyNormalizationRateLimitError) as caught:
        transport.call_tool(GET_PRODUCT_TOOL, {"id": "not-persisted"})
    error = caught.value
    assert len(recorder.calls) == MAX_SEARCH_CATALOG_CALLS + 1
    assert error.network_http_requests_attempted == len(recorder.calls)
    assert error.logical_search_operations_attempted == 5
    assert error.logical_search_operations_completed == 5
    assert error.logical_get_product_operations_attempted == 1
    assert error.logical_get_product_operations_completed == 0
    assert error.failed_tool == GET_PRODUCT_TOOL
    assert error.jsonrpc_request_id == 6
    assert error.retry_after == "1"
    assert error.pacing_sleep_count == 5
    assert error.total_pacing_sleep_seconds == 5 * MIN_NETWORK_REQUEST_INTERVAL_SECONDS
    assert clock.sleeps == [MIN_NETWORK_REQUEST_INTERVAL_SECONDS] * 5
    assert 1.0 not in clock.sleeps
    assert error.http_status == 429
    assert str(error) == "rate_limit"
    assert "not-persisted" not in str(error)


def test_harness_429_records_sanitized_pacing_and_does_not_retry(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
    capsys: pytest.CaptureFixture[str],
) -> None:
    recorder = _install(
        monkeypatch,
        [_response(429, headers={"Retry-After": "1", "Set-Cookie": "session=secret"})],
    )
    output = tmp_path / "paced"
    code = harness_main(["--live", "--output-dir", str(output)])
    captured = capsys.readouterr()
    assert code == 1
    assert len(recorder.calls) == 1
    assert "retry_after=1" in captured.err
    assert "minimum_request_interval_seconds=1.25" in captured.err
    assert "pacing_sleep_count=0" in captured.err
    assert "total_pacing_sleep_seconds=0.0" in captured.err
    assert "secret" not in captured.err
    artifact = json.loads((output / FAILURE_ARTIFACT_NAME).read_text(encoding="utf-8"))
    assert artifact["minimum_request_interval_seconds"] == 1.25
    assert artifact["pacing_sleep_count"] == 0
    assert artifact["total_pacing_sleep_seconds"] == 0.0
    assert artifact["retry_after"] == "1"
    assert artifact["http_status"] == 429
    assert "secret" not in json.dumps(artifact)
    assert "gid://shopify/" not in json.dumps(artifact)


def test_retry_after_does_not_change_the_pacing_sleep(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    clock = FakeClock()
    recorder = _install(monkeypatch, [_ok(), _response(429, headers={"Retry-After": "1"})])
    transport = _LiveStagingCatalogTransport(clock=clock, sleeper=clock.sleep)
    transport.call_tool(SEARCH_TOOL, {})
    with pytest.raises(ShopifyNormalizationRateLimitError) as caught:
        transport.call_tool(GET_PRODUCT_TOOL, {})
    assert caught.value.retry_after == "1"
    assert clock.sleeps == [MIN_NETWORK_REQUEST_INTERVAL_SECONDS]
    assert len(recorder.calls) == 2


def test_operation_caps_lookup_and_pagination_stay_prohibited() -> None:
    assert MAX_SEARCH_CATALOG_CALLS == 5
    assert MAX_GET_PRODUCT_CALLS == 5
    budget = ShopifyNormalizationHarnessBudget()
    for _ in range(5):
        budget.consume_search()
        budget.consume_get_product()
    with pytest.raises(ShopifyNormalizationHarnessError, match="search_catalog budget exceeded"):
        budget.consume_search()
    with pytest.raises(ShopifyNormalizationHarnessError, match="get_product budget exceeded"):
        budget.consume_get_product()
    with pytest.raises(ShopifyNormalizationHarnessError, match="lookup_catalog prohibited"):
        budget.reject_lookup()
    with pytest.raises(ShopifyNormalizationHarnessError, match="pagination prohibited"):
        budget.reject_pagination()
    with pytest.raises(ShopifyNormalizationHarnessError, match="lookup_catalog prohibited"):
        _assert_request_in_bounds(FORBIDDEN_LOOKUP_TOOL, {})
    with pytest.raises(ShopifyNormalizationHarnessError, match="pagination prohibited"):
        _assert_request_in_bounds(
            SEARCH_TOOL,
            {"catalog": {"pagination": {"cursor": "next-page"}}},
        )


def test_live_transport_rejects_lookup_without_an_http_call(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    clock = FakeClock()
    recorder = _install(monkeypatch, [_ok()])
    transport = _LiveStagingCatalogTransport(clock=clock, sleeper=clock.sleep)
    with pytest.raises(ShopifyNormalizationHarnessError, match="lookup_catalog prohibited"):
        transport.call_tool(FORBIDDEN_LOOKUP_TOOL, {})
    assert recorder.calls == []
    assert clock.sleeps == []
    assert transport.network_http_requests_attempted == 0


def test_attempt_two_is_recorded_separately_and_is_not_certification() -> None:
    sprint32 = SPRINT32.read_text(encoding="utf-8")
    attempt_1, attempt_2 = sprint32.split(
        "### 2026-09-25 owner live normalization validation attempt #2",
        maxsplit=1,
    )
    assert "attempt #1" in attempt_1
    assert "How many Shopify calls completed before the HTTP 429 is not recorded here." in (
        attempt_1
    )
    assert "5 `search_catalog` logical operations completed." in attempt_2
    assert "0 `get_product` logical operations completed." in attempt_2
    assert "JSON-RPC request id 6." in attempt_2
    assert "network HTTP request #6." in attempt_2
    assert "Retry-After = 1 second." in attempt_2
    assert "Successful 5/5 normalization validation was not obtained." in attempt_2
    assert "not full certification success" in attempt_2
    assert "Detail/`get_product` validation did not complete." in attempt_2
    assert "not a provider rejection" in attempt_2
    assert "Sprint 32 remains open." in attempt_2
    assert "Sprint 38 remains unstarted." in attempt_2
    assert "Sprint 41 remains unstarted." in attempt_2
    assert "No PiqSavi AWS infrastructure/resource mutation and no deployment." in attempt_2
    assert "fresh output directory" in attempt_2.casefold()
    assert "exact merged harness from main" in attempt_2.casefold()

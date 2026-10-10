"""Sprint 40.5 URL trust-boundary regressions.

These tests do not open a socket and do not call Shopify.
"""

from __future__ import annotations

import io
import urllib.error
import urllib.request
from email.message import Message
from pathlib import Path

import pytest
from app.affiliate.linking.builder import AffiliateLinkBuilder
from app.consumer.pages import _offer_link
from app.domain.entities.marketplace_data import SourceMode
from app.domain.exceptions import AffiliateValidationError, MerchantValidationError
from app.marketplace.normalization.normalizer import MarketplaceRecordNormalizer
from app.marketplace.security import validate_url
from app.merchant.security.validation import validate_safe_url
from app.research.shopify_global_catalog_execution import GLOBAL_CATALOG_ENDPOINT
from app.research.shopify_global_catalog_ph_probe import anonymous_http_headers
from app.research.shopify_global_catalog_transport import (
    SHOPIFY_PRODUCTION_CATALOG_ENDPOINT,
    UrllibJsonTransport,
    _RefuseRedirectHandler,
)
from app.schemas.product import ProductCreate
from app.security.url_trust import (
    UrlTrustError,
    validate_browser_destination,
    validate_server_fetch_url,
)
from pydantic import ValidationError

ROOT = Path(__file__).resolve().parents[2]
START_SHA = "5dbc52295a38d056bca9347f7a69f605b3ad7414"
QUERY_URL = "https://www.lazada.com.ph/example?id=1&utm=piq"
APPROVED_HTTPS = "https://example.com/path?q=1&utm=a"

_SERVER_REJECTED = (
    "https://localhost/admin",
    "https://localhost./admin",
    "https://LOCALHOST/admin",
    "https://api.localhost/admin",
    "https://127.0.0.1/",
    "https://127.0.0.1:80/",
    "https://[::1]/",
    "https://10.1.2.3/",
    "https://192.168.1.20/x",
    "https://172.16.5.5/",
    "https://[fc00::1]/",
    "https://[fd12:3456:789a::1]/",
    "https://169.254.169.254/latest/meta-data",
    "https://[fe80::1]/",
    "https://0.0.0.0/",
    "https://[::]/",
    "https://224.0.0.1/",
    "https://[ff02::1]/",
    "https://[::ffff:127.0.0.1]/",
    "https://[::ffff:10.0.0.1]/",
    "https://[0:0:0:0:0:ffff:127.0.0.1]/",
    "https://user:pass@example.com/",
    "https://user@example.com/",
    "https://example.com:99999/",
    "https://",
    "https://[::1",
    "file:///etc/passwd",
    "ftp://example.com/",
    "gopher://example.com/",
    "javascript:alert(1)",
    "http://example.com/",
    "http://127.0.0.1/",
    "https://2130706433/",
    "https://0x7f000001/",
    "https://0177.0.0.1/",
    "https://127.1/",
    "https://0/",
    "https://example.com\\@127.0.0.1/",
    "https://127.0.0.1%00.example.com/",
    "https://example.com\n.evil.com/",
    "https://good.example@evil.example/",
    "https://100.64.0.1/",
    "https://255.255.255.255/",
    "https://192.0.2.1/",
)

_BROWSER_REJECTED = (
    "javascript:alert(1)",
    "file:///etc/passwd",
    "ftp://shop.example/item",
    "https://user:pass@shop.example/item",
    "https://user@shop.example/item",
    "https://shop.example:99999/",
    "https://",
    "https://example.com\\@127.0.0.1/",
    "https://2130706433/",
    "https://0x7f000001/",
    "https://127.1/",
    "https://example.com\n.evil.com/",
    "https://127.0.0.1%00.example.com/",
    "https://[::ffff:127.0.0.1]/",
    "https://[::ffff:10.0.0.1]/",
)


def test_server_fetch_accepts_an_ordinary_https_target() -> None:
    assert validate_server_fetch_url(SHOPIFY_PRODUCTION_CATALOG_ENDPOINT) == (
        SHOPIFY_PRODUCTION_CATALOG_ENDPOINT
    )
    assert validate_server_fetch_url(APPROVED_HTTPS) == APPROVED_HTTPS
    assert validate_server_fetch_url("https://8.8.8.8/dns") == "https://8.8.8.8/dns"


@pytest.mark.parametrize("url", _SERVER_REJECTED)
def test_server_fetch_rejects_unsafe_targets(url: str) -> None:
    with pytest.raises(UrlTrustError):
        validate_server_fetch_url(url)


def test_public_hostname_is_not_resolved(monkeypatch: pytest.MonkeyPatch) -> None:
    def _boom(*_args: object, **_kwargs: object) -> None:
        raise AssertionError("server-fetch validation must not resolve DNS")

    monkeypatch.setattr("app.security.url_trust.socket.getaddrinfo", _boom)
    assert validate_server_fetch_url(APPROVED_HTTPS) == APPROVED_HTTPS
    assert (
        validate_server_fetch_url("https://127.0.0.1.example.com/x")
        == "https://127.0.0.1.example.com/x"
    )


# IDNA compatibility forms, and the canonical hosts they normalize to.
# Server fetch rejects a canonical localhost name or blocked address.
# Browser destinations keep a canonical private address and the localhost name.
# A non-canonical spelling that IDNA-normalizes into a numeric address is rejected
# for both classes. None of these cases resolve DNS.
_IDNA_CASES = (
    ("https://ⓛocalhost/", False, True),
    ("https://ｌocalhost/", False, True),
    ("https://127。0。0。1/", False, False),
    ("https://127．0．0．1/", False, False),
    ("https://localhost/admin", False, True),
    ("https://127.0.0.1/", False, True),
    ("https://münchen.example/shop", True, True),
    ("https://example.com/path", True, True),
)


@pytest.mark.parametrize(("url", "server_ok", "browser_ok"), _IDNA_CASES)
def test_idna_canonical_host_classification(
    monkeypatch: pytest.MonkeyPatch,
    url: str,
    server_ok: bool,
    browser_ok: bool,
) -> None:
    def _boom(*_args: object, **_kwargs: object) -> None:
        raise AssertionError("IDNA classification must not resolve DNS")

    monkeypatch.setattr("app.security.url_trust.socket.getaddrinfo", _boom)
    if server_ok:
        assert validate_server_fetch_url(url) == url
    else:
        with pytest.raises(UrlTrustError):
            validate_server_fetch_url(url)
    if browser_ok:
        assert validate_browser_destination(url) == url
    else:
        with pytest.raises(UrlTrustError):
            validate_browser_destination(url)


def test_browser_destination_keeps_merchant_and_marketplace_urls() -> None:
    assert validate_browser_destination("https://techhaven.demo/products/x1-pro") == (
        "https://techhaven.demo/products/x1-pro"
    )
    assert validate_browser_destination(QUERY_URL) == QUERY_URL
    assert validate_browser_destination("https://imported.dealbrain.local/x?q=1") == (
        "https://imported.dealbrain.local/x?q=1"
    )
    assert validate_browser_destination("http://cdn.example.com/img.png?width=100") == (
        "http://cdn.example.com/img.png?width=100"
    )
    # Canonical private addresses are browser destinations. The server does not fetch them.
    assert validate_browser_destination("https://192.168.1.10/catalog") == (
        "https://192.168.1.10/catalog"
    )
    assert validate_browser_destination("https://127.0.0.1/demo") == "https://127.0.0.1/demo"


@pytest.mark.parametrize("url", _BROWSER_REJECTED)
def test_browser_destination_rejects_ambiguous_or_unsupported_urls(url: str) -> None:
    with pytest.raises(UrlTrustError):
        validate_browser_destination(url)


def test_merchant_links_keep_queries_and_reject_credentials() -> None:
    accepted = "https://techhaven.demo/products/x1?sku=1&utm_source=piq"
    assert validate_safe_url(accepted) == accepted
    with pytest.raises(MerchantValidationError):
        validate_safe_url("https://user:pass@techhaven.demo/x")
    with pytest.raises(MerchantValidationError):
        validate_safe_url("javascript:alert(1)")
    with pytest.raises(MerchantValidationError):
        validate_safe_url("https://evil.demo/x?api_key=secret")


def test_marketplace_url_keeps_a_query_and_rejects_embedded_credentials() -> None:
    tracked = "https://shop.example/item?id=1&token=tracking"
    assert validate_url(tracked) == tracked
    with pytest.raises(ValueError):
        validate_url("https://user:pass@shop.example/item")
    with pytest.raises(ValueError):
        validate_url("javascript:alert(1)")
    builder = AffiliateLinkBuilder()
    assert builder.validate_url(QUERY_URL) == QUERY_URL
    with pytest.raises(AffiliateValidationError):
        builder.validate_url("ftp://bad.example/file")
    with pytest.raises(AffiliateValidationError):
        builder.validate_url("https://user:pass@shop.example/item")


def test_imported_marketplace_url_stays_imported_data() -> None:
    normalizer = MarketplaceRecordNormalizer()
    offer = normalizer.normalize(
        {
            "marketplace_product_id": "imp-1",
            "title": "Imported Phone",
            "sale_price": 10,
            "marketplace_url": QUERY_URL,
            "image_url": "https://cdn.example/img.png?width=100",
        },
        source_mode=SourceMode.IMPORTED,
        source_id="imported",
    )
    assert offer.source_mode is SourceMode.IMPORTED
    assert offer.simulated is False
    assert offer.marketplace_url == QUERY_URL
    assert offer.image_url == "https://cdn.example/img.png?width=100"
    with pytest.raises(ValueError):
        normalizer.normalize(
            {
                "marketplace_product_id": "imp-2",
                "title": "Imported Phone",
                "sale_price": 10,
                "marketplace_url": "https://user:pass@shop.example/item",
            },
            source_mode=SourceMode.IMPORTED,
            source_id="imported",
        )


def test_import_pipeline_rejects_a_credential_url_as_imported_data() -> None:
    from tests.unit.test_marketplace_data_imports import make_service

    service = make_service()
    header = "marketplace_product_id,title,sale_price,marketplace_url\n"
    accepted = service.import_payload(
        filename="ok.csv",
        payload=header + f"ok-1,Phone,10,{QUERY_URL}\n",
        actor="tester",
    )
    assert accepted.records_accepted == 1
    assert accepted.source_mode is SourceMode.IMPORTED
    offers = service.list_offers(source_mode="imported")
    assert offers[0].marketplace_url == QUERY_URL
    assert offers[0].source_mode is SourceMode.IMPORTED
    assert offers[0].simulated is False

    rejected = service.import_payload(
        filename="bad.csv",
        payload=header + "bad-1,Phone,10,https://user:pass@shop.example/item\n",
        actor="tester",
    )
    assert rejected.records_accepted == 0
    assert rejected.records_rejected == 1
    assert rejected.source_mode is SourceMode.IMPORTED


def test_product_image_url_is_a_browser_resource() -> None:
    created = ProductCreate(
        brand="Acme",
        category="Phones",
        model="X1",
        manufacturer_sku="sku-1",
        image_url="https://cdn.example/a.png?w=10",
    )
    assert str(created.image_url) == "https://cdn.example/a.png?w=10"
    with pytest.raises(ValidationError):
        ProductCreate(
            brand="Acme",
            category="Phones",
            model="X1",
            manufacturer_sku="sku-1",
            image_url="javascript:alert(1)",
        )
    with pytest.raises(ValidationError):
        ProductCreate(
            brand="Acme",
            category="Phones",
            model="X1",
            manufacturer_sku="sku-1",
            image_url="https://user:pass@cdn.example/a.png",
        )


def test_consumer_offer_link_renders_a_query_url_and_drops_unsafe_urls() -> None:
    html = _offer_link(QUERY_URL, "btn")
    assert "View offer" in html
    assert "https://www.lazada.com.ph/example?id=1&amp;utm=piq" in html
    assert 'rel="nofollow noopener"' in html
    assert _offer_link("javascript:alert(1)", "btn") == ""
    assert _offer_link("https://user:pass@shop.example/item", "btn") == ""
    assert _offer_link("/", "btn") == ""
    private = _offer_link("https://192.168.1.10/catalog", "btn")
    assert "https://192.168.1.10/catalog" in private


def test_shopify_transport_opens_only_the_fixed_endpoint(monkeypatch: pytest.MonkeyPatch) -> None:
    calls: list[tuple[str, float]] = []

    class _Response:
        status = 200

        def read(self) -> bytes:
            return b'{"jsonrpc":"2.0","result":{}}'

        def __enter__(self) -> _Response:
            return self

        def __exit__(self, *_args: object) -> None:
            return None

    def _open(request: urllib.request.Request, timeout: float) -> _Response:
        calls.append((request.full_url, timeout))
        return _Response()

    monkeypatch.setattr("app.research.shopify_global_catalog_transport._open_http", _open)
    result = UrllibJsonTransport().post_json(
        GLOBAL_CATALOG_ENDPOINT,
        anonymous_http_headers(),
        {"jsonrpc": "2.0"},
        5.0,
    )
    assert calls == [(SHOPIFY_PRODUCTION_CATALOG_ENDPOINT, 5.0)]
    assert result.status_code == 200
    assert result.raw_body_persisted is False
    assert result.payload == {"jsonrpc": "2.0", "result": {}}


@pytest.mark.parametrize(
    "endpoint",
    [
        "https://127.0.0.1/",
        "https://evil.example/api/ucp/mcp",
        "https://catalog.shopify.com/api/ucp/mcp/",
        "https://user:pass@catalog.shopify.com/api/ucp/mcp",
        "http://catalog.shopify.com/api/ucp/mcp",
    ],
)
def test_shopify_transport_does_not_open_an_unapproved_endpoint(
    monkeypatch: pytest.MonkeyPatch,
    endpoint: str,
) -> None:
    def _open(*_args: object, **_kwargs: object) -> None:
        raise AssertionError("unapproved endpoint was opened")

    monkeypatch.setattr("app.research.shopify_global_catalog_transport._open_http", _open)
    result = UrllibJsonTransport().post_json(endpoint, {}, {"jsonrpc": "2.0"}, 5.0)
    assert result.transport_unavailable is True
    assert result.status_code == 0
    assert result.payload is None
    assert result.raw_body_persisted is False


def test_shopify_redirect_to_a_blocked_host_is_not_followed() -> None:
    handler = _RefuseRedirectHandler()

    class _Parent:
        def open(self, *_args: object, **_kwargs: object) -> None:
            raise AssertionError("redirect was followed")

    handler.parent = _Parent()  # type: ignore[assignment]
    request = urllib.request.Request(SHOPIFY_PRODUCTION_CATALOG_ENDPOINT, method="POST")
    headers = Message()
    headers["Location"] = "http://127.0.0.1/secret"
    with pytest.raises(urllib.error.HTTPError) as exc:
        handler.http_error_302(request, io.BytesIO(b"redirect-body"), 302, "Found", headers)
    assert exc.value.code == 302

    headers["Location"] = "https://catalog.shopify.com/elsewhere"
    with pytest.raises(urllib.error.HTTPError) as second:
        handler.http_error_302(request, io.BytesIO(b"redirect-body"), 302, "Found", headers)
    assert second.value.code == 302


def test_shopify_http_redirect_result_is_a_single_response(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    calls: list[str] = []

    def _open(request: urllib.request.Request, timeout: float) -> None:
        del timeout
        calls.append(request.full_url)
        raise urllib.error.HTTPError(
            request.full_url,
            302,
            "Found",
            hdrs=None,  # type: ignore[arg-type]
            fp=io.BytesIO(b""),
        )

    monkeypatch.setattr("app.research.shopify_global_catalog_transport._open_http", _open)
    result = UrllibJsonTransport().post_json(
        SHOPIFY_PRODUCTION_CATALOG_ENDPOINT,
        {},
        {"jsonrpc": "2.0"},
        5.0,
    )
    assert calls == [SHOPIFY_PRODUCTION_CATALOG_ENDPOINT]
    assert result.status_code == 302
    assert result.payload is None
    assert result.raw_body_persisted is False
    assert result.transport_unavailable is False


def test_architecture_lock_keeps_the_server_fetch_check_on_the_transport() -> None:
    transport = (ROOT / "app/research/shopify_global_catalog_transport.py").read_text(
        encoding="utf-8"
    )
    execution = (ROOT / "app/research/shopify_global_catalog_execution.py").read_text(
        encoding="utf-8"
    )
    resend = (ROOT / "app/auth/email_resend.py").read_text(encoding="utf-8")
    ci = (ROOT / ".github/workflows/ci.yml").read_text(encoding="utf-8")
    evidence = (ROOT / "docs/roadmap/evidence/SPRINT_40_5_URL_TRUST_2026-10-10.md").read_text(
        encoding="utf-8"
    )
    sprint = (ROOT / "docs/roadmap/sprints/SPRINT_40_SECURITY_ABUSE_HARDENING.md").read_text(
        encoding="utf-8"
    )

    assert SHOPIFY_PRODUCTION_CATALOG_ENDPOINT == GLOBAL_CATALOG_ENDPOINT
    assert "urlopen" not in transport
    call = transport.split("approved = _approved_catalog_endpoint(endpoint)", 1)[1]
    assert call.index("_open_http") < call.index("except TimeoutError")
    assert "validate_server_fetch_url" in transport
    assert "_RefuseRedirectHandler" in transport
    assert "self._transport.post_json(\n                GLOBAL_CATALOG_ENDPOINT," in execution
    assert "validate_server_fetch_url" in resend
    assert "follow_redirects=False" in resend
    assert "approved != RESEND_EMAILS_URL" in resend
    assert "tests/unit/test_sprint40_5_url_trust.py" in ci
    assert START_SHA in evidence
    assert "IMPLEMENTED-NOT-PROVEN" in evidence
    assert "Not ENGINEERING COMPLETE" in evidence
    assert "No reachable SSRF exploit is demonstrated." in evidence
    assert "not closed and not PROVEN" in evidence
    assert "CSP `'unsafe-inline'`" in evidence
    assert "R6 stays PARTIAL" in evidence
    assert "Class C count remains 19" in evidence
    assert "selected next engineering slice remains NONE" in evidence
    assert "Sprint 41 stays UNSTARTED" in evidence
    assert "No deploy was performed." in evidence
    assert "Routing stays 0." in evidence
    assert "**Status:** Planned" in sprint
    assert "Sprint 40.5" in sprint
    assert "ENGINEERING COMPLETE" not in evidence.split("Not ENGINEERING COMPLETE")[0]

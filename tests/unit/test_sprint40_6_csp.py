"""Sprint 40.6 Content-Security-Policy regressions.

These tests do not deploy and do not call Shopify.
"""

from __future__ import annotations

import re
from pathlib import Path

import pytest
from app.core.config import DEFAULT_SECURITY_CSP, Settings, get_settings
from app.main import create_app
from fastapi.testclient import TestClient

ROOT = Path(__file__).resolve().parents[2]
START_SHA = "c0c341187515d480bb4318c26c085d44a16af14e"
OLD_CSP = (
    "default-src 'self'; "
    "script-src 'self' 'unsafe-inline'; "
    "style-src 'self' 'unsafe-inline'; "
    "img-src 'self' data: https:; "
    "connect-src 'self'; "
    "frame-ancestors 'none'; "
    "base-uri 'self'; "
    "form-action 'self'"
)

_SCRIPT = re.compile(r"<script\b([^>]*)>(.*?)</script>", re.IGNORECASE | re.DOTALL)
_EVENT = re.compile(r"""\son[a-z]+\s*=""", re.IGNORECASE)
_STYLE_ATTR = re.compile(r"""\sstyle\s*=""", re.IGNORECASE)
_STYLE_TAG = re.compile(r"<style\b", re.IGNORECASE)
_JS_URL = re.compile(r"javascript\s*:", re.IGNORECASE)
_STRING_TIMER = re.compile(r"""set(?:Timeout|Interval)\(\s*['"]""")

PRODUCT_PAGES = (
    "/",
    "/privacy",
    "/terms",
    "/login",
    "/register",
    "/reset-password",
    "/verify-email",
    "/confirm-email-change",
    "/account",
    "/support",
    "/results/headphones-standard",
    "/compare/headphones-standard",
    "/why-best-piq/headphones-standard",
    "/demo",
)

FIRST_PARTY_ASSETS = (
    "/static/consumer/js/consumer.js",
    "/static/consumer/js/account.js",
    "/static/consumer/css/piqsavi.css",
    "/static/consumer/manifest.webmanifest",
    "/static/early_access/early-access.js",
    "/static/early_access/early-access.css",
    "/static/early_access/assets/piqsavi-logo.png",
    "/static/legal/policy.css",
    "/static/demo/demo.js",
    "/static/demo/demo.css",
)

FIRST_PARTY_JS = (
    "app/static/consumer/js/consumer.js",
    "app/static/consumer/js/account.js",
    "app/static/consumer/js/tracking_preference.js",
    "app/static/consumer/js/product_analytics.js",
    "app/static/consumer/js/product_feedback.js",
    "app/static/early_access/early-access.js",
    "app/static/demo/demo.js",
)


def _directives(policy: str) -> dict[str, str]:
    parsed: dict[str, str] = {}
    for part in policy.split(";"):
        item = part.strip()
        if not item:
            continue
        name, _, value = item.partition(" ")
        parsed[name] = value
    return parsed


def _script_kinds(html: str) -> list[str]:
    kinds: list[str] = []
    for attrs, _body in _SCRIPT.findall(html):
        if re.search(r"\bsrc\s*=", attrs, re.IGNORECASE):
            kinds.append("external")
        elif re.search(
            r"""type\s*=\s*["']application/ld\+json["']""",
            attrs,
            re.IGNORECASE,
        ):
            kinds.append("jsonld")
        else:
            kinds.append("inline")
    return kinds


def _assert_strict_csp(header: str | None) -> None:
    assert header == DEFAULT_SECURITY_CSP
    assert "'unsafe-inline'" not in header
    assert "'unsafe-eval'" not in header
    assert "jsdelivr" not in header
    assert "googleapis" not in header


@pytest.fixture(scope="module")
def client() -> TestClient:
    with TestClient(create_app()) as test_client:
        yield test_client


def test_default_csp_is_first_party_only() -> None:
    fresh = Settings(_env_file=None)
    assert fresh.security_csp == DEFAULT_SECURITY_CSP
    assert get_settings().security_csp == DEFAULT_SECURITY_CSP
    assert DEFAULT_SECURITY_CSP != OLD_CSP
    assert "'unsafe-inline'" not in DEFAULT_SECURITY_CSP
    assert "'unsafe-eval'" not in DEFAULT_SECURITY_CSP
    assert "*" not in DEFAULT_SECURITY_CSP
    directives = _directives(DEFAULT_SECURITY_CSP)
    assert directives == {
        "default-src": "'self'",
        "script-src": "'self'",
        "style-src": "'self'",
        "img-src": "'self'",
        "font-src": "'self'",
        "connect-src": "'self'",
        "form-action": "'self'",
        "frame-ancestors": "'none'",
        "base-uri": "'self'",
        "object-src": "'none'",
    }
    assert "data:" not in directives["img-src"]
    assert "https:" not in directives["img-src"]


def test_security_headers_middleware_emits_the_strict_csp(client: TestClient) -> None:
    public = client.get("/live")
    protected = client.get("/api/v1/profile")
    missing = client.get("/not-a-piqsavi-page")
    assert public.status_code == 200
    assert protected.status_code == 401
    assert missing.status_code == 404
    for response in (public, protected, missing):
        _assert_strict_csp(response.headers.get("Content-Security-Policy"))
        assert response.headers.get("X-Frame-Options") == "DENY"
        assert "<script" not in response.text
        assert "application/json" in response.headers.get("content-type", "")


@pytest.mark.parametrize("path", PRODUCT_PAGES)
def test_rendered_product_pages_have_no_inline_execution(client: TestClient, path: str) -> None:
    response = client.get(path)
    assert response.status_code == 200, path
    _assert_strict_csp(response.headers.get("Content-Security-Policy"))
    html = response.text
    kinds = _script_kinds(html)
    assert "inline" not in kinds, (path, kinds)
    assert _EVENT.search(html) is None, path
    assert _STYLE_ATTR.search(html) is None, path
    assert _STYLE_TAG.search(html) is None, path
    assert _JS_URL.search(html) is None, path
    if path == "/":
        assert kinds.count("jsonld") == 2
        assert "/static/early_access/early-access.js" in html
        assert "/static/early_access/early-access.css" in html
    else:
        assert "jsonld" not in kinds, path
    if path in {"/privacy", "/terms"}:
        assert "/static/legal/policy.css" in html
        assert kinds == []
    if path in {
        "/results/headphones-standard",
        "/compare/headphones-standard",
        "/why-best-piq/headphones-standard",
    }:
        assert "/static/consumer/js/consumer.js" in html
        assert "/static/consumer/css/piqsavi.css" in html
        assert 'action="/consumer/shopping-market"' in html
    if path in {
        "/login",
        "/register",
        "/reset-password",
        "/verify-email",
        "/confirm-email-change",
        "/account",
        "/support",
    }:
        assert "/static/consumer/js/account.js" in html
        assert "/static/consumer/css/piqsavi.css" in html
    if path == "/demo":
        assert "/static/demo/demo.js" in html
        assert "/static/demo/demo.css" in html


def test_first_party_assets_are_served_from_self(client: TestClient) -> None:
    for path in FIRST_PARTY_ASSETS:
        response = client.get(path)
        assert response.status_code == 200, path
        _assert_strict_csp(response.headers.get("Content-Security-Policy"))


def test_first_party_scripts_do_not_eval_or_call_third_parties() -> None:
    fetch_call = re.compile(r"""fetch\(\s*['"]([^'"]+)""")
    for relative in FIRST_PARTY_JS:
        text = (ROOT / relative).read_text(encoding="utf-8")
        assert "eval(" not in text, relative
        assert "new Function" not in text, relative
        assert _STRING_TIMER.search(text) is None, relative
        assert " style=" not in text, relative
        for target in fetch_call.findall(text):
            assert target.startswith("/"), (relative, target)


def test_fastapi_docs_stay_outside_the_strict_policy(client: TestClient) -> None:
    docs = client.get("/docs")
    redoc = client.get("/redoc")
    assert docs.status_code == 200
    assert redoc.status_code == 200
    _assert_strict_csp(docs.headers.get("Content-Security-Policy"))
    _assert_strict_csp(redoc.headers.get("Content-Security-Policy"))
    assert "inline" in _script_kinds(docs.text)
    assert "cdn.jsdelivr.net" in docs.text
    assert "cdn.jsdelivr.net" in redoc.text
    assert "fonts.googleapis.com" in redoc.text


def test_sprint_40_6_record_does_not_close_the_sprint() -> None:
    evidence = (ROOT / "docs/roadmap/evidence/SPRINT_40_6_CSP_HARDENING_2026-10-10.md").read_text(
        encoding="utf-8"
    )
    sprint = (ROOT / "docs/roadmap/sprints/SPRINT_40_SECURITY_ABUSE_HARDENING.md").read_text(
        encoding="utf-8"
    )
    ci = (ROOT / ".github/workflows/ci.yml").read_text(encoding="utf-8")
    assert START_SHA in evidence
    assert "IMPLEMENTED-NOT-PROVEN" in evidence
    assert "Not ENGINEERING COMPLETE" in evidence
    assert "No Included requirement is PROVEN." in evidence
    assert "CSP `'unsafe-inline'`" in evidence
    assert "not closed and not PROVEN" in evidence
    assert "Staging has not exercised the policy." in evidence
    assert "Sprint 40.3" in evidence
    assert "Sprint 40.4" in evidence
    assert "Sprint 40.5" in evidence
    assert "R6 stays PARTIAL" in evidence
    assert "Dependabot, CodeQL, and Trivy are still absent." in evidence
    assert "Section I of the gap inventory is not rewritten." in evidence
    assert "Class C count remains 19" in evidence
    assert "selected next engineering slice remains NONE" in evidence
    assert "Sprint 41 stays UNSTARTED" in evidence
    assert "No deploy was performed." in evidence
    assert "Routing stays 0." in evidence
    assert "**Status:** Planned" in sprint
    assert "Sprint 40.6" in sprint
    assert "tests/unit/test_sprint40_6_csp.py" in ci
    assert "ENGINEERING COMPLETE" not in evidence.split("Not ENGINEERING COMPLETE")[0]

"""Static contract tests for the PiqSavi Early Access landing page."""

from __future__ import annotations

from pathlib import Path

from app.core.public_brand import PUBLIC_BRAND, PUBLIC_TAGLINE
from app.main import create_app
from fastapi.testclient import TestClient

ROOT = Path(__file__).resolve().parents[2]
HTML = (ROOT / "app/static/early_access/index.html").read_text(encoding="utf-8")
JS = (ROOT / "app/static/early_access/early-access.js").read_text(encoding="utf-8")


def test_correct_public_brand() -> None:
    with TestClient(create_app()) as client:
        page = client.get("/").text
    assert PUBLIC_BRAND in page
    assert PUBLIC_TAGLINE in page
    assert "Know what’s worth buying." in page or "Know what's worth buying." in page


def test_no_unintended_user_visible_dealbrain() -> None:
    with TestClient(create_app()) as client:
        page = client.get("/").text
    assert "DealBrain" not in page
    assert "DealBrain" not in HTML
    assert "DealBrain" not in JS


def test_approved_headline_and_copy() -> None:
    with TestClient(create_app()) as client:
        page = client.get("/").text
    assert "Know what’s worth buying." in page or "Know what's worth buying." in page
    assert "Be one of the first to try PiqSavi." in page
    assert "You’re on the list." in page or "You're on the list." in page
    assert "Something went wrong." in page
    assert "Check your inbox" not in page
    assert "We sent you an email" not in page


def test_exactly_approved_form_fields() -> None:
    assert 'name="full_name"' in HTML
    assert 'name="email"' in HTML
    assert 'name="country"' in HTML
    assert 'name="shopping_interest"' in HTML
    assert 'name="password"' not in HTML
    assert 'type="password"' not in HTML
    assert 'name="phone"' not in HTML
    assert 'type="tel"' not in HTML
    assert 'name="address"' not in HTML
    assert 'name="company"' not in HTML
    assert 'autocomplete="cc-' not in HTML


def test_privacy_and_terms_footer_links() -> None:
    assert 'href="/privacy"' in HTML
    assert 'href="/terms"' in HTML
    assert "data-legal-gated" in HTML


def test_no_pricing_merchant_logos_or_fake_social_proof() -> None:
    lowered = HTML.lower()
    assert "testimonial" not in lowered
    assert "$" not in HTML
    assert "pricing" not in lowered
    assert "amazon" not in lowered
    assert "shopee" not in lowered
    assert "/demo" not in HTML


def test_responsive_breakpoint_present() -> None:
    css = (ROOT / "app/static/early_access/early-access.css").read_text(encoding="utf-8")
    assert "max-width: 767px" in css
    assert "SOURCE-ASSET-GATE" in css


def test_approved_master_logo_is_used() -> None:
    logo = ROOT / "app/static/early_access/assets/piqsavi-logo.png"
    assert logo.is_file()
    assert logo.read_bytes()[:8] == b"\x89PNG\r\n\x1a\n"
    assert "/static/early_access/assets/piqsavi-logo.png" in HTML
    assert HTML.count("/static/early_access/assets/piqsavi-logo.png") == 3
    assert 'alt="PiqSavi"' in HTML
    assert "piq-grad" not in HTML
    assert "brand-mark" not in HTML
    assert "brand-mark" not in (ROOT / "app/static/early_access/early-access.css").read_text(
        encoding="utf-8"
    )


def test_approximating_logo_svg_is_gone() -> None:
    assert '<svg class="brand-mark"' not in HTML
    assert "circular mark is a placeholder" not in HTML
    assert HTML.count("js-open-signup") == 2


def test_source_asset_gate_is_not_publicly_served() -> None:
    gate = ROOT / "app/early_access/SOURCE_ASSET_GATE.md"
    assert gate.is_file()
    assert not (ROOT / "app/static/early_access/assets/SOURCE_ASSET_GATE.md").exists()
    with TestClient(create_app()) as client:
        response = client.get("/static/early_access/assets/SOURCE_ASSET_GATE.md")
    assert response.status_code == 404

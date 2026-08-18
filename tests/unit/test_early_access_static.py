"""Static contract tests for the PiqSavi Early Access landing page."""

from __future__ import annotations

import hashlib
import re
from pathlib import Path

from app.core.public_brand import PUBLIC_BRAND, PUBLIC_TAGLINE
from app.main import create_app
from fastapi.testclient import TestClient

ROOT = Path(__file__).resolve().parents[2]
HTML = (ROOT / "app/static/early_access/index.html").read_text(encoding="utf-8")
JS = (ROOT / "app/static/early_access/early-access.js").read_text(encoding="utf-8")


def _relative_luminance(hex_color: str) -> float:
    channels = [int(hex_color[index : index + 2], 16) / 255 for index in (1, 3, 5)]
    linear = [
        channel / 12.92 if channel <= 0.03928 else ((channel + 0.055) / 1.055) ** 2.4
        for channel in channels
    ]
    return (0.2126 * linear[0]) + (0.7152 * linear[1]) + (0.0722 * linear[2])


def _contrast_ratio(first: str, second: str) -> float:
    bright, dark = sorted((_relative_luminance(first), _relative_luminance(second)), reverse=True)
    return (bright + 0.05) / (dark + 0.05)


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
    assert (
        "We’re getting PiqSavi ready for its first users. Join the Early Access list and we’ll "
        "let you know when it’s ready to try."
    ) in page or (
        "We're getting PiqSavi ready for its first users. Join the Early Access list and we'll "
        "let you know when it's ready to try."
    ) in page
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
    assert "max-width: 1023px" in css
    assert "min-width: 1024px" in css
    assert "max-width: 1279px" in css
    assert "max-width: 768px" in css
    assert "900px" not in css
    assert "SOURCE-ASSET-GATE" not in css
    assert "object-position: 58% 42%" in css
    assert "object-position: 59% 42%" in css
    assert "object-position: 60% 42%" in css


def test_signup_states_keep_locked_master_proportions() -> None:
    css = (ROOT / "app/static/early_access/early-access.css").read_text(encoding="utf-8")
    assert "width: min(470px, 100%)" in css
    assert "padding: 2.6rem 3.4rem 1.25rem" in css
    assert "max-width: 18.5rem" in css
    assert "margin: 0.75rem auto 3.25rem" in css
    assert "min-height: 42px" in css
    assert "min-height: 25.9rem" in css
    assert "max-width: 260px" in css
    assert "padding: 1rem 1.5rem 2rem" in css
    assert "min-height: 39.5rem" in css
    assert "max-width: 300px" in css
    assert "margin-bottom: 4rem" in css
    assert ".signup-sheet:has(.result-body:not([hidden]))" in css
    assert ".signup-sheet:has(.field-error:not([hidden]))" in css


APPROVED_LOGO_SHA256 = "916a1f5165e7b8e6b8390221b040717ef8a22cf24ce5a26cb0c9a621d9d5dd97"


def test_approved_master_logo_is_used() -> None:
    logo = ROOT / "app/static/early_access/assets/piqsavi-logo.png"
    assert logo.is_file()
    raw = logo.read_bytes()
    assert raw[:8] == b"\x89PNG\r\n\x1a\n"
    assert hashlib.sha256(raw).hexdigest() == APPROVED_LOGO_SHA256
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


def test_field_error_describedby_and_live_regions() -> None:
    assert 'id="ea-full-name"' in HTML
    assert 'aria-describedby="err-full-name"' in HTML
    assert 'id="ea-email"' in HTML
    assert 'aria-describedby="err-email"' in HTML
    assert 'id="ea-country"' in HTML
    assert 'aria-describedby="err-country"' in HTML
    assert 'id="ea-interest"' in HTML
    interest_block = HTML.split('id="ea-interest"', 1)[1].split("</div>", 1)[0]
    assert "aria-describedby" not in interest_block
    for err_id in ("err-full-name", "err-email", "err-country"):
        marker = f'id="{err_id}"'
        assert marker in HTML
        snippet = HTML[HTML.index(marker) : HTML.index(marker) + 80]
        assert 'aria-live="polite"' in snippet


def test_result_panels_are_polite_status_live_regions() -> None:
    for panel in ("success", "duplicate", "technical_error"):
        marker = f'data-panel="{panel}"'
        start = HTML.index(marker)
        snippet = HTML[start : start + 120]
        assert 'role="status"' in snippet
        assert 'aria-live="polite"' in snippet


def test_duplicate_response_uses_the_distinct_duplicate_panel() -> None:
    assert 'if (body.outcome === "already_registered")' in JS
    assert 'showResult("duplicate")' in JS
    assert "You’re already on the Early Access list." in HTML


def test_mobile_signup_logo_links_home_and_is_larger() -> None:
    css = (ROOT / "app/static/early_access/early-access.css").read_text(encoding="utf-8")
    mobile_css = css.split("@media (max-width: 767px)", 1)[1]
    assert '<a class="signup-brand" href="/" aria-label="Back to PiqSavi home">' in HTML
    assert '<img\n              class="brand-logo"' in HTML
    assert "PiqSavi home" in HTML
    assert ".site-header .brand-logo {\n    height: 72px;" in mobile_css
    assert ".signup-brand .brand-logo {\n    height: 72px;" in mobile_css
    assert ".signup-brand:focus-visible" in css


def test_js_manages_aria_busy_on_form() -> None:
    assert "function setLoading(loading)" in JS
    assert 'form.setAttribute("aria-busy", loading ? "true" : "false")' in JS
    assert "submitBtn.disabled = loading" in JS
    assert 'submitBtn.classList.toggle("is-loading", loading)' in JS


def test_loading_button_text_meets_normal_text_contrast() -> None:
    css = (ROOT / "app/static/early_access/early-access.css").read_text(encoding="utf-8")
    match = re.search(r"--blue-soft:\s*(#[0-9a-fA-F]{6})", css)
    assert match is not None
    assert _contrast_ratio("#ffffff", match.group(1)) >= 4.5


def test_desktop_modal_and_mobile_aria_modal_breakpoint() -> None:
    assert 'id="signup-sheet"' in HTML
    assert 'role="dialog"' in HTML
    assert 'aria-modal="true"' in HTML
    assert 'aria-labelledby="signup-title"' in HTML
    assert "max-width: ${BREAKPOINT}px" in JS
    assert "const BREAKPOINT = 767" in JS
    assert "matchMedia" in JS
    assert 'mobileQuery.addEventListener("change"' in JS
    assert 'sheet.setAttribute("aria-modal", isMobile() ? "false" : "true")' in JS
    assert "syncSignupAriaModal" in JS


def test_existing_focus_behavior_remains() -> None:
    assert "function focusables()" in JS
    assert 'if (event.key === "Escape")' in JS
    assert "closeSignup()" in JS
    assert "if (restore) restore.focus()" in JS
    assert 'if (event.key !== "Tab" || isMobile()) return' in JS
    assert "last.focus()" in JS
    assert "first.focus()" in JS
    assert 'document.getElementById("ea-full-name").focus()' in JS


def test_locked_landing_architecture() -> None:
    assert HTML.count("<header") == 2
    assert 'class="hero"' in HTML
    assert 'id="how-it-works"' in HTML
    assert "PIQSCORE / TRUST" in HTML
    assert 'class="site-footer"' in HTML
    assert "Product Preview" not in HTML
    assert "product-preview" not in HTML
    assert 'id="early-access-form"' in HTML
    assert HTML.index('class="hero"') < HTML.index('id="early-access-form"')
    assert "Join Early Access" in HTML
    assert HTML.count("js-open-signup") == 2
    assert 'data-cta-source="header"' in HTML
    assert 'data-cta-source="hero"' in HTML
    assert "Full name" in HTML
    assert "full name" in HTML.lower()
    assert "/demo" not in HTML
    assert "login" not in HTML.lower()
    assert "search" not in HTML.lower()
    assert 'href="/privacy"' in HTML
    assert 'href="/terms"' in HTML
    assert 'data-legal-gated="true"' in HTML
    assert 'aria-disabled="true"' in HTML


def test_final_hero_source_is_served() -> None:
    hero_png = ROOT / "app/static/early_access/assets/piqsavi-hero-photographic-master.png"
    hero_webp = ROOT / "app/static/early_access/assets/piqsavi-hero-photographic-master.webp"
    hero_mobile = ROOT / "app/static/early_access/assets/piqsavi-hero-mobile-crop-752x941.png"
    assert hero_png.is_file()
    assert hero_webp.is_file()
    assert hero_mobile.is_file()
    assert hero_png.read_bytes()[:8] == b"\x89PNG\r\n\x1a\n"
    assert hero_mobile.read_bytes()[:8] == b"\x89PNG\r\n\x1a\n"
    assert hashlib.sha256(hero_png.read_bytes()).hexdigest() == (
        "5773da03035e1bdea6f1a27a93aa2081789c224e66db7976744526c0fa4a4270"
    )
    assert hashlib.sha256(hero_webp.read_bytes()).hexdigest() == (
        "b5808a86478e7fe7c3e2efcb87f9144da9564fc25dc13a66294e4e97d777295f"
    )
    assert hashlib.sha256(hero_mobile.read_bytes()).hexdigest() == (
        "8233c03be73f23ee5ad430f15320dfd770eeae302910cbc361fbbd1cae303d9d"
    )
    assert "/static/early_access/assets/piqsavi-hero-photographic-master.png" in HTML
    assert "/static/early_access/assets/piqsavi-hero-photographic-master.webp" in HTML
    assert "/static/early_access/assets/piqsavi-hero-mobile-crop-752x941.png" in HTML
    gate = (ROOT / "app/early_access/SOURCE_ASSET_GATE.md").read_text(encoding="utf-8")
    assert "approved photographic master" in gate
    assert "CSS gradient placeholder has been removed" in gate
    assert "5773da03035e1bdea6f1a27a93aa2081789c224e66db7976744526c0fa4a4270" in gate


def test_mobile_menu_contains_only_how_it_works() -> None:
    assert 'id="nav-toggle"' in HTML
    assert 'aria-controls="mobile-menu"' in HTML
    assert 'id="mobile-menu"' in HTML
    assert 'id="mobile-how-link"' in HTML
    menu = HTML.split('id="mobile-menu"', 1)[1].split("</div>", 1)[0]
    assert "How it works" in menu
    assert "Join Early Access" not in menu
    assert "js-open-signup" not in menu
    assert "login" not in menu.lower()
    assert "pricing" not in menu.lower()
    assert "const NAV_BREAKPOINT = 1023" in JS
    assert "function setMenuOpen(open)" in JS
    assert "closeMenu()" in JS
    assert "prefersReducedMotion" in JS


def test_registration_endpoints_remain_in_client() -> None:
    assert 'fetch("/api/v1/early-access"' in JS
    assert 'fetch("/api/v1/early-access/events"' in JS
    assert 'method: "POST"' in JS

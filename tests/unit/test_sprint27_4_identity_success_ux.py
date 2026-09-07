"""Sprint 27.4 — consumer email-change exposure and identity success states."""

from __future__ import annotations

from pathlib import Path

import pytest
from app.consumer.account_pages import (
    render_account_settings_page,
    render_confirm_email_change_page,
    render_reset_password_page,
    render_verify_email_page,
)
from httpx import AsyncClient

ROOT = Path(__file__).resolve().parents[2]
ACCOUNT_JS = (ROOT / "app/static/consumer/js/account.js").read_text(encoding="utf-8")
ACCOUNT_HTML = render_account_settings_page()
CONFIRM_TOKEN_HTML = render_confirm_email_change_page(has_token=True)
CONFIRM_EMPTY_HTML = render_confirm_email_change_page(has_token=False)
RESET_REQUEST_HTML = render_reset_password_page()
RESET_CONFIRM_HTML = render_reset_password_page(token="sample-token")
VERIFY_REQUEST_HTML = render_verify_email_page()
VERIFY_CONFIRM_HTML = render_verify_email_page(token="sample-token")


def _section(html: str, start_marker: str, end_marker: str | None = None) -> str:
    start = html.index(start_marker)
    if end_marker is None:
        return html[start:]
    return html[start : html.index(end_marker, start)]


def _signed_in_html() -> str:
    start = ACCOUNT_HTML.index("data-account-signed-in")
    return ACCOUNT_HTML[start:]


def _signed_out_html() -> str:
    start = ACCOUNT_HTML.index("data-account-signed-out")
    end = ACCOUNT_HTML.index("data-account-signed-in")
    return ACCOUNT_HTML[start:end]


def test_account_page_exposes_email_change_only_when_signed_in() -> None:
    signed_in = _signed_in_html()
    signed_out = _signed_out_html()
    assert 'data-account-form="email-change"' in signed_in
    assert 'name="new_email"' in signed_in
    assert 'autocomplete="email"' in signed_in
    assert 'autocomplete="current-password"' in signed_in
    assert "Send confirmation" in signed_in
    assert "Change email" in signed_in
    assert "We'll send a confirmation link there before changing your account." in signed_in
    assert "data-email-change-status" in signed_in
    assert 'role="status"' in signed_in
    assert 'aria-live="polite"' in signed_in
    assert 'data-account-form="email-change"' not in signed_out
    assert "Send confirmation" not in signed_out
    assert "Sprint 27 identity APIs" not in ACCOUNT_HTML
    assert "Request or confirm email verification" not in ACCOUNT_HTML


def test_verified_account_state_does_not_prompt_verification_by_default() -> None:
    assert "data-account-verify-needed hidden" in ACCOUNT_HTML
    assert "Verify your email" in ACCOUNT_HTML
    assert "payload.email_verified" in ACCOUNT_JS
    assert "verifyNeeded.hidden = true" in ACCOUNT_JS
    assert "verifyNeeded.hidden = false" in ACCOUNT_JS
    assert 'textContent = "Verified"' in ACCOUNT_JS
    assert "Request or confirm email verification" not in ACCOUNT_JS


def test_email_change_request_uses_existing_authenticated_endpoint() -> None:
    assert '"/api/v1/auth/email-change"' in ACCOUNT_JS
    assert "new_email:" in ACCOUNT_JS
    assert "password:" in ACCOUNT_JS
    assert "Authorization = `Bearer ${token}`" in ACCOUNT_JS
    assert ACCOUNT_JS.count('qs("[data-account-email]").textContent') == 1
    assert "Check your new email. If this address can be used" in ACCOUNT_JS
    assert "Check your new email for a confirmation link." in ACCOUNT_JS
    assert "email_delivery === true" in ACCOUNT_JS


def test_email_change_confirm_page_does_not_claim_success_before_submit() -> None:
    assert 'data-page="confirm-email-change"' in CONFIRM_TOKEN_HTML
    assert 'data-account-form="email-change-confirm"' in CONFIRM_TOKEN_HTML
    assert "Confirm email change" in CONFIRM_TOKEN_HTML
    assert "Email changed" in CONFIRM_TOKEN_HTML
    assert "data-identity-success hidden" in CONFIRM_TOKEN_HTML
    assert "data-identity-failure hidden" in CONFIRM_TOKEN_HTML
    assert "data-identity-pending hidden" not in CONFIRM_TOKEN_HTML
    pending = _section(CONFIRM_TOKEN_HTML, "data-identity-pending", "data-identity-success")
    assert "Email changed" not in pending
    assert "updated and verified" not in pending
    assert 'name="token"' not in CONFIRM_TOKEN_HTML


def test_email_change_confirm_without_token_starts_in_failure_state() -> None:
    assert "<div data-identity-pending hidden>" in CONFIRM_EMPTY_HTML
    assert "<div data-identity-success hidden>" in CONFIRM_EMPTY_HTML
    assert "<div data-identity-failure>" in CONFIRM_EMPTY_HTML
    assert "This email-change link is invalid or has expired." in CONFIRM_EMPTY_HTML
    assert "Back to sign in" in CONFIRM_EMPTY_HTML
    assert "Your email address has been updated and verified." not in _section(
        CONFIRM_EMPTY_HTML, "data-identity-failure"
    )


def test_email_change_confirm_js_clears_local_auth_and_hides_form() -> None:
    assert '"/api/v1/auth/email-change/confirm"' in ACCOUNT_JS
    assert "clearLocalAuth()" in ACCOUNT_JS
    assert "clearToken()" in ACCOUNT_JS
    assert 'revealIdentityOutcome("success")' in ACCOUNT_JS
    assert 'revealIdentityOutcome("failure")' in ACCOUNT_JS
    assert "pendingIdentityToken" in ACCOUNT_JS
    assert "consumeUrlToken" in ACCOUNT_JS
    assert 'searchParams.delete("token")' in ACCOUNT_JS
    assert "Sign in again using your new email address." in CONFIRM_TOKEN_HTML
    assert 'href="/login"' in CONFIRM_TOKEN_HTML


def test_verification_and_reset_final_states_hide_active_forms() -> None:
    assert "data-identity-success hidden" in VERIFY_CONFIRM_HTML
    assert "Email verified" in VERIFY_CONFIRM_HTML
    assert "Your email address has been verified." in VERIFY_CONFIRM_HTML
    assert "Continue to account" in VERIFY_CONFIRM_HTML
    assert "Confirm email" in _section(
        VERIFY_CONFIRM_HTML, "data-identity-pending", "data-identity-success"
    )
    assert "Confirm email" not in _section(
        VERIFY_CONFIRM_HTML, "data-identity-success", "data-identity-failure"
    )
    assert "Password reset" in RESET_CONFIRM_HTML
    assert "Your password has been updated." in RESET_CONFIRM_HTML
    assert "You can now sign in using your new password." in RESET_CONFIRM_HTML
    assert "Set new password" in _section(
        RESET_CONFIRM_HTML, "data-identity-pending", "data-identity-success"
    )
    assert "Set new password" not in _section(
        RESET_CONFIRM_HTML, "data-identity-success", "data-identity-failure"
    )
    assert "Request a new reset link" in RESET_CONFIRM_HTML
    assert 'revealIdentityOutcome("success")' in ACCOUNT_JS
    assert '"/api/v1/auth/verify-email/confirm"' in ACCOUNT_JS
    assert '"/api/v1/auth/password-reset/confirm"' in ACCOUNT_JS


def test_request_sent_states_are_enumeration_safe() -> None:
    assert "Check your email" in RESET_REQUEST_HTML
    assert (
        "If an account exists for that address, we've sent password-reset instructions."
        in RESET_REQUEST_HTML
    )
    assert "Check your email" in VERIFY_REQUEST_HTML
    assert (
        "If an account exists for that address, we've sent a verification link."
        in VERIFY_REQUEST_HTML
    )
    assert "demo token" not in RESET_REQUEST_HTML.lower()
    assert "demo token" not in VERIFY_REQUEST_HTML.lower()
    assert "Sprint 27" not in RESET_REQUEST_HTML
    assert "Sprint 27" not in VERIFY_REQUEST_HTML
    assert "This page does not invent email delivery" not in RESET_REQUEST_HTML
    assert "identity APIs" not in VERIFY_REQUEST_HTML
    assert 'revealIdentityOutcome("sent")' in ACCOUNT_JS


def test_identity_success_and_error_copy_never_includes_raw_tokens() -> None:
    for html in (CONFIRM_TOKEN_HTML, VERIFY_CONFIRM_HTML, RESET_CONFIRM_HTML, ACCOUNT_JS):
        assert (
            "sample-token" not in _section(html, "data-identity-success")
            if "data-identity-success" in html
            else True
        )
        assert "reset_token_demo_only" not in html
        assert "verification_token_demo_only" not in html
        assert "email_change_token_demo_only" not in html
    assert "redactToken" in ACCOUNT_JS
    assert "console.log" not in ACCOUNT_JS
    success_copy = "\n".join(
        [
            _section(CONFIRM_TOKEN_HTML, "data-identity-success", "data-identity-failure"),
            _section(VERIFY_CONFIRM_HTML, "data-identity-success", "data-identity-failure"),
            _section(RESET_CONFIRM_HTML, "data-identity-success", "data-identity-failure"),
        ]
    )
    assert "token=" not in success_copy
    assert "sample-token" not in success_copy


@pytest.mark.asyncio
async def test_confirm_email_change_route_is_noindex_and_omits_query_token(
    client: AsyncClient,
) -> None:
    secret = "raw-identity-token-value-27-4"
    page = await client.get("/confirm-email-change", params={"token": secret})
    missing = await client.get("/confirm-email-change")
    assert page.status_code == 200
    assert missing.status_code == 200
    assert page.headers.get("X-Robots-Tag") == "noindex, nofollow"
    assert secret not in page.text
    assert 'data-account-form="email-change-confirm"' in page.text
    assert "data-identity-success hidden" in page.text
    assert "This email-change link is invalid or has expired." in missing.text
    assert "Your email address has been updated and verified." not in _section(
        missing.text, "data-identity-failure"
    )


@pytest.mark.asyncio
async def test_account_and_identity_pages_keep_existing_export_delete_surfaces(
    client: AsyncClient,
) -> None:
    account = await client.get("/account")
    reset = await client.get("/reset-password")
    verify = await client.get("/verify-email")
    assert "Download my data" in account.text
    assert "Delete my account" in account.text
    assert "Watch is not available yet" in account.text
    assert 'data-account-form="email-change"' in account.text
    assert "Change email" in account.text
    assert (
        "If an account exists for that address, we'll send password-reset instructions."
        in reset.text
    )
    assert "If an account exists for that address, we'll send a verification link." in verify.text


@pytest.mark.asyncio
async def test_email_change_request_does_not_mutate_account_email(
    client: AsyncClient,
) -> None:
    email = "sprint27-4-current@example.invalid"
    created = await client.post(
        "/api/v1/auth/register",
        json={
            "email": email,
            "password": "Password123",
            "display_name": "Sprint 27.4",
            "terms_accepted": False,
            "privacy_acknowledged": False,
        },
    )
    assert created.status_code == 201
    token = created.json()["access_token"]
    headers = {"Authorization": f"Bearer {token}"}
    accepted = await client.post(
        "/api/v1/auth/email-change",
        headers=headers,
        json={"new_email": "sprint27-4-next@example.invalid", "password": "Password123"},
    )
    assert accepted.status_code == 200
    assert accepted.json()["status"] == "accepted"
    me = await client.get("/api/v1/auth/me", headers=headers)
    assert me.status_code == 200
    assert me.json()["email"] == email
    assert me.json()["email_verified"] is False
    failed = await client.post(
        "/api/v1/auth/email-change/confirm",
        json={"token": "expired-or-unknown-token"},
    )
    assert failed.status_code == 401
    assert failed.json()["detail"] == "Invalid or expired email-change token."
    still = await client.get("/api/v1/auth/me", headers=headers)
    assert still.json()["email"] == email

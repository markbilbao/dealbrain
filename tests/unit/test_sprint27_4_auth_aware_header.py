"""Sprint 27.4 follow-up — consumer header reflects validated auth state."""

from __future__ import annotations

from pathlib import Path

import pytest
from app.consumer.account_pages import (
    render_account_settings_page,
    render_confirm_email_change_page,
    render_login_page,
    render_register_page,
    render_reset_password_page,
    render_support_page,
    render_verify_email_page,
)
from httpx import AsyncClient

ROOT = Path(__file__).resolve().parents[2]
ACCOUNT_JS = (ROOT / "app/static/consumer/js/account.js").read_text(encoding="utf-8")
ACCOUNT_CSS = (ROOT / "app/static/consumer/css/piqsavi.css").read_text(encoding="utf-8")
LOGIN_HTML = render_login_page(next_path="/account")
REGISTER_HTML = render_register_page(next_path="/account")
ACCOUNT_HTML = render_account_settings_page()
RESET_HTML = render_reset_password_page()
VERIFY_HTML = render_verify_email_page()
CONFIRM_HTML = render_confirm_email_change_page(has_token=True)
SUPPORT_HTML = render_support_page()


def _header(html: str) -> str:
    start = html.index("<header")
    end = html.index("</header>") + len("</header>")
    return html[start:end]


def _header_nav(html: str) -> str:
    header = _header(html)
    start = header.index("<nav")
    end = header.index("</nav>") + len("</nav>")
    return header[start:end]


HEADER = _header(LOGIN_HTML)
HEADER_NAV = _header_nav(LOGIN_HTML)


def test_header_contains_separate_signed_in_and_signed_out_states() -> None:
    assert 'data-header-auth="signed-out"' in HEADER
    assert 'data-header-auth="signed-in"' in HEADER
    assert HEADER.count('data-header-auth="signed-out"') == 2
    assert HEADER.count('data-header-auth="signed-in"') == 2
    assert "How it works" in HEADER_NAV
    assert "Support" in HEADER_NAV
    assert "function setHeaderAuthState(signedIn)" in ACCOUNT_JS
    assert "async function resolveAuthSession()" in ACCOUNT_JS
    assert ".site-header [data-header-auth][hidden]" in ACCOUNT_CSS
    assert "display: none !important" in ACCOUNT_CSS


def test_initial_header_hides_auth_dependent_actions() -> None:
    assert 'data-header-auth="signed-out" hidden>Sign in</a>' in HEADER
    assert 'data-header-auth="signed-out" hidden>Sign up</a>' in HEADER
    assert 'data-header-auth="signed-in" hidden>Account</a>' in HEADER_NAV
    assert 'data-sign-out-redirect="/" hidden>Sign out</button>' in HEADER
    assert 'type="button"' in HEADER
    assert "<button" in HEADER
    assert 'data-header-auth="signed-in">Account</a>' not in HEADER
    assert ">Sign in</a>" in HEADER
    assert ">Sign up</a>" in HEADER


def _resolve_auth_session_js() -> str:
    return ACCOUNT_JS[
        ACCOUNT_JS.index("async function resolveAuthSession()") : ACCOUNT_JS.index(
            "function applyAccountPageSession"
        )
    ]


def test_no_token_restores_signed_out_header_and_hides_authenticated_actions() -> None:
    resolve = _resolve_auth_session_js()
    missing_branch = resolve[: resolve.index("try {")]
    assert "if (!token)" in missing_branch
    assert "setHeaderAuthState(false)" in missing_branch
    assert 'reason: "missing"' in missing_branch
    assert "setHeaderAuthState(true)" not in missing_branch
    assert 'await api("/api/v1/auth/me")' not in missing_branch
    assert 'node.hidden = signedIn ? state !== "signed-in" : state !== "signed-out";' in ACCOUNT_JS


def test_valid_token_requires_auth_me_success_before_signed_in_header() -> None:
    resolve = _resolve_auth_session_js()
    assert 'await api("/api/v1/auth/me")' in resolve
    assert "if (!response.ok)" in resolve
    assert "setHeaderAuthState(true)" in resolve
    assert 'reason: "valid"' in resolve
    assert "readToken()" in resolve
    before_me = resolve[: resolve.index('await api("/api/v1/auth/me")')]
    assert "setHeaderAuthState(true)" not in before_me


def test_invalid_token_clears_local_auth_and_restores_signed_out_header() -> None:
    resolve = _resolve_auth_session_js()
    invalid = resolve[
        resolve.index("if (!response.ok)") : resolve.index("setHeaderAuthState(true)")
    ]
    assert "await clearLocalAuth()" in invalid
    assert "setHeaderAuthState(false)" in invalid
    assert 'reason: "invalid"' in invalid
    assert "setHeaderAuthState(true)" not in invalid
    assert "function clearLocalAuth()" in ACCOUNT_JS
    assert 'fetch("/account/clear-device"' in ACCOUNT_JS
    assert "function clearToken()" in ACCOUNT_JS


def _sign_out_js() -> str:
    return ACCOUNT_JS[
        ACCOUNT_JS.index("async function signOutCurrentDevice") : ACCOUNT_JS.index(
            "function bindActions()"
        )
    ]


def test_header_sign_out_posts_logout_clears_auth_and_redirects_home() -> None:
    assert 'data-account-action="sign-out"' in HEADER
    assert 'data-sign-out-redirect="/"' in HEADER
    assert 'href="/"' not in HEADER[HEADER.index("Sign out") - 80 : HEADER.index("Sign out")]
    sign_out = _sign_out_js()
    assert 'await api("/api/v1/auth/logout", { method: "POST" })' in sign_out
    assert "await clearLocalAuth()" in sign_out
    assert "window.location.assign(redirectTo)" in sign_out
    assert "document.querySelectorAll('[data-account-action=\"sign-out\"]')" in ACCOUNT_JS
    assert 'button.getAttribute("data-sign-out-redirect") || "/login"' in ACCOUNT_JS


def test_sign_out_clears_local_auth_and_redirects_when_logout_request_fails() -> None:
    sign_out = _sign_out_js()
    try_idx = sign_out.index("try {")
    logout_idx = sign_out.index('await api("/api/v1/auth/logout", { method: "POST" })')
    catch_idx = sign_out.index("} catch {")
    clear_idx = sign_out.index("await clearLocalAuth()")
    redirect_idx = sign_out.index("window.location.assign(redirectTo)")
    assert try_idx < logout_idx < catch_idx < clear_idx < redirect_idx
    try_body = sign_out[try_idx:catch_idx]
    catch_body = sign_out[catch_idx:clear_idx]
    after_catch = sign_out[catch_idx:]
    assert "await clearLocalAuth()" not in try_body
    assert "window.location.assign(redirectTo)" not in try_body
    assert "await clearLocalAuth()" in after_catch
    assert "window.location.assign(redirectTo)" in after_catch
    assert "setStatus(" not in catch_body
    assert "apiError" not in sign_out
    assert "payload" not in sign_out
    assert "console." not in sign_out
    assert "alert(" not in sign_out


def test_account_sessions_sign_out_still_uses_shared_logout() -> None:
    account = ACCOUNT_HTML[ACCOUNT_HTML.index("data-account-signed-in") :]
    sessions = account[account.index("<h2>Sessions</h2>") : account.index('<h2 id="export">')]
    assert 'data-account-action="sign-out"' in sessions
    assert ">Sign out</button>" in sessions
    assert "data-sign-out-redirect" not in sessions
    assert ACCOUNT_HTML.count('data-account-action="sign-out"') == 2
    assert ACCOUNT_JS.count("signOutCurrentDevice(") == 2


@pytest.mark.parametrize(
    "html",
    (
        LOGIN_HTML,
        REGISTER_HTML,
        RESET_HTML,
        VERIFY_HTML,
        CONFIRM_HTML,
        ACCOUNT_HTML,
        SUPPORT_HTML,
    ),
)
def test_identity_pages_keep_auth_aware_header_and_existing_forms(html: str) -> None:
    header = _header(html)
    assert "How it works" in header
    assert "Support" in header
    assert 'data-header-auth="signed-out" hidden>Sign in</a>' in header
    assert 'data-header-auth="signed-out" hidden>Sign up</a>' in header
    assert 'data-header-auth="signed-in" hidden>Account</a>' in header
    assert 'data-sign-out-redirect="/" hidden>Sign out</button>' in header
    assert "/static/consumer/js/account.js" in html


@pytest.mark.asyncio
async def test_login_register_verify_reset_and_email_change_pages_still_render(
    client: AsyncClient,
) -> None:
    login = await client.get("/login")
    register = await client.get("/register")
    reset = await client.get("/reset-password")
    verify = await client.get("/verify-email")
    confirm = await client.get("/confirm-email-change", params={"token": "sample"})
    account = await client.get("/account")
    assert login.status_code == 200
    assert register.status_code == 200
    assert reset.status_code == 200
    assert verify.status_code == 200
    assert confirm.status_code == 200
    assert account.status_code == 200
    assert 'data-account-form="login"' in login.text
    assert 'data-account-form="register"' in register.text
    assert 'data-account-form="reset-request"' in reset.text
    assert 'data-account-form="verify-request"' in verify.text
    assert 'data-account-form="email-change-confirm"' in confirm.text
    assert 'data-account-form="email-change"' in account.text
    assert "Download my data" in account.text
    assert "Delete my account" in account.text
    assert "Change email" in account.text
    for page in (login, register, reset, verify, confirm, account):
        header = _header(page.text)
        assert 'data-header-auth="signed-out"' in header
        assert 'data-header-auth="signed-in"' in header
        assert "DealBrain" not in page.text

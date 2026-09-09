"""Server-rendered account, auth, and support document pages."""

# ruff: noqa: E501

from __future__ import annotations

from html import escape

from app.consumer.html import ICON_USER, h, logo_markup
from app.consumer.seo import CANONICAL_ORIGIN, organization_json_ld, website_json_ld
from app.core.public_brand import (
    PUBLIC_BRAND,
    PUBLIC_PRIVACY_EMAIL,
    PUBLIC_SUPPORT_EMAIL,
    PUBLIC_TAGLINE,
)
from app.legal.publication import LegalPublicationCatalog, unpublished_catalog
from app.privacy.tracking import HTML_TRACKING_MODE_ATTR


def _esc(value: object) -> str:
    return escape("" if value is None else str(value), quote=True)


def _identity_panels(
    *,
    pending: str,
    sent: str = "",
    success: str = "",
    failure: str = "",
    start: str = "pending",
) -> str:
    """Render mutually exclusive identity request/confirm outcomes."""

    sections: list[str] = []
    for name, body in (
        ("pending", pending),
        ("sent", sent),
        ("success", success),
        ("failure", failure),
    ):
        if not body:
            continue
        hidden = "" if name == start else " hidden"
        sections.append(f"<div data-identity-{name}{hidden}>{body}</div>")
    return "".join(sections)


def render_account_document(
    *,
    title: str,
    page: str,
    main: str,
    next_path: str = "/account",
    description: str | None = None,
    noindex: bool = True,
    extra_script: str = "/static/consumer/js/account.js",
) -> str:
    robots = (
        '<meta name="robots" content="noindex, nofollow">'
        if noindex
        else f'<link rel="canonical" href="{_esc(CANONICAL_ORIGIN + "/")}">'
    )
    desc = description or f"{PUBLIC_BRAND} is {PUBLIC_TAGLINE}."
    return f"""<!DOCTYPE html>
<html lang="en">
  <head>
    <meta charset="utf-8">
    <meta name="viewport" content="width=device-width, initial-scale=1, viewport-fit=cover">
    <meta name="theme-color" content="#0B1B33">
    <title>{h(title)}</title>
    <meta name="description" content="{h(desc)}">
    {robots}
    <link rel="icon" href="/static/early_access/assets/piqsavi-logo.png">
    <link rel="manifest" href="/static/consumer/manifest.webmanifest">
    <link rel="stylesheet" href="/static/consumer/css/piqsavi.css">
  </head>
  <body class="page-account" data-page="{h(page)}" data-next="{h(next_path)}" data-tracking-mode="{h(HTML_TRACKING_MODE_ATTR)}">
    <a class="skip-link" href="#main">Skip to content</a>
    {_account_header(next_path)}
    <main id="main" class="account-main">
      {main}
    </main>
    {_account_footer()}
    <script type="module" src="{h(extra_script)}"></script>
  </body>
</html>
"""


def _account_header(next_path: str) -> str:
    return f"""
    <header class="site-header">
      <a class="brand" href="/">{logo_markup()}</a>
      <nav class="header-nav" aria-label="Primary">
        <a href="/#how-it-works">How it works</a>
        <a href="/account" data-header-auth="signed-in" hidden>Account</a>
        <a href="/support">Support</a>
      </nav>
      <div class="header-actions">
        <a class="text-link" href="/login?next={_esc(next_path)}" data-header-auth="signed-out" hidden>Sign in</a>
        <a class="btn btn-primary btn-compact" href="/register?next={_esc(next_path)}" data-header-auth="signed-out" hidden>Sign up</a>
        <button type="button" class="text-link" data-header-auth="signed-in" data-account-action="sign-out" data-sign-out-redirect="/" hidden>Sign out</button>
        <a class="profile-btn" href="/account" aria-label="Account">{ICON_USER}</a>
      </div>
    </header>
    """


def _account_footer() -> str:
    return """
    <footer class="account-footer">
      <p>PiqSavi — Your AI Personal Shopper</p>
      <nav aria-label="Support and legal">
        <a href="/support">Support</a>
        <a href="/support#report">Report incorrect information</a>
        <a href="/privacy">Privacy</a>
        <a href="/terms">Terms</a>
      </nav>
      <p class="form-hint">Privacy Policy and Terms will appear when they are available.</p>
    </footer>
    """


def render_login_page(*, next_path: str, message: str = "") -> str:
    notice = f'<p class="form-status" role="status">{h(message)}</p>' if message else ""
    return render_account_document(
        title="Sign in — PiqSavi",
        page="login",
        next_path=next_path,
        main=f"""
        <section class="account-card">
          <h1>Sign in</h1>
          <p>Sign in to manage your account, export your data, or continue a saved decision.</p>
          {notice}
          <p class="form-status" data-account-status role="status"></p>
          <form class="account-form" data-account-form="login">
            <input type="hidden" name="next" value="{_esc(next_path)}">
            <label class="field">
              <span>Email</span>
              <input name="email" type="email" autocomplete="username" required maxlength="254">
            </label>
            <label class="field">
              <span>Password</span>
              <input name="password" type="password" autocomplete="current-password" required minlength="1">
            </label>
            <label class="check">
              <input name="remember_me" type="checkbox">
              <span>Remember me on this device</span>
            </label>
            <button type="submit" class="btn btn-primary btn-block">Sign in</button>
          </form>
          <p><a class="text-link" href="/reset-password">Forgot password</a></p>
          <p>No account yet? <a class="text-link" href="/register?next={_esc(next_path)}">Create one</a></p>
        </section>
        """,
    )


def _register_legal_fields(catalog: LegalPublicationCatalog) -> tuple[str, str]:
    """Render acceptance controls from the Sprint 28 publication catalog only."""

    terms = catalog.published("terms")
    privacy = catalog.published("privacy")
    terms_required = catalog.requires_acceptance("terms")
    privacy_required = catalog.requires_acceptance("privacy")
    fields: list[str] = []
    if terms_required and terms is not None:
        fields.append(
            f"""
            <label class="check">
              <input name="terms_accepted" type="checkbox" required>
              <span>I accept the <a href="/terms">Terms of Service</a> (version {_esc(terms.version_id)}).</span>
            </label>
            """
        )
    if privacy_required and privacy is not None:
        fields.append(
            f"""
            <label class="check">
              <input name="privacy_acknowledged" type="checkbox" required>
              <span>I acknowledge the <a href="/privacy">Privacy Policy</a> (version {_esc(privacy.version_id)}).</span>
            </label>
            """
        )
    if not fields:
        intro = "Create your PiqSavi account."
        return intro, (
            '<p class="form-hint" data-legal-unpublished="true">'
            "Legal policies are not yet available for this beta. "
            "No policy acceptance will be recorded until they are published."
            "</p>"
            '<p class="form-hint" data-eligibility-unpublished="true">'
            "PiqSavi does not currently ask for your date of birth during registration."
            "</p>"
        )
    intro = (
        "Registration stores your account and records acceptance of the published legal policies."
    )
    return intro, "".join(fields)


def render_register_page(
    *,
    next_path: str,
    message: str = "",
    catalog: LegalPublicationCatalog | None = None,
) -> str:
    notice = f'<p class="form-status" role="status">{h(message)}</p>' if message else ""
    intro, legal_fields = _register_legal_fields(catalog or unpublished_catalog())
    return render_account_document(
        title="Create account — PiqSavi",
        page="register",
        next_path=next_path,
        main=f"""
        <section class="account-card">
          <h1>Create a PiqSavi account</h1>
          <p>{h(intro)}</p>
          {notice}
          <p class="form-status" data-account-status role="status"></p>
          <form class="account-form" data-account-form="register">
            <input type="hidden" name="next" value="{_esc(next_path)}">
            <label class="field">
              <span>Display name</span>
              <input name="display_name" type="text" autocomplete="name" required maxlength="128">
            </label>
            <label class="field">
              <span>Email</span>
              <input name="email" type="email" autocomplete="email" required maxlength="254">
            </label>
            <label class="field">
              <span>Password</span>
              <input name="password" type="password" autocomplete="new-password" required minlength="8">
            </label>
            <label class="check">
              <input name="remember_me" type="checkbox">
              <span>Remember me on this device</span>
            </label>
            {legal_fields}
            <button type="submit" class="btn btn-primary btn-block">Create account</button>
          </form>
          <p>Already have an account? <a class="text-link" href="/login?next={_esc(next_path)}">Sign in</a></p>
        </section>
        """,
    )


def render_reset_password_page(*, token: str = "", message: str = "") -> str:
    notice = f'<p class="form-status" role="status">{h(message)}</p>' if message else ""
    if token:
        panels = _identity_panels(
            pending=f"""
          <h1>Choose a new password</h1>
          <p>Enter a new password for your PiqSavi account.</p>
          {notice}
          <p class="form-status" data-account-status role="status" aria-live="polite"></p>
          <form class="account-form" data-account-form="reset-confirm">
            <input type="hidden" name="token" value="{_esc(token)}">
            <label class="field">
              <span>New password</span>
              <input name="new_password" type="password" autocomplete="new-password" required minlength="8">
            </label>
            <button type="submit" class="btn btn-primary btn-block">Set new password</button>
          </form>
            """,
            success="""
          <h1>Password reset</h1>
          <p>Your password has been updated.</p>
          <p>You can now sign in using your new password.</p>
          <p><a class="btn btn-primary" href="/login">Sign in</a></p>
            """,
            failure="""
          <h1>Reset link expired</h1>
          <p>This password-reset link is invalid or has expired.</p>
          <p><a class="text-link" href="/reset-password">Request a new reset link</a></p>
            """,
        )
        footer = ""
    else:
        panels = _identity_panels(
            pending=f"""
          <h1>Reset your password</h1>
          <p>Enter the email address for your account. If an account exists for that address, we'll send password-reset instructions.</p>
          {notice}
          <p class="form-status" data-account-status role="status" aria-live="polite"></p>
          <form class="account-form" data-account-form="reset-request">
            <label class="field">
              <span>Email</span>
              <input name="email" type="email" autocomplete="email" required maxlength="254">
            </label>
            <button type="submit" class="btn btn-primary btn-block">Request reset</button>
          </form>
            """,
            sent="""
          <h1>Check your email</h1>
          <p>If an account exists for that address, we've sent password-reset instructions.</p>
            """,
        )
        footer = '<p><a class="text-link" href="/login">Back to sign in</a></p>'
    return render_account_document(
        title="Reset password — PiqSavi",
        page="reset-password",
        main=f"""
        <section class="account-card">
          {panels}
          {footer}
        </section>
        """,
    )


def render_verify_email_page(*, token: str = "", email: str = "") -> str:
    if token:
        panels = _identity_panels(
            pending=f"""
          <h1>Confirm your email</h1>
          <p>Confirm to verify the email address for this account.</p>
          <p class="form-status" data-account-status role="status" aria-live="polite"></p>
          <form class="account-form" data-account-form="verify-confirm">
            <input type="hidden" name="token" value="{_esc(token)}">
            <button type="submit" class="btn btn-primary btn-block">Confirm email</button>
          </form>
            """,
            success="""
          <h1>Email verified</h1>
          <p>Your email address has been verified.</p>
          <p><a class="btn btn-primary" href="/account">Continue to account</a></p>
            """,
            failure="""
          <h1>Verification link expired</h1>
          <p>This verification link is invalid or has expired.</p>
          <p><a class="text-link" href="/verify-email">Request a new verification link</a></p>
            """,
        )
        footer = ""
    else:
        panels = _identity_panels(
            pending=f"""
          <h1>Verify your email</h1>
          <p>Enter the email address for your account. If an account exists for that address, we'll send a verification link.</p>
          <p class="form-status" data-account-status role="status" aria-live="polite"></p>
          <form class="account-form" data-account-form="verify-request">
            <label class="field">
              <span>Email</span>
              <input name="email" type="email" value="{_esc(email)}" autocomplete="email" required maxlength="254">
            </label>
            <button type="submit" class="btn btn-primary btn-block">Request verification</button>
          </form>
            """,
            sent="""
          <h1>Check your email</h1>
          <p>If an account exists for that address, we've sent a verification link.</p>
            """,
        )
        footer = '<p><a class="text-link" href="/account">Account settings</a></p>'
    return render_account_document(
        title="Verify email — PiqSavi",
        page="verify-email",
        main=f"""
        <section class="account-card">
          {panels}
          {footer}
        </section>
        """,
    )


def render_confirm_email_change_page(*, has_token: bool = False) -> str:
    start = "pending" if has_token else "failure"
    panels = _identity_panels(
        start=start,
        pending="""
          <h1>Confirm email change</h1>
          <p>Confirm to finish updating the email address for this account. Your current email stays the same until you confirm.</p>
          <p class="form-status" data-account-status role="status" aria-live="polite"></p>
          <form class="account-form" data-account-form="email-change-confirm">
            <button type="submit" class="btn btn-primary btn-block">Confirm email change</button>
          </form>
        """,
        success="""
          <h1>Email changed</h1>
          <p>Your email address has been updated and verified.</p>
          <p>For your security, you've been signed out on all devices. Sign in again using your new email address.</p>
          <p><a class="btn btn-primary" href="/login">Sign in</a></p>
        """,
        failure="""
          <h1>Email change link expired</h1>
          <p>This email-change link is invalid or has expired.</p>
          <p><a class="text-link" href="/login">Back to sign in</a></p>
        """,
    )
    return render_account_document(
        title="Confirm email change — PiqSavi",
        page="confirm-email-change",
        next_path="/login",
        main=f"""
        <section class="account-card">
          {panels}
        </section>
        """,
    )


def render_account_settings_page(*, next_path: str = "/account") -> str:
    return render_account_document(
        title="Account settings — PiqSavi",
        page="account",
        next_path=next_path,
        main=f"""
        <section class="account-card">
          <h1>Account settings</h1>
          <p class="form-status" data-account-status role="status" aria-live="polite">Checking this device session…</p>
          <div data-account-signed-out hidden>
            <p>Sign in to view account information, export your data, or delete your account.</p>
            <p>
              <a class="btn btn-primary" href="/login?next={_esc(next_path)}">Sign in</a>
              <a class="btn btn-secondary" href="/register?next={_esc(next_path)}">Create account</a>
            </p>
          </div>
          <div data-account-signed-in hidden>
            <h2>Account information</h2>
            <dl class="account-dl">
              <div><dt>Display name</dt><dd data-account-name></dd></div>
              <div><dt>Email</dt><dd data-account-email></dd></div>
              <div><dt>Email status</dt><dd data-account-verified></dd></div>
              <div><dt>Account id</dt><dd data-account-id></dd></div>
            </dl>
            <p data-account-verify-needed hidden>
              <a class="text-link" href="/verify-email">Verify your email</a>
            </p>

            <h2>Change email</h2>
            <p>Enter the new email address you want to use. We'll send a confirmation link there before changing your account.</p>
            <p class="form-status" data-email-change-status role="status" aria-live="polite"></p>
            <form class="account-form" data-account-form="email-change">
              <label class="field">
                <span>New email</span>
                <input name="new_email" type="email" autocomplete="email" required maxlength="254">
              </label>
              <label class="field">
                <span>Current password</span>
                <input name="password" type="password" autocomplete="current-password" required>
              </label>
              <button type="submit" class="btn btn-primary btn-block">Send confirmation</button>
            </form>

            <h2 id="saved">Saved decisions</h2>
            <p>Save keeps a buying decision or context for later. It does not watch prices and does not send notifications.</p>

            <h2 id="watch">Watch</h2>
            <p>Watch is not available yet. PiqSavi does not send price-update notifications or monitor saved items in the background.</p>

            <h2 id="consents">Privacy and consent</h2>
            <p>Your policy acknowledgements will appear here when applicable. See also <a href="/privacy">Privacy</a> and <a href="/terms">Terms</a>.</p>
            <p class="form-status" data-consent-status role="status"></p>
            <ul data-consent-records></ul>
            <p class="form-hint" data-consent-unpublished hidden>There are no policy acknowledgements recorded for this account yet.</p>

            <h2>Sessions</h2>
            <p>Sign out ends this device session.</p>
            <button type="button" class="btn btn-secondary" data-account-action="sign-out">Sign out</button>

            <h2 id="export">Download your data</h2>
            <p>Download a copy of the data stored on this PiqSavi account.</p>
            <p class="form-status" data-export-status role="status"></p>
            <button type="button" class="btn btn-primary" data-account-action="export">Download my data</button>

            <h2 id="delete">Delete account</h2>
            <p>Deleting your account requires your password and typing <strong>DELETE</strong>. This signs you out on all devices.</p>
            <p class="form-status" data-delete-status role="status"></p>
            <form class="account-form" data-account-form="delete">
              <label class="field">
                <span>Password</span>
                <input name="password" type="password" autocomplete="current-password" required>
              </label>
              <label class="field">
                <span>Type DELETE to confirm</span>
                <input name="confirmation" type="text" required maxlength="32">
              </label>
              <button type="submit" class="btn btn-danger btn-block">Delete my account</button>
            </form>
          </div>
        </section>
        """,
    )


def render_support_page() -> str:
    support = _esc(PUBLIC_SUPPORT_EMAIL)
    privacy = _esc(PUBLIC_PRIVACY_EMAIL)
    return render_account_document(
        title="Support — PiqSavi",
        page="support",
        main=f"""
        <section class="account-card">
          <h1>Support</h1>
          <p>Need help or want to report incorrect product information? Contact <a href="mailto:{support}">{support}</a>.</p>
          <p>For privacy questions, contact <a href="mailto:{privacy}">{privacy}</a>.</p>
          <h2 id="report">Report incorrect information</h2>
          <p>Email {support} to report an incorrect price, product fact, outdated offer, misleading evidence, or source issue.</p>
        </section>
        """,
    )


def public_head_extras(*, staging: bool) -> str:
    robots = (
        '<meta name="robots" content="noindex, nofollow">'
        if staging
        else f'<link rel="canonical" href="{escape(CANONICAL_ORIGIN + "/", quote=True)}">'
    )
    return (
        f"{robots}"
        '<link rel="icon" href="/static/early_access/assets/piqsavi-logo.png">'
        '<link rel="manifest" href="/static/consumer/manifest.webmanifest">'
        f'<script type="application/ld+json">{organization_json_ld()}</script>'
        f'<script type="application/ld+json">{website_json_ld()}</script>'
    )

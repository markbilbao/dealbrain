"""Server-rendered account, auth, and support document pages."""

# ruff: noqa: E501

from __future__ import annotations

from html import escape

from app.consumer.html import ICON_USER, h, logo_markup
from app.consumer.seo import CANONICAL_ORIGIN, organization_json_ld, website_json_ld
from app.core.public_brand import PUBLIC_BRAND, PUBLIC_TAGLINE
from app.legal.publication import LegalPublicationCatalog, unpublished_catalog


def _esc(value: object) -> str:
    return escape("" if value is None else str(value), quote=True)


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
  <body class="page-account" data-page="{h(page)}" data-next="{h(next_path)}">
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
        <a href="/account">Account</a>
        <a href="/support">Support</a>
      </nav>
      <div class="header-actions">
        <a class="text-link" href="/login?next={_esc(next_path)}">Sign in</a>
        <a class="btn btn-primary btn-compact" href="/register?next={_esc(next_path)}">Sign up</a>
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
      <p class="form-hint">Privacy Policy and Terms are not published yet. Those links return 404 until counsel publication.</p>
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
        intro = (
            "Registration stores your account. Terms of Service and Privacy Policy "
            "are not published yet. This form does not record acceptance of unpublished policies."
        )
        return intro, (
            '<p class="form-hint" data-legal-unpublished="true">'
            "Policies are not yet published. Registration will submit "
            "terms_accepted=false and privacy_acknowledged=false, and will not invent a consent record."
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
        form = f"""
          <form class="account-form" data-account-form="reset-confirm">
            <input type="hidden" name="token" value="{_esc(token)}">
            <label class="field">
              <span>New password</span>
              <input name="new_password" type="password" autocomplete="new-password" required minlength="8">
            </label>
            <button type="submit" class="btn btn-primary btn-block">Set new password</button>
          </form>
        """
        heading = "Choose a new password"
        copy = "This form confirms a reset token. It does not invent email delivery."
    else:
        form = """
          <form class="account-form" data-account-form="reset-request">
            <label class="field">
              <span>Email</span>
              <input name="email" type="email" autocomplete="email" required maxlength="254">
            </label>
            <button type="submit" class="btn btn-primary btn-block">Request reset</button>
          </form>
        """
        heading = "Reset your password"
        copy = (
            "If an account exists, PiqSavi accepts the request. "
            "A reset email is sent only when identity email delivery is available. "
            "This page does not display demo tokens."
        )
    return render_account_document(
        title="Reset password — PiqSavi",
        page="reset-password",
        main=f"""
        <section class="account-card">
          <h1>{h(heading)}</h1>
          <p>{h(copy)}</p>
          {notice}
          <p class="form-status" data-account-status role="status"></p>
          {form}
          <p><a class="text-link" href="/login">Back to sign in</a></p>
        </section>
        """,
    )


def render_verify_email_page(*, token: str = "", email: str = "") -> str:
    if token:
        form = f"""
          <form class="account-form" data-account-form="verify-confirm">
            <input type="hidden" name="token" value="{_esc(token)}">
            <button type="submit" class="btn btn-primary btn-block">Confirm email</button>
          </form>
        """
        copy = "Confirm this verification token. The page does not invent a verified state before the API succeeds."
    else:
        form = f"""
          <form class="account-form" data-account-form="verify-request">
            <label class="field">
              <span>Email</span>
              <input name="email" type="email" value="{_esc(email)}" autocomplete="email" required maxlength="254">
            </label>
            <button type="submit" class="btn btn-primary btn-block">Request verification</button>
          </form>
        """
        copy = (
            "Verification email is sent only when identity email delivery is available. "
            "This page does not display demo tokens."
        )
    return render_account_document(
        title="Verify email — PiqSavi",
        page="verify-email",
        main=f"""
        <section class="account-card">
          <h1>Email verification</h1>
          <p>{h(copy)}</p>
          <p class="form-status" data-account-status role="status"></p>
          {form}
          <p><a class="text-link" href="/account">Account settings</a></p>
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
          <p class="form-status" data-account-status role="status">Checking this device session…</p>
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
            <p class="form-hint">Email verification uses the Sprint 27 identity APIs. Delivery happens only when the identity email adapter is ready.</p>
            <p><a class="text-link" href="/verify-email">Request or confirm email verification</a></p>

            <h2 id="saved">Saved decisions</h2>
            <p>Save keeps a buying decision or context for later. It does not watch prices and does not send notifications.</p>

            <h2 id="watch">Watch</h2>
            <p>Watch is not available yet. PiqSavi does not send price-update notifications or monitor saved items in the background.</p>

            <h2>Privacy and consent</h2>
            <p>Consent records are stored only when a published policy version exists. <a href="/privacy">Privacy</a> and <a href="/terms">Terms</a> are unpublished 404 pages until counsel publication.</p>

            <h2>Sessions</h2>
            <p>Sign out ends this device session. A session list or revoke-other-devices API is not exposed. Export includes session metadata for this account.</p>
            <button type="button" class="btn btn-secondary" data-account-action="sign-out">Sign out</button>

            <h2 id="export">Download your data</h2>
            <p>This requests the Sprint 28 engineering export <code>piqsavi.account_owned_export.v1</code>. It is not a complete legal DSAR and does not include Early Access waitlist rows.</p>
            <p class="form-status" data-export-status role="status"></p>
            <button type="button" class="btn btn-primary" data-account-action="export">Download my data</button>

            <h2 id="delete">Delete account</h2>
            <p>Deletion requires your password and typing <strong>DELETE</strong>. This calls the Sprint 28 deletion API, revokes sessions, and does not claim backup, log, or vendor erasure.</p>
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
    return render_account_document(
        title="Support — PiqSavi",
        page="support",
        main="""
        <section class="account-card">
          <h1>Support and feedback</h1>
          <p>Use these contacts. An in-product ticket or analytics backend is owned by Sprint 39 and is not live.</p>
          <ul>
            <li><a href="mailto:support@piqsavi.com">support@piqsavi.com</a></li>
            <li><a href="mailto:privacy@piqsavi.com">privacy@piqsavi.com</a></li>
            <li><a href="mailto:legal@piqsavi.com">legal@piqsavi.com</a></li>
          </ul>
          <h2 id="report">Report incorrect information</h2>
          <p>Email support@piqsavi.com to report an incorrect price, product fact, outdated offer, misleading evidence, or source issue. There is no automated report form until Sprint 39.</p>
          <p class="form-hint">This page does not collect a support ticket and does not claim a monitored product inbox beyond the published mailbox identities.</p>
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

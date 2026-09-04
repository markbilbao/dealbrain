"""Identity email sender factory and trusted action-link helpers."""

from __future__ import annotations

from typing import Any
from urllib.parse import urlencode, urlparse

from app.auth.email import EmailSender, NullEmailSender
from app.auth.email_resend import ResendEmailSender
from app.core.config import Settings
from app.domain.exceptions import ConfigurationValidationError, UserPlatformValidationError

KNOWN_APP_ENVS = frozenset({"development", "staging", "production"})


def _current_settings() -> Settings:
    from app.core.config import settings as current

    return current


def allows_inline_identity_tokens(cfg: Settings | None = None) -> bool:
    """Return True only when the environment contract permits demo tokens.

    Development may expose tokens when ``ALLOW_DEMO_RESET_TOKENS`` is true.
    Staging, production, and unknown environments never may.
    """
    cfg = cfg or _current_settings()
    if cfg.app_env not in KNOWN_APP_ENVS:
        return False
    return bool(cfg.allow_demo_reset_tokens and cfg.is_development)


def build_trusted_action_url(base_url: str, path: str, token: str) -> str:
    """Build an action URL from trusted server configuration only.

    Never use an untrusted request Host header.
    """
    cleaned = (base_url or "").strip().rstrip("/")
    if not cleaned:
        raise UserPlatformValidationError("PUBLIC_APP_BASE_URL is not configured.")
    parsed = urlparse(cleaned)
    if parsed.scheme not in {"http", "https"} or not parsed.netloc:
        raise UserPlatformValidationError("PUBLIC_APP_BASE_URL is invalid.")
    if parsed.username or parsed.password:
        raise UserPlatformValidationError("PUBLIC_APP_BASE_URL is invalid.")
    normalized_path = path if path.startswith("/") else f"/{path}"
    return f"{cleaned}{normalized_path}?{urlencode({'token': token})}"


def identity_email_status(cfg: Settings | None = None) -> dict[str, Any]:
    """Report identity-email adapter truth without claiming inbox E2E.

    Staging may operate with ``NullEmailSender`` during external setup.
    That is not configured, verified, or ready transactional email.
    ``ready`` stays False until Sprint 27 external evidence exists.
    """
    cfg = cfg or _current_settings()
    if cfg.app_env not in KNOWN_APP_ENVS or (
        cfg.is_production and cfg.transactional_email_provider != "resend"
    ):
        adapter = "unavailable"
    elif cfg.transactional_email_provider == "resend":
        adapter = "resend"
    else:
        adapter = "null"
    return {
        "adapter": adapter,
        "ready": False,
    }


def build_identity_email_sender(cfg: Settings | None = None) -> EmailSender:
    """Select the identity email sender.

    Production refuses ``NullEmailSender``. Staging may use it when the
    provider is still ``null``, but that is not email readiness.
    """
    cfg = cfg or _current_settings()
    if cfg.app_env not in KNOWN_APP_ENVS:
        raise ConfigurationValidationError(
            [f"Unknown APP_ENV {cfg.app_env!r} — refuse identity email sender"]
        )
    if cfg.is_production:
        if cfg.transactional_email_provider != "resend":
            raise ConfigurationValidationError(
                [
                    "TRANSACTIONAL_EMAIL_PROVIDER must be 'resend' in "
                    "production (NullEmailSender is not permitted)"
                ]
            )
        return _resend_from_settings(cfg)
    if cfg.transactional_email_provider == "resend":
        return _resend_from_settings(cfg)
    return NullEmailSender()


def _resend_from_settings(cfg: Settings) -> ResendEmailSender:
    return ResendEmailSender(
        api_key=cfg.resend_api_key,
        from_address=cfg.transactional_email_from,
        from_name=cfg.transactional_email_from_name,
    )

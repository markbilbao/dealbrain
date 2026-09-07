"""Identity email sender factory and trusted action-link helpers."""

from __future__ import annotations

from typing import Any
from urllib.parse import urlencode, urlparse

from app.auth.email import EmailSender, NullEmailSender
from app.auth.email_resend import ResendEmailSender
from app.core.config import Settings
from app.domain.exceptions import ConfigurationValidationError, UserPlatformValidationError

KNOWN_APP_ENVS = frozenset({"development", "staging", "production"})
EXTERNAL_EVIDENCE_PENDING = "pending"


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


def build_trusted_action_url(
    base_url: str,
    path: str,
    token: str,
    *,
    require_https: bool = False,
) -> str:
    """Build an action URL from trusted server configuration only.

    Never use an untrusted request Host header.
    Production callers must pass ``require_https=True``. Staging may use http
    in the builder when that is the configured origin; that is not TLS proof.
    """
    cleaned = (base_url or "").strip().rstrip("/")
    if not cleaned:
        raise UserPlatformValidationError("PUBLIC_APP_BASE_URL is not configured.")
    parsed = urlparse(cleaned)
    allowed_schemes = {"https"} if require_https else {"http", "https"}
    if parsed.scheme not in allowed_schemes or not parsed.netloc:
        raise UserPlatformValidationError("PUBLIC_APP_BASE_URL is invalid.")
    if parsed.username or parsed.password:
        raise UserPlatformValidationError("PUBLIC_APP_BASE_URL is invalid.")
    normalized_path = path if path.startswith("/") else f"/{path}"
    return f"{cleaned}{normalized_path}?{urlencode({'token': token})}"


def identity_email_configured(cfg: Settings | None = None) -> bool:
    """Return True when the Resend adapter has non-placeholder runtime config.

    Configuration is not inbox delivery, DNS verification, or Sprint 27 ready.
    """
    cfg = cfg or _current_settings()
    if cfg.transactional_email_provider != "resend":
        return False
    key = (cfg.resend_api_key or "").strip()
    sender = (cfg.transactional_email_from or "").strip()
    if not key or _looks_like_unusable_secret(key):
        return False
    if not sender or "@" not in sender or _looks_like_unusable_secret(sender):
        return False
    parsed = urlparse((cfg.public_app_base_url or "").strip())
    if not parsed.netloc or parsed.username or parsed.password:
        return False
    if cfg.is_production:
        return parsed.scheme == "https"
    return parsed.scheme in {"http", "https"}


def identity_email_status(cfg: Settings | None = None) -> dict[str, Any]:
    """Report identity-email adapter truth without claiming inbox E2E.

    Staging may operate with ``NullEmailSender`` during external setup.
    That is not configured, verified, or ready transactional email.
    ``ready`` stays False until Sprint 27 external evidence exists.
    ``configured`` means the Resend adapter can be constructed from settings.
    ``external_evidence`` stays ``pending`` until DNS + real inbox E2E exist.
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
        "configured": identity_email_configured(cfg),
        "external_evidence": EXTERNAL_EVIDENCE_PENDING,
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


def _looks_like_unusable_secret(value: str) -> bool:
    lowered = value.strip().lower()
    if not lowered:
        return True
    if lowered in {
        "change_me",
        "changeme",
        "replace_me",
        "password",
        "secret",
        "todo",
        "placeholder",
        "example",
        "test",
        "dev",
    }:
        return True
    if "change_me" in lowered or "replace_me" in lowered:
        return True
    if lowered.startswith("<") and lowered.endswith(">"):
        return True
    return lowered.startswith("${") and lowered.endswith("}")

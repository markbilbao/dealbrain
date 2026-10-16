"""Launch-readiness admin bearer.

Staging and production authorize only with ``LAUNCH_ADMIN_TOKEN`` injected from
the environment (Secrets Manager leaf ``dealbrain/<env>/launch_admin_token``).
They never accept the local development bearer, and a missing, placeholder, or
demo value fails closed.

Development accepts that published bearer only when ``LAUNCH_ADMIN_TOKEN`` is
empty. An explicit development token replaces it and does not fall back to the
published bearer.

``APP_SECRET_KEY`` is a signing secret. It is not this bearer.
"""

from __future__ import annotations

import hmac

from app.core.config import Settings, settings
from app.domain.exceptions import LaunchAuthorizationError

# Published local-development bearer. The name is not a credential store:
# staging and production never authorize with this value.
_LOCAL_DEVELOPMENT_GATE = "demo-token-internal-admin"
_SHARED_ENVIRONMENTS = frozenset({"staging", "production"})
MINIMUM_SHARED_LAUNCH_ADMIN_TOKEN_LENGTH = 32


def _equals(left: str, right: str) -> bool:
    """Constant-time string compare. Different lengths compare as unequal."""

    return hmac.compare_digest(left.encode("utf-8"), right.encode("utf-8"))


def launch_admin_token_is_acceptable(value: str) -> bool:
    """Return True when a staging or production process may authorize with ``value``.

    Callers must not log ``value``. The local development bearer is rejected
    even when it is supplied through the environment.
    """

    from app.core.validation import _looks_like_placeholder

    token = (value or "").strip()
    if len(token) < MINIMUM_SHARED_LAUNCH_ADMIN_TOKEN_LENGTH:
        return False
    if _equals(token.casefold(), _LOCAL_DEVELOPMENT_GATE.casefold()):
        return False
    return not _looks_like_placeholder(token)


def _presented_bearer(authorization: str | None) -> str:
    if not authorization or not authorization.lower().startswith("bearer "):
        raise LaunchAuthorizationError("Admin bearer token required")
    presented = authorization.split(" ", 1)[1].strip()
    if not presented:
        raise LaunchAuthorizationError("Admin bearer token required")
    return presented


def _authorize_shared(presented: str, cfg: Settings) -> None:
    configured = (cfg.launch_admin_token or "").strip()
    acceptable = launch_admin_token_is_acceptable(configured)
    # Always compare. An unacceptable configuration must not skip the compare
    # and it must not succeed, including when the presented value is the
    # local development bearer.
    reference = configured if acceptable else _LOCAL_DEVELOPMENT_GATE
    matches = _equals(presented, reference)
    if not acceptable or not matches:
        raise LaunchAuthorizationError("Internal admin token required for this action")


def _authorize_development(presented: str, cfg: Settings) -> None:
    configured = (cfg.launch_admin_token or "").strip()
    if configured:
        if not _equals(presented, configured):
            raise LaunchAuthorizationError("Internal admin token required for this action")
        return
    if not _equals(presented, _LOCAL_DEVELOPMENT_GATE):
        raise LaunchAuthorizationError("Internal admin token required for this action")


def require_internal_launch_admin(
    authorization: str | None,
    cfg: Settings | None = None,
) -> None:
    """Authorize one launch-admin request. Never logs the bearer."""

    active = cfg or settings
    presented = _presented_bearer(authorization)
    if active.app_env in _SHARED_ENVIRONMENTS:
        _authorize_shared(presented, active)
        return
    if active.app_env == "development":
        _authorize_development(presented, active)
        return
    raise LaunchAuthorizationError("Internal admin token required for this action")

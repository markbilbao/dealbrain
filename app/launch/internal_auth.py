"""Shared demo/internal launch admin gate.

Sprint 22 introduced this bearer check for the launch readiness surface.
Sprint 39.2 reuses the same token and the same error text for the internal
product-learning routes. This is not production IAM. Sprint 40 and Sprint 41
own later hardening and deployment. Do not add a second hard-coded token.
"""

from __future__ import annotations

from app.domain.exceptions import LaunchAuthorizationError

INTERNAL_LAUNCH_ADMIN_TOKEN = "demo-token-internal-admin"


def require_internal_launch_admin(authorization: str | None) -> None:
    """Demo admin gate — bearer demo-token-internal-admin (no real IAM)."""

    if not authorization or not authorization.lower().startswith("bearer "):
        raise LaunchAuthorizationError("Admin bearer token required")
    token = authorization.split(" ", 1)[1].strip()
    if token != INTERNAL_LAUNCH_ADMIN_TOKEN:
        raise LaunchAuthorizationError("Internal admin token required for this action")

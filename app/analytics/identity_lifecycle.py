"""Server-owned identity lifecycle product analytics.

These events measure the existing account and guest-claim transitions. They
are not security-audit copies and they do not carry raw account identity.

Emission points
---------------
``registration_completed``
    After ``POST /api/v1/auth/register`` has created the account and session.
    Validation failure, duplicate email, rate limit, and failed persistence
    do not emit.

``registration_verified``
    After ``POST /api/v1/auth/verify-email/confirm`` has marked the account
    verified. Requesting a verification email does not emit. An invalid or
    expired token does not emit.

``login_success``
    After ``POST /api/v1/auth/login`` has authenticated and issued a session.

``login_failure``
    After that same login endpoint has determined the attempt failed.
    ``error_code`` is one of ``auth_failed``, ``validation_failed``, or
    ``rate_limited``. Unknown email, inactive account, and a wrong password
    all use ``auth_failed``. The code does not say which one happened.

``account_deleted``
    After the existing account-deletion operation has completed. The event
    records that operation. It does not claim legal erasure beyond Sprint 28.

``authentication_transition``
    After ``POST /consumer/claim-decision`` returns ``claimed`` true. Every
    unsuccessful claim, including an immutable snapshot owner, emits nothing.

Consent and identity
--------------------
Callers use ``analytics_context_for_request`` with subject minting left off.
Analytics off writes zero rows. Explicit consent without an already valid
opaque subject also writes zero rows. Authentication does not mint a subject
and does not create an account-linked analytics identity.

``identity_kind`` stays whatever that helper derived from the request owner
cookie. A login or claim that succeeds while the browser is still a guest is
recorded as guest. This module does not rewrite it to authenticated.

Event ids
---------
Every emission uses the random server event id from ``record_server_event``.
``deterministic_event_id`` is not used.

- ``registration_completed``: email and user id are forbidden id material.
  A duplicate registration does not emit, so a retry does not need a stable id.
- ``registration_verified``: the verification token and account id are forbidden.
  A second confirmation fails and does not emit.
- ``login_success`` and ``login_failure``: each attempt is its own action.
  A stable id would collapse distinct attempts.
- ``account_deleted``: user id is forbidden. A rejected repeat does not emit.
- ``authentication_transition``: conversation id, account id, and session id
  are forbidden. Only a successful claim emits, so a failed retry adds no row.

Analytics failure
-----------------
Persistence, schema, and repository failures are swallowed here. The helper
does not catch the auth or claim exception. Those still propagate.
"""

from __future__ import annotations

from starlette.requests import Request
from starlette.responses import Response

from app.analytics.request_context import analytics_context_for_request
from app.analytics.schema import IDENTITY_LIFECYCLE_EVENT_NAMES
from app.analytics.service import ProductAnalyticsService
from app.domain.exceptions import UserPlatformRateLimitError, UserPlatformValidationError

LOGIN_FAILURE_ERROR_CODES: frozenset[str] = frozenset(
    {
        "auth_failed",
        "validation_failed",
        "rate_limited",
    }
)

_ACCOUNT_COMPLETE = {
    "surface": "account",
    "action_type": "complete",
    "outcome": "completed",
}


def login_failure_error_code(exc: BaseException) -> str:
    """Map a login failure to a generic product code.

    The message, audit detail, and exception class name are not the code.
    Anything other than validation or rate limit stays ``auth_failed``.
    """

    if isinstance(exc, UserPlatformRateLimitError):
        return "rate_limited"
    if isinstance(exc, UserPlatformValidationError):
        return "validation_failed"
    return "auth_failed"


def emit_registration_completed(
    request: Request,
    response: Response | None,
    analytics: ProductAnalyticsService,
) -> None:
    _emit(request, response, analytics, event_name="registration_completed", **_ACCOUNT_COMPLETE)


def emit_registration_verified(
    request: Request,
    response: Response | None,
    analytics: ProductAnalyticsService,
) -> None:
    _emit(request, response, analytics, event_name="registration_verified", **_ACCOUNT_COMPLETE)


def emit_login_success(
    request: Request,
    response: Response | None,
    analytics: ProductAnalyticsService,
) -> None:
    _emit(
        request,
        response,
        analytics,
        event_name="login_success",
        surface="account",
        action_type="submit",
        outcome="completed",
    )


def emit_login_failure(
    request: Request,
    response: Response | None,
    analytics: ProductAnalyticsService,
    exc: BaseException,
) -> None:
    _emit(
        request,
        response,
        analytics,
        event_name="login_failure",
        surface="account",
        action_type="submit",
        outcome="failed",
        error_code=login_failure_error_code(exc),
    )


def emit_account_deleted(
    request: Request,
    response: Response | None,
    analytics: ProductAnalyticsService,
) -> None:
    _emit(request, response, analytics, event_name="account_deleted", **_ACCOUNT_COMPLETE)


def emit_authentication_transition(
    request: Request,
    response: Response | None,
    analytics: ProductAnalyticsService,
    *,
    claimed: bool,
) -> None:
    if claimed is not True:
        return
    _emit(
        request,
        response,
        analytics,
        event_name="authentication_transition",
        **_ACCOUNT_COMPLETE,
    )


def _emit(
    request: Request,
    response: Response | None,
    analytics: ProductAnalyticsService,
    *,
    event_name: str,
    surface: str,
    action_type: str,
    outcome: str,
    error_code: str | None = None,
) -> None:
    if event_name not in IDENTITY_LIFECYCLE_EVENT_NAMES:
        return
    if error_code is not None and error_code not in LOGIN_FAILURE_ERROR_CODES:
        return
    try:
        context = analytics_context_for_request(request, response, mint_subject=False)
        analytics.record_server_event(
            context,
            event_name=event_name,
            surface=surface,
            action_type=action_type,
            outcome=outcome,
            error_code=error_code,
        )
    except Exception:  # noqa: BLE001 — analytics must not change the auth or claim result
        return

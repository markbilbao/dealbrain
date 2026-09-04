"""User Platform authentication API endpoints.

Sessions are opaque bearer tokens returned on register/login and must be sent
as ``Authorization: Bearer <token>`` on subsequent authenticated requests.
Password reset and email verification are Sprint 27.1 identity flows.
"""

from __future__ import annotations

from fastapi import APIRouter, Depends, Header, HTTPException, Response, status

from app.api.v1.mappers.user_platform import (
    to_auth_response,
    to_demo_response,
    to_meta_response,
    to_user_payload,
)
from app.core.dependencies import get_user_platform_service
from app.domain.exceptions import (
    UserPlatformAuthError,
    UserPlatformConflictError,
    UserPlatformNotFoundError,
    UserPlatformRateLimitError,
    UserPlatformValidationError,
)
from app.schemas.user_platform import (
    AccountDeleteRequest,
    AccountDeleteResponse,
    AuthResponse,
    EmailVerificationConfirmRequest,
    EmailVerificationConfirmResponse,
    EmailVerificationRequestBody,
    IdentityEmailAcceptedResponse,
    LoginRequest,
    PasswordResetConfirmRequest,
    PasswordResetConfirmResponse,
    PasswordResetRequestBody,
    PersonalDataExportResponse,
    RegisterRequest,
    UserPayload,
    UserPlatformDemoResponse,
    UserPlatformMetaResponse,
)
from app.services.user_platform_service import UserPlatformService

router = APIRouter(prefix="/auth")


def extract_bearer_token(authorization: str | None) -> str | None:
    """Extract a bearer token from an ``Authorization`` header value.

    Returns ``None`` when the header is missing or malformed rather than
    raising, so callers can decide how to handle anonymous requests.
    """
    if not authorization:
        return None
    parts = authorization.strip().split(" ", 1)
    if len(parts) != 2 or parts[0].lower() != "bearer":
        return None
    token = parts[1].strip()
    return token or None


def map_user_platform_error(exc: Exception) -> HTTPException:
    if isinstance(exc, UserPlatformValidationError):
        return HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=exc.message)
    if isinstance(exc, UserPlatformAuthError):
        return HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail=exc.message)
    if isinstance(exc, UserPlatformConflictError):
        return HTTPException(status_code=status.HTTP_409_CONFLICT, detail=exc.message)
    if isinstance(exc, UserPlatformRateLimitError):
        return HTTPException(status_code=status.HTTP_429_TOO_MANY_REQUESTS, detail=exc.message)
    if isinstance(exc, UserPlatformNotFoundError):
        return HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc))
    return HTTPException(
        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        detail="User platform failed to process the request.",
    )


@router.post(
    "/register",
    response_model=AuthResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Register a new demo account and start a session",
)
async def register(
    body: RegisterRequest,
    service: UserPlatformService = Depends(get_user_platform_service),
) -> AuthResponse:
    try:
        result = service.register(
            email=body.email,
            password=body.password,
            display_name=body.display_name,
            remember_me=body.remember_me,
            terms_accepted=body.terms_accepted,
            privacy_acknowledged=body.privacy_acknowledged,
        )
    except (
        UserPlatformValidationError,
        UserPlatformConflictError,
        UserPlatformRateLimitError,
    ) as exc:
        raise map_user_platform_error(exc) from exc
    return to_auth_response(result)


@router.post(
    "/login",
    response_model=AuthResponse,
    summary="Log in to a demo account and start a session",
)
async def login(
    body: LoginRequest,
    service: UserPlatformService = Depends(get_user_platform_service),
) -> AuthResponse:
    try:
        result = service.login(
            email=body.email,
            password=body.password,
            remember_me=body.remember_me,
        )
    except (
        UserPlatformValidationError,
        UserPlatformAuthError,
        UserPlatformRateLimitError,
    ) as exc:
        raise map_user_platform_error(exc) from exc
    return to_auth_response(result)


@router.post(
    "/logout",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Log out and revoke the current session",
)
async def logout(
    response: Response,
    authorization: str | None = Header(default=None),
    service: UserPlatformService = Depends(get_user_platform_service),
) -> Response:
    token = extract_bearer_token(authorization)
    try:
        service.logout(token)
    except UserPlatformValidationError as exc:
        raise map_user_platform_error(exc) from exc
    response.status_code = status.HTTP_204_NO_CONTENT
    return response


@router.post(
    "/password-reset",
    response_model=IdentityEmailAcceptedResponse,
    response_model_exclude_none=True,
    summary="Request a password reset (enumeration-safe)",
)
async def request_password_reset(
    body: PasswordResetRequestBody,
    service: UserPlatformService = Depends(get_user_platform_service),
) -> IdentityEmailAcceptedResponse:
    try:
        payload = service.request_password_reset(body.email)
    except (
        UserPlatformValidationError,
        UserPlatformRateLimitError,
    ) as exc:
        raise map_user_platform_error(exc) from exc
    return IdentityEmailAcceptedResponse.model_validate(payload)


@router.post(
    "/password-reset/confirm",
    response_model=PasswordResetConfirmResponse,
    summary="Confirm a password reset token and set a new password",
)
async def confirm_password_reset(
    body: PasswordResetConfirmRequest,
    service: UserPlatformService = Depends(get_user_platform_service),
) -> PasswordResetConfirmResponse:
    try:
        payload = service.confirm_password_reset(body.token, body.new_password)
    except (
        UserPlatformValidationError,
        UserPlatformAuthError,
        UserPlatformRateLimitError,
    ) as exc:
        raise map_user_platform_error(exc) from exc
    return PasswordResetConfirmResponse.model_validate(payload)


@router.post(
    "/verify-email",
    response_model=IdentityEmailAcceptedResponse,
    response_model_exclude_none=True,
    summary="Request email verification (enumeration-safe)",
)
async def request_email_verification(
    body: EmailVerificationRequestBody,
    service: UserPlatformService = Depends(get_user_platform_service),
) -> IdentityEmailAcceptedResponse:
    try:
        payload = service.request_email_verification(body.email)
    except (
        UserPlatformValidationError,
        UserPlatformRateLimitError,
    ) as exc:
        raise map_user_platform_error(exc) from exc
    return IdentityEmailAcceptedResponse.model_validate(payload)


@router.post(
    "/verify-email/confirm",
    response_model=EmailVerificationConfirmResponse,
    summary="Confirm an email verification token",
)
async def confirm_email_verification(
    body: EmailVerificationConfirmRequest,
    service: UserPlatformService = Depends(get_user_platform_service),
) -> EmailVerificationConfirmResponse:
    try:
        payload = service.confirm_email_verification(body.token)
    except (
        UserPlatformValidationError,
        UserPlatformAuthError,
        UserPlatformRateLimitError,
    ) as exc:
        raise map_user_platform_error(exc) from exc
    return EmailVerificationConfirmResponse.model_validate(payload)


@router.get(
    "/me",
    response_model=UserPayload,
    summary="Get the currently authenticated user",
)
async def me(
    authorization: str | None = Header(default=None),
    service: UserPlatformService = Depends(get_user_platform_service),
) -> UserPayload:
    token = extract_bearer_token(authorization)
    try:
        user = service.me(token)
    except (UserPlatformAuthError, UserPlatformValidationError) as exc:
        raise map_user_platform_error(exc) from exc
    return to_user_payload(user)


@router.post(
    "/account/delete",
    response_model=AccountDeleteResponse,
    summary="Delete the authenticated consumer account",
)
async def delete_account(
    body: AccountDeleteRequest,
    authorization: str | None = Header(default=None),
    service: UserPlatformService = Depends(get_user_platform_service),
) -> AccountDeleteResponse:
    token = extract_bearer_token(authorization)
    try:
        result = service.delete_account(
            token,
            confirmation=body.confirmation,
            password=body.password,
        )
    except (UserPlatformAuthError, UserPlatformValidationError) as exc:
        raise map_user_platform_error(exc) from exc
    return AccountDeleteResponse.model_validate(result.to_dict())


@router.get(
    "/account/export",
    response_model=PersonalDataExportResponse,
    summary="Export personal data for the authenticated consumer account",
)
async def export_account(
    authorization: str | None = Header(default=None),
    service: UserPlatformService = Depends(get_user_platform_service),
) -> PersonalDataExportResponse:
    token = extract_bearer_token(authorization)
    try:
        payload = service.export_personal_data(token)
    except (UserPlatformAuthError, UserPlatformValidationError) as exc:
        raise map_user_platform_error(exc) from exc
    return PersonalDataExportResponse.model_validate(payload)


@router.get(
    "/demo",
    response_model=UserPlatformDemoResponse,
    summary="List demo accounts available for login (Sprint 17)",
)
async def demo(
    service: UserPlatformService = Depends(get_user_platform_service),
) -> UserPlatformDemoResponse:
    return to_demo_response(service.demo())


@router.get(
    "/meta",
    response_model=UserPlatformMetaResponse,
    summary="User platform metadata, limitations, and endpoint map",
)
async def meta(
    service: UserPlatformService = Depends(get_user_platform_service),
) -> UserPlatformMetaResponse:
    return to_meta_response(service.meta())

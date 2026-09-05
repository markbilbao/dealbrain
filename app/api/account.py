"""FastAPI document routes for account, auth presentation, and support."""

from __future__ import annotations

from fastapi import APIRouter, Depends, Header, Query, Request
from fastapi.responses import HTMLResponse, JSONResponse

from app.api.v1.endpoints.auth import extract_bearer_token
from app.consumer.account_pages import (
    render_account_settings_page,
    render_login_page,
    render_register_page,
    render_reset_password_page,
    render_support_page,
    render_verify_email_page,
)
from app.consumer.decision_owner import OWNER_COOKIE, parse_owner_cookie, set_owner_cookie
from app.consumer.guest_continuity import (
    account_owner_from_session,
    claim_guest_conversation,
    clear_owner_cookie,
)
from app.consumer.robots import apply_private_decision_noindex
from app.consumer.seo import apply_noindex
from app.core.dependencies import (
    get_legal_publication_catalog,
    get_shopping_conversation_repository,
    get_shopping_decision_snapshot_repository,
    get_user_platform_service,
)
from app.legal.publication import LegalPublicationCatalog
from app.domain.exceptions import UserPlatformAuthError, UserPlatformValidationError
from app.domain.interfaces.decision_snapshot_repository import DecisionSnapshotRepository
from app.domain.interfaces.shopping_assistant_repository import ConversationRepository
from app.services.user_platform_service import UserPlatformService

router = APIRouter(include_in_schema=False)

_ALLOWED_NEXT_PREFIXES = (
    "/results/",
    "/compare/",
    "/why-best-piq/",
    "/account",
    "/search",
)


def _safe_next(next_path: str | None) -> str:
    value = next_path or "/account"
    if value.startswith(_ALLOWED_NEXT_PREFIXES) or value in {"/account", "/search"}:
        return value
    return "/account"


def _page(html: str) -> HTMLResponse:
    return apply_noindex(apply_private_decision_noindex(HTMLResponse(html)))


@router.get("/login", response_class=HTMLResponse)
async def login_page(next: str | None = Query(default="/account")) -> HTMLResponse:
    return _page(render_login_page(next_path=_safe_next(next)))


@router.get("/register", response_class=HTMLResponse)
async def register_page(
    next: str | None = Query(default="/account"),
    catalog: LegalPublicationCatalog = Depends(get_legal_publication_catalog),
) -> HTMLResponse:
    return _page(render_register_page(next_path=_safe_next(next), catalog=catalog))


@router.get("/reset-password", response_class=HTMLResponse)
async def reset_password_page(token: str | None = Query(default=None)) -> HTMLResponse:
    return _page(render_reset_password_page(token=token or ""))


@router.get("/verify-email", response_class=HTMLResponse)
async def verify_email_page(
    token: str | None = Query(default=None),
    email: str | None = Query(default=None),
) -> HTMLResponse:
    return _page(render_verify_email_page(token=token or "", email=email or ""))


@router.get("/account", response_class=HTMLResponse)
async def account_settings_page(next: str | None = Query(default="/account")) -> HTMLResponse:
    return _page(render_account_settings_page(next_path=_safe_next(next)))


@router.get("/support", response_class=HTMLResponse)
async def support_page() -> HTMLResponse:
    return _page(render_support_page())


@router.post("/account/clear-device")
async def clear_device_session() -> JSONResponse:
    response = JSONResponse({"status": "cleared"})
    clear_owner_cookie(response)
    return apply_noindex(response)


@router.post("/consumer/claim-decision")
async def claim_decision(
    request: Request,
    authorization: str | None = Header(default=None),
    service: UserPlatformService = Depends(get_user_platform_service),
    conversations: ConversationRepository = Depends(get_shopping_conversation_repository),
    snapshots: DecisionSnapshotRepository = Depends(get_shopping_decision_snapshot_repository),
) -> JSONResponse:
    token = extract_bearer_token(authorization)
    try:
        user = service.require_user(token)
        session = service.current_session(token)
    except (UserPlatformAuthError, UserPlatformValidationError) as exc:
        return apply_noindex(JSONResponse({"detail": exc.message}, status_code=401))

    try:
        payload = await request.json()
    except Exception:  # noqa: BLE001 — invalid JSON is a client error
        payload = {}
    if not isinstance(payload, dict):
        payload = {}

    guest = parse_owner_cookie(request.cookies.get(OWNER_COOKIE))
    account_owner = account_owner_from_session(
        user_id=user.user_id,
        session_id=session.session_id,
        expires_at=session.expires_at,
    )
    result = claim_guest_conversation(
        conversation_id=str(payload.get("conversation_id") or ""),
        decision_id=str(payload.get("decision_id") or "") or None,
        guest_owner=guest,
        account_owner=account_owner,
        conversations=conversations,
        snapshots=snapshots,
    )
    response = JSONResponse(result)
    if result.get("claimed"):
        set_owner_cookie(response, account_owner)
    return apply_noindex(response)

"""Merchant Platform API endpoints — Sprint 21.

Routes under ``/api/v1/merchants`` and ``/api/v1/admin/...``.

Authentication: ``Authorization: Bearer <demo-token>`` (or raw demo token).
Demo merchants only — no public self-service launch, no real billing.
"""

from __future__ import annotations

from fastapi import APIRouter, Depends, Header, HTTPException, Query, status

from app.api.v1.mappers.merchant import (
    drop_none,
    parse_optional_datetime,
    to_analytics_response,
    to_campaign_payload,
    to_invitation_payload,
    to_membership_payload,
    to_offer_payload,
    to_organization_payload,
    to_product_payload,
    to_promotion_payload,
    to_ranking_explanation_response,
)
from app.core.dependencies import (
    get_merchant_admin_service,
    get_merchant_analytics_service,
    get_merchant_auth_service,
    get_merchant_campaign_service,
    get_merchant_membership_service,
    get_merchant_offer_service,
    get_merchant_organization_service,
    get_merchant_product_service,
    get_merchant_promotion_service,
    get_merchant_repository,
)
from app.domain.exceptions import (
    MerchantAuthorizationError,
    MerchantIsolationError,
    MerchantNotFoundError,
    MerchantValidationError,
)
from app.merchant.fixtures import DEMO_TOKENS, LIMITATIONS
from app.schemas.merchant import (
    MerchantAdminNotesRequest,
    MerchantAdminRejectRequest,
    MerchantAnalyticsResponse,
    MerchantAuditLogResponse,
    MerchantCampaignCreateRequest,
    MerchantCampaignListResponse,
    MerchantCampaignPayload,
    MerchantCampaignUpdateRequest,
    MerchantDemoMetaResponse,
    MerchantInvitationCreateRequest,
    MerchantInvitationPayload,
    MerchantMembershipListResponse,
    MerchantMembershipPayload,
    MerchantOfferCreateRequest,
    MerchantOfferListResponse,
    MerchantOfferPayload,
    MerchantOfferUpdateRequest,
    MerchantOrganizationCreateRequest,
    MerchantOrganizationListResponse,
    MerchantOrganizationPayload,
    MerchantOrganizationUpdateRequest,
    MerchantProductCreateRequest,
    MerchantProductListResponse,
    MerchantProductPayload,
    MerchantProductUpdateRequest,
    MerchantPromotionCreateRequest,
    MerchantPromotionListResponse,
    MerchantPromotionPayload,
    MerchantPromotionUpdateRequest,
    MerchantRankingExplanationResponse,
    MerchantRoleUpdateRequest,
    MerchantVerificationUpdateRequest,
)
from app.services.merchant_admin_service import MerchantAdminService
from app.services.merchant_analytics_service import MerchantAnalyticsService
from app.services.merchant_auth_service import MerchantAuthService
from app.services.merchant_campaign_service import MerchantCampaignService
from app.services.merchant_membership_service import MerchantMembershipService
from app.services.merchant_offer_service import MerchantOfferService
from app.services.merchant_organization_service import MerchantOrganizationService
from app.services.merchant_product_service import MerchantProductService
from app.services.merchant_promotion_service import MerchantPromotionService

router = APIRouter(prefix="/merchants")
admin_router = APIRouter(prefix="/admin")


def _map_error(exc: Exception) -> HTTPException:
    if isinstance(exc, MerchantValidationError):
        return HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=exc.message)
    if isinstance(exc, MerchantAuthorizationError):
        return HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail=exc.message)
    if isinstance(exc, MerchantIsolationError):
        return HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail=exc.message)
    if isinstance(exc, MerchantNotFoundError):
        return HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc))
    return HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=str(exc))


def _actor(
    auth: MerchantAuthService,
    authorization: str | None,
    organization_id: str | None = None,
):
    token = auth.require_token(authorization)
    return auth.resolve_actor(token, organization_id=organization_id)


@router.get(
    "/meta/demo",
    response_model=MerchantDemoMetaResponse,
    summary="List demo merchant accounts and limitations",
)
async def merchant_demo_meta(
    repository=Depends(get_merchant_repository),
) -> MerchantDemoMetaResponse:
    accounts = []
    for account in repository.list_accounts():
        accounts.append(
            {
                "account_id": account.account_id,
                "email": account.email,
                "display_name": account.display_name,
                "is_internal_admin": account.is_internal_admin,
                "demo_token": account.demo_token,
            }
        )
    return MerchantDemoMetaResponse(
        demo_accounts=accounts,
        limitations=list(LIMITATIONS),
        roles=["owner", "admin", "manager", "analyst", "editor", "viewer", "internal_admin"],
    )


@router.post(
    "",
    response_model=MerchantOrganizationPayload,
    status_code=status.HTTP_201_CREATED,
    summary="Create a merchant organization",
)
async def create_merchant(
    body: MerchantOrganizationCreateRequest,
    authorization: str | None = Header(default=None),
    auth: MerchantAuthService = Depends(get_merchant_auth_service),
    service: MerchantOrganizationService = Depends(get_merchant_organization_service),
) -> MerchantOrganizationPayload:
    try:
        actor = _actor(auth, authorization)
        org = service.create_organization(
            actor,
            business_name=body.business_name,
            legal_name=body.legal_name,
            display_name=body.display_name,
            country=body.country,
            business_category=body.business_category,
            website=body.website,
            support_email=body.support_email,
            marketplace_presence=body.marketplace_presence,
            business_description=body.business_description,
            logo_reference=body.logo_reference,
            contact_references=body.contact_references,
            affiliate_merchant_id=body.affiliate_merchant_id,
            accept_terms=body.accept_terms,
        )
        return to_organization_payload(org)
    except Exception as exc:  # noqa: BLE001
        raise _map_error(exc) from exc


@router.get("", response_model=MerchantOrganizationListResponse, summary="List merchants")
async def list_merchants(
    status_filter: str | None = Query(default=None, alias="status"),
    authorization: str | None = Header(default=None),
    auth: MerchantAuthService = Depends(get_merchant_auth_service),
    service: MerchantOrganizationService = Depends(get_merchant_organization_service),
) -> MerchantOrganizationListResponse:
    try:
        actor = _actor(auth, authorization)
        orgs = service.list_organizations(actor, status=status_filter)
        return MerchantOrganizationListResponse(items=[to_organization_payload(o) for o in orgs])
    except Exception as exc:  # noqa: BLE001
        raise _map_error(exc) from exc


@router.post(
    "/invitations/{invitation_id}/accept",
    response_model=MerchantMembershipPayload,
    summary="Accept a merchant invitation",
)
async def accept_invitation(
    invitation_id: str,
    authorization: str | None = Header(default=None),
    auth: MerchantAuthService = Depends(get_merchant_auth_service),
    service: MerchantMembershipService = Depends(get_merchant_membership_service),
) -> MerchantMembershipPayload:
    try:
        actor = _actor(auth, authorization)
        return to_membership_payload(service.accept_invitation(actor, invitation_id))
    except Exception as exc:  # noqa: BLE001
        raise _map_error(exc) from exc


@router.get(
    "/{merchant_id}",
    response_model=MerchantOrganizationPayload,
    summary="Get a merchant organization",
)
async def get_merchant(
    merchant_id: str,
    authorization: str | None = Header(default=None),
    auth: MerchantAuthService = Depends(get_merchant_auth_service),
    service: MerchantOrganizationService = Depends(get_merchant_organization_service),
) -> MerchantOrganizationPayload:
    try:
        actor = _actor(auth, authorization, organization_id=merchant_id)
        return to_organization_payload(service.get_organization(actor, merchant_id))
    except Exception as exc:  # noqa: BLE001
        raise _map_error(exc) from exc


@router.put(
    "/{merchant_id}",
    response_model=MerchantOrganizationPayload,
    summary="Update merchant organization profile",
)
async def update_merchant(
    merchant_id: str,
    body: MerchantOrganizationUpdateRequest,
    authorization: str | None = Header(default=None),
    auth: MerchantAuthService = Depends(get_merchant_auth_service),
    service: MerchantOrganizationService = Depends(get_merchant_organization_service),
) -> MerchantOrganizationPayload:
    try:
        actor = _actor(auth, authorization, organization_id=merchant_id)
        org = service.update_profile(actor, merchant_id, **drop_none(body.model_dump()))
        return to_organization_payload(org)
    except Exception as exc:  # noqa: BLE001
        raise _map_error(exc) from exc


@router.post(
    "/{merchant_id}/archive",
    response_model=MerchantOrganizationPayload,
    summary="Archive a merchant organization",
)
async def archive_merchant(
    merchant_id: str,
    authorization: str | None = Header(default=None),
    auth: MerchantAuthService = Depends(get_merchant_auth_service),
    service: MerchantOrganizationService = Depends(get_merchant_organization_service),
) -> MerchantOrganizationPayload:
    try:
        actor = _actor(auth, authorization, organization_id=merchant_id)
        return to_organization_payload(service.archive(actor, merchant_id))
    except Exception as exc:  # noqa: BLE001
        raise _map_error(exc) from exc


@router.get(
    "/{merchant_id}/members",
    response_model=MerchantMembershipListResponse,
    summary="List organization members",
)
async def list_members(
    merchant_id: str,
    authorization: str | None = Header(default=None),
    auth: MerchantAuthService = Depends(get_merchant_auth_service),
    service: MerchantMembershipService = Depends(get_merchant_membership_service),
) -> MerchantMembershipListResponse:
    try:
        actor = _actor(auth, authorization, organization_id=merchant_id)
        members = service.list_members(actor, merchant_id)
        return MerchantMembershipListResponse(items=[to_membership_payload(m) for m in members])
    except Exception as exc:  # noqa: BLE001
        raise _map_error(exc) from exc


@router.post(
    "/{merchant_id}/invitations",
    response_model=MerchantInvitationPayload,
    status_code=status.HTTP_201_CREATED,
    summary="Invite a merchant user",
)
async def invite_member(
    merchant_id: str,
    body: MerchantInvitationCreateRequest,
    authorization: str | None = Header(default=None),
    auth: MerchantAuthService = Depends(get_merchant_auth_service),
    service: MerchantMembershipService = Depends(get_merchant_membership_service),
) -> MerchantInvitationPayload:
    try:
        actor = _actor(auth, authorization, organization_id=merchant_id)
        invitation = service.invite(actor, merchant_id, email=body.email, role=body.role)
        return to_invitation_payload(invitation)
    except Exception as exc:  # noqa: BLE001
        raise _map_error(exc) from exc


@router.put(
    "/{merchant_id}/members/{member_id}",
    response_model=MerchantMembershipPayload,
    summary="Change a member role",
)
async def update_member_role(
    merchant_id: str,
    member_id: str,
    body: MerchantRoleUpdateRequest,
    authorization: str | None = Header(default=None),
    auth: MerchantAuthService = Depends(get_merchant_auth_service),
    service: MerchantMembershipService = Depends(get_merchant_membership_service),
) -> MerchantMembershipPayload:
    try:
        actor = _actor(auth, authorization, organization_id=merchant_id)
        return to_membership_payload(
            service.change_role(actor, merchant_id, member_id, role=body.role)
        )
    except Exception as exc:  # noqa: BLE001
        raise _map_error(exc) from exc


@router.delete(
    "/{merchant_id}/members/{member_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Remove a member",
)
async def remove_member(
    merchant_id: str,
    member_id: str,
    authorization: str | None = Header(default=None),
    auth: MerchantAuthService = Depends(get_merchant_auth_service),
    service: MerchantMembershipService = Depends(get_merchant_membership_service),
) -> None:
    try:
        actor = _actor(auth, authorization, organization_id=merchant_id)
        service.remove_member(actor, merchant_id, member_id)
    except Exception as exc:  # noqa: BLE001
        raise _map_error(exc) from exc


# ---- products ----
@router.get(
    "/{merchant_id}/products",
    response_model=MerchantProductListResponse,
    summary="List product submissions",
)
async def list_products(
    merchant_id: str,
    status_filter: str | None = Query(default=None, alias="status"),
    authorization: str | None = Header(default=None),
    auth: MerchantAuthService = Depends(get_merchant_auth_service),
    service: MerchantProductService = Depends(get_merchant_product_service),
) -> MerchantProductListResponse:
    try:
        actor = _actor(auth, authorization, organization_id=merchant_id)
        items = service.list_products(actor, merchant_id, status=status_filter)
        return MerchantProductListResponse(items=[to_product_payload(p) for p in items])
    except Exception as exc:  # noqa: BLE001
        raise _map_error(exc) from exc


@router.post(
    "/{merchant_id}/products",
    response_model=MerchantProductPayload,
    status_code=status.HTTP_201_CREATED,
    summary="Create a product submission draft",
)
async def create_product(
    merchant_id: str,
    body: MerchantProductCreateRequest,
    authorization: str | None = Header(default=None),
    auth: MerchantAuthService = Depends(get_merchant_auth_service),
    service: MerchantProductService = Depends(get_merchant_product_service),
) -> MerchantProductPayload:
    try:
        actor = _actor(auth, authorization, organization_id=merchant_id)
        return to_product_payload(service.create_product(actor, merchant_id, **body.model_dump()))
    except Exception as exc:  # noqa: BLE001
        raise _map_error(exc) from exc


@router.get(
    "/{merchant_id}/products/{submission_id}",
    response_model=MerchantProductPayload,
    summary="Get a product submission",
)
async def get_product(
    merchant_id: str,
    submission_id: str,
    authorization: str | None = Header(default=None),
    auth: MerchantAuthService = Depends(get_merchant_auth_service),
    service: MerchantProductService = Depends(get_merchant_product_service),
) -> MerchantProductPayload:
    try:
        actor = _actor(auth, authorization, organization_id=merchant_id)
        return to_product_payload(service.get_product(actor, merchant_id, submission_id))
    except Exception as exc:  # noqa: BLE001
        raise _map_error(exc) from exc


@router.put(
    "/{merchant_id}/products/{submission_id}",
    response_model=MerchantProductPayload,
    summary="Update a pending product submission",
)
async def update_product(
    merchant_id: str,
    submission_id: str,
    body: MerchantProductUpdateRequest,
    authorization: str | None = Header(default=None),
    auth: MerchantAuthService = Depends(get_merchant_auth_service),
    service: MerchantProductService = Depends(get_merchant_product_service),
) -> MerchantProductPayload:
    try:
        actor = _actor(auth, authorization, organization_id=merchant_id)
        return to_product_payload(
            service.update_product(
                actor, merchant_id, submission_id, **drop_none(body.model_dump())
            )
        )
    except Exception as exc:  # noqa: BLE001
        raise _map_error(exc) from exc


@router.post(
    "/{merchant_id}/products/{submission_id}/submit",
    response_model=MerchantProductPayload,
    summary="Submit a product for review (runs matching)",
)
async def submit_product(
    merchant_id: str,
    submission_id: str,
    authorization: str | None = Header(default=None),
    auth: MerchantAuthService = Depends(get_merchant_auth_service),
    service: MerchantProductService = Depends(get_merchant_product_service),
) -> MerchantProductPayload:
    try:
        actor = _actor(auth, authorization, organization_id=merchant_id)
        return to_product_payload(service.submit_product(actor, merchant_id, submission_id))
    except Exception as exc:  # noqa: BLE001
        raise _map_error(exc) from exc


@router.post(
    "/{merchant_id}/products/{submission_id}/withdraw",
    response_model=MerchantProductPayload,
    summary="Withdraw a product submission",
)
async def withdraw_product(
    merchant_id: str,
    submission_id: str,
    authorization: str | None = Header(default=None),
    auth: MerchantAuthService = Depends(get_merchant_auth_service),
    service: MerchantProductService = Depends(get_merchant_product_service),
) -> MerchantProductPayload:
    try:
        actor = _actor(auth, authorization, organization_id=merchant_id)
        return to_product_payload(service.withdraw_product(actor, merchant_id, submission_id))
    except Exception as exc:  # noqa: BLE001
        raise _map_error(exc) from exc


@router.get(
    "/{merchant_id}/products/{product_id}/performance",
    response_model=dict,
    summary="Product performance analytics",
)
async def product_performance(
    merchant_id: str,
    product_id: str,
    authorization: str | None = Header(default=None),
    auth: MerchantAuthService = Depends(get_merchant_auth_service),
    service: MerchantAnalyticsService = Depends(get_merchant_analytics_service),
) -> dict:
    try:
        actor = _actor(auth, authorization, organization_id=merchant_id)
        return service.get_product_performance(actor, merchant_id, product_id)
    except Exception as exc:  # noqa: BLE001
        raise _map_error(exc) from exc


@router.get(
    "/{merchant_id}/products/{product_id}/ranking-explanation",
    response_model=MerchantRankingExplanationResponse,
    summary="Safe ranking explanation for a product",
)
async def ranking_explanation(
    merchant_id: str,
    product_id: str,
    authorization: str | None = Header(default=None),
    auth: MerchantAuthService = Depends(get_merchant_auth_service),
    service: MerchantAnalyticsService = Depends(get_merchant_analytics_service),
) -> MerchantRankingExplanationResponse:
    try:
        actor = _actor(auth, authorization, organization_id=merchant_id)
        return to_ranking_explanation_response(
            service.get_ranking_explanation(actor, merchant_id, product_id)
        )
    except Exception as exc:  # noqa: BLE001
        raise _map_error(exc) from exc


# ---- offers ----
@router.get(
    "/{merchant_id}/offers",
    response_model=MerchantOfferListResponse,
    summary="List offer submissions",
)
async def list_offers(
    merchant_id: str,
    status_filter: str | None = Query(default=None, alias="status"),
    authorization: str | None = Header(default=None),
    auth: MerchantAuthService = Depends(get_merchant_auth_service),
    service: MerchantOfferService = Depends(get_merchant_offer_service),
) -> MerchantOfferListResponse:
    try:
        actor = _actor(auth, authorization, organization_id=merchant_id)
        items = service.list_offers(actor, merchant_id, status=status_filter)
        return MerchantOfferListResponse(items=[to_offer_payload(o) for o in items])
    except Exception as exc:  # noqa: BLE001
        raise _map_error(exc) from exc


@router.post(
    "/{merchant_id}/offers",
    response_model=MerchantOfferPayload,
    status_code=status.HTTP_201_CREATED,
    summary="Submit an offer",
)
async def create_offer(
    merchant_id: str,
    body: MerchantOfferCreateRequest,
    authorization: str | None = Header(default=None),
    auth: MerchantAuthService = Depends(get_merchant_auth_service),
    service: MerchantOfferService = Depends(get_merchant_offer_service),
) -> MerchantOfferPayload:
    try:
        actor = _actor(auth, authorization, organization_id=merchant_id)
        return to_offer_payload(service.create_offer(actor, merchant_id, **body.model_dump()))
    except Exception as exc:  # noqa: BLE001
        raise _map_error(exc) from exc


@router.put(
    "/{merchant_id}/offers/{offer_id}",
    response_model=MerchantOfferPayload,
    summary="Update an offer",
)
async def update_offer(
    merchant_id: str,
    offer_id: str,
    body: MerchantOfferUpdateRequest,
    authorization: str | None = Header(default=None),
    auth: MerchantAuthService = Depends(get_merchant_auth_service),
    service: MerchantOfferService = Depends(get_merchant_offer_service),
) -> MerchantOfferPayload:
    try:
        actor = _actor(auth, authorization, organization_id=merchant_id)
        return to_offer_payload(
            service.update_offer(actor, merchant_id, offer_id, **drop_none(body.model_dump()))
        )
    except Exception as exc:  # noqa: BLE001
        raise _map_error(exc) from exc


@router.delete(
    "/{merchant_id}/offers/{offer_id}",
    response_model=MerchantOfferPayload,
    summary="Deactivate / archive an offer",
)
async def deactivate_offer(
    merchant_id: str,
    offer_id: str,
    authorization: str | None = Header(default=None),
    auth: MerchantAuthService = Depends(get_merchant_auth_service),
    service: MerchantOfferService = Depends(get_merchant_offer_service),
) -> MerchantOfferPayload:
    try:
        actor = _actor(auth, authorization, organization_id=merchant_id)
        return to_offer_payload(service.deactivate_offer(actor, merchant_id, offer_id))
    except Exception as exc:  # noqa: BLE001
        raise _map_error(exc) from exc


# ---- promotions ----
@router.get(
    "/{merchant_id}/promotions",
    response_model=MerchantPromotionListResponse,
    summary="List promotions",
)
async def list_promotions(
    merchant_id: str,
    status_filter: str | None = Query(default=None, alias="status"),
    authorization: str | None = Header(default=None),
    auth: MerchantAuthService = Depends(get_merchant_auth_service),
    service: MerchantPromotionService = Depends(get_merchant_promotion_service),
) -> MerchantPromotionListResponse:
    try:
        actor = _actor(auth, authorization, organization_id=merchant_id)
        items = service.list_promotions(actor, merchant_id, status=status_filter)
        return MerchantPromotionListResponse(items=[to_promotion_payload(p) for p in items])
    except Exception as exc:  # noqa: BLE001
        raise _map_error(exc) from exc


@router.post(
    "/{merchant_id}/promotions",
    response_model=MerchantPromotionPayload,
    status_code=status.HTTP_201_CREATED,
    summary="Create a promotion",
)
async def create_promotion(
    merchant_id: str,
    body: MerchantPromotionCreateRequest,
    authorization: str | None = Header(default=None),
    auth: MerchantAuthService = Depends(get_merchant_auth_service),
    service: MerchantPromotionService = Depends(get_merchant_promotion_service),
) -> MerchantPromotionPayload:
    try:
        actor = _actor(auth, authorization, organization_id=merchant_id)
        payload = body.model_dump()
        payload["starts_at"] = parse_optional_datetime(payload.pop("starts_at"))
        payload["ends_at"] = parse_optional_datetime(payload.pop("ends_at"))
        return to_promotion_payload(service.create_promotion(actor, merchant_id, **payload))
    except Exception as exc:  # noqa: BLE001
        raise _map_error(exc) from exc


@router.put(
    "/{merchant_id}/promotions/{promotion_id}",
    response_model=MerchantPromotionPayload,
    summary="Update a promotion",
)
async def update_promotion(
    merchant_id: str,
    promotion_id: str,
    body: MerchantPromotionUpdateRequest,
    authorization: str | None = Header(default=None),
    auth: MerchantAuthService = Depends(get_merchant_auth_service),
    service: MerchantPromotionService = Depends(get_merchant_promotion_service),
) -> MerchantPromotionPayload:
    try:
        actor = _actor(auth, authorization, organization_id=merchant_id)
        payload = drop_none(body.model_dump())
        if "starts_at" in payload:
            payload["starts_at"] = parse_optional_datetime(payload["starts_at"])
        if "ends_at" in payload:
            payload["ends_at"] = parse_optional_datetime(payload["ends_at"])
        return to_promotion_payload(
            service.update_promotion(actor, merchant_id, promotion_id, **payload)
        )
    except Exception as exc:  # noqa: BLE001
        raise _map_error(exc) from exc


@router.post(
    "/{merchant_id}/promotions/{promotion_id}/pause",
    response_model=MerchantPromotionPayload,
    summary="Pause a promotion",
)
async def pause_promotion(
    merchant_id: str,
    promotion_id: str,
    authorization: str | None = Header(default=None),
    auth: MerchantAuthService = Depends(get_merchant_auth_service),
    service: MerchantPromotionService = Depends(get_merchant_promotion_service),
) -> MerchantPromotionPayload:
    try:
        actor = _actor(auth, authorization, organization_id=merchant_id)
        return to_promotion_payload(service.pause_promotion(actor, merchant_id, promotion_id))
    except Exception as exc:  # noqa: BLE001
        raise _map_error(exc) from exc


# ---- campaigns ----
@router.get(
    "/{merchant_id}/campaigns",
    response_model=MerchantCampaignListResponse,
    summary="List sponsored campaign drafts",
)
async def list_campaigns(
    merchant_id: str,
    status_filter: str | None = Query(default=None, alias="status"),
    authorization: str | None = Header(default=None),
    auth: MerchantAuthService = Depends(get_merchant_auth_service),
    service: MerchantCampaignService = Depends(get_merchant_campaign_service),
) -> MerchantCampaignListResponse:
    try:
        actor = _actor(auth, authorization, organization_id=merchant_id)
        items = service.list_campaigns(actor, merchant_id, status=status_filter)
        return MerchantCampaignListResponse(items=[to_campaign_payload(c) for c in items])
    except Exception as exc:  # noqa: BLE001
        raise _map_error(exc) from exc


@router.post(
    "/{merchant_id}/campaigns",
    response_model=MerchantCampaignPayload,
    status_code=status.HTTP_201_CREATED,
    summary="Create a sponsored campaign draft",
)
async def create_campaign(
    merchant_id: str,
    body: MerchantCampaignCreateRequest,
    authorization: str | None = Header(default=None),
    auth: MerchantAuthService = Depends(get_merchant_auth_service),
    service: MerchantCampaignService = Depends(get_merchant_campaign_service),
) -> MerchantCampaignPayload:
    try:
        actor = _actor(auth, authorization, organization_id=merchant_id)
        payload = body.model_dump()
        payload["starts_at"] = parse_optional_datetime(payload.pop("starts_at"))
        payload["ends_at"] = parse_optional_datetime(payload.pop("ends_at"))
        return to_campaign_payload(service.create_campaign(actor, merchant_id, **payload))
    except Exception as exc:  # noqa: BLE001
        raise _map_error(exc) from exc


@router.put(
    "/{merchant_id}/campaigns/{campaign_id}",
    response_model=MerchantCampaignPayload,
    summary="Update a sponsored campaign draft",
)
async def update_campaign(
    merchant_id: str,
    campaign_id: str,
    body: MerchantCampaignUpdateRequest,
    authorization: str | None = Header(default=None),
    auth: MerchantAuthService = Depends(get_merchant_auth_service),
    service: MerchantCampaignService = Depends(get_merchant_campaign_service),
) -> MerchantCampaignPayload:
    try:
        actor = _actor(auth, authorization, organization_id=merchant_id)
        payload = drop_none(body.model_dump())
        if "starts_at" in payload:
            payload["starts_at"] = parse_optional_datetime(payload["starts_at"])
        if "ends_at" in payload:
            payload["ends_at"] = parse_optional_datetime(payload["ends_at"])
        return to_campaign_payload(
            service.update_campaign(actor, merchant_id, campaign_id, **payload)
        )
    except Exception as exc:  # noqa: BLE001
        raise _map_error(exc) from exc


@router.post(
    "/{merchant_id}/campaigns/{campaign_id}/pause",
    response_model=MerchantCampaignPayload,
    summary="Pause a sponsored campaign",
)
async def pause_campaign(
    merchant_id: str,
    campaign_id: str,
    authorization: str | None = Header(default=None),
    auth: MerchantAuthService = Depends(get_merchant_auth_service),
    service: MerchantCampaignService = Depends(get_merchant_campaign_service),
) -> MerchantCampaignPayload:
    try:
        actor = _actor(auth, authorization, organization_id=merchant_id)
        return to_campaign_payload(service.pause_campaign(actor, merchant_id, campaign_id))
    except Exception as exc:  # noqa: BLE001
        raise _map_error(exc) from exc


@router.post(
    "/{merchant_id}/campaigns/{campaign_id}/resume",
    response_model=MerchantCampaignPayload,
    summary="Resume a sponsored campaign",
)
async def resume_campaign(
    merchant_id: str,
    campaign_id: str,
    authorization: str | None = Header(default=None),
    auth: MerchantAuthService = Depends(get_merchant_auth_service),
    service: MerchantCampaignService = Depends(get_merchant_campaign_service),
) -> MerchantCampaignPayload:
    try:
        actor = _actor(auth, authorization, organization_id=merchant_id)
        return to_campaign_payload(service.resume_campaign(actor, merchant_id, campaign_id))
    except Exception as exc:  # noqa: BLE001
        raise _map_error(exc) from exc


# ---- analytics / audit ----
@router.get(
    "/{merchant_id}/analytics",
    response_model=MerchantAnalyticsResponse,
    summary="Merchant analytics dashboard",
)
async def get_analytics(
    merchant_id: str,
    authorization: str | None = Header(default=None),
    auth: MerchantAuthService = Depends(get_merchant_auth_service),
    service: MerchantAnalyticsService = Depends(get_merchant_analytics_service),
) -> MerchantAnalyticsResponse:
    try:
        actor = _actor(auth, authorization, organization_id=merchant_id)
        return to_analytics_response(service.get_analytics(actor, merchant_id))
    except Exception as exc:  # noqa: BLE001
        raise _map_error(exc) from exc


@router.get(
    "/{merchant_id}/audit-log",
    response_model=MerchantAuditLogResponse,
    summary="Merchant audit log",
)
async def get_audit_log(
    merchant_id: str,
    limit: int = Query(default=100, ge=1, le=500),
    authorization: str | None = Header(default=None),
    auth: MerchantAuthService = Depends(get_merchant_auth_service),
    service: MerchantAnalyticsService = Depends(get_merchant_analytics_service),
) -> MerchantAuditLogResponse:
    try:
        actor = _actor(auth, authorization, organization_id=merchant_id)
        return MerchantAuditLogResponse(
            items=service.list_audit_log(actor, merchant_id, limit=limit)
        )
    except Exception as exc:  # noqa: BLE001
        raise _map_error(exc) from exc


# ---- admin ----
@admin_router.get(
    "/merchant-submissions",
    response_model=MerchantProductListResponse,
    summary="List merchant product submissions for review",
)
async def admin_list_submissions(
    status_filter: str | None = Query(default=None, alias="status"),
    authorization: str | None = Header(default=None),
    auth: MerchantAuthService = Depends(get_merchant_auth_service),
    service: MerchantAdminService = Depends(get_merchant_admin_service),
) -> MerchantProductListResponse:
    try:
        actor = _actor(auth, authorization)
        items = service.list_submissions(actor, status=status_filter)
        return MerchantProductListResponse(items=[to_product_payload(p) for p in items])
    except Exception as exc:  # noqa: BLE001
        raise _map_error(exc) from exc


@admin_router.post(
    "/merchant-submissions/{submission_id}/approve",
    response_model=MerchantProductPayload,
    summary="Approve a merchant product submission",
)
async def admin_approve_submission(
    submission_id: str,
    body: MerchantAdminNotesRequest | None = None,
    authorization: str | None = Header(default=None),
    auth: MerchantAuthService = Depends(get_merchant_auth_service),
    service: MerchantAdminService = Depends(get_merchant_admin_service),
) -> MerchantProductPayload:
    try:
        actor = _actor(auth, authorization)
        notes = body.notes if body else ""
        return to_product_payload(service.approve_submission(actor, submission_id, notes=notes))
    except Exception as exc:  # noqa: BLE001
        raise _map_error(exc) from exc


@admin_router.post(
    "/merchant-submissions/{submission_id}/reject",
    response_model=MerchantProductPayload,
    summary="Reject a merchant product submission",
)
async def admin_reject_submission(
    submission_id: str,
    body: MerchantAdminRejectRequest | None = None,
    authorization: str | None = Header(default=None),
    auth: MerchantAuthService = Depends(get_merchant_auth_service),
    service: MerchantAdminService = Depends(get_merchant_admin_service),
) -> MerchantProductPayload:
    try:
        actor = _actor(auth, authorization)
        notes = body.notes if body else ""
        needs_changes = body.needs_changes if body else False
        return to_product_payload(
            service.reject_submission(
                actor, submission_id, notes=notes, needs_changes=needs_changes
            )
        )
    except Exception as exc:  # noqa: BLE001
        raise _map_error(exc) from exc


@admin_router.post(
    "/merchants/{merchant_id}/suspend",
    response_model=MerchantOrganizationPayload,
    summary="Suspend a merchant organization",
)
async def admin_suspend_merchant(
    merchant_id: str,
    body: MerchantAdminNotesRequest | None = None,
    authorization: str | None = Header(default=None),
    auth: MerchantAuthService = Depends(get_merchant_auth_service),
    service: MerchantAdminService = Depends(get_merchant_admin_service),
) -> MerchantOrganizationPayload:
    try:
        actor = _actor(auth, authorization)
        notes = body.notes if body else ""
        return to_organization_payload(service.suspend_merchant(actor, merchant_id, notes=notes))
    except Exception as exc:  # noqa: BLE001
        raise _map_error(exc) from exc


@admin_router.post(
    "/merchants/{merchant_id}/activate",
    response_model=MerchantOrganizationPayload,
    summary="Activate a merchant organization",
)
async def admin_activate_merchant(
    merchant_id: str,
    body: MerchantAdminNotesRequest | None = None,
    authorization: str | None = Header(default=None),
    auth: MerchantAuthService = Depends(get_merchant_auth_service),
    service: MerchantAdminService = Depends(get_merchant_admin_service),
) -> MerchantOrganizationPayload:
    try:
        actor = _actor(auth, authorization)
        notes = body.notes if body else ""
        return to_organization_payload(service.activate_merchant(actor, merchant_id, notes=notes))
    except Exception as exc:  # noqa: BLE001
        raise _map_error(exc) from exc


@admin_router.post(
    "/merchants/{merchant_id}/verification",
    response_model=MerchantOrganizationPayload,
    summary="Update merchant verification status",
)
async def admin_update_verification(
    merchant_id: str,
    body: MerchantVerificationUpdateRequest,
    authorization: str | None = Header(default=None),
    auth: MerchantAuthService = Depends(get_merchant_auth_service),
    service: MerchantAdminService = Depends(get_merchant_admin_service),
) -> MerchantOrganizationPayload:
    try:
        actor = _actor(auth, authorization)
        return to_organization_payload(
            service.update_verification(actor, merchant_id, status=body.status, notes=body.notes)
        )
    except Exception as exc:  # noqa: BLE001
        raise _map_error(exc) from exc


# Silence unused import warning for DEMO_TOKENS (documented for clients).
_ = DEMO_TOKENS

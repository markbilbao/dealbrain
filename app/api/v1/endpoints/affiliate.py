"""Affiliate Revenue Engine API endpoints — Sprint 20.

Routes:
  /api/v1/affiliate/link
  /api/v1/affiliate/click
  /api/v1/affiliate/report
  /api/v1/affiliate/merchant
  /api/v1/affiliate/disclosure

Demo only — no real affiliate APIs, commissions, conversions, billing, or payouts.
Affiliate data is never applied to DealScore or recommendation ranking.
"""

from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, Query, status

from app.api.v1.mappers.affiliate import (
    to_attribution_payload,
    to_click_payload,
    to_disclosure_payload,
    to_link_payload,
    to_merchant_payload,
    to_report_payload,
    to_resolve_payload,
)
from app.core.dependencies import (
    get_affiliate_disclosure_service,
    get_affiliate_link_service,
    get_affiliate_merchant_service,
    get_affiliate_reporting_service,
    get_affiliate_tracking_service,
)
from app.domain.exceptions import (
    AffiliateClickNotFoundError,
    AffiliateDisclosureNotFoundError,
    AffiliateLinkNotFoundError,
    AffiliateMerchantNotFoundError,
    AffiliateNotFoundError,
    AffiliateValidationError,
)
from app.schemas.affiliate import (
    AffiliateAttributeRequest,
    AffiliateClickConversionRequest,
    AffiliateClickListResponse,
    AffiliateClickPayload,
    AffiliateClickTrackRequest,
    AffiliateCommissionUpdateRequest,
    AffiliateCountriesUpdateRequest,
    AffiliateDisclosureCreateRequest,
    AffiliateDisclosureListResponse,
    AffiliateDisclosurePayload,
    AffiliateDisclosureResolveResponse,
    AffiliateHealthUpdateRequest,
    AffiliateLinkGenerateRequest,
    AffiliateLinkListResponse,
    AffiliateLinkPayload,
    AffiliateMerchantCreateRequest,
    AffiliateMerchantListResponse,
    AffiliateMerchantPayload,
    AffiliateMerchantUpdateRequest,
    AffiliatePriorityUpdateRequest,
    AffiliateReportResponse,
    AttributionResultPayload,
)
from app.services.affiliate_disclosure_service import AffiliateDisclosureService
from app.services.affiliate_link_service import AffiliateLinkService
from app.services.affiliate_merchant_service import AffiliateMerchantService
from app.services.affiliate_reporting_service import AffiliateReportingService
from app.services.affiliate_tracking_service import AffiliateTrackingService

link_router = APIRouter(prefix="/affiliate/link")
click_router = APIRouter(prefix="/affiliate/click")
report_router = APIRouter(prefix="/affiliate/report")
merchant_router = APIRouter(prefix="/affiliate/merchant")
disclosure_router = APIRouter(prefix="/affiliate/disclosure")


def _map_error(exc: Exception) -> HTTPException:
    if isinstance(exc, AffiliateValidationError):
        return HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=exc.message)
    if isinstance(exc, AffiliateNotFoundError):
        return HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc))
    return HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=str(exc))


# ------------------------------------------------------------------ /link
@link_router.post(
    "",
    response_model=AffiliateLinkPayload,
    status_code=status.HTTP_201_CREATED,
    summary="Generate an affiliate link for a selected product",
)
async def generate_affiliate_link(
    body: AffiliateLinkGenerateRequest,
    service: AffiliateLinkService = Depends(get_affiliate_link_service),
) -> AffiliateLinkPayload:
    try:
        link = service.generate_link(
            product_id=body.product_id,
            product_name=body.product_name,
            marketplace=body.marketplace,
            merchant_id=body.merchant_id,
            original_url=body.original_url,
            product_ref=body.product_ref,
            campaign_id=body.campaign_id,
            sub_id=body.sub_id,
            click_id=body.click_id,
            country=body.country,
            category=body.category,
            order_value=body.order_value,
            deep_link=body.deep_link,
            currency=body.currency,
        )
    except (AffiliateValidationError, AffiliateMerchantNotFoundError) as exc:
        raise _map_error(exc) from exc
    return to_link_payload(link)


@link_router.get(
    "",
    response_model=AffiliateLinkListResponse,
    summary="List generated affiliate links",
)
async def list_affiliate_links(
    merchant_id: str | None = None,
    product_id: str | None = None,
    limit: int = Query(default=100, ge=1, le=500),
    service: AffiliateLinkService = Depends(get_affiliate_link_service),
) -> AffiliateLinkListResponse:
    links = service.list_links(merchant_id=merchant_id, product_id=product_id, limit=limit)
    return AffiliateLinkListResponse(links=[to_link_payload(link) for link in links])


@link_router.get(
    "/{link_id}",
    response_model=AffiliateLinkPayload,
    summary="Get a generated affiliate link",
)
async def get_affiliate_link(
    link_id: str,
    service: AffiliateLinkService = Depends(get_affiliate_link_service),
) -> AffiliateLinkPayload:
    try:
        link = service.get_link(link_id)
    except AffiliateLinkNotFoundError as exc:
        raise _map_error(exc) from exc
    return to_link_payload(link)


# ----------------------------------------------------------------- /click
@click_router.post(
    "",
    response_model=AffiliateClickPayload,
    status_code=status.HTTP_201_CREATED,
    summary="Track an affiliate click",
)
async def track_affiliate_click(
    body: AffiliateClickTrackRequest,
    service: AffiliateTrackingService = Depends(get_affiliate_tracking_service),
) -> AffiliateClickPayload:
    try:
        click = service.track_click(
            merchant_id=body.merchant_id,
            product_id=body.product_id,
            link_id=body.link_id,
            user_id=body.user_id,
            session_id=body.session_id,
            device=body.device,
            country=body.country,
            campaign_id=body.campaign_id,
            source=body.source,
            referrer=body.referrer,
            product_name=body.product_name,
            category=body.category,
            revenue=body.revenue,
            estimated_commission=body.estimated_commission,
            currency=body.currency,
            metadata=body.metadata,
        )
    except (
        AffiliateValidationError,
        AffiliateLinkNotFoundError,
        AffiliateMerchantNotFoundError,
    ) as exc:
        raise _map_error(exc) from exc
    return to_click_payload(click)


@click_router.get(
    "",
    response_model=AffiliateClickListResponse,
    summary="List tracked affiliate clicks",
)
async def list_affiliate_clicks(
    user_id: str | None = None,
    session_id: str | None = None,
    merchant_id: str | None = None,
    product_id: str | None = None,
    limit: int = Query(default=200, ge=1, le=1000),
    service: AffiliateTrackingService = Depends(get_affiliate_tracking_service),
) -> AffiliateClickListResponse:
    clicks = service.list_clicks(
        user_id=user_id,
        session_id=session_id,
        merchant_id=merchant_id,
        product_id=product_id,
        limit=limit,
    )
    return AffiliateClickListResponse(clicks=[to_click_payload(c) for c in clicks])


@click_router.get(
    "/{click_id}",
    response_model=AffiliateClickPayload,
    summary="Get a tracked affiliate click",
)
async def get_affiliate_click(
    click_id: str,
    service: AffiliateTrackingService = Depends(get_affiliate_tracking_service),
) -> AffiliateClickPayload:
    try:
        click = service.get_click(click_id)
    except AffiliateClickNotFoundError as exc:
        raise _map_error(exc) from exc
    return to_click_payload(click)


@click_router.patch(
    "/{click_id}/conversion",
    response_model=AffiliateClickPayload,
    summary="Update conversion status for a click (simulated)",
)
async def update_click_conversion(
    click_id: str,
    body: AffiliateClickConversionRequest,
    service: AffiliateTrackingService = Depends(get_affiliate_tracking_service),
) -> AffiliateClickPayload:
    try:
        click = service.update_conversion_status(
            click_id,
            conversion_status=body.conversion_status,
            revenue=body.revenue,
            estimated_commission=body.estimated_commission,
        )
    except (AffiliateValidationError, AffiliateClickNotFoundError) as exc:
        raise _map_error(exc) from exc
    return to_click_payload(click)


@click_router.post(
    "/attribute",
    response_model=AttributionResultPayload,
    summary="Run attribution over tracked clicks (simulated)",
)
async def attribute_clicks(
    body: AffiliateAttributeRequest,
    service: AffiliateTrackingService = Depends(get_affiliate_tracking_service),
) -> AttributionResultPayload:
    try:
        result = service.attribute(
            model=body.model,
            user_id=body.user_id,
            session_id=body.session_id,
            product_id=body.product_id,
            merchant_id=body.merchant_id,
            revenue=body.revenue,
            estimated_commission=body.estimated_commission,
            mark_click_converted=body.mark_click_converted,
        )
    except AffiliateValidationError as exc:
        raise _map_error(exc) from exc
    return to_attribution_payload(result)


# ---------------------------------------------------------------- /report
@report_router.get(
    "",
    response_model=AffiliateReportResponse,
    summary="Affiliate revenue report (demo estimates)",
)
async def affiliate_report(
    merchant_id: str | None = None,
    product_id: str | None = None,
    currency: str = "USD",
    top_n: int = Query(default=5, ge=1, le=50),
    service: AffiliateReportingService = Depends(get_affiliate_reporting_service),
) -> AffiliateReportResponse:
    report = service.build_report(
        merchant_id=merchant_id,
        product_id=product_id,
        currency=currency,
        top_n=top_n,
    )
    return to_report_payload(report)


# -------------------------------------------------------------- /merchant
@merchant_router.get(
    "",
    response_model=AffiliateMerchantListResponse,
    summary="List affiliate merchants",
)
async def list_merchants(
    status_filter: str | None = Query(default=None, alias="status"),
    marketplace: str | None = None,
    country: str | None = None,
    active_only: bool = False,
    service: AffiliateMerchantService = Depends(get_affiliate_merchant_service),
) -> AffiliateMerchantListResponse:
    merchants = service.list_merchants(
        status=status_filter,
        marketplace=marketplace,
        country=country,
        active_only=active_only,
    )
    return AffiliateMerchantListResponse(merchants=[to_merchant_payload(m) for m in merchants])


@merchant_router.post(
    "",
    response_model=AffiliateMerchantPayload,
    status_code=status.HTTP_201_CREATED,
    summary="Create a placeholder affiliate merchant",
)
async def create_merchant(
    body: AffiliateMerchantCreateRequest,
    service: AffiliateMerchantService = Depends(get_affiliate_merchant_service),
) -> AffiliateMerchantPayload:
    try:
        merchant = service.create_merchant(
            merchant_name=body.merchant_name,
            marketplace=body.marketplace,
            country=body.country,
            affiliate_network=body.affiliate_network,
            tracking_template=body.tracking_template,
            commission_type=body.commission_type,
            commission_value=body.commission_value,
            cookie_days=body.cookie_days,
            status=body.status,
            priority=body.priority,
            health_status=body.health_status,
            allowed_countries=body.allowed_countries,
            deep_link_supported=body.deep_link_supported,
        )
    except AffiliateValidationError as exc:
        raise _map_error(exc) from exc
    return to_merchant_payload(merchant)


@merchant_router.get(
    "/{merchant_id}",
    response_model=AffiliateMerchantPayload,
    summary="Get an affiliate merchant",
)
async def get_merchant(
    merchant_id: str,
    service: AffiliateMerchantService = Depends(get_affiliate_merchant_service),
) -> AffiliateMerchantPayload:
    try:
        merchant = service.get_merchant(merchant_id)
    except AffiliateMerchantNotFoundError as exc:
        raise _map_error(exc) from exc
    return to_merchant_payload(merchant)


@merchant_router.patch(
    "/{merchant_id}",
    response_model=AffiliateMerchantPayload,
    summary="Update an affiliate merchant",
)
async def update_merchant(
    merchant_id: str,
    body: AffiliateMerchantUpdateRequest,
    service: AffiliateMerchantService = Depends(get_affiliate_merchant_service),
) -> AffiliateMerchantPayload:
    try:
        kwargs = body.model_dump(exclude_unset=True)
        merchant = service.update_merchant(merchant_id, **kwargs)
    except (AffiliateValidationError, AffiliateMerchantNotFoundError) as exc:
        raise _map_error(exc) from exc
    return to_merchant_payload(merchant)


@merchant_router.post(
    "/{merchant_id}/activate",
    response_model=AffiliateMerchantPayload,
    summary="Activate an affiliate merchant",
)
async def activate_merchant(
    merchant_id: str,
    service: AffiliateMerchantService = Depends(get_affiliate_merchant_service),
) -> AffiliateMerchantPayload:
    try:
        merchant = service.activate_merchant(merchant_id)
    except AffiliateMerchantNotFoundError as exc:
        raise _map_error(exc) from exc
    return to_merchant_payload(merchant)


@merchant_router.post(
    "/{merchant_id}/deactivate",
    response_model=AffiliateMerchantPayload,
    summary="Deactivate an affiliate merchant",
)
async def deactivate_merchant(
    merchant_id: str,
    service: AffiliateMerchantService = Depends(get_affiliate_merchant_service),
) -> AffiliateMerchantPayload:
    try:
        merchant = service.deactivate_merchant(merchant_id)
    except AffiliateMerchantNotFoundError as exc:
        raise _map_error(exc) from exc
    return to_merchant_payload(merchant)


@merchant_router.patch(
    "/{merchant_id}/commission",
    response_model=AffiliateMerchantPayload,
    summary="Update merchant commission (demo estimate only)",
)
async def update_merchant_commission(
    merchant_id: str,
    body: AffiliateCommissionUpdateRequest,
    service: AffiliateMerchantService = Depends(get_affiliate_merchant_service),
) -> AffiliateMerchantPayload:
    try:
        merchant = service.update_commission(
            merchant_id,
            commission_type=body.commission_type,
            commission_value=body.commission_value,
        )
    except (AffiliateValidationError, AffiliateMerchantNotFoundError) as exc:
        raise _map_error(exc) from exc
    return to_merchant_payload(merchant)


@merchant_router.patch(
    "/{merchant_id}/priority",
    response_model=AffiliateMerchantPayload,
    summary="Update merchant priority",
)
async def update_merchant_priority(
    merchant_id: str,
    body: AffiliatePriorityUpdateRequest,
    service: AffiliateMerchantService = Depends(get_affiliate_merchant_service),
) -> AffiliateMerchantPayload:
    try:
        merchant = service.set_priority(merchant_id, body.priority)
    except AffiliateMerchantNotFoundError as exc:
        raise _map_error(exc) from exc
    return to_merchant_payload(merchant)


@merchant_router.patch(
    "/{merchant_id}/countries",
    response_model=AffiliateMerchantPayload,
    summary="Update merchant country restrictions",
)
async def update_merchant_countries(
    merchant_id: str,
    body: AffiliateCountriesUpdateRequest,
    service: AffiliateMerchantService = Depends(get_affiliate_merchant_service),
) -> AffiliateMerchantPayload:
    try:
        merchant = service.set_country_restrictions(merchant_id, body.allowed_countries)
    except AffiliateMerchantNotFoundError as exc:
        raise _map_error(exc) from exc
    return to_merchant_payload(merchant)


@merchant_router.patch(
    "/{merchant_id}/health",
    response_model=AffiliateMerchantPayload,
    summary="Update merchant health status (synthetic)",
)
async def update_merchant_health(
    merchant_id: str,
    body: AffiliateHealthUpdateRequest,
    service: AffiliateMerchantService = Depends(get_affiliate_merchant_service),
) -> AffiliateMerchantPayload:
    try:
        merchant = service.set_health_status(merchant_id, body.health_status)
    except (AffiliateValidationError, AffiliateMerchantNotFoundError) as exc:
        raise _map_error(exc) from exc
    return to_merchant_payload(merchant)


# ----------------------------------------------------------- /disclosure
@disclosure_router.get(
    "",
    response_model=AffiliateDisclosureListResponse,
    summary="List affiliate disclosures",
)
async def list_disclosures(
    region: str | None = None,
    merchant_id: str | None = None,
    disclosure_type: str | None = None,
    active_only: bool = True,
    service: AffiliateDisclosureService = Depends(get_affiliate_disclosure_service),
) -> AffiliateDisclosureListResponse:
    disclosures = service.list_disclosures(
        region=region,
        merchant_id=merchant_id,
        disclosure_type=disclosure_type,
        active_only=active_only,
    )
    return AffiliateDisclosureListResponse(
        disclosures=[to_disclosure_payload(d) for d in disclosures]
    )


@disclosure_router.get(
    "/resolve",
    response_model=AffiliateDisclosureResolveResponse,
    summary="Resolve contextual affiliate / FTC disclosures",
)
async def resolve_disclosures(
    region: str | None = None,
    merchant_id: str | None = None,
    include_general: bool = True,
    include_ftc: bool = True,
    service: AffiliateDisclosureService = Depends(get_affiliate_disclosure_service),
) -> AffiliateDisclosureResolveResponse:
    resolved = service.resolve(
        region=region,
        merchant_id=merchant_id,
        include_general=include_general,
        include_ftc=include_ftc,
    )
    payload = to_resolve_payload(resolved)
    return AffiliateDisclosureResolveResponse(**payload)


@disclosure_router.post(
    "",
    response_model=AffiliateDisclosurePayload,
    status_code=status.HTTP_201_CREATED,
    summary="Create an affiliate disclosure record",
)
async def create_disclosure(
    body: AffiliateDisclosureCreateRequest,
    service: AffiliateDisclosureService = Depends(get_affiliate_disclosure_service),
) -> AffiliateDisclosurePayload:
    try:
        disclosure = service.create_disclosure(
            disclosure_type=body.disclosure_type,
            text=body.text,
            region=body.region,
            merchant_id=body.merchant_id,
            locale=body.locale,
            ftc_placeholder=body.ftc_placeholder,
            active=body.active,
        )
    except AffiliateValidationError as exc:
        raise _map_error(exc) from exc
    return to_disclosure_payload(disclosure)


@disclosure_router.get(
    "/{disclosure_id}",
    response_model=AffiliateDisclosurePayload,
    summary="Get an affiliate disclosure",
)
async def get_disclosure(
    disclosure_id: str,
    service: AffiliateDisclosureService = Depends(get_affiliate_disclosure_service),
) -> AffiliateDisclosurePayload:
    try:
        disclosure = service.get_disclosure(disclosure_id)
    except AffiliateDisclosureNotFoundError as exc:
        raise _map_error(exc) from exc
    return to_disclosure_payload(disclosure)

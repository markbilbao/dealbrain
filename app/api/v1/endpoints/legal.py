"""Legal publication-status API — non-PII readiness, fail-closed by default."""

from __future__ import annotations

from fastapi import APIRouter, Depends

from app.core.dependencies import get_legal_publication_catalog
from app.legal.publication import LegalPublicationCatalog
from app.privacy.consent_audit import publication_status_payload
from app.schemas.legal import LegalPublicationStatusResponse

router = APIRouter()


@router.get(
    "/legal/publication-status",
    response_model=LegalPublicationStatusResponse,
    summary="Legal publication and essential-only tracking posture",
    description=(
        "Non-PII readiness. Production remains unpublished until EXT-20 / EXT-21. "
        "Counsel drafts are never public. Does not activate analytics or a CMP."
    ),
)
async def publication_status(
    catalog: LegalPublicationCatalog = Depends(get_legal_publication_catalog),
) -> LegalPublicationStatusResponse:
    return LegalPublicationStatusResponse.model_validate(publication_status_payload(catalog))

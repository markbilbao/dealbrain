"""Legal publication-status API — non-PII product state, fail-closed by default."""

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
        "Unauthenticated product state for whether Terms and Privacy are published, "
        "whether acceptance is required, provisioned support/privacy contacts, and "
        "whether non-essential tracking is allowed. Unpublished remains the production "
        "default. Does not activate analytics or a consent banner."
    ),
)
async def publication_status(
    catalog: LegalPublicationCatalog = Depends(get_legal_publication_catalog),
) -> LegalPublicationStatusResponse:
    return LegalPublicationStatusResponse.model_validate(publication_status_payload(catalog))

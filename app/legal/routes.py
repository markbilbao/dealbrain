"""Public /privacy and /terms routes — fail closed until a published version exists."""

from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.responses import HTMLResponse

from app.core.dependencies import get_legal_publication_catalog
from app.legal.publication import (
    POLICY_PRIVACY,
    POLICY_TERMS,
    LegalPublicationCatalog,
    PolicyType,
)

router = APIRouter(include_in_schema=False)


def _published_html(
    catalog: LegalPublicationCatalog,
    policy_type: PolicyType,
) -> str:
    document = catalog.published(policy_type)
    if document is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Not Found")
    html = catalog.published_html(document)
    if html is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Not Found")
    return html


@router.get("/privacy", response_class=HTMLResponse)
async def privacy_page(
    catalog: LegalPublicationCatalog = Depends(get_legal_publication_catalog),
) -> HTMLResponse:
    return HTMLResponse(content=_published_html(catalog, POLICY_PRIVACY))


@router.get("/terms", response_class=HTMLResponse)
async def terms_page(
    catalog: LegalPublicationCatalog = Depends(get_legal_publication_catalog),
) -> HTMLResponse:
    return HTMLResponse(content=_published_html(catalog, POLICY_TERMS))

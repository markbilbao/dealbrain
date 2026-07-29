"""Affiliate disclosure text helpers — Sprint 20.

FTC / regional / merchant disclosure hooks. Placeholder copy only —
not legal advice and not a compliance system.
"""

from __future__ import annotations

from collections.abc import Sequence

from app.domain.entities.affiliate import AffiliateDisclosure


def select_disclosures(
    disclosures: Sequence[AffiliateDisclosure],
    *,
    region: str | None = None,
    merchant_id: str | None = None,
    include_general: bool = True,
    include_ftc: bool = True,
) -> list[AffiliateDisclosure]:
    """Pick the most relevant active disclosures for a UI / API context."""
    active = [d for d in disclosures if d.active]
    selected: list[AffiliateDisclosure] = []
    seen: set[str] = set()

    def _add(item: AffiliateDisclosure) -> None:
        if item.disclosure_id not in seen:
            selected.append(item)
            seen.add(item.disclosure_id)

    if include_general:
        for item in active:
            if item.disclosure_type == "affiliate_general" and item.merchant_id is None:
                _add(item)

    if include_ftc:
        for item in active:
            if item.disclosure_type == "ftc" and (
                region is None or item.region is None or item.region.upper() == region.upper()
            ):
                _add(item)

    if region is not None:
        for item in active:
            if (
                item.disclosure_type == "regional"
                and item.region is not None
                and item.region.upper() == region.upper()
            ):
                _add(item)

    if merchant_id is not None:
        for item in active:
            if item.disclosure_type == "merchant" and item.merchant_id == merchant_id:
                _add(item)

    return selected


def combined_disclosure_text(disclosures: Sequence[AffiliateDisclosure]) -> str:
    """Join disclosure texts for a single display block."""
    parts = [d.text.strip() for d in disclosures if d.text.strip()]
    return " ".join(parts)

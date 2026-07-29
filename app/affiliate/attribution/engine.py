"""Pure attribution engine — Sprint 20.

Chooses which tracked click (if any) owns a conversion under a selected
attribution model. No DealScore, ranking, or merchant payout logic.
"""

from __future__ import annotations

from collections.abc import Sequence
from datetime import datetime

from app.domain.entities.affiliate import (
    AffiliateClick,
    AttributionModel,
    AttributionResult,
    ClickSource,
    ConversionStatus,
)


class AttributionEngine:
    """Attribute simulated conversions to clicks (pure, no I/O)."""

    def attribute(
        self,
        clicks: Sequence[AffiliateClick],
        *,
        model: AttributionModel,
        attribution_id: str,
        attributed_at: datetime,
        revenue: float = 0.0,
        estimated_commission: float = 0.0,
        product_id: str | None = None,
        merchant_id: str | None = None,
    ) -> AttributionResult:
        """Select an attributed click under ``model`` and return the result."""
        candidates = list(clicks)
        if product_id is not None:
            candidates = [c for c in candidates if c.product_id == product_id]
        if merchant_id is not None:
            candidates = [c for c in candidates if c.merchant_id == merchant_id]

        # Prefer chronological order (oldest first) for first-click, reverse for last.
        candidates_sorted = sorted(candidates, key=lambda c: c.timestamp)

        selected: AffiliateClick | None = None
        reason: str

        if model is AttributionModel.DIRECT:
            reason = "Direct attribution — no prior click required."
            return AttributionResult(
                attribution_id=attribution_id,
                model=model,
                click_id=None,
                merchant_id=merchant_id,
                product_id=product_id,
                attributed_at=attributed_at,
                revenue=revenue,
                estimated_commission=estimated_commission,
                reason=reason,
                candidates_considered=len(candidates_sorted),
            )

        if model is AttributionModel.ORGANIC:
            organic = [
                c
                for c in candidates_sorted
                if c.source in {ClickSource.ORGANIC, ClickSource.UNKNOWN}
            ]
            selected = organic[-1] if organic else None
            reason = (
                f"Organic attribution selected click {selected.click_id}."
                if selected
                else "Organic attribution — no organic click found."
            )
        elif model is AttributionModel.INTERNAL_RECOMMENDATION:
            internal = [
                c
                for c in candidates_sorted
                if c.source
                in {
                    ClickSource.SHOPPING_ASSISTANT,
                    ClickSource.RECOMMENDATION_API,
                }
            ]
            selected = internal[-1] if internal else None
            reason = (
                f"Internal recommendation attribution selected click {selected.click_id}."
                if selected
                else "Internal recommendation — no assistant/recommendation click found."
            )
        elif model is AttributionModel.EXTERNAL_CAMPAIGN:
            external = [
                c
                for c in candidates_sorted
                if c.source is ClickSource.EXTERNAL_CAMPAIGN or c.campaign_id
            ]
            selected = external[-1] if external else None
            reason = (
                f"External campaign attribution selected click {selected.click_id}."
                if selected
                else "External campaign — no campaign click found (future support hook)."
            )
        elif model is AttributionModel.FIRST_CLICK:
            selected = candidates_sorted[0] if candidates_sorted else None
            reason = (
                f"First-click attribution selected click {selected.click_id}."
                if selected
                else "First-click attribution — no candidate clicks."
            )
        else:  # LAST_CLICK (default)
            selected = candidates_sorted[-1] if candidates_sorted else None
            reason = (
                f"Last-click attribution selected click {selected.click_id}."
                if selected
                else "Last-click attribution — no candidate clicks."
            )

        return AttributionResult(
            attribution_id=attribution_id,
            model=model,
            click_id=selected.click_id if selected else None,
            merchant_id=(selected.merchant_id if selected else merchant_id),
            product_id=(selected.product_id if selected else product_id),
            attributed_at=attributed_at,
            revenue=revenue if revenue else (selected.revenue if selected else 0.0),
            estimated_commission=(
                estimated_commission
                if estimated_commission
                else (selected.estimated_commission if selected else 0.0)
            ),
            reason=reason,
            candidates_considered=len(candidates_sorted),
        )

    def mark_converted(self, click: AffiliateClick, *, status: ConversionStatus) -> AffiliateClick:
        """Return a copy-friendly status hint (caller persists via dataclasses.replace)."""
        # Pure helper documenting allowed conversion transitions; actual replace
        # happens in the tracking service to keep this engine I/O-free.
        _ = click
        return click if status in ConversionStatus else click

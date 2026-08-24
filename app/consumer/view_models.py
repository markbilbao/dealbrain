"""Presentation view-models for Results, Compare, and Why pages.

These objects hold values already supplied by canonical authorities or explicit
non-live presentation fixtures. They do not compute PiqScore or Recommendation.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Literal

from app.consumer.location import DeliveryContext
from app.consumer.pricing import MoneyComponent, PriceState

FitRating = Literal["1", "2", "3", "4", "5"]
EvidenceStatus = Literal["verified", "not_applicable", "unknown", "unverified"]
WhyVariant = Literal["standard", "score_diff", "cross_border", "qualified"]
PageName = Literal["results", "compare", "why"]


@dataclass(frozen=True, slots=True)
class PiqScoreView:
    value: float
    descriptor: str
    percentile_label: str | None
    snapshot_sha256: str


@dataclass(frozen=True, slots=True)
class OfferEconomicsView:
    listing: MoneyComponent
    voucher: MoneyComponent | None
    shipping: MoneyComponent
    taxes: MoneyComponent
    import_charges: MoneyComponent | None
    other_costs: tuple[MoneyComponent, ...]
    dominant_state: PriceState
    dominant_label: str
    dominant_amount: float | None
    international: bool
    shipping_material: bool
    breakdown_lines: tuple[tuple[str, str, str], ...]  # label, display, tone


@dataclass(frozen=True, slots=True)
class ProductCardView:
    product_id: str
    brand: str
    model: str
    category: str
    merchant: str
    offer_url: str
    image_key: str
    tags: tuple[str, ...]
    piqscore: PiqScoreView
    economics: OfferEconomicsView
    is_best_piq: bool
    is_highest_piqscore: bool
    is_qualified: bool
    alternative_badge: str | None
    alternative_reason: str
    compact_breakdown: str
    why_it_won: tuple[str, ...]
    freshness_label: str | None
    origin_label: str | None
    display_name: str = ""

    @property
    def identity_name(self) -> str:
        captured = f"{self.brand} {self.model}".strip()
        return captured or self.display_name


@dataclass(frozen=True, slots=True)
class CompareFitRow:
    label: str
    values: tuple[str, ...]
    kind: Literal["text", "stars"] = "text"


@dataclass(frozen=True, slots=True)
class EvidenceCategoryView:
    label: str
    status: EvidenceStatus
    status_label: str


@dataclass(frozen=True, slots=True)
class SourceView:
    name: str
    proven: bool


@dataclass(frozen=True, slots=True)
class WhySectionView:
    number: int
    title: str
    narrative: str
    bullets: tuple[tuple[str, str], ...]  # icon, text
    callout: str | None = None
    callout_tone: str = "info"
    extra: dict[str, object] = field(default_factory=dict)


@dataclass(frozen=True, slots=True)
class ShopperContextView:
    budget_label: str
    top_priority: str
    use_case: str
    delivery_label: str
    urgency: str
    why_this_fits: str


@dataclass(frozen=True, slots=True)
class DecisionPageView:
    decision_id: str
    context_version: int
    catalog_id: str
    query_label: str
    evaluated_count: int
    page: PageName
    why_variant: WhyVariant
    location: DeliveryContext
    location_prompt: bool
    recalculating: bool
    recommendation_changed: bool
    recommendation_changed_message: str | None
    best_piq: ProductCardView
    alternatives: tuple[ProductCardView, ...]
    compared: tuple[ProductCardView, ...]
    highest_piqscore_product_id: str
    highest_piqscore_name: str
    recommendation_decision: str
    shopper: ShopperContextView
    affiliate_disclosure: str
    freshness_disclaimer: str
    data_classification: str
    unknowns: tuple[str, ...]
    evidence_categories: tuple[EvidenceCategoryView, ...]
    sources: tuple[SourceView, ...]
    why_sections: tuple[WhySectionView, ...]
    ask_placeholder: str
    ask_suggestions: tuple[str, ...]
    compare_pay_rows: tuple[CompareFitRow, ...]
    compare_fit_rows: tuple[CompareFitRow, ...]
    canonical_piqscore_set_sha256: str
    recommendation_snapshot_sha256: str
    geocode_available: bool = False
    location_error: str | None = None
    geolocation_needs_city: bool = False
    delivery_costs_verified: bool = False
    data_unavailable: bool = False
    unavailable_message: str | None = None
    destination_snapshot_known: bool = False
    recommendation_qualified_message: str | None = None
    session_location_differs: bool = False
    session_location_label: str | None = None
    presentation_mode: Literal["canonical", "fixture", "unavailable"] = "fixture"
    qualification_state: str | None = None

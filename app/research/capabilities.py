"""Derive required research capabilities from a frozen authorized scope."""

from __future__ import annotations

from app.domain.entities.research_authorization import FrozenResearchScope
from app.domain.entities.research_execution import ResearchCapability

_TOPIC_CAPABILITIES: tuple[tuple[tuple[str, ...], ResearchCapability], ...] = (
    (("price", "pricing", "cost"), ResearchCapability.CURRENT_PRICING),
    (("ship", "delivery", "deliver"), ResearchCapability.SHIPPING),
    (("tax", "duty", "duties", "import"), ResearchCapability.TAXES_IMPORT),
    (("warrant",), ResearchCapability.WARRANTY_EVIDENCE),
    (("review", "reddit", "community", "youtube"), ResearchCapability.REVIEW_COMMUNITY_EVIDENCE),
    (("spec", "microphone", "mic", "battery", "anc"), ResearchCapability.PRODUCT_SPECIFICATION),
    (("available", "availability", "stock"), ResearchCapability.AVAILABILITY),
    (("promo", "voucher", "discount"), ResearchCapability.PROMOTION_EVIDENCE),
)


def derive_required_capabilities(scope: FrozenResearchScope) -> tuple[ResearchCapability, ...]:
    """Map frozen authorization scope to bounded required capabilities.

    Does not invent SKUs, sources, or destination economics. Destination-
    sensitive scopes still declare shipping/tax requirements so the router
    can block them honestly before Sprint 37.
    """

    required: list[ResearchCapability] = []
    if scope.reason == "outside_evaluated_set" or scope.outside_set_product_names:
        required.extend(
            (
                ResearchCapability.PRODUCT_DISCOVERY,
                ResearchCapability.OFFER_DISCOVERY,
            )
        )
    if scope.reason == "evaluated_set_expansion" or scope.expansion_required:
        required.extend(
            (
                ResearchCapability.PRODUCT_DISCOVERY,
                ResearchCapability.OFFER_DISCOVERY,
            )
        )
    if scope.reason == "freshness_required" or scope.freshness_required:
        required.append(ResearchCapability.CURRENT_PRICING)
    if scope.reason == "requested_source" or scope.requested_sources:
        required.extend(
            (
                ResearchCapability.OFFER_DISCOVERY,
                ResearchCapability.CURRENT_PRICING,
            )
        )
    if scope.reason == "reevaluation_required" or scope.destination_label:
        required.extend(
            (
                ResearchCapability.SHIPPING,
                ResearchCapability.TAXES_IMPORT,
            )
        )
    if scope.reason == "insufficient_evidence" and not required:
        required.append(ResearchCapability.PRODUCT_SPECIFICATION)
    for topic in scope.requested_evidence_topics:
        required.extend(_capabilities_for_topic(topic))
    return _dedupe(required)


def _capabilities_for_topic(topic: str) -> tuple[ResearchCapability, ...]:
    lowered = topic.casefold()
    matched: list[ResearchCapability] = []
    for needles, capability in _TOPIC_CAPABILITIES:
        if any(needle in lowered for needle in needles):
            matched.append(capability)
    return tuple(matched)


def _dedupe(items: list[ResearchCapability]) -> tuple[ResearchCapability, ...]:
    seen: set[ResearchCapability] = set()
    ordered: list[ResearchCapability] = []
    for item in items:
        if item not in seen:
            seen.add(item)
            ordered.append(item)
    return tuple(ordered)

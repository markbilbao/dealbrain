"""Build evidence items from shopping candidates and optional module outputs."""

from __future__ import annotations

from app.domain.entities.shopping_assistant import ShoppingCandidate, ShoppingEvidence


class ShoppingEvidenceService:
    """Map known candidate attributes into evidence records."""

    def build_for_candidates(
        self,
        candidates: list[ShoppingCandidate],
        *,
        limit_per_product: int = 8,
    ) -> list[ShoppingEvidence]:
        evidence: list[ShoppingEvidence] = []
        for candidate in candidates:
            product_evidence = self._for_candidate(candidate)
            evidence.extend(product_evidence[:limit_per_product])
        return evidence

    def _for_candidate(self, candidate: ShoppingCandidate) -> list[ShoppingEvidence]:
        items: list[ShoppingEvidence] = []
        pid = candidate.product_id

        items.append(
            ShoppingEvidence(
                evidence_id=f"{pid}:identity",
                type="product_identity",
                source_id="shopping_catalog",
                description=f"Product identity: {candidate.product_name} ({candidate.category})",
                product_id=pid,
                value=candidate.product_name,
            )
        )
        if candidate.known_price is not None:
            items.append(
                ShoppingEvidence(
                    evidence_id=f"{pid}:price",
                    type="price",
                    source_id=candidate.marketplace or "catalog",
                    description=(
                        f"Known offer price {candidate.known_price:,.2f} "
                        f"{candidate.currency} on {candidate.marketplace or 'unknown marketplace'}"
                    ),
                    product_id=pid,
                    value=candidate.known_price,
                )
            )
        if candidate.marketplace:
            items.append(
                ShoppingEvidence(
                    evidence_id=f"{pid}:marketplace",
                    type="marketplace",
                    source_id=candidate.marketplace,
                    description=(
                        f"Marketplace offer observed in mock/imported data: {candidate.marketplace}"
                    ),
                    product_id=pid,
                    value=candidate.marketplace,
                )
            )
        if candidate.deal_score is not None:
            items.append(
                ShoppingEvidence(
                    evidence_id=f"{pid}:deal_score",
                    type="deal_score",
                    source_id="dealscore",
                    description=(
                        f"DealScore {candidate.deal_score:.1f} from available ranking inputs"
                    ),
                    product_id=pid,
                    value=candidate.deal_score,
                )
            )
        if candidate.rating is not None:
            items.append(
                ShoppingEvidence(
                    evidence_id=f"{pid}:rating",
                    type="rating",
                    source_id="review_intelligence",
                    description=(
                        f"Average rating {candidate.rating:.2f} across "
                        f"{candidate.review_count:,} reviews (mock/imported)"
                    ),
                    product_id=pid,
                    value=candidate.rating,
                )
            )
        if candidate.complaints:
            items.append(
                ShoppingEvidence(
                    evidence_id=f"{pid}:review",
                    type="review",
                    source_id="review_summary",
                    description="Main complaints: " + "; ".join(candidate.complaints[:3]),
                    product_id=pid,
                    value="; ".join(candidate.complaints[:3]),
                )
            )
        if candidate.strengths:
            items.append(
                ShoppingEvidence(
                    evidence_id=f"{pid}:review_strengths",
                    type="review",
                    source_id="review_summary",
                    description=(
                        "Strengths from review insights: " + "; ".join(candidate.strengths[:3])
                    ),
                    product_id=pid,
                    value="; ".join(candidate.strengths[:3]),
                )
            )
        if candidate.seller_name is not None:
            trust = (
                f" (trust score {candidate.seller_trust_score:.2f})"
                if candidate.seller_trust_score is not None
                else ""
            )
            items.append(
                ShoppingEvidence(
                    evidence_id=f"{pid}:seller",
                    type="seller",
                    source_id="marketplace_intelligence",
                    description=f"Seller {candidate.seller_name}{trust}",
                    product_id=pid,
                    value=candidate.seller_name,
                )
            )
        if candidate.recent_price_direction is not None or candidate.price_near_low is not None:
            near = (
                "near the lowest known historical price"
                if candidate.price_near_low
                else "not confirmed near the known historical low"
            )
            direction = candidate.recent_price_direction or "unknown"
            items.append(
                ShoppingEvidence(
                    evidence_id=f"{pid}:price_history",
                    type="price_history",
                    source_id="price_history",
                    description=(
                        f"Price history signal: recent direction={direction}; "
                        f"current offer is {near}"
                    ),
                    product_id=pid,
                    value=direction,
                )
            )
        items.append(
            ShoppingEvidence(
                evidence_id=f"{pid}:recommendation",
                type="recommendation",
                source_id="recommendation_engine",
                description=(
                    f"Candidate match score {candidate.match_score:.2f} using DealScore, "
                    "ratings, and constraint matching"
                ),
                product_id=pid,
                value=candidate.match_score,
            )
        )
        return items

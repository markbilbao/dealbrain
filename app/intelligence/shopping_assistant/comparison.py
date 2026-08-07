"""Deterministic product comparison for the shopping assistant."""

from __future__ import annotations

from app.domain.entities.shopping_assistant import (
    CategoryWinner,
    ProductComparison,
    ShoppingCandidate,
    ShoppingEvidence,
)


class ProductComparisonService:
    """Compare candidates using only known numeric / structured attributes."""

    def compare(
        self,
        candidates: list[ShoppingCandidate],
        evidence: list[ShoppingEvidence],
        *,
        priorities: tuple[str, ...] = (),
    ) -> ProductComparison | None:
        if len(candidates) < 2:
            return None

        left, right = candidates[0], candidates[1]
        winners: list[CategoryWinner] = []
        evidence_ids = [
            item.evidence_id
            for item in evidence
            if item.product_id in {left.product_id, right.product_id}
        ]

        def _winner(
            category: str,
            winner: ShoppingCandidate,
            loser: ShoppingCandidate,
            reason: str,
            evidence_suffix: str,
        ) -> CategoryWinner:
            return CategoryWinner(
                category=category,
                product_id=winner.product_id,
                product_name=winner.product_name,
                reason=reason,
                evidence_ids=(f"{winner.product_id}:{evidence_suffix}",),
            )

        if left.known_price is not None and right.known_price is not None:
            cheaper = left if left.known_price <= right.known_price else right
            other = right if cheaper is left else left
            winners.append(
                _winner(
                    "price",
                    cheaper,
                    other,
                    (
                        f"Lower known price ({cheaper.known_price:,.0f} vs "
                        f"{other.known_price:,.0f} {cheaper.currency})"
                    ),
                    "price",
                )
            )

        if left.deal_score is not None and right.deal_score is not None:
            better = left if left.deal_score >= right.deal_score else right
            other = right if better is left else left
            winners.append(
                _winner(
                    "deal_score",
                    better,
                    other,
                    f"Higher PiqScore ({better.deal_score:.1f} vs {other.deal_score:.1f})",
                    "deal_score",
                )
            )

        if left.rating is not None and right.rating is not None:
            better = left if left.rating >= right.rating else right
            other = right if better is left else left
            winners.append(
                _winner(
                    "rating",
                    better,
                    other,
                    f"Higher average rating ({better.rating:.2f} vs {other.rating:.2f})",
                    "rating",
                )
            )

        if left.review_count or right.review_count:
            better = left if left.review_count >= right.review_count else right
            other = right if better is left else left
            winners.append(
                _winner(
                    "review_volume",
                    better,
                    other,
                    f"More reviews ({better.review_count:,} vs {other.review_count:,})",
                    "rating",
                )
            )

        for priority in priorities:
            key = priority.lower()
            left_text = (" ".join(left.features) + " " + " ".join(left.strengths)).lower()
            left_hit = key in left_text
            right_hit = (
                key in " ".join(right.features).lower() or key in " ".join(right.strengths).lower()
            )
            if left_hit and not right_hit:
                winners.append(
                    _winner(
                        key,
                        left,
                        right,
                        f"Stronger supported signal for {key} in available strengths/features",
                        "review_strengths",
                    )
                )
            elif right_hit and not left_hit:
                winners.append(
                    _winner(
                        key,
                        right,
                        left,
                        f"Stronger supported signal for {key} in available strengths/features",
                        "review_strengths",
                    )
                )
            elif left_hit and right_hit:
                # Prefer higher rating as a soft tie-break when both claim the priority.
                better = left if (left.rating or 0) >= (right.rating or 0) else right
                other = right if better is left else left
                winners.append(
                    _winner(
                        key,
                        better,
                        other,
                        (
                            f"Both list {key}; {better.product_name} has the higher known rating "
                            f"({better.rating})"
                        ),
                        "rating",
                    )
                )

        price_difference = None
        currency = left.currency if left.currency == right.currency else None
        if left.known_price is not None and right.known_price is not None and currency:
            price_difference = abs(left.known_price - right.known_price)

        review_differences = (
            (f"{left.product_name}: rating {left.rating}, {left.review_count:,} reviews"),
            (f"{right.product_name}: rating {right.rating}, {right.review_count:,} reviews"),
        )

        # Overall recommendation: DealScore then rating, unless a priority winner dominates.
        overall = left if (left.deal_score or 0) >= (right.deal_score or 0) else right
        if priorities:
            priority_wins = [item for item in winners if item.category in priorities]
            if priority_wins:
                counts: dict[str, int] = {}
                for item in priority_wins:
                    counts[item.product_id] = counts.get(item.product_id, 0) + 1
                top_id = max(counts, key=counts.get)  # type: ignore[arg-type]
                overall = left if left.product_id == top_id else right

        recommended_use = None
        if overall.use_cases:
            recommended_use = overall.use_cases[0]

        uncertainty: list[str] = [
            (
                "Comparison uses mock/imported PiqSavi data only — "
                "not complete live marketplace coverage."
            ),
        ]
        if left.currency != right.currency:
            uncertainty.append("Currencies differ; price difference is not directly comparable.")
        if not priorities:
            uncertainty.append(
                "No explicit priorities were provided; overall pick leans on PiqScore and ratings."
            )

        return ProductComparison(
            product_ids=(left.product_id, right.product_id),
            product_names=(left.product_name, right.product_name),
            category_winners=tuple(winners),
            strengths={
                left.product_id: left.strengths,
                right.product_id: right.strengths,
            },
            weaknesses={
                left.product_id: left.complaints,
                right.product_id: right.complaints,
            },
            price_difference=price_difference,
            currency=currency,
            review_differences=review_differences,
            recommended_use_case=recommended_use,
            overall_recommendation=(
                f"{overall.product_name} is the better supported pick based on available "
                f"PiqScore, ratings, and requested priorities."
            ),
            unresolved_uncertainty=tuple(uncertainty),
            evidence_ids=tuple(evidence_ids),
        )

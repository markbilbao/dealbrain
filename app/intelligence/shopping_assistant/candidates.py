"""Deterministic product candidate selection for the shopping assistant."""

from __future__ import annotations

from typing import Any

from app.domain.entities.shopping_assistant import ShoppingCandidate, ShoppingIntent
from app.intelligence.shopping_assistant.fixtures import get_catalog


def _as_candidate(row: dict[str, Any], *, match_score: float = 0.0) -> ShoppingCandidate:
    return ShoppingCandidate(
        product_id=str(row["product_id"]),
        product_name=str(row["product_name"]),
        category=str(row["category"]),
        known_price=float(row["known_price"]) if row.get("known_price") is not None else None,
        currency=str(row.get("currency") or "PHP"),
        marketplace=row.get("marketplace"),
        deal_score=float(row["deal_score"]) if row.get("deal_score") is not None else None,
        rating=float(row["rating"]) if row.get("rating") is not None else None,
        review_count=int(row.get("review_count") or 0),
        brand=row.get("brand"),
        use_cases=tuple(row.get("use_cases") or ()),
        features=tuple(row.get("features") or ()),
        seller_name=row.get("seller_name"),
        seller_trust_score=(
            float(row["seller_trust_score"]) if row.get("seller_trust_score") is not None else None
        ),
        price_near_low=row.get("price_near_low"),
        recent_price_direction=row.get("recent_price_direction"),
        complaints=tuple(row.get("complaints") or ()),
        strengths=tuple(row.get("strengths") or ()),
        data_status=row.get("data_status") or "mock",
        match_score=match_score,
    )


def _name_match_score(query_name: str, product_name: str) -> float:
    q = query_name.lower().strip()
    p = product_name.lower().strip()
    if not q:
        return 0.0
    if q == p:
        return 1.0
    if q in p or p in q:
        return 0.85
    q_tokens = set(q.split())
    p_tokens = set(p.split())
    if not q_tokens:
        return 0.0
    overlap = len(q_tokens & p_tokens) / len(q_tokens)
    return overlap if overlap >= 0.5 else 0.0


class ProductCandidateService:
    """Filter and score catalog products against shopping constraints."""

    def __init__(self, catalog: list[dict[str, Any]] | None = None) -> None:
        self._catalog = catalog if catalog is not None else get_catalog()

    def find_candidates(self, intent: ShoppingIntent) -> list[ShoppingCandidate]:
        constraints = intent.constraints
        scored: list[ShoppingCandidate] = []

        for row in self._catalog:
            score = 0.0
            name = str(row["product_name"])

            if constraints.products:
                best = max(_name_match_score(product, name) for product in constraints.products)
                if best <= 0:
                    # Explicit product list: skip non-matches unless empty later.
                    continue
                score += 3.0 * best

            if (
                constraints.category
                and row.get("category") != constraints.category
                and not constraints.products
            ):
                continue

            if constraints.brand_preference:
                brand = str(row.get("brand") or "").lower()
                if brand != constraints.brand_preference.lower() and not constraints.products:
                    continue
                if brand == constraints.brand_preference.lower():
                    score += 0.5

            price = row.get("known_price")
            if constraints.budget_max is not None and price is not None:
                if float(price) > float(constraints.budget_max):
                    continue
                score += 1.0
            if (
                constraints.budget_min is not None
                and price is not None
                and float(price) < float(constraints.budget_min)
            ):
                continue

            if constraints.currency and row.get("currency") != constraints.currency:
                # Keep but de-prioritize mismatched currency.
                score -= 0.5

            use_cases = set(row.get("use_cases") or ())
            for use_case in constraints.use_cases:
                if use_case in use_cases:
                    score += 1.2

            features = {str(item).lower() for item in (row.get("features") or ())}
            for feature in constraints.preferred_features:
                if feature.lower() in features or feature.lower() in name.lower():
                    score += 0.4
            for feature in constraints.priorities:
                if feature.lower() in features or feature.lower() in name.lower():
                    score += 0.35

            preferred = (constraints.preferred_marketplace or "").lower()
            marketplace = str(row.get("marketplace") or "").lower()
            if preferred and marketplace == preferred:
                score += 0.6

            deal = row.get("deal_score")
            if deal is not None:
                score += float(deal) / 100.0

            rating = row.get("rating")
            if rating is not None:
                score += float(rating) / 10.0

            scored.append(_as_candidate(row, match_score=score))

        # If named products produced no matches, fall back to category/use-case scan.
        if not scored and constraints.products:
            relaxed = ShoppingIntent(
                intent=intent.intent,
                constraints=type(constraints)(
                    category=constraints.category,
                    products=(),
                    budget_min=constraints.budget_min,
                    budget_max=constraints.budget_max,
                    currency=constraints.currency,
                    preferred_marketplace=constraints.preferred_marketplace,
                    use_cases=constraints.use_cases,
                    preferred_features=constraints.preferred_features,
                    excluded_features=constraints.excluded_features,
                    brand_preference=constraints.brand_preference,
                    urgency=constraints.urgency,
                    location=constraints.location,
                    priorities=constraints.priorities,
                ),
                raw_query=intent.raw_query,
                parser=intent.parser,
            )
            return self.find_candidates(relaxed)

        scored.sort(
            key=lambda item: (
                item.match_score,
                item.deal_score or 0.0,
                item.rating or 0.0,
                item.review_count,
            ),
            reverse=True,
        )
        return scored

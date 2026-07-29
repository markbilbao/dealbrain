"""Deterministic shopping assistant narrative builder (always-on fallback)."""

from __future__ import annotations

from typing import Any

from app.domain.entities.shopping_assistant import (
    ProductComparison,
    ShoppingCandidate,
    ShoppingIntent,
    ShoppingRecommendation,
)
from app.domain.interfaces.shopping_assistant_repository import ShoppingExplanationProvider
from app.intelligence.shopping_assistant.buy_now_wait import build_buy_now_or_wait


def build_answer(
    intent: ShoppingIntent,
    *,
    top: ShoppingRecommendation | None,
    alternatives: list[ShoppingRecommendation],
    comparison: ProductComparison | None,
    candidates: list[ShoppingCandidate],
    buy_now_or_wait: str | None,
) -> str:
    """Compose a factual, qualified answer from structured results."""
    if intent.intent == "comparison" and comparison is not None:
        winners = ", ".join(
            f"{item.category}: {item.product_name}" for item in comparison.category_winners[:4]
        )
        return (
            f"Based on available DealBrain mock/imported data, "
            f"{comparison.overall_recommendation} "
            f"Category signals — {winners}. "
            "Unresolved: "
            f"{(comparison.unresolved_uncertainty or ('none noted',))[0]}."
        )

    if intent.intent == "buy_now_or_wait":
        focus = candidates[0].product_name if candidates else "the product"
        guidance = buy_now_or_wait or build_buy_now_or_wait(
            candidates[0] if candidates else None,
            [],
        )
        return f"Regarding {focus}: {guidance}"

    if intent.intent == "complaints":
        if not candidates:
            return "No matching product complaints are available in the current mock catalog."
        focus = candidates[0]
        if not focus.complaints:
            return (
                f"No recurring complaint themes are available for {focus.product_name} "
                "in the current dataset."
            )
        return (
            f"Main complaints reported for {focus.product_name} in available review insights: "
            + "; ".join(focus.complaints)
            + ". These are derived from mock/imported review summaries, not a live scrape."
        )

    if intent.intent == "seller_trust":
        if not candidates:
            return "No seller trust evidence is available for this query."
        # Prefer cheapest among candidates when asking about cheapest seller.
        ordered = sorted(
            [item for item in candidates if item.known_price is not None],
            key=lambda item: item.known_price or 0.0,
        )
        focus = ordered[0] if ordered else candidates[0]
        trust = focus.seller_trust_score
        if trust is None:
            return (
                f"Seller trust data is incomplete for {focus.seller_name or 'the cheapest offer'}. "
                "DealBrain cannot guarantee authenticity."
            )
        label = "relatively strong" if trust >= 0.9 else "moderate" if trust >= 0.8 else "weaker"
        return (
            f"The lowest known-price offer among matches is {focus.product_name} from "
            f"{focus.seller_name or 'an unknown seller'} with a seller trust score of {trust:.2f} "
            f"({label}). This is not a guarantee of authenticity or fulfillment quality."
        )

    if intent.intent == "best_offer":
        if top is None:
            return "No marketplace offers are available in the mock catalog for this query."
        return (
            f"Among available mock/imported offers, {top.product_name} on "
            f"{top.marketplace or 'an unknown marketplace'} at "
            f"{top.known_price:,.0f} {top.currency} is the best supported pick "
            f"(DealScore {top.deal_score}). This is not a claim of the lowest price online."
        )

    if intent.intent == "worth_buying":
        if top is None and not candidates:
            return "There is not enough evidence to judge whether this product is worth buying."
        focus = top or ShoppingRecommendation(
            product_id=candidates[0].product_id,
            product_name=candidates[0].product_name,
            reason="",
            known_price=candidates[0].known_price,
            currency=candidates[0].currency,
            marketplace=candidates[0].marketplace,
            deal_score=candidates[0].deal_score,
            confidence=0.5,
        )
        candidate = next((c for c in candidates if c.product_id == focus.product_id), None)
        cons = "; ".join((candidate.complaints if candidate else ())[:2]) or "none listed"
        return (
            f"{focus.product_name} looks reasonably supported by available data "
            f"(DealScore {focus.deal_score}, rating {focus.rating}). "
            f"Trade-offs include: {cons}. This is an AI interpretation over DealBrain evidence, "
            "not a purchase guarantee."
        )

    if top is None:
        return (
            "No products in the mock/imported catalog matched those constraints. "
            "Try broadening budget, category, or use-case filters."
        )

    alt_text = ""
    if alternatives:
        alt_text = (
            " Alternatives: "
            + ", ".join(
                f"{item.product_name} (DealScore {item.deal_score})" for item in alternatives[:2]
            )
            + "."
        )

    use_case = ""
    if intent.constraints.use_cases:
        use_case = f" for {', '.join(intent.constraints.use_cases)}"

    budget = ""
    if intent.constraints.budget_max is not None:
        currency = intent.constraints.currency or top.currency
        symbol = "₱" if currency == "PHP" else f"{currency} "
        budget = f" under {symbol}{intent.constraints.budget_max:,.0f}"

    return (
        f"Top supported recommendation{use_case}{budget}: {top.product_name} at "
        f"{top.known_price:,.0f} {top.currency} on {top.marketplace or 'unknown marketplace'} "
        f"(DealScore {top.deal_score}, confidence {top.confidence:.2f}). "
        f"{top.reason}{alt_text} "
        "Based on mock/imported DealBrain data — not live marketplace coverage."
    )


class DeterministicShoppingExplanationProvider(ShoppingExplanationProvider):
    """Always-available explanation provider with no external AI calls."""

    @property
    def provider_name(self) -> str:
        return "deterministic"

    @property
    def model_name(self) -> str:
        return "deterministic-shopping-v1"

    def is_available(self) -> bool:
        return True

    def explain(self, payload: dict[str, Any]) -> dict[str, Any]:
        intent = payload["intent"]
        top = payload.get("top")
        alternatives = list(payload.get("alternatives") or [])
        comparison = payload.get("comparison")
        candidates = list(payload.get("candidates") or [])
        buy_now_or_wait = payload.get("buy_now_or_wait")
        answer = build_answer(
            intent,
            top=top,
            alternatives=alternatives,
            comparison=comparison,
            candidates=candidates,
            buy_now_or_wait=buy_now_or_wait,
        )
        return {
            "provider": self.provider_name,
            "model": self.model_name,
            "status": "ok",
            "answer": answer,
            "confidence": 0.72,
            "claims": self._claims(top, comparison),
        }

    @staticmethod
    def _claims(
        top: ShoppingRecommendation | None,
        comparison: ProductComparison | None,
    ) -> list[dict[str, Any]]:
        claims: list[dict[str, Any]] = []
        if top is not None:
            claims.append(
                {
                    "field": "top_recommendation",
                    "value": top.product_name,
                    "evidence_ids": list(top.evidence_ids),
                }
            )
        if comparison is not None:
            claims.append(
                {
                    "field": "overall_recommendation",
                    "value": comparison.overall_recommendation,
                    "evidence_ids": list(comparison.evidence_ids),
                }
            )
        return claims

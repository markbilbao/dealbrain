"""Evidence-based buy-now-or-wait guidance (no future price certainty)."""

from __future__ import annotations

from app.domain.entities.shopping_assistant import ShoppingCandidate, ShoppingEvidence


def build_buy_now_or_wait(
    candidate: ShoppingCandidate | None,
    evidence: list[ShoppingEvidence],
) -> str | None:
    """Return a qualified buy/wait statement from known history signals only."""
    if candidate is None:
        return (
            "There is not enough product evidence to confidently recommend buying now or waiting."
        )

    history = [
        item
        for item in evidence
        if item.type == "price_history" and item.product_id == candidate.product_id
    ]
    no_history_signal = (
        not history
        and candidate.recent_price_direction is None
        and candidate.price_near_low is None
    )
    if no_history_signal:
        return (
            "There is not enough history to confidently recommend waiting. "
            "Future price movement is uncertain."
        )

    parts: list[str] = []
    if candidate.price_near_low is True:
        parts.append("The current offer is close to the lowest price in the available history.")
    elif candidate.price_near_low is False:
        parts.append(
            "The current offer is not confirmed near the lowest price in the available history."
        )

    direction = candidate.recent_price_direction
    if direction == "down":
        parts.append("The price has recently decreased, but future movement is uncertain.")
    elif direction == "up":
        parts.append("The price has recently increased, but future movement is uncertain.")
    elif direction == "stable":
        parts.append(
            "The price has been relatively stable recently; waiting is not clearly better."
        )

    if candidate.deal_score is not None and candidate.deal_score >= 85:
        parts.append(
            f"DealScore {candidate.deal_score:.1f} is relatively strong among available candidates."
        )

    parts.append("This is not a guarantee that the price will drop or rise.")
    return " ".join(parts)

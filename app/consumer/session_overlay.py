"""Apply a session Recommendation overlay to consumer views and evidence packets.

Does not recalculate PiqScore, rewrite the canonical snapshot, or invent evidence.
"""

from __future__ import annotations

from dataclasses import replace

from app.consumer.view_models import DecisionPageView, ProductCardView, WhySectionView
from app.domain.entities.session_refinement import SessionRecommendationRefinement
from app.services.decision_evidence_packet import DecisionEvidencePacket, EvidenceFact


def apply_session_overlay_to_view(
    view: DecisionPageView,
    overlay: SessionRecommendationRefinement | None,
) -> DecisionPageView:
    """Return a view that shows the session Best Piq without mutating scores."""

    if overlay is None or view.data_unavailable:
        return view
    session_id = overlay.session_best_piq_product_id
    cards = tuple(_card_with_session_flag(card, session_id, overlay) for card in view.compared)
    if not any(card.product_id == session_id for card in cards):
        return view
    best = next(card for card in cards if card.product_id == session_id)
    alternatives = tuple(card for card in cards if card.product_id != session_id)
    changed = overlay.recommendation_changed
    original = next(
        (card for card in cards if card.product_id == overlay.original_best_piq_product_id),
        None,
    )
    message = None
    if changed and original is not None:
        priority = (
            overlay.priorities.top_priority
            or overlay.priorities.use_case
            or "your updated priority"
        )
        message = (
            f"Originally {original.identity_name} was Best Piq for You. "
            f"After you said {priority} matters more, {best.identity_name} is the "
            "current session Recommendation. PiqScores are unchanged."
        )
    elif overlay.status == "reset_to_original":
        message = "Session priorities were restored to the original decision."
    shopper = view.shopper
    if overlay.priorities.top_priority:
        shopper = replace(
            shopper,
            top_priority=overlay.priorities.top_priority.title(),
            why_this_fits=(
                overlay.reasons[0]
                if overlay.reasons
                else f"{best.identity_name} is the current session Best Piq for You."
            ),
        )
    elif overlay.reasons:
        shopper = replace(shopper, why_this_fits=overlay.reasons[0])
    why_variant = view.why_variant
    if best.product_id != view.highest_piqscore_product_id and why_variant == "standard":
        why_variant = "score_diff"
    return replace(
        view,
        recommendation_changed=changed or view.recommendation_changed,
        recommendation_changed_message=message or view.recommendation_changed_message,
        best_piq=best,
        alternatives=alternatives,
        compared=cards,
        shopper=shopper,
        why_variant=why_variant,
        why_sections=_overlay_why_sections(view, overlay, best, original),
        qualification_state=overlay.qualification_state or view.qualification_state,
    )


def apply_session_overlay_to_packet(
    packet: DecisionEvidencePacket,
    overlay: SessionRecommendationRefinement | None,
) -> DecisionEvidencePacket:
    """Point Ask at the current session Best Piq without changing PiqScores."""

    if overlay is None or not packet.available:
        return packet
    session_id = overlay.session_best_piq_product_id
    if session_id not in packet.evaluated_product_ids:
        return packet
    offers = tuple(
        replace(
            offer,
            is_best_piq=offer.product_id == session_id,
            is_qualified=offer.is_qualified if offer.product_id == session_id else False,
        )
        for offer in packet.offers
    )
    best = next(item for item in offers if item.product_id == session_id)
    original = next(
        (item for item in packet.offers if item.product_id == overlay.original_best_piq_product_id),
        None,
    )
    extra = [
        EvidenceFact(
            evidence_id="session-original-best",
            topic="recommendation",
            fact=(
                "Originally "
                f"{original.display_name if original else overlay.original_best_piq_product_id} "
                "was the historical Best Piq for You."
            ),
            product_id=overlay.original_best_piq_product_id,
            source="session-refinement",
        ),
        EvidenceFact(
            evidence_id="session-current-best",
            topic="recommendation",
            fact=(
                f"{best.display_name} is the current session Best Piq for You after the shopper "
                "clarified "
                f"{overlay.priorities.top_priority or overlay.priorities.use_case or 'priorities'}."
            ),
            product_id=best.product_id,
            source="session-refinement",
        ),
    ]
    extra.extend(
        EvidenceFact(
            evidence_id=f"session-reason:{index}",
            topic="recommendation",
            fact=reason,
            product_id=best.product_id,
            source="session-refinement",
        )
        for index, reason in enumerate(overlay.reasons)
    )
    return replace(
        packet,
        best_piq_product_id=best.product_id,
        best_piq_name=best.display_name,
        offers=offers,
        facts=packet.facts + tuple(extra),
        is_qualified=bool(overlay.qualification_state == "qualified" or packet.is_qualified),
        qualification_state=overlay.qualification_state or packet.qualification_state,
    )


def _card_with_session_flag(
    card: ProductCardView,
    session_id: str,
    overlay: SessionRecommendationRefinement,
) -> ProductCardView:
    is_best = card.product_id == session_id
    qualified = bool(
        overlay.qualification_state == "qualified" and is_best
    ) or (card.is_qualified and is_best)
    why = card.why_it_won
    if is_best and overlay.reasons:
        why = overlay.reasons[:3]
    alt = card.alternative_reason
    if not is_best and card.product_id == overlay.original_best_piq_product_id:
        alt = (
            "Originally Best Piq for You. Still in the evaluated set with the same PiqScore."
        )
    return replace(
        card,
        is_best_piq=is_best,
        is_qualified=qualified,
        why_it_won=why,
        alternative_reason=alt,
    )


def _overlay_why_sections(
    view: DecisionPageView,
    overlay: SessionRecommendationRefinement,
    best: ProductCardView,
    original: ProductCardView | None,
) -> tuple[WhySectionView, ...]:
    sections = list(view.why_sections)
    if not sections:
        return view.why_sections
    priority = overlay.priorities.top_priority or overlay.priorities.use_case
    original_name = (
        original.identity_name
        if original is not None
        else overlay.original_best_piq_product_id
    )
    if overlay.status == "reset_to_original":
        narrative = (
            f"{best.identity_name} is again Best Piq for You after you asked to use your "
            "original priorities. The historical Recommendation was not rewritten."
        )
    elif overlay.recommendation_changed:
        narrative = (
            f"Originally I recommended {original_name}. You then clarified "
            f"{priority or 'an updated priority'}. {best.identity_name} is now the session "
            "Best Piq for You from the same evaluated set and captured evidence. "
            "This does not mean the original decision was wrong — your priorities changed."
        )
        if original is not None and original.is_highest_piqscore and not best.is_highest_piqscore:
            narrative += (
                f" {original.identity_name} still has the higher objective PiqScore. "
                "PiqScore evaluates the offer; Best Piq for You reflects what best fits you."
            )
    else:
        narrative = (
            f"You clarified {priority or 'your priorities'}. {best.identity_name} still best "
            "satisfies the updated session context from captured evidence. "
            "The historical Recommendation remains unchanged."
        )
    if overlay.reasons:
        narrative = f"{narrative} {overlay.reasons[0]}"
    bullets = (
        ("priority", f"Original Best Piq: {original_name}"),
        ("check", f"Current session Best Piq: {best.identity_name}"),
        ("priority", f"Updated priority: {priority or 'session clarification'}"),
    )
    sections[0] = replace(
        sections[0],
        narrative=narrative,
        bullets=bullets + sections[0].bullets,
    )
    return tuple(sections)

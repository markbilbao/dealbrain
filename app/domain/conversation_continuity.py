"""Shared invariants for conversations bound to canonical decision snapshots."""

from __future__ import annotations

from app.domain.entities.shopping_assistant import ConversationContext
from app.domain.exceptions import ConversationContextDriftError


def require_stable_decision_context(
    existing: ConversationContext | None,
    updated: ConversationContext,
) -> None:
    """Reject replacement of an already-bound canonical decision reference."""

    if (
        existing is not None
        and existing.decision_context is not None
        and updated.decision_context != existing.decision_context
    ):
        raise ConversationContextDriftError(
            updated.conversation_id,
            "bound decision identity, version, evaluated set, or digests changed",
        )
    require_context_membership(updated)


def require_context_membership(context: ConversationContext) -> None:
    """Ensure structured turn state never escapes the bound evaluated set."""

    reference = context.decision_context
    if reference is None:
        return
    allowed_products = set(reference.evaluated_product_ids)
    unexpected_last_products = set(context.last_product_ids) - allowed_products
    if unexpected_last_products:
        raise ConversationContextDriftError(
            context.conversation_id,
            "last product state contains a product outside the canonical evaluated set",
        )
    for turn in context.turns:
        if turn.decision_id not in {None, reference.decision_id}:
            raise ConversationContextDriftError(
                context.conversation_id,
                "turn decision_id does not match the canonical decision",
            )
        if turn.context_version not in {None, reference.context_version}:
            raise ConversationContextDriftError(
                context.conversation_id,
                "turn context_version does not match the canonical decision",
            )
        if set(turn.product_ids) - allowed_products:
            raise ConversationContextDriftError(
                context.conversation_id,
                "turn contains a product outside the canonical evaluated set",
            )

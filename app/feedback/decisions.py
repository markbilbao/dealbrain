"""Owner-bound decision references for feedback. Missing and foreign look the same."""

from __future__ import annotations

from dataclasses import dataclass

from app.consumer.canonical_resolve import resolve_canonical_snapshot
from app.domain.entities.shopping_assistant import ConversationOwner
from app.domain.interfaces.decision_snapshot_repository import DecisionSnapshotRepository


@dataclass(frozen=True, slots=True)
class BoundDecision:
    decision_id: str
    context_version: int
    product_ids: frozenset[str]


def resolve_bound_decision(
    decision_id: str,
    owner: ConversationOwner | None,
    snapshots: DecisionSnapshotRepository | None,
) -> BoundDecision | None:
    """Return the owner-verified decision, or None for any safe failure."""

    snapshot = resolve_canonical_snapshot(decision_id, owner, snapshots)
    if snapshot is None:
        return None
    return BoundDecision(
        decision_id=snapshot.decision_id,
        context_version=snapshot.context_version,
        product_ids=frozenset(snapshot.evaluated_product_ids),
    )

"""Owner-bound resolution of canonical UUID snapshots for consumer routes."""

from __future__ import annotations

from app.consumer.uuid import is_canonical_uuid
from app.domain.entities.decision_snapshot import CanonicalDecisionSnapshot
from app.domain.entities.shopping_assistant import ConversationOwner
from app.domain.exceptions import DecisionSnapshotIntegrityError
from app.domain.interfaces.decision_snapshot_repository import DecisionSnapshotRepository


def resolve_canonical_snapshot(
    decision_id: str,
    owner: ConversationOwner | None,
    snapshots: DecisionSnapshotRepository | None,
    *,
    context_version: int | None = None,
) -> CanonicalDecisionSnapshot | None:
    """Return the owner-verified snapshot, or None for any safe failure.

    Missing, unauthorized, and integrity-failed snapshots all return None so
    document routes cannot leak another user's decision existence.
    """

    if not is_canonical_uuid(decision_id) or snapshots is None or owner is None:
        return None
    try:
        if context_version is not None:
            return snapshots.get_for_owner(decision_id, context_version, owner)
        return snapshots.get_latest_for_owner(decision_id, owner)
    except DecisionSnapshotIntegrityError:
        return None

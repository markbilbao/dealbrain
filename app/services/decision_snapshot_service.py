"""Server-side binding of conversations to persisted canonical decisions."""

from __future__ import annotations

from app.domain.entities.shopping_assistant import ConversationContext, ConversationOwner
from app.domain.exceptions import DecisionSnapshotOwnershipError
from app.domain.interfaces.decision_snapshot_repository import DecisionSnapshotRepository
from app.domain.interfaces.shopping_assistant_repository import ConversationRepository


class DecisionSnapshotBinder:
    """Bind only repository-verified canonical snapshot references."""

    def __init__(
        self,
        snapshots: DecisionSnapshotRepository,
        conversations: ConversationRepository,
    ) -> None:
        self._snapshots = snapshots
        self._conversations = conversations

    def bind(
        self,
        conversation_id: str,
        *,
        decision_id: str,
        context_version: int,
        owner: ConversationOwner,
        expected_conversation_version: int | None = None,
    ) -> ConversationContext:
        snapshot = self._snapshots.get_for_owner(decision_id, context_version, owner)
        if snapshot is None:
            raise DecisionSnapshotOwnershipError(
                decision_id,
                "snapshot not found or owner identity mismatch",
            )
        return self._conversations.bind_decision_context(
            conversation_id,
            owner=owner,
            decision_context=snapshot.to_reference(),
            expected_version=expected_conversation_version,
        )

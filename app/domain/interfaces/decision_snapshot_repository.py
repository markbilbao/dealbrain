"""Persistence port for immutable canonical decision snapshots."""

from __future__ import annotations

from abc import ABC, abstractmethod

from app.domain.entities.decision_snapshot import CanonicalDecisionSnapshot
from app.domain.entities.shopping_assistant import ConversationOwner


class DecisionSnapshotRepository(ABC):
    """Store canonical decision versions without update or delete operations."""

    @abstractmethod
    def add(self, snapshot: CanonicalDecisionSnapshot) -> CanonicalDecisionSnapshot:
        """Atomically insert one immutable decision version."""

    @abstractmethod
    def get(
        self,
        decision_id: str,
        context_version: int,
    ) -> CanonicalDecisionSnapshot | None:
        """Return one exact canonical version for trusted server-side use."""

    @abstractmethod
    def get_for_owner(
        self,
        decision_id: str,
        context_version: int,
        owner: ConversationOwner,
    ) -> CanonicalDecisionSnapshot | None:
        """Return one active version only when its owner identity matches."""

    @abstractmethod
    def get_latest_for_owner(
        self,
        decision_id: str,
        owner: ConversationOwner,
    ) -> CanonicalDecisionSnapshot | None:
        """Return the highest owner-bound version, or None if none match."""

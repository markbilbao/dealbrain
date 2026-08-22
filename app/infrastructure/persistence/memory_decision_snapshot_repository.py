"""Process-scoped immutable decision snapshot store with integrity checks."""

from __future__ import annotations

from collections.abc import Callable
from datetime import UTC, datetime
from threading import RLock

from app.domain.entities.decision_snapshot import CanonicalDecisionSnapshot
from app.domain.entities.shopping_assistant import ConversationOwner
from app.domain.exceptions import (
    DecisionSnapshotConflictError,
    DecisionSnapshotIntegrityError,
    DecisionSnapshotOwnershipError,
)
from app.domain.interfaces.decision_snapshot_repository import DecisionSnapshotRepository


class InMemoryDecisionSnapshotRepository(DecisionSnapshotRepository):
    """Append-only in-memory snapshots. Does not update or delete versions."""

    def __init__(self, *, clock: Callable[[], datetime] | None = None) -> None:
        self._clock = clock or (lambda: datetime.now(UTC))
        self._lock = RLock()
        self._records: dict[tuple[str, int], tuple[CanonicalDecisionSnapshot, str]] = {}

    def add(self, snapshot: CanonicalDecisionSnapshot) -> CanonicalDecisionSnapshot:
        if snapshot.owner.expires_at <= self._clock():
            raise DecisionSnapshotOwnershipError(snapshot.decision_id, "owner binding is expired")
        key = (snapshot.decision_id, snapshot.context_version)
        digest = snapshot.content_sha256
        with self._lock:
            if key in self._records:
                raise DecisionSnapshotConflictError(snapshot.decision_id, snapshot.context_version)
            self._records[key] = (snapshot, digest)
        return snapshot

    def get(
        self,
        decision_id: str,
        context_version: int,
    ) -> CanonicalDecisionSnapshot | None:
        with self._lock:
            record = self._records.get((decision_id, context_version))
        if record is None:
            return None
        snapshot, stored_digest = record
        if snapshot.content_sha256 != stored_digest:
            raise DecisionSnapshotIntegrityError(decision_id, context_version)
        return snapshot

    def get_for_owner(
        self,
        decision_id: str,
        context_version: int,
        owner: ConversationOwner,
    ) -> CanonicalDecisionSnapshot | None:
        snapshot = self.get(decision_id, context_version)
        if snapshot is None:
            return None
        if not snapshot.owner.has_same_identity(owner):
            return None
        now = self._clock()
        if snapshot.owner.expires_at <= now or owner.expires_at <= now:
            return None
        return snapshot

    def get_latest_for_owner(
        self,
        decision_id: str,
        owner: ConversationOwner,
    ) -> CanonicalDecisionSnapshot | None:
        with self._lock:
            versions = sorted(
                (version for key_id, version in self._records if key_id == decision_id),
                reverse=True,
            )
        for version in versions:
            loaded = self.get_for_owner(decision_id, version, owner)
            if loaded is not None:
                return loaded
        return None

"""Immutable canonical decision snapshots on the existing operational store."""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass
from datetime import UTC, datetime
from hashlib import sha256

from sqlalchemy.orm import Session, sessionmaker

from app.domain.entities.decision_snapshot import CanonicalDecisionSnapshot
from app.domain.entities.shopping_assistant import ConversationOwner
from app.domain.exceptions import (
    DecisionSnapshotConflictError,
    DecisionSnapshotIntegrityError,
    DecisionSnapshotOwnershipError,
)
from app.domain.interfaces.decision_snapshot_repository import DecisionSnapshotRepository
from app.infrastructure.persistence.errors import PersistenceConflictError
from app.infrastructure.persistence.session_bound import SessionBound
from app.infrastructure.persistence.stores import SHOPPING_DECISION_SNAPSHOTS


@dataclass(frozen=True, slots=True)
class _StoredDecisionSnapshot:
    """Persistence envelope carrying an independently checked content digest."""

    snapshot: CanonicalDecisionSnapshot
    content_sha256: str


class SqlAlchemyDecisionSnapshotRepository(DecisionSnapshotRepository, SessionBound):
    """Append-only decision versions with owner and content-integrity checks."""

    def __init__(
        self,
        session_factory: sessionmaker[Session] | None = None,
        session: Session | None = None,
        *,
        clock: Callable[[], datetime] | None = None,
    ) -> None:
        SessionBound.__init__(self, session_factory=session_factory, session=session)
        self._clock = clock or (lambda: datetime.now(UTC))

    def add(self, snapshot: CanonicalDecisionSnapshot) -> CanonicalDecisionSnapshot:
        if snapshot.owner.expires_at <= self._clock():
            raise DecisionSnapshotOwnershipError(snapshot.decision_id, "owner binding is expired")
        record = _StoredDecisionSnapshot(
            snapshot=snapshot,
            content_sha256=snapshot.content_sha256,
        )
        with self._ops() as ops:
            try:
                ops.insert_versioned(
                    SHOPPING_DECISION_SNAPSHOTS,
                    self._entity_id(snapshot.decision_id, snapshot.context_version),
                    record,
                    version=snapshot.context_version,
                    owner_id=self._owner_key(snapshot.owner),
                )
            except PersistenceConflictError as exc:
                raise DecisionSnapshotConflictError(
                    snapshot.decision_id,
                    snapshot.context_version,
                ) from exc
        return snapshot

    def get(
        self,
        decision_id: str,
        context_version: int,
    ) -> CanonicalDecisionSnapshot | None:
        with self._ops() as ops:
            loaded = ops.get_versioned(
                SHOPPING_DECISION_SNAPSHOTS,
                self._entity_id(decision_id, context_version),
                _StoredDecisionSnapshot,
            )
        if loaded is None:
            return None
        record, row_version, _ = loaded
        snapshot = record.snapshot
        if (
            snapshot.decision_id != decision_id
            or snapshot.context_version != context_version
            or row_version != context_version
            or record.content_sha256 != snapshot.content_sha256
        ):
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
        now = self._clock()
        if snapshot.owner.expires_at <= now or owner.expires_at <= now:
            return None
        if not snapshot.owner.has_same_identity(owner):
            return None
        return snapshot

    @staticmethod
    def _entity_id(decision_id: str, context_version: int) -> str:
        if not decision_id:
            raise ValueError("decision_id is required")
        if context_version < 1:
            raise ValueError("context_version must be at least 1")
        return f"{decision_id}:{context_version}"

    @staticmethod
    def _owner_key(owner: ConversationOwner) -> str:
        material = "\0".join((owner.principal_type, owner.principal_id, owner.session_id)).encode()
        return f"{owner.principal_type}:{sha256(material).hexdigest()}"

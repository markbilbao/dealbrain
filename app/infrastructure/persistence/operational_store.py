"""Low-level helpers for the operational_entities table."""

from __future__ import annotations

from collections.abc import Callable, Sequence
from typing import Any, TypeVar

from sqlalchemy import Select, delete, func, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.infrastructure.database.models.operational_entity import OperationalEntityModel
from app.infrastructure.persistence.codec import decode_entity, encode_entity
from app.infrastructure.persistence.session import translate_db_error

T = TypeVar("T")


class OperationalStore:
    """Thin JSON-entity repository used by Sprint 17–21 SQLAlchemy adapters."""

    def __init__(self, session: Session) -> None:
        self._session = session

    def upsert(
        self,
        store: str,
        entity_id: str,
        entity: Any,
        *,
        secondary_key: str | None = None,
        owner_id: str | None = None,
    ) -> Any:
        payload = encode_entity(entity)
        existing = self._get_row(store, entity_id)
        try:
            if existing is None:
                next_seq = self._next_seq(store)
                row = OperationalEntityModel(
                    store=store,
                    entity_id=entity_id,
                    secondary_key=secondary_key,
                    owner_id=owner_id,
                    payload=payload,
                    seq=next_seq,
                )
                self._session.add(row)
            else:
                existing.payload = payload
                existing.secondary_key = secondary_key
                existing.owner_id = owner_id
            self._session.flush()
        except IntegrityError as exc:
            raise translate_db_error(exc) from exc
        return entity

    def get(self, store: str, entity_id: str, cls: type[T]) -> T | None:
        row = self._get_row(store, entity_id)
        if row is None:
            return None
        return decode_entity(cls, row.payload)

    def get_by_secondary(self, store: str, secondary_key: str, cls: type[T]) -> T | None:
        row = self._session.scalar(
            select(OperationalEntityModel).where(
                OperationalEntityModel.store == store,
                OperationalEntityModel.secondary_key == secondary_key,
            )
        )
        if row is None:
            return None
        return decode_entity(cls, row.payload)

    def list(
        self,
        store: str,
        cls: type[T],
        *,
        owner_id: str | None = None,
        limit: int | None = None,
        reverse: bool = False,
        predicate: Callable[[T], bool] | None = None,
    ) -> list[T]:
        stmt: Select[Any] = select(OperationalEntityModel).where(
            OperationalEntityModel.store == store
        )
        if owner_id is not None:
            stmt = stmt.where(OperationalEntityModel.owner_id == owner_id)
        ordering = OperationalEntityModel.seq.desc() if reverse else OperationalEntityModel.seq.asc()
        stmt = stmt.order_by(ordering, OperationalEntityModel.id.asc())
        if limit is not None and predicate is None:
            stmt = stmt.limit(max(0, limit))
        rows = self._session.scalars(stmt).all()
        items = [decode_entity(cls, row.payload) for row in rows]
        if predicate is not None:
            items = [item for item in items if predicate(item)]
            if limit is not None:
                items = items[: max(0, limit)]
        return items

    def delete(self, store: str, entity_id: str) -> bool:
        result = self._session.execute(
            delete(OperationalEntityModel).where(
                OperationalEntityModel.store == store,
                OperationalEntityModel.entity_id == entity_id,
            )
        )
        self._session.flush()
        return bool(result.rowcount)

    def clear_store(self, store: str) -> None:
        self._session.execute(
            delete(OperationalEntityModel).where(OperationalEntityModel.store == store)
        )
        self._session.flush()

    def clear_stores(self, stores: Sequence[str]) -> None:
        for store in stores:
            self.clear_store(store)

    def count(self, store: str, *, owner_id: str | None = None) -> int:
        stmt = select(func.count()).select_from(OperationalEntityModel).where(
            OperationalEntityModel.store == store
        )
        if owner_id is not None:
            stmt = stmt.where(OperationalEntityModel.owner_id == owner_id)
        return int(self._session.scalar(stmt) or 0)

    def _get_row(self, store: str, entity_id: str) -> OperationalEntityModel | None:
        return self._session.scalar(
            select(OperationalEntityModel).where(
                OperationalEntityModel.store == store,
                OperationalEntityModel.entity_id == entity_id,
            )
        )

    def _next_seq(self, store: str) -> int:
        """Allocate a per-store insertion-order hint.

        ``seq`` is **not** a uniqueness key. Concurrent writers may observe the
        same ``max(seq)`` and produce duplicate seq values; ``list()`` tie-breaks
        with ``id``. Entity uniqueness is enforced by ``(store, entity_id)`` and
        optional ``(store, secondary_key)``.

        Deferred: a dedicated sequence/advisory-lock allocator would require a
        broader concurrency redesign beyond Sprint 23 acceptance scope.
        """
        current = self._session.scalar(
            select(func.max(OperationalEntityModel.seq)).where(
                OperationalEntityModel.store == store
            )
        )
        return int(current or 0) + 1

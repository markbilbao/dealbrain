"""Canonical Product Registry engine — resolve-or-create identities."""

from __future__ import annotations

from datetime import UTC, datetime
from typing import Any
from uuid import UUID, uuid4

from app.domain.entities.canonical_product import CanonicalProduct
from app.domain.entities.product_relation import ProductRelation, ProductRelationType, RelationDirection
from app.domain.entities.registered_product import (
    CanonicalProductStatus,
    RegisteredCanonicalProduct,
    RegistryResolveResult,
)
from app.domain.exceptions import (
    CanonicalProductNotFoundError,
    InsufficientCanonicalIdentityError,
    InvalidProductRelationError,
)
from app.domain.identity import missing_identity_fields
from app.domain.interfaces.canonical_registry import (
    CanonicalProductRegistry,
    CanonicalProductStore,
)
from app.intelligence.canonical_registry.identity import (
    build_display_name,
    build_identity_key,
)


class CanonicalProductRegistryService(CanonicalProductRegistry):
    """Resolve parsed products to durable UUIDs with relationship support.

    Lookup is deterministic via ``identity_key``. Relationships are stored as
    typed directed edges for accessories, compatibility, successors, and
    alternatives — ready for the knowledge graph without marketplace coupling.
    """

    def __init__(self, store: CanonicalProductStore) -> None:
        self._store = store

    async def resolve(self, parsed: CanonicalProduct) -> RegistryResolveResult:
        missing = missing_identity_fields(parsed)
        if missing:
            raise InsufficientCanonicalIdentityError(missing)

        identity_key = build_identity_key(parsed)
        existing = await self._store.find_by_identity_key(identity_key)
        if existing is not None:
            return RegistryResolveResult(
                product_id=existing.id,
                created=False,
                product=existing,
            )

        now = datetime.now(UTC)
        brand = parsed.brand.strip() if parsed.brand else ""
        family = parsed.family.strip() if parsed.family else ""
        model = parsed.model.strip() if parsed.model else ""
        candidate = RegisteredCanonicalProduct(
            id=uuid4(),
            identity_key=identity_key,
            brand=brand,
            family=family,
            model=model,
            storage=parsed.storage.strip() if parsed.storage else None,
            color=parsed.color.strip() if parsed.color else None,
            display_name=build_display_name(parsed),
            attributes={
                "confidence": parsed.confidence,
                "raw_input": parsed.raw_input,
            },
            status=CanonicalProductStatus.ACTIVE,
            created_at=now,
            updated_at=now,
        )
        created = await self._store.create(candidate)
        return RegistryResolveResult(
            product_id=created.id,
            created=True,
            product=created,
        )

    async def get(self, product_id: UUID) -> RegisteredCanonicalProduct | None:
        return await self._store.get_by_id(product_id)

    async def link(
        self,
        source_id: UUID,
        target_id: UUID,
        relation_type: ProductRelationType,
        *,
        metadata: dict[str, Any] | None = None,
    ) -> ProductRelation:
        if source_id == target_id:
            raise InvalidProductRelationError(
                "Cannot create a relationship from a product to itself"
            )

        source = await self._store.get_by_id(source_id)
        if source is None:
            raise CanonicalProductNotFoundError(source_id)
        target = await self._store.get_by_id(target_id)
        if target is None:
            raise CanonicalProductNotFoundError(target_id)

        existing = await self._store.find_relation(source_id, target_id, relation_type)
        if existing is not None:
            return existing

        relation = ProductRelation(
            id=uuid4(),
            source_id=source_id,
            target_id=target_id,
            relation_type=relation_type,
            metadata=dict(metadata or {}),
            created_at=datetime.now(UTC),
        )
        return await self._store.add_relation(relation)

    async def list_relations(
        self,
        product_id: UUID,
        *,
        relation_type: ProductRelationType | None = None,
        direction: RelationDirection | str = RelationDirection.OUTGOING,
    ) -> list[ProductRelation]:
        if isinstance(direction, str):
            try:
                direction = RelationDirection(direction)
            except ValueError as exc:
                raise InvalidProductRelationError(
                    f"Invalid relation direction: {direction!r}; "
                    f"expected {[d.value for d in RelationDirection]}"
                ) from exc

        product = await self._store.get_by_id(product_id)
        if product is None:
            raise CanonicalProductNotFoundError(product_id)

        if direction == RelationDirection.OUTGOING:
            return await self._store.list_relations(
                source_id=product_id,
                relation_type=relation_type,
            )
        if direction == RelationDirection.INCOMING:
            return await self._store.list_relations(
                target_id=product_id,
                relation_type=relation_type,
            )

        outgoing = await self._store.list_relations(
            source_id=product_id,
            relation_type=relation_type,
        )
        incoming = await self._store.list_relations(
            target_id=product_id,
            relation_type=relation_type,
        )
        # De-dupe by relation id while preserving order.
        seen: set[UUID] = set()
        merged: list[ProductRelation] = []
        for relation in (*outgoing, *incoming):
            if relation.id in seen:
                continue
            seen.add(relation.id)
            merged.append(relation)
        return merged

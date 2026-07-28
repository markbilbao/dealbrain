"""Unit tests for Canonical Product Registry resolve-or-create behavior."""

import pytest
from app.domain.entities.canonical_product import CanonicalProduct
from app.domain.entities.product_relation import ProductRelationType, RelationDirection
from app.domain.exceptions import (
    CanonicalProductNotFoundError,
    InsufficientCanonicalIdentityError,
    InvalidProductRelationError,
)
from app.domain.interfaces.canonical_registry import CanonicalProductRegistry
from app.intelligence import RuleBasedProductParser
from app.intelligence.canonical_registry import (
    CanonicalProductRegistryService,
    InMemoryCanonicalProductStore,
)
from app.intelligence.canonical_registry.identity import build_identity_key


def _parsed(**overrides: object) -> CanonicalProduct:
    defaults: dict[str, object] = {
        "brand": "Apple",
        "family": "iPhone",
        "model": "17 Pro Max",
        "storage": "256GB",
        "color": "Black Titanium",
        "confidence": 0.98,
        "raw_input": "Apple IP17PM 256 BT",
    }
    defaults.update(overrides)
    return CanonicalProduct(**defaults)  # type: ignore[arg-type]


@pytest.fixture
def store() -> InMemoryCanonicalProductStore:
    return InMemoryCanonicalProductStore()


@pytest.fixture
def registry(store: InMemoryCanonicalProductStore) -> CanonicalProductRegistryService:
    return CanonicalProductRegistryService(store)


def test_registry_implements_port(registry: CanonicalProductRegistryService) -> None:
    assert isinstance(registry, CanonicalProductRegistry)


@pytest.mark.asyncio
async def test_resolve_creates_new_canonical_product(
    registry: CanonicalProductRegistryService,
) -> None:
    result = await registry.resolve(_parsed())

    assert result.created is True
    assert result.product_id == result.product.id
    assert result.product.brand == "Apple"
    assert result.product.family == "iPhone"
    assert result.product.model == "17 Pro Max"
    assert result.product.storage == "256GB"
    assert result.product.color == "Black Titanium"
    assert result.product.identity_key == "apple/iphone/17-pro-max/256gb/black-titanium"
    assert result.product.display_name == "Apple iPhone 17 Pro Max 256GB Black Titanium"
    assert result.product.attributes["confidence"] == 0.98


@pytest.mark.asyncio
async def test_resolve_returns_existing_uuid(
    registry: CanonicalProductRegistryService,
) -> None:
    first = await registry.resolve(_parsed())
    second = await registry.resolve(_parsed())

    assert first.created is True
    assert second.created is False
    assert second.product_id == first.product_id
    assert second.product.id == first.product.id


@pytest.mark.asyncio
async def test_resolve_is_idempotent_across_casing(
    registry: CanonicalProductRegistryService,
) -> None:
    first = await registry.resolve(_parsed(brand="Apple"))
    second = await registry.resolve(_parsed(brand="APPLE", family="IPHONE"))

    assert second.product_id == first.product_id
    assert second.created is False


@pytest.mark.asyncio
async def test_different_variants_get_distinct_uuids(
    registry: CanonicalProductRegistryService,
) -> None:
    black = await registry.resolve(_parsed(color="Black Titanium"))
    white = await registry.resolve(_parsed(color="White Titanium"))

    assert black.product_id != white.product_id
    assert black.created is True
    assert white.created is True


@pytest.mark.asyncio
async def test_resolve_rejects_insufficient_identity(
    registry: CanonicalProductRegistryService,
) -> None:
    with pytest.raises(InsufficientCanonicalIdentityError) as exc:
        await registry.resolve(
            CanonicalProduct(brand="Apple", family=None, model=None, confidence=0.1)
        )
    assert set(exc.value.missing_fields) == {"family", "model"}


@pytest.mark.asyncio
async def test_get_by_id(
    registry: CanonicalProductRegistryService,
) -> None:
    created = await registry.resolve(_parsed())
    fetched = await registry.get(created.product_id)
    assert fetched is not None
    assert fetched.id == created.product_id
    assert await registry.get(created.product_id) is not None


@pytest.mark.asyncio
async def test_parser_to_registry_pipeline(
    registry: CanonicalProductRegistryService,
) -> None:
    parsed = RuleBasedProductParser().parse("Apple IP17PM 256 BT")
    result = await registry.resolve(parsed)

    assert result.created is True
    assert result.product.identity_key == build_identity_key(parsed)
    again = await registry.resolve(parsed)
    assert again.created is False
    assert again.product_id == result.product_id


@pytest.mark.asyncio
async def test_link_accessory_compatible_successor_alternative(
    registry: CanonicalProductRegistryService,
) -> None:
    phone = await registry.resolve(_parsed())
    case = await registry.resolve(
        _parsed(
            family="Accessory",
            model="Silicone Case 17 Pro Max",
            storage=None,
            color="Black",
            raw_input="Apple Silicone Case",
        )
    )
    successor = await registry.resolve(
        _parsed(model="18 Pro Max", raw_input="Apple IP18PM 256 BT")
    )
    alt = await registry.resolve(
        _parsed(
            brand="Samsung",
            family="Galaxy",
            model="S25 Ultra",
            storage="256GB",
            color="Titanium Black",
        )
    )

    accessory = await registry.link(
        case.product_id,
        phone.product_id,
        ProductRelationType.ACCESSORY,
        metadata={"role": "protective_case"},
    )
    compatible = await registry.link(
        case.product_id,
        phone.product_id,
        ProductRelationType.COMPATIBLE,
    )
    successor_edge = await registry.link(
        phone.product_id,
        successor.product_id,
        ProductRelationType.SUCCESSOR,
    )
    alternative = await registry.link(
        phone.product_id,
        alt.product_id,
        ProductRelationType.ALTERNATIVE,
        metadata={"reason": "flagship_peer"},
    )

    assert accessory.relation_type == ProductRelationType.ACCESSORY
    assert compatible.relation_type == ProductRelationType.COMPATIBLE
    assert successor_edge.relation_type == ProductRelationType.SUCCESSOR
    assert alternative.relation_type == ProductRelationType.ALTERNATIVE
    assert accessory.metadata["role"] == "protective_case"

    outgoing = await registry.list_relations(
        phone.product_id, direction=RelationDirection.OUTGOING
    )
    types = {edge.relation_type for edge in outgoing}
    assert ProductRelationType.SUCCESSOR in types
    assert ProductRelationType.ALTERNATIVE in types

    incoming = await registry.list_relations(
        phone.product_id,
        relation_type=ProductRelationType.ACCESSORY,
        direction=RelationDirection.INCOMING,
    )
    assert len(incoming) == 1
    assert incoming[0].source_id == case.product_id


@pytest.mark.asyncio
async def test_link_is_idempotent(
    registry: CanonicalProductRegistryService,
) -> None:
    a = await registry.resolve(_parsed())
    b = await registry.resolve(_parsed(color="White Titanium"))

    first = await registry.link(a.product_id, b.product_id, ProductRelationType.ALTERNATIVE)
    second = await registry.link(a.product_id, b.product_id, ProductRelationType.ALTERNATIVE)

    assert first.id == second.id


@pytest.mark.asyncio
async def test_link_rejects_self_reference(
    registry: CanonicalProductRegistryService,
) -> None:
    product = await registry.resolve(_parsed())
    with pytest.raises(InvalidProductRelationError):
        await registry.link(
            product.product_id,
            product.product_id,
            ProductRelationType.ALTERNATIVE,
        )


@pytest.mark.asyncio
async def test_link_rejects_missing_endpoints(
    registry: CanonicalProductRegistryService,
) -> None:
    product = await registry.resolve(_parsed())
    from uuid import uuid4

    missing = uuid4()
    with pytest.raises(CanonicalProductNotFoundError):
        await registry.link(product.product_id, missing, ProductRelationType.COMPATIBLE)


@pytest.mark.asyncio
async def test_list_relations_both_and_invalid_direction(
    registry: CanonicalProductRegistryService,
) -> None:
    phone = await registry.resolve(_parsed())
    case = await registry.resolve(
        _parsed(family="Accessory", model="Case", storage=None, color="Black")
    )
    await registry.link(case.product_id, phone.product_id, ProductRelationType.ACCESSORY)
    await registry.link(
        phone.product_id,
        case.product_id,
        ProductRelationType.COMPATIBLE,
    )

    both = await registry.list_relations(phone.product_id, direction=RelationDirection.BOTH)
    assert len(both) == 2

    with pytest.raises(InvalidProductRelationError):
        await registry.list_relations(phone.product_id, direction="sideways")


@pytest.mark.asyncio
async def test_in_memory_create_is_idempotent_on_same_key(
    store: InMemoryCanonicalProductStore,
    registry: CanonicalProductRegistryService,
) -> None:
    first = await registry.resolve(_parsed())
    # Simulate a duplicate create attempt with a new UUID but same key.
    from dataclasses import replace
    from uuid import uuid4

    duplicate = replace(first.product, id=uuid4())
    stored = await store.create(duplicate)
    assert stored.id == first.product_id

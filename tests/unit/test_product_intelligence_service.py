"""Unit tests for ProductIntelligenceService orchestration."""

from uuid import uuid4

import pytest
from app.domain.entities.canonical_product import CanonicalProduct, ParseSignal
from app.domain.entities.registered_product import (
    CanonicalProductStatus,
    RegisteredCanonicalProduct,
    RegistryResolveResult,
)
from app.domain.exceptions import InsufficientCanonicalIdentityError, UnsupportedProductError
from app.domain.interfaces.canonical_registry import CanonicalProductRegistry
from app.domain.interfaces.product_intelligence import ProductIntelligenceEngine
from app.intelligence.canonical_registry import (
    CanonicalProductRegistryService,
    InMemoryCanonicalProductStore,
)
from app.intelligence.product_matcher import ExactVariantProductMatcher
from app.intelligence.product_parser import RuleBasedProductParser
from app.services.product_intelligence_service import ProductIntelligenceService


class StubParser(ProductIntelligenceEngine):
    def __init__(self, parsed: CanonicalProduct) -> None:
        self._parsed = parsed

    @property
    def engine_name(self) -> str:
        return "stub"

    def parse(self, raw_name: str) -> CanonicalProduct:
        return self._parsed


class StubRegistry(CanonicalProductRegistry):
    def __init__(
        self,
        result: RegistryResolveResult | None = None,
        *,
        missing: list[str] | None = None,
    ) -> None:
        self._result = result
        self._missing = missing
        self.calls: list[CanonicalProduct] = []

    async def resolve(self, parsed: CanonicalProduct) -> RegistryResolveResult:
        self.calls.append(parsed)
        if self._missing is not None:
            raise InsufficientCanonicalIdentityError(self._missing)
        assert self._result is not None
        return self._result

    async def get(self, product_id):  # noqa: ANN001
        return None

    async def link(self, *args, **kwargs):  # noqa: ANN001, ANN003
        raise NotImplementedError

    async def list_relations(self, *args, **kwargs):  # noqa: ANN001, ANN003
        return []


def _registered(**overrides: object) -> RegisteredCanonicalProduct:
    defaults = {
        "id": uuid4(),
        "identity_key": "apple/iphone/17-pro-max/256gb/black-titanium",
        "brand": "Apple",
        "family": "iPhone",
        "model": "17 Pro Max",
        "storage": "256GB",
        "color": "Black Titanium",
        "display_name": "Apple iPhone 17 Pro Max 256GB Black Titanium",
        "attributes": {},
        "status": CanonicalProductStatus.ACTIVE,
    }
    defaults.update(overrides)
    return RegisteredCanonicalProduct(**defaults)  # type: ignore[arg-type]


def _service(parser, registry) -> ProductIntelligenceService:  # noqa: ANN001
    return ProductIntelligenceService(parser, registry, ExactVariantProductMatcher())


@pytest.mark.asyncio
async def test_parse_listing_maps_parser_and_registry() -> None:
    product_id = uuid4()
    parsed = CanonicalProduct(
        brand="Apple",
        family="iPhone",
        model="17 Pro Max",
        storage="256GB",
        color="Black Titanium",
        confidence=0.98,
        raw_input="Apple IP17PM 256 BT",
        signals=(
            ParseSignal("brand", "Apple", "brand.alias", 1.0, "Apple"),
            ParseSignal("family", "iPhone", "family_model.apple", 1.0, "IP17PM"),
        ),
    )
    registry = StubRegistry(
        RegistryResolveResult(
            product_id=product_id,
            created=True,
            product=_registered(id=product_id),
        )
    )
    service = _service(StubParser(parsed), registry)

    result = await service.parse_listing("  Apple IP17PM 256 BT  ")

    assert result.original_title == "Apple IP17PM 256 BT"
    assert result.product.id == product_id
    assert result.product.brand == "Apple"
    assert result.confidence == 0.98
    assert result.is_new_product is True
    assert result.signals[0].attribute == "brand"
    assert result.signals[0].source_span == "Apple"
    assert result.signals[1].attribute == "family"
    assert result.signals[1].source_span == "IP17PM"
    assert len(registry.calls) == 1


@pytest.mark.asyncio
async def test_parse_listing_rejects_blank_title() -> None:
    service = _service(StubParser(CanonicalProduct()), StubRegistry(missing=["brand"]))
    with pytest.raises(UnsupportedProductError):
        await service.parse_listing("   ")


@pytest.mark.asyncio
async def test_parse_listing_rejects_unsupported_product() -> None:
    parsed = CanonicalProduct(brand="Samsung", confidence=0.25)
    service = _service(StubParser(parsed), StubRegistry(missing=["family", "model"]))
    with pytest.raises(UnsupportedProductError) as exc:
        await service.parse_listing("Samsung mystery device")
    assert "family" in exc.value.reason
    assert "model" in exc.value.reason


@pytest.mark.asyncio
async def test_end_to_end_with_real_parser_and_memory_registry() -> None:
    store = InMemoryCanonicalProductStore()
    parser = RuleBasedProductParser()
    service = ProductIntelligenceService(
        parser,
        CanonicalProductRegistryService(store),
        ExactVariantProductMatcher(),
    )

    first = await service.parse_listing("Apple IP17PM 256 BT")
    second = await service.parse_listing("Apple IP17PM 256 BT")

    assert first.is_new_product is True
    assert second.is_new_product is False
    assert first.product.id == second.product.id
    assert first.confidence == 0.98
    assert {signal.attribute for signal in first.signals} >= {
        "brand",
        "family",
        "model",
        "storage",
        "color",
    }


@pytest.mark.asyncio
async def test_match_listings_uses_parser_then_matcher() -> None:
    parser = RuleBasedProductParser()
    service = ProductIntelligenceService(
        parser,
        CanonicalProductRegistryService(InMemoryCanonicalProductStore()),
        ExactVariantProductMatcher(),
    )
    result = service.match_listings(
        "Apple iPhone 17 Pro Max 256GB Black Titanium",
        "Apple IP17PM 256 BT",
    )
    assert result.is_match is True
    assert result.confidence >= 0.95

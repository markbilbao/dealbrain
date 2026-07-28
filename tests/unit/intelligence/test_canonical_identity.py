"""Unit tests for canonical identity key generation."""

import pytest
from app.domain.entities.canonical_product import CanonicalProduct
from app.domain.exceptions import InsufficientCanonicalIdentityError
from app.intelligence.canonical_registry.identity import (
    build_display_name,
    build_identity_hash,
    build_identity_key,
    normalize_identity_part,
    slugify,
)
from app.domain.identity import missing_identity_fields


def _parsed(**overrides: object) -> CanonicalProduct:
    defaults: dict[str, object] = {
        "brand": "Apple",
        "family": "iPhone",
        "model": "17 Pro Max",
        "storage": "256GB",
        "color": "Black Titanium",
        "confidence": 0.98,
    }
    defaults.update(overrides)
    return CanonicalProduct(**defaults)  # type: ignore[arg-type]


def test_normalize_and_slugify() -> None:
    assert normalize_identity_part("  Black   Titanium ") == "black titanium"
    assert slugify("black titanium") == "black-titanium"
    assert slugify("") == "_"


def test_build_identity_key_golden() -> None:
    key = build_identity_key(_parsed())
    assert key == "apple/iphone/17-pro-max/256gb/black-titanium"


def test_identity_key_is_case_and_whitespace_insensitive() -> None:
    a = build_identity_key(_parsed(brand="APPLE", family=" iPhone "))
    b = build_identity_key(_parsed(brand="apple", family="iphone"))
    assert a == b


def test_missing_optional_dimensions_use_sentinel() -> None:
    key = build_identity_key(_parsed(storage=None, color=None))
    assert key == "apple/iphone/17-pro-max/_/_"


def test_variants_produce_distinct_keys() -> None:
    black = build_identity_key(_parsed(color="Black Titanium"))
    white = build_identity_key(_parsed(color="White Titanium"))
    assert black != white


def test_missing_required_fields() -> None:
    parsed = CanonicalProduct(brand="Apple", family=None, model="17")
    assert missing_identity_fields(parsed) == ["family"]
    with pytest.raises(InsufficientCanonicalIdentityError) as exc:
        build_identity_key(parsed)
    assert exc.value.missing_fields == ["family"]


def test_display_name() -> None:
    assert (
        build_display_name(_parsed())
        == "Apple iPhone 17 Pro Max 256GB Black Titanium"
    )


def test_identity_hash_is_stable() -> None:
    key = build_identity_key(_parsed())
    assert build_identity_hash(key) == build_identity_hash(key)
    assert len(build_identity_hash(key)) == 64

"""Sprint 20 unit tests — merchant registry & management."""

from __future__ import annotations

from datetime import UTC, datetime

import pytest
from app.affiliate.memory import InMemoryAffiliateRepository
from app.domain.exceptions import AffiliateMerchantNotFoundError, AffiliateValidationError
from app.services.affiliate_merchant_service import AffiliateMerchantService

FIXED_NOW = datetime(2026, 7, 29, 12, 0, tzinfo=UTC)


def _service(seed: bool = True) -> tuple[AffiliateMerchantService, InMemoryAffiliateRepository]:
    repo = InMemoryAffiliateRepository(seed=seed)
    if not seed:
        repo.clear()
    counter = {"n": 0}

    def next_id() -> str:
        counter["n"] += 1
        return f"{counter['n']}"

    return (
        AffiliateMerchantService(repo, clock=lambda: FIXED_NOW, id_factory=next_id),
        repo,
    )


def test_placeholder_merchants_seeded() -> None:
    service, _ = _service(seed=True)
    merchants = service.list_merchants()
    names = {m.merchant_name for m in merchants}
    assert {"Amazon", "Shopee", "Lazada", "TikTok Shop", "eBay", "AliExpress"} <= names


def test_activate_deactivate_merchant() -> None:
    service, _ = _service()
    merchant = service.deactivate_merchant("merchant-shopee-ph")
    assert merchant.status.value == "inactive"
    merchant = service.activate_merchant("merchant-shopee-ph")
    assert merchant.status.value == "active"


def test_update_commission_and_priority() -> None:
    service, _ = _service()
    merchant = service.update_commission(
        "merchant-amazon-us", commission_type="percent", commission_value=5.25
    )
    assert merchant.commission_value == 5.25
    merchant = service.set_priority("merchant-amazon-us", 1)
    assert merchant.priority == 1


def test_country_restrictions_and_health() -> None:
    service, _ = _service()
    merchant = service.set_country_restrictions("merchant-ebay-us", ["US", "CA"])
    assert merchant.allowed_countries == ("US", "CA")
    merchant = service.set_health_status("merchant-ebay-us", "degraded")
    assert merchant.health_status.value == "degraded"


def test_resolve_for_marketplace_prefers_active_priority() -> None:
    service, _ = _service()
    resolved = service.resolve_for_marketplace("Shopee", country="PH")
    assert resolved is not None
    assert resolved.merchant_id == "merchant-shopee-ph"


def test_inactive_aliexpress_not_resolved_when_inactive() -> None:
    service, _ = _service()
    resolved = service.resolve_for_marketplace("aliexpress")
    assert resolved is None


def test_create_merchant_validation() -> None:
    service, _ = _service(seed=False)
    with pytest.raises(AffiliateValidationError):
        service.create_merchant(
            merchant_name="",
            marketplace="shopee",
            country="PH",
            affiliate_network="shopee_affiliate",
            tracking_template="https://example.com/{product_ref}",
        )


def test_get_missing_merchant() -> None:
    service, _ = _service(seed=False)
    with pytest.raises(AffiliateMerchantNotFoundError):
        service.get_merchant("missing")

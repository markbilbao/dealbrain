"""Sprint 21 compatibility with Sprints 17–20 and regression smoke checks."""

from __future__ import annotations

from app.affiliate.memory import InMemoryAffiliateRepository
from app.main import create_app
from app.marketplace.matching.matcher import CatalogEntry, MarketplaceProductMatcher
from app.merchant.matching import MerchantProductMatcher
from app.merchant.memory import InMemoryMerchantRepository
from app.services.affiliate_merchant_service import AffiliateMerchantService
from app.services.merchant_auth_service import MerchantAuthService
from fastapi.testclient import TestClient


def test_sprint18_matcher_reuse() -> None:
    catalog = [
        CatalogEntry(
            product_id="prod-a",
            brand="Acme",
            model="A1",
            title="Acme A1 Widget",
            upc="111",
        )
    ]
    market = MarketplaceProductMatcher(catalog)
    merchant = MerchantProductMatcher(catalog)
    m1 = market.match(brand="Acme", model="A1", title="Acme A1 Widget", upc="111")
    m2 = merchant.match(brand="Acme", model="A1", title="Acme A1 Widget", upc="111")
    assert m1.matched_product_id == m2.matched_product_id == "prod-a"


def test_sprint20_affiliate_registry_still_works() -> None:
    repo = InMemoryAffiliateRepository(seed=True)
    service = AffiliateMerchantService(repo)
    merchants = service.list_merchants(active_only=True)
    assert any(m.merchant_id == "merchant-amazon-us" for m in merchants)


def test_sprint21_links_to_affiliate_merchant_ids() -> None:
    repo = InMemoryMerchantRepository(seed=True)
    org = repo.get_organization("org-techhaven")
    assert org is not None
    assert org.affiliate_merchant_id == "merchant-amazon-us"
    affiliate = InMemoryAffiliateRepository(seed=True)
    assert affiliate.get_merchant("merchant-amazon-us") is not None


def test_sprint17_user_platform_auth_still_available() -> None:
    client = TestClient(create_app())
    r = client.get("/api/v1/auth/demo")
    assert r.status_code == 200


def test_sprint19_watchlists_route_still_present() -> None:
    client = TestClient(create_app())
    # Unauthenticated list may 401 depending on flag; route must exist (not 404).
    r = client.get("/api/v1/watchlists")
    assert r.status_code != 404


def test_sprint20_affiliate_report_still_works() -> None:
    client = TestClient(create_app())
    r = client.get("/api/v1/affiliate/report")
    assert r.status_code == 200


def test_merchant_auth_resolves_demo_tokens() -> None:
    repo = InMemoryMerchantRepository(seed=True)
    auth = MerchantAuthService(repo, repo)
    actor = auth.resolve_actor("demo-token-internal-admin", organization_id="org-techhaven")
    assert actor.is_internal_admin

"""Unit tests for mocked marketplace connectors."""

from app.domain.entities.marketplace_listing import AvailabilityStatus
from app.intelligence.marketplace.lazada import LazadaConnector
from app.intelligence.marketplace.shopee import ShopeeConnector


def test_shopee_search_normalizes_listings() -> None:
    connector = ShopeeConnector()
    results = connector.search("iPhone 17 Pro Max")

    assert len(results) == 1
    listing = results[0]
    assert listing.marketplace == "shopee"
    assert listing.product_id == "1001001"
    assert listing.price == 74_999.0
    assert listing.currency == "PHP"
    assert listing.seller == "Apple Authorized PH"
    assert listing.rating == 4.9
    assert "shopee.ph" in listing.url
    assert listing.availability is AvailabilityStatus.IN_STOCK


def test_shopee_get_product_price_and_availability() -> None:
    connector = ShopeeConnector()

    listing = connector.get_product("1001003")
    assert listing is not None
    assert listing.title == "Apple AirPods Pro 2 USB-C"
    assert connector.get_price("1001003") == listing.price
    assert connector.get_availability("1001003") is AvailabilityStatus.LIMITED
    assert connector.get_availability("1001004") is AvailabilityStatus.OUT_OF_STOCK
    assert connector.get_product("missing") is None
    assert connector.get_price("missing") is None
    assert connector.get_availability("missing") is AvailabilityStatus.UNKNOWN


def test_lazada_search_and_normalize() -> None:
    connector = LazadaConnector()
    results = connector.search("AirPods")

    assert len(results) == 1
    listing = results[0]
    assert listing.marketplace == "lazada"
    assert listing.product_id == "2002003"
    assert listing.price == 12_490.0
    assert listing.availability is AvailabilityStatus.LIMITED
    assert listing.url.endswith("i2002003.html")


def test_lazada_get_product_out_of_stock() -> None:
    connector = LazadaConnector()
    listing = connector.get_product("2002004")

    assert listing is not None
    assert connector.get_availability("2002004") is AvailabilityStatus.OUT_OF_STOCK
    assert connector.get_price("2002004") == 63_990.0


def test_blank_query_returns_empty() -> None:
    assert ShopeeConnector().search("   ") == []
    assert LazadaConnector().search("") == []

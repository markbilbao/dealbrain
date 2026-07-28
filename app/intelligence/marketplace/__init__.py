"""Marketplace Intelligence — pluggable marketplace connectors.

Sprint 4 scaffolding: mock Shopee and Lazada adapters with a shared
:class:`~app.domain.interfaces.marketplace_connector.MarketplaceConnector`
port. Future connectors (Amazon, eBay, Facebook Marketplace, Carousell)
implement the same interface.
"""

from app.intelligence.marketplace.lazada import LazadaConnector
from app.intelligence.marketplace.shopee import ShopeeConnector

__all__ = [
    "LazadaConnector",
    "ShopeeConnector",
]

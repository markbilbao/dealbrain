"""Merchant Platform bounded context — Sprint 21.

Merchant tools never manipulate organic DealScore or recommendation ranking.
Sponsored campaigns are labeled and rendered separately from organic results.
"""

from app.merchant.memory import InMemoryMerchantRepository

__all__ = ["InMemoryMerchantRepository"]

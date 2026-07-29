"""Affiliate Revenue Engine package — Sprint 20.

Bounded context for merchant registry, affiliate link generation, click
tracking, attribution, disclosure, and demo revenue reporting.

Affiliate data is applied **after** recommendation selection only.
DealScore and ranking engines must never receive commission inputs.
"""

from app.affiliate.memory import InMemoryAffiliateRepository

__all__ = ["InMemoryAffiliateRepository"]

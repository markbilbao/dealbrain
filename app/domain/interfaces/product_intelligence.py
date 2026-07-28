"""Product Intelligence Engine — parse messy listing titles.

Responsibility: deterministic tokenization and rule-based attribute extraction.
Does not register products or perform matching.
"""

from abc import ABC, abstractmethod

from app.domain.entities.canonical_product import CanonicalProduct


class ProductIntelligenceEngine(ABC):
    """Abstract contract for deterministic product-name intelligence.

    Implementations must be replaceable and must not depend on LLMs.
    """

    @property
    @abstractmethod
    def engine_name(self) -> str:
        """Human-readable engine identifier."""

    @abstractmethod
    def parse(self, raw_name: str) -> CanonicalProduct:
        """Parse a messy product name into a structured canonical product."""

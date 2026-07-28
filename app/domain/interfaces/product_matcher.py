"""Product Matcher port — compare two parsed canonical products.

The matcher depends only on :class:`CanonicalProduct` outputs from the parser.
Title parsing belongs in the application service, not on this port.
"""

from abc import ABC, abstractmethod

from app.domain.entities.canonical_product import CanonicalProduct
from app.domain.entities.product_match import ProductMatchResult


class ProductMatcher(ABC):
    """Abstract contract for deterministic product matching.

    Implementations must be replaceable and must not depend on LLMs.
    """

    @property
    @abstractmethod
    def matcher_name(self) -> str:
        """Human-readable matcher identifier."""

    @abstractmethod
    def match_products(
        self,
        product_a: CanonicalProduct,
        product_b: CanonicalProduct,
    ) -> ProductMatchResult:
        """Compare two already-parsed canonical products."""

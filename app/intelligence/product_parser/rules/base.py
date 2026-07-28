"""Base contract for product-parser rules."""

from __future__ import annotations

from abc import ABC, abstractmethod

from app.intelligence.product_parser.context import ParseContext


class ParseRule(ABC):
    """A replaceable extraction rule applied to a :class:`ParseContext`.

    Rules must be deterministic and side-effect free beyond mutating context.
    """

    @property
    @abstractmethod
    def rule_id(self) -> str:
        """Stable identifier used in parse signals."""

    @property
    def priority(self) -> int:
        """Lower runs first. Override to reorder relative to other rules."""
        return 100

    @abstractmethod
    def apply(self, context: ParseContext) -> None:
        """Extract attributes from available tokens and update context."""

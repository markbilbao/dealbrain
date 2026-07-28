"""Storage capacity extraction rule."""

from __future__ import annotations

from app.intelligence.product_parser.catalogs.storage import normalize_storage
from app.intelligence.product_parser.context import ParseContext
from app.intelligence.product_parser.rules.base import ParseRule


class StorageRule(ParseRule):
    """Match storage capacities such as ``256``, ``256GB``, ``1TB``."""

    @property
    def rule_id(self) -> str:
        return "storage.capacity"

    @property
    def priority(self) -> int:
        return 30

    def apply(self, context: ParseContext) -> None:
        if context.storage is not None:
            return

        for token in context.available_tokens():
            canonical = normalize_storage(token.normalized)
            if canonical is None:
                continue

            # Bare numbers are weaker signals than explicit units.
            weight = 0.9 if token.normalized.isdigit() else 1.0
            if context.set_storage(
                canonical,
                rule_id=self.rule_id,
                weight=weight,
                source=token.raw,
            ):
                context.consume(token.index)
                return

"""Screen size extraction rule."""

from __future__ import annotations

from app.intelligence.product_parser.catalogs.screen_sizes import normalize_screen_size
from app.intelligence.product_parser.context import ParseContext
from app.intelligence.product_parser.rules.base import ParseRule


class ScreenSizeRule(ParseRule):
    """Match screen sizes such as ``13-inch`` or ``14"``."""

    @property
    def rule_id(self) -> str:
        return "screen_size.normalize"

    @property
    def priority(self) -> int:
        return 45

    def apply(self, context: ParseContext) -> None:
        if context.screen_size is not None:
            return

        for token in context.available_tokens():
            canonical = normalize_screen_size(token.normalized)
            if canonical is None:
                canonical = normalize_screen_size(token.raw)
            if canonical is None:
                continue
            if context.set_screen_size(
                canonical,
                rule_id=self.rule_id,
                weight=1.0,
                source=token.raw,
            ):
                context.consume(token.index)
                return

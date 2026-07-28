"""Brand extraction rule."""

from __future__ import annotations

from app.intelligence.product_parser.catalogs.brands import BRAND_ALIASES
from app.intelligence.product_parser.context import ParseContext
from app.intelligence.product_parser.rules.alias_window import match_alias_window
from app.intelligence.product_parser.rules.base import ParseRule
from app.intelligence.product_parser.tokenizer import Token


class BrandRule(ParseRule):
    """Match brand aliases against single- and multi-token windows."""

    def __init__(self, aliases: dict[str, str] | None = None) -> None:
        self._aliases = aliases if aliases is not None else BRAND_ALIASES

    @property
    def rule_id(self) -> str:
        return "brand.alias"

    @property
    def priority(self) -> int:
        return 10

    def apply(self, context: ParseContext) -> None:
        if context.brand is not None:
            return

        def _apply(canonical: str, source: str, window: tuple[Token, ...]) -> bool:
            if context.set_brand(
                canonical,
                rule_id=self.rule_id,
                weight=1.0,
                source=source,
            ):
                context.consume(*(token.index for token in window))
                return True
            return False

        match_alias_window(context, self._aliases, max_window=3, apply=_apply)

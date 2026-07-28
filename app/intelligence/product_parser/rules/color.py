"""Color extraction rule."""

from __future__ import annotations

from app.intelligence.product_parser.catalogs.colors import COLOR_ALIASES
from app.intelligence.product_parser.context import ParseContext
from app.intelligence.product_parser.rules.alias_window import match_alias_window
from app.intelligence.product_parser.rules.base import ParseRule
from app.intelligence.product_parser.tokenizer import Token


class ColorRule(ParseRule):
    """Match color codes and multi-word color names."""

    def __init__(self, aliases: dict[str, str] | None = None) -> None:
        self._aliases = aliases if aliases is not None else COLOR_ALIASES

    @property
    def rule_id(self) -> str:
        return "color.alias"

    @property
    def priority(self) -> int:
        return 40

    def apply(self, context: ParseContext) -> None:
        if context.color is not None:
            return

        def _apply(canonical: str, source: str, window: tuple[Token, ...]) -> bool:
            phrase = " ".join(token.normalized for token in window)
            weight = 1.0 if len(phrase) > 2 or len(window) > 1 else 0.95
            if len(phrase) <= 3 and len(window) == 1:
                weight = 0.98
            if context.set_color(
                canonical,
                rule_id=self.rule_id,
                weight=weight,
                source=source,
            ):
                context.consume(*(token.index for token in window))
                return True
            return False

        match_alias_window(context, self._aliases, max_window=3, apply=_apply)

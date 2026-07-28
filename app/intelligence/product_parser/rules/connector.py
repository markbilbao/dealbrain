"""Connector extraction rule (USB-C, Lightning, etc.)."""

from __future__ import annotations

from app.intelligence.product_parser.catalogs.connectors import CONNECTOR_ALIASES
from app.intelligence.product_parser.context import ParseContext
from app.intelligence.product_parser.rules.alias_window import match_alias_window
from app.intelligence.product_parser.rules.base import ParseRule
from app.intelligence.product_parser.tokenizer import Token


class ConnectorRule(ParseRule):
    """Match connector aliases such as ``USB-C`` / ``Type C``."""

    def __init__(self, aliases: dict[str, str] | None = None) -> None:
        self._aliases = aliases if aliases is not None else CONNECTOR_ALIASES

    @property
    def rule_id(self) -> str:
        return "connector.alias"

    @property
    def priority(self) -> int:
        return 35

    def apply(self, context: ParseContext) -> None:
        if context.connector is not None:
            return

        def _apply(canonical: str, source: str, window: tuple[Token, ...]) -> bool:
            if context.set_connector(
                canonical,
                rule_id=self.rule_id,
                weight=1.0,
                source=source,
            ):
                context.consume(*(token.index for token in window))
                return True
            return False

        match_alias_window(
            context,
            self._aliases,
            max_window=2,
            apply=_apply,
            compact_lookup=True,
        )

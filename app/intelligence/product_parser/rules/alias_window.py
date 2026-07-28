"""Shared multi-token alias window matching for catalog-backed rules."""

from __future__ import annotations

from collections.abc import Callable

from app.intelligence.product_parser.context import ParseContext
from app.intelligence.product_parser.tokenizer import Token


def match_alias_window(
    context: ParseContext,
    aliases: dict[str, str],
    *,
    max_window: int,
    apply: Callable[[str, str, tuple[Token, ...]], bool],
    compact_lookup: bool = False,
) -> bool:
    """Scan available tokens for the longest matching alias phrase.

    ``apply(canonical, source, window)`` should set the attribute and return
    True when the match is consumed.
    """
    available = context.available_tokens()
    if not available:
        return False

    window_limit = min(max_window, len(available))
    for window_size in range(window_limit, 0, -1):
        for start in range(0, len(available) - window_size + 1):
            window = tuple(available[start : start + window_size])
            phrase = " ".join(token.normalized for token in window)
            canonical = aliases.get(phrase)
            if canonical is None and compact_lookup:
                compact = phrase.replace(" ", "").replace("-", "")
                canonical = aliases.get(compact)
            if canonical is None:
                continue
            source = " ".join(token.raw for token in window)
            if apply(canonical, source, window):
                return True
    return False

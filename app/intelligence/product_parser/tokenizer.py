"""Tokenization and normalization for product title parsing."""

from __future__ import annotations

import re
from dataclasses import dataclass


_WHITESPACE_RE = re.compile(r"\s+")
# Keep alphanumeric; treat common separators as token boundaries.
_SPLIT_RE = re.compile(r"[\s,/|]+")
# Strip wrapping punctuation from individual tokens but keep internal structure
# for compound codes like IP17PM and 256GB.
_EDGE_PUNCT_RE = re.compile(r"^[^A-Za-z0-9+]+|[^A-Za-z0-9+]+$")


@dataclass(frozen=True, slots=True)
class Token:
    """A normalized token with its original surface form and position."""

    index: int
    raw: str
    normalized: str


def normalize_text(text: str) -> str:
    """Collapse whitespace and strip outer whitespace."""
    return _WHITESPACE_RE.sub(" ", text.strip())


def tokenize(raw_name: str) -> list[Token]:
    """Split a product name into ordered normalized tokens.

    Compound codes (``IP17PM``, ``256GB``) stay intact as single tokens so
    catalog rules can match them deterministically.
    """
    normalized = normalize_text(raw_name)
    if not normalized:
        return []

    parts = [p for p in _SPLIT_RE.split(normalized) if p]
    tokens: list[Token] = []
    for index, part in enumerate(parts):
        cleaned = _EDGE_PUNCT_RE.sub("", part)
        if not cleaned:
            continue
        tokens.append(
            Token(
                index=len(tokens),
                raw=cleaned,
                normalized=cleaned.lower(),
            )
        )
    return tokens

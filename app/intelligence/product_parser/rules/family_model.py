"""Family and model extraction for Apple-style compound codes and phrases."""

from __future__ import annotations

import re

from app.intelligence.product_parser.catalogs.apple import (
    FAMILY_ALIASES,
    FAMILY_REFINEMENTS,
    is_apple_chip,
    match_apple_compound,
    resolve_tier,
)
from app.intelligence.product_parser.context import ParseContext
from app.intelligence.product_parser.rules.base import ParseRule
from app.intelligence.product_parser.tokenizer import Token

_GENERATION_RE = re.compile(r"^\d{1,2}$")
_FAMILY_PREFIXES = ("iphone", "ipad", "airpods", "iph", "ip", "app")


class FamilyModelRule(ParseRule):
    """Extract product family and model from compound codes and token spans.

    Handles forms such as:
    - ``IP17PM`` → family=iPhone, model=17 Pro Max
    - ``iPhone 17 Pro Max`` → same via multi-token assembly
    - ``APP2`` → family=AirPods, model=Pro 2
    - ``MacBook Air M5`` → family=MacBook Air, model=M5
    """

    @property
    def rule_id(self) -> str:
        return "family_model.apple"

    @property
    def priority(self) -> int:
        return 20

    def apply(self, context: ParseContext) -> None:
        if context.family is not None and context.model is not None:
            return

        if self._apply_compound(context):
            return

        self._apply_spaced(context)

    def _apply_compound(self, context: ParseContext) -> bool:
        for token in context.available_tokens():
            matched = match_apple_compound(token.normalized)
            if matched is None:
                continue

            if not self._has_family_prefix(token.normalized) and not self._apple_context_ok(
                context
            ):
                continue

            if context.family is None:
                context.set_family(
                    matched.family,
                    rule_id=self.rule_id,
                    weight=1.0,
                    source=token.raw,
                )
            if context.model is None:
                context.set_model(
                    matched.model,
                    rule_id=self.rule_id,
                    weight=1.0,
                    source=token.raw,
                )
            if matched.connector and context.connector is None:
                context.set_connector(
                    matched.connector,
                    rule_id=self.rule_id,
                    weight=0.95,
                    source=token.raw,
                )
            context.consume(token.index)
            return True
        return False

    @staticmethod
    def _has_family_prefix(normalized: str) -> bool:
        return any(normalized.startswith(prefix) for prefix in _FAMILY_PREFIXES)

    @staticmethod
    def _apple_context_ok(context: ParseContext) -> bool:
        if context.brand == "Apple":
            return True
        return context.family in {
            "iPhone",
            "iPad",
            "Apple Watch",
            "AirPods",
            "MacBook",
            "MacBook Air",
            "MacBook Pro",
        }

    def _apply_spaced(self, context: ParseContext) -> None:
        available = context.available_tokens()
        if not available:
            return

        family_token: Token | None = None
        family_value = context.family
        refine_token: Token | None = None

        for i, token in enumerate(available):
            alias = FAMILY_ALIASES.get(token.normalized)
            if alias is None:
                continue
            family_token = token
            family_value = alias
            # Refine MacBook + Air/Pro into MacBook Air / MacBook Pro.
            if i + 1 < len(available):
                nxt = available[i + 1]
                refined = FAMILY_REFINEMENTS.get((token.normalized, nxt.normalized))
                if refined is not None:
                    family_value = refined
                    refine_token = nxt
            break

        if family_value is None:
            return

        search_from = 0
        if family_token is not None:
            for i, token in enumerate(available):
                if token.index == family_token.index:
                    search_from = i + 1
                    break
            if refine_token is not None:
                search_from += 1

        model, used_indices = self._extract_model_span(
            available,
            search_from,
            family_value=family_value,
        )

        if family_token is not None and context.family is None:
            source = family_token.raw
            if refine_token is not None:
                source = f"{family_token.raw} {refine_token.raw}"
            context.set_family(
                family_value,
                rule_id=self.rule_id,
                weight=0.95,
                source=source,
            )
            context.consume(family_token.index)
            if refine_token is not None:
                context.consume(refine_token.index)

        if model is not None and context.model is None:
            source_tokens = [t.raw for t in available if t.index in used_indices]
            context.set_model(
                model,
                rule_id=self.rule_id,
                weight=0.95,
                source=" ".join(source_tokens),
            )
            context.consume(*used_indices)

    def _extract_model_span(
        self,
        available: list[Token],
        search_from: int,
        *,
        family_value: str,
    ) -> tuple[str | None, list[int]]:
        if search_from >= len(available):
            return None, []

        # AirPods: "Pro 2" (tier then generation)
        if family_value == "AirPods":
            return self._extract_airpods_model(available, search_from)

        # MacBook lines: chip model like M5
        if family_value.startswith("MacBook"):
            token = available[search_from]
            if is_apple_chip(token.normalized):
                chip = token.normalized.upper()
                return chip, [token.index]

        generation: str | None = None
        tier: str | None = None
        used: list[int] = []

        i = search_from
        token = available[i]
        if not _GENERATION_RE.fullmatch(token.normalized):
            # Chip-style model without MacBook family prefix already handled.
            if is_apple_chip(token.normalized):
                chip = "M" + token.normalized[1:]
                return chip, [token.index]
            return None, []

        generation = token.normalized
        used.append(token.index)
        i += 1

        if i >= len(available):
            return generation, used

        token = available[i]
        if (
            token.normalized == "pro"
            and i + 1 < len(available)
            and available[i + 1].normalized == "max"
        ):
            tier = "Pro Max"
            used.extend([token.index, available[i + 1].index])
            return f"{generation} {tier}", used

        resolved = resolve_tier(token.normalized)
        if resolved is not None:
            tier = resolved
            used.append(token.index)
            return f"{generation} {tier}", used

        return generation, used

    def _extract_airpods_model(
        self,
        available: list[Token],
        search_from: int,
    ) -> tuple[str | None, list[int]]:
        used: list[int] = []
        i = search_from
        if i >= len(available):
            return None, used

        token = available[i]
        tier = resolve_tier(token.normalized)
        if tier is None:
            return None, used
        used.append(token.index)
        i += 1

        if i < len(available) and _GENERATION_RE.fullmatch(available[i].normalized):
            gen = available[i].normalized
            used.append(available[i].index)
            return f"{tier} {gen}", used

        return tier, used

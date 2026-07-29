"""Deterministic product matching for marketplace offers."""

from __future__ import annotations

from collections.abc import Sequence
from dataclasses import dataclass

from app.domain.entities.marketplace_data import MatchAmbiguityStatus, ProductMatchDecision
from app.marketplace.security import normalize_key

SAFE_MATCH_THRESHOLD = 0.85
AMBIGUOUS_THRESHOLD = 0.55


@dataclass(frozen=True, slots=True)
class CatalogEntry:
    product_id: str
    brand: str | None
    model: str | None
    title: str
    sku: str | None = None
    upc: str | None = None
    ean: str | None = None
    gtin: str | None = None
    aliases: tuple[str, ...] = ()
    marketplace_product_ids: tuple[str, ...] = ()


class MarketplaceProductMatcher:
    """Match offers to catalog / knowledge-graph style identities.

    Never silently merges uncertain products — returns conflict/review status
    when confidence is below the safe threshold.
    """

    def __init__(self, catalog: Sequence[CatalogEntry] | None = None) -> None:
        self._catalog: list[CatalogEntry] = list(catalog or ())

    def register(self, entry: CatalogEntry) -> None:
        self._catalog = [e for e in self._catalog if e.product_id != entry.product_id] + [entry]

    def match(
        self,
        *,
        brand: str | None = None,
        model: str | None = None,
        title: str = "",
        sku: str | None = None,
        upc: str | None = None,
        ean: str | None = None,
        gtin: str | None = None,
        marketplace_product_id: str | None = None,
        marketplace: str | None = None,
    ) -> ProductMatchDecision:
        del marketplace  # reserved for marketplace-scoped IDs
        scored: list[tuple[float, CatalogEntry, list[str]]] = []
        for entry in self._catalog:
            score, reasons = self._score(
                entry,
                brand=brand,
                model=model,
                title=title,
                sku=sku,
                upc=upc,
                ean=ean,
                gtin=gtin,
                marketplace_product_id=marketplace_product_id,
            )
            if score > 0:
                scored.append((score, entry, reasons))

        if not scored:
            return ProductMatchDecision(
                matched_product_id=None,
                confidence=0.0,
                reasons=("no catalog evidence matched",),
                ambiguity=MatchAmbiguityStatus.UNMATCHED,
            )

        scored.sort(key=lambda item: item[0], reverse=True)
        best_score, best_entry, best_reasons = scored[0]
        near = [item for item in scored if item[0] >= AMBIGUOUS_THRESHOLD]

        if best_score >= SAFE_MATCH_THRESHOLD:
            # Ambiguous if another candidate is very close
            if len(near) > 1 and (best_score - near[1][0]) < 0.08:
                return ProductMatchDecision(
                    matched_product_id=None,
                    confidence=best_score,
                    reasons=tuple(best_reasons)
                    + ("multiple high-confidence candidates — review required",),
                    ambiguity=MatchAmbiguityStatus.AMBIGUOUS,
                    candidate_ids=tuple(item[1].product_id for item in near[:5]),
                )
            return ProductMatchDecision(
                matched_product_id=best_entry.product_id,
                confidence=best_score,
                reasons=tuple(best_reasons),
                ambiguity=MatchAmbiguityStatus.MATCHED,
                candidate_ids=(best_entry.product_id,),
            )

        if best_score >= AMBIGUOUS_THRESHOLD:
            return ProductMatchDecision(
                matched_product_id=None,
                confidence=best_score,
                reasons=tuple(best_reasons)
                + ("confidence below safe merge threshold — review required",),
                ambiguity=MatchAmbiguityStatus.AMBIGUOUS,
                candidate_ids=tuple(item[1].product_id for item in near[:5]),
            )

        return ProductMatchDecision(
            matched_product_id=None,
            confidence=best_score,
            reasons=tuple(best_reasons) + ("insufficient evidence for merge",),
            ambiguity=MatchAmbiguityStatus.UNMATCHED,
            candidate_ids=tuple(item[1].product_id for item in scored[:3]),
        )

    def _score(
        self,
        entry: CatalogEntry,
        *,
        brand: str | None,
        model: str | None,
        title: str,
        sku: str | None,
        upc: str | None,
        ean: str | None,
        gtin: str | None,
        marketplace_product_id: str | None,
    ) -> tuple[float, list[str]]:
        score = 0.0
        reasons: list[str] = []

        if marketplace_product_id and marketplace_product_id in entry.marketplace_product_ids:
            score += 0.95
            reasons.append("marketplace product id exact match")

        for code_name, left, right in (
            ("upc", upc, entry.upc),
            ("ean", ean, entry.ean),
            ("gtin", gtin, entry.gtin),
            ("sku", sku, entry.sku),
        ):
            if left and right and normalize_key(left) == normalize_key(right):
                score += 0.9
                reasons.append(f"{code_name} exact match")

        brand_n = normalize_key(brand)
        model_n = normalize_key(model)
        entry_brand = normalize_key(entry.brand)
        entry_model = normalize_key(entry.model)
        if brand_n and entry_brand and brand_n == entry_brand:
            score += 0.25
            reasons.append("normalized brand match")
        if model_n and entry_model and model_n == entry_model:
            score += 0.35
            reasons.append("normalized model match")
        if brand_n and model_n and brand_n == entry_brand and model_n == entry_model:
            score += 0.25
            reasons.append("brand+model pair match")

        title_n = normalize_key(title)
        entry_title = normalize_key(entry.title)
        if title_n and entry_title:
            if title_n == entry_title:
                score += 0.4
                reasons.append("title exact match")
            elif title_n in entry_title or entry_title in title_n:
                score += 0.2
                reasons.append("title similarity")
            for alias in entry.aliases:
                alias_n = normalize_key(alias)
                if alias_n and (alias_n in title_n or title_n in alias_n):
                    score += 0.25
                    reasons.append("known alias match")
                    break

        return min(score, 1.0), reasons

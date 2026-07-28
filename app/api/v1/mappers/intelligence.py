"""Map Product Identity domain results to HTTP response schemas."""

from __future__ import annotations

from app.domain.entities.canonical_product import ParseSignal
from app.domain.entities.product_match import FieldConflict, ProductMatchResult
from app.domain.entities.registered_product import ParseListingResult
from app.schemas.intelligence import (
    CanonicalProductPayload,
    EvidenceItem,
    IntelligenceMatchResponse,
    IntelligenceParseResponse,
    MatchConflictPayload,
)


def to_parse_response(result: ParseListingResult) -> IntelligenceParseResponse:
    """Convert a parse/registry result into the public parse response schema."""
    product = result.product
    return IntelligenceParseResponse(
        original_title=result.original_title,
        canonical_product=CanonicalProductPayload(
            id=product.id,
            brand=product.brand,
            family=product.family,
            model=product.model,
            storage=product.storage,
            color=product.color,
        ),
        confidence=result.confidence,
        is_new_product=result.is_new_product,
        evidence=_signals_to_evidence(result.signals),
    )


def to_match_response(result: ProductMatchResult) -> IntelligenceMatchResponse:
    """Convert a matcher result into the public match response schema."""
    return IntelligenceMatchResponse(
        is_match=result.is_match,
        confidence=result.confidence,
        match_type=result.match_type,
        matched_fields=list(result.matched_fields),
        conflicts=[_to_conflict(conflict) for conflict in result.conflicts],
        explanation=list(result.explanation),
    )


def _signals_to_evidence(signals: tuple[ParseSignal, ...] | list[ParseSignal]) -> list[EvidenceItem]:
    return [
        EvidenceItem(
            field=signal.attribute,
            matched_text=signal.source_span or signal.value,
            rule=signal.rule_id,
        )
        for signal in signals
    ]


def _to_conflict(conflict: FieldConflict) -> MatchConflictPayload:
    return MatchConflictPayload(
        field=conflict.field,
        value_a=conflict.value_a,
        value_b=conflict.value_b,
    )

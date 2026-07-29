"""Parse and lightly coerce raw provider JSON into ProviderAnalysis."""

from __future__ import annotations

import json
from typing import Any

from app.domain.entities.review_analysis import (
    RECOMMENDATION_DISPLAY,
    SENTIMENT_DISPLAY,
    EvidenceClaim,
    ProviderAnalysis,
    ProviderUsageMetadata,
)
from app.domain.exceptions import AIProviderMalformedResponseError

_SENTIMENT_ALIASES = {
    **{k: k for k in SENTIMENT_DISPLAY},
    **{v.lower(): k for k, v in SENTIMENT_DISPLAY.items()},
    "very positive": "very_positive",
    "highly positive": "very_positive",
}
_RECOMMENDATION_ALIASES = {
    **{k: k for k in RECOMMENDATION_DISPLAY},
    **{v.lower(): k for k, v in RECOMMENDATION_DISPLAY.items()},
    "consider carefully": "consider_alternatives",
    "highly recommended": "highly_recommended",
    "not recommended": "not_recommended",
}


def _as_claim_list(raw: Any) -> list[EvidenceClaim]:
    if raw is None:
        return []
    if not isinstance(raw, list):
        raise ValueError("claim list must be an array")
    claims: list[EvidenceClaim] = []
    for item in raw:
        if isinstance(item, str):
            # Reject bare strings — evidence IDs are required.
            raise ValueError("claims must be objects with evidence_review_ids")
        if not isinstance(item, dict):
            raise ValueError("invalid claim object")
        claim = str(item.get("claim", "")).strip()
        if not claim:
            raise ValueError("claim text required")
        ids_raw = item.get("evidence_review_ids") or item.get("evidence") or []
        if not isinstance(ids_raw, list):
            raise ValueError("evidence_review_ids must be a list")
        evidence_ids = tuple(str(x).strip() for x in ids_raw if str(x).strip())
        try:
            confidence = float(item.get("confidence", 0.0))
        except (TypeError, ValueError) as exc:
            raise ValueError("confidence must be numeric") from exc
        claims.append(
            EvidenceClaim(
                claim=claim,
                evidence_review_ids=evidence_ids,
                confidence=max(0.0, min(1.0, confidence)),
            )
        )
    return claims


def parse_provider_json(
    content: str,
    *,
    provider: str,
    model: str,
    product_id: str,
    usage: ProviderUsageMetadata | None = None,
) -> ProviderAnalysis:
    """Parse model JSON into ProviderAnalysis or raise malformed error."""
    try:
        payload = json.loads(content)
    except json.JSONDecodeError as exc:
        raise AIProviderMalformedResponseError(provider, "response is not valid JSON") from exc
    if not isinstance(payload, dict):
        raise AIProviderMalformedResponseError(provider, "response JSON must be an object")
    try:
        sentiment_raw = str(payload.get("overall_sentiment", "")).strip().lower()
        sentiment = _SENTIMENT_ALIASES.get(sentiment_raw)
        if sentiment is None:
            raise ValueError(f"unsupported sentiment: {sentiment_raw}")
        recommendation_raw = str(payload.get("recommendation", "")).strip().lower()
        recommendation = _RECOMMENDATION_ALIASES.get(recommendation_raw)
        if recommendation is None:
            raise ValueError(f"unsupported recommendation: {recommendation_raw}")
        summary = str(payload.get("summary", "")).strip()
        if not summary:
            raise ValueError("summary is required")
        confidence = float(payload.get("confidence", 0.5))
        pros = tuple(_as_claim_list(payload.get("pros")))
        cons = tuple(_as_claim_list(payload.get("cons")))
        warnings = tuple(_as_claim_list(payload.get("warnings")))
    except (TypeError, ValueError) as exc:
        raise AIProviderMalformedResponseError(provider, str(exc)) from exc

    return ProviderAnalysis(
        product_id=str(payload.get("product_id") or product_id),
        overall_sentiment=sentiment,  # type: ignore[arg-type]
        summary=summary,
        pros=pros,
        cons=cons,
        warnings=warnings,
        recommendation=recommendation,  # type: ignore[arg-type]
        confidence=max(0.0, min(1.0, confidence)),
        provider=provider,
        model=model,
        status="ok",
        usage=usage,
    )

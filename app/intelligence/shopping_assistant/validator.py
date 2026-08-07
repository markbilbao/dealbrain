"""Validate shopping assistant answers against evidence (reject unsupported claims)."""

from __future__ import annotations

import re
from typing import Any

from app.domain.entities.shopping_assistant import (
    AssistantWarning,
    ShoppingAssistantResponse,
    ShoppingEvidence,
)

_UNSUPPORTED_PHRASES = (
    "lowest price online",
    "guaranteed authentic",
    "definitely drop",
    "will definitely",
    "fake reviews",
    "best camera in the world",
    "guaranteed",
    "live marketplace coverage is complete",
    "scraped live",
)

_NUMBER_RE = re.compile(r"\b\d+(?:,\d{3})*(?:\.\d+)?\b")


def _dedupe_warnings(warnings: list[AssistantWarning]) -> list[AssistantWarning]:
    seen: set[str] = set()
    result: list[AssistantWarning] = []
    for warning in warnings:
        if warning.message in seen:
            continue
        seen.add(warning.message)
        result.append(warning)
    return result


class ShoppingResponseValidator:
    """Evidence-ground shopping assistant narratives and strip unsafe claims."""

    def validate(
        self,
        response: ShoppingAssistantResponse,
        *,
        evidence: list[ShoppingEvidence] | None = None,
    ) -> ShoppingAssistantResponse:
        evidence_items = list(evidence if evidence is not None else response.evidence)
        evidence_text = " ".join(item.description for item in evidence_items).lower()
        evidence_ids = {item.evidence_id for item in evidence_items}

        warnings = list(response.warnings)
        answer = response.answer
        top = response.top_recommendation

        for phrase in _UNSUPPORTED_PHRASES:
            if phrase in answer.lower():
                answer = self._qualify_unsupported(answer, phrase)
                warnings.append(
                    AssistantWarning(
                        message=f"Removed or qualified unsupported claim pattern: '{phrase}'.",
                        code="unsupported_claim",
                    )
                )

        # Reject numeric claims in the answer that never appear in evidence.
        for match in _NUMBER_RE.findall(answer):
            normalized = match.replace(",", "")
            if normalized not in evidence_text.replace(",", "") and not self._number_in_structured(
                normalized,
                response,
            ):
                # Soft-qualify: do not hard-fail the whole response.
                warnings.append(
                    AssistantWarning(
                        message=(
                            f"Numeric value {match} is not clearly grounded in cited evidence; "
                            "treat it cautiously."
                        ),
                        code="ungrounded_number",
                    )
                )

        if top is not None:
            missing = [eid for eid in top.evidence_ids if eid not in evidence_ids]
            if missing:
                warnings.append(
                    AssistantWarning(
                        message="Top recommendation referenced missing evidence IDs; trimmed.",
                        code="missing_evidence",
                    )
                )
                top = type(top)(
                    product_id=top.product_id,
                    product_name=top.product_name,
                    reason=top.reason,
                    known_price=top.known_price,
                    currency=top.currency,
                    marketplace=top.marketplace,
                    deal_score=top.deal_score,
                    confidence=min(top.confidence, 0.55),
                    evidence_ids=tuple(eid for eid in top.evidence_ids if eid in evidence_ids),
                    rating=top.rating,
                    review_count=top.review_count,
                )

        if response.data_status == "mock" and not any(
            item.code == "mock_data" for item in warnings
        ):
            warnings.append(
                AssistantWarning(
                    message=(
                        "Results use mock or demo PiqSavi data — not live marketplace access."
                    ),
                    code="mock_data",
                )
            )

        # Cap false precision on confidence.
        confidence = response.confidence
        if confidence.score > 0.93:
            confidence = type(confidence)(
                score=0.93,
                band=confidence.band,
                factors=confidence.factors + ("capped false precision",),
            )

        processing: dict[str, Any] = dict(response.processing)
        processing["validated"] = True
        processing["secrets_included"] = False
        processing["prompts_included"] = False

        return ShoppingAssistantResponse(
            query=response.query,
            intent=response.intent,
            answer=answer,
            top_recommendation=top,
            alternatives=response.alternatives,
            evidence=response.evidence,
            warnings=tuple(_dedupe_warnings(warnings)),
            data_status=response.data_status,
            providers_used=response.providers_used,
            fallback_used=response.fallback_used,
            confidence=confidence,
            mode=response.mode,
            comparison=response.comparison,
            conversation_id=response.conversation_id,
            disagreements=response.disagreements,
            fallback_reason=response.fallback_reason,
            buy_now_or_wait=response.buy_now_or_wait,
            processing=processing,
            generated_at=response.generated_at,
            personal_recommendation=response.personal_recommendation,
            profile_id=response.profile_id,
        )

    @staticmethod
    def _qualify_unsupported(answer: str, phrase: str) -> str:
        pattern = re.compile(re.escape(phrase), re.I)
        return pattern.sub(
            "[unsupported claim removed — evidence incomplete]",
            answer,
        )

    @staticmethod
    def _number_in_structured(number: str, response: ShoppingAssistantResponse) -> bool:
        blobs: list[str] = []
        if response.top_recommendation:
            top = response.top_recommendation
            blobs.extend(
                [
                    str(top.known_price or ""),
                    str(top.deal_score or ""),
                    str(top.confidence),
                    str(top.rating or ""),
                    str(top.review_count),
                ]
            )
        for alt in response.alternatives:
            blobs.extend(
                [
                    str(alt.known_price or ""),
                    str(alt.deal_score or ""),
                    str(alt.rating or ""),
                ]
            )
        if response.comparison and response.comparison.price_difference is not None:
            blobs.append(str(response.comparison.price_difference))
        joined = " ".join(blobs).replace(",", "")
        return number in joined

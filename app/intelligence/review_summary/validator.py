"""Validate provider analysis against supplied review evidence."""

from __future__ import annotations

import re

from app.domain.entities.review_analysis import (
    EvidenceClaim,
    ProviderAnalysis,
    ReviewAnalysisRequest,
    ReviewEvidenceItem,
)

_NUMBER_RE = re.compile(
    r"(?<![A-Za-z])(\d+(?:\.\d+)?)\s*(%|percent|hours?|days?|stars?|\$|usd|php|sgd)?",
    re.IGNORECASE,
)


class ReviewAnalysisValidator:
    """Reject unsupported claims and strip evidence-less findings."""

    def validate(
        self,
        analysis: ProviderAnalysis,
        request: ReviewAnalysisRequest,
    ) -> ProviderAnalysis:
        if analysis.status != "ok":
            return analysis

        valid_ids = {item.review_id for item in request.reviews}
        text_by_id = {item.review_id: item.text for item in request.reviews}

        pros = self._filter_claims(analysis.pros, valid_ids, text_by_id)
        cons = self._filter_claims(analysis.cons, valid_ids, text_by_id)
        warnings = self._filter_claims(analysis.warnings, valid_ids, text_by_id)

        if not analysis.summary.strip():
            return ProviderAnalysis(
                product_id=analysis.product_id,
                overall_sentiment=analysis.overall_sentiment,
                summary="",
                pros=(),
                cons=(),
                warnings=(),
                recommendation=analysis.recommendation,
                confidence=0.0,
                provider=analysis.provider,
                model=analysis.model,
                status="validation_failed",
                error_code="empty_summary",
                usage=analysis.usage,
            )

        # Cap confidence when little evidence survives.
        evidence_count = sum(len(c.evidence_review_ids) for c in (*pros, *cons, *warnings))
        confidence = analysis.confidence
        if evidence_count == 0:
            confidence = min(confidence, 0.35)
        elif analysis.confidence > 0.95 and evidence_count < 3:
            confidence = min(confidence, 0.8)

        return ProviderAnalysis(
            product_id=analysis.product_id,
            overall_sentiment=analysis.overall_sentiment,
            summary=analysis.summary.strip(),
            pros=pros,
            cons=cons,
            warnings=warnings,
            recommendation=analysis.recommendation,
            confidence=confidence,
            provider=analysis.provider,
            model=analysis.model,
            status="ok",
            usage=analysis.usage,
        )

    def _filter_claims(
        self,
        claims: tuple[EvidenceClaim, ...],
        valid_ids: set[str],
        text_by_id: dict[str, str],
    ) -> tuple[EvidenceClaim, ...]:
        kept: list[EvidenceClaim] = []
        for claim in claims:
            evidence = tuple(rid for rid in claim.evidence_review_ids if rid in valid_ids)
            if not evidence:
                continue
            if self._has_unsupported_numeric_claim(claim.claim, evidence, text_by_id):
                continue
            # Soft lexical grounding: at least one evidence text shares a token.
            if not self._claim_grounded(claim.claim, evidence, text_by_id):
                continue
            confidence = claim.confidence
            if confidence > 0.95 and len(evidence) < 2:
                confidence = 0.85
            kept.append(
                EvidenceClaim(
                    claim=claim.claim.strip(),
                    evidence_review_ids=evidence,
                    confidence=confidence,
                )
            )
        return tuple(kept)

    def _claim_grounded(
        self,
        claim: str,
        evidence_ids: tuple[str, ...],
        text_by_id: dict[str, str],
    ) -> bool:
        tokens = {
            tok
            for tok in re.findall(r"[a-zA-Z]{4,}", claim.lower())
            if tok not in {"with", "that", "this", "from", "have", "were", "very"}
        }
        if not tokens:
            return True
        for rid in evidence_ids:
            text = text_by_id.get(rid, "").lower()
            if any(tok in text for tok in tokens):
                return True
        return False

    def _has_unsupported_numeric_claim(
        self,
        claim: str,
        evidence_ids: tuple[str, ...],
        text_by_id: dict[str, str],
    ) -> bool:
        """Reject numbers in claims that never appear in cited evidence."""
        numbers = {match.group(1) for match in _NUMBER_RE.finditer(claim)}
        if not numbers:
            return False
        joined = " ".join(text_by_id.get(rid, "") for rid in evidence_ids)
        return any(number not in joined for number in numbers)


def build_review_evidence(
    texts: list[str],
    *,
    prefix: str = "rv",
) -> tuple[ReviewEvidenceItem, ...]:
    """Assign stable review IDs to mock / imported review texts."""
    return tuple(
        ReviewEvidenceItem(review_id=f"{prefix}-{index:03d}", text=text)
        for index, text in enumerate(texts, start=1)
    )

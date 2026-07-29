"""Deterministic consensus across independent provider analyses."""

from __future__ import annotations

from collections import Counter

from app.domain.entities.review_analysis import (
    AnalysisDisagreement,
    AnalysisMode,
    ConsensusMetadata,
    EvidenceClaim,
    ProviderAnalysis,
)


class ConsensusService:
    """Merge multi-provider analyses without letting any provider self-grade."""

    def build(
        self,
        *,
        mode: AnalysisMode,
        analyses: list[ProviderAnalysis],
        fallback_used: bool = False,
        fallback_reason: str | None = None,
    ) -> tuple[ProviderAnalysis, ConsensusMetadata]:
        successful = [item for item in analyses if item.status == "ok"]
        if not successful:
            raise ValueError("No successful provider analyses to consensus.")

        sentiment = self._majority_str([item.overall_sentiment for item in successful])
        recommendation = self._majority_str([item.recommendation for item in successful])
        summary = self._pick_summary(successful, sentiment)
        pros = self._merge_claims([item.pros for item in successful])
        cons = self._merge_claims([item.cons for item in successful])
        warnings = self._merge_claims([item.warnings for item in successful])
        disagreements = self._find_disagreements(successful)
        agreement = self._agreement_score(successful, disagreements)
        confidence = round(
            sum(item.confidence for item in successful) / len(successful) * agreement,
            3,
        )

        providers = tuple(sorted({item.provider for item in successful}))
        merged = ProviderAnalysis(
            product_id=successful[0].product_id,
            overall_sentiment=sentiment,  # type: ignore[arg-type]
            summary=summary,
            pros=pros,
            cons=cons,
            warnings=warnings,
            recommendation=recommendation,  # type: ignore[arg-type]
            confidence=confidence,
            provider="+".join(providers) if len(providers) > 1 else providers[0],
            model="consensus" if len(providers) > 1 else successful[0].model,
            status="ok",
        )
        meta = ConsensusMetadata(
            mode=mode,
            providers_requested=len(analyses),
            providers_completed=len(successful),
            agreement_score=agreement,
            consensus_confidence=confidence,
            provider_results=tuple(analyses),
            disagreements=tuple(disagreements),
            fallback_used=fallback_used,
            fallback_reason=fallback_reason,
        )
        return merged, meta

    def _majority_str(self, values: list[str]) -> str:
        counts = Counter(values)
        return counts.most_common(1)[0][0]

    def _pick_summary(self, analyses: list[ProviderAnalysis], sentiment: str) -> str:
        matching = [item for item in analyses if item.overall_sentiment == sentiment]
        pool = matching or analyses
        return max(pool, key=lambda item: (item.confidence, len(item.summary))).summary

    def _merge_claims(
        self,
        groups: list[tuple[EvidenceClaim, ...]],
    ) -> tuple[EvidenceClaim, ...]:
        """Keep claims supported by at least one provider; merge evidence IDs."""
        by_key: dict[str, EvidenceClaim] = {}
        support: Counter[str] = Counter()
        for group in groups:
            seen_in_provider: set[str] = set()
            for claim in group:
                key = claim.claim.strip().lower()
                if not key or key in seen_in_provider:
                    continue
                seen_in_provider.add(key)
                support[key] += 1
                existing = by_key.get(key)
                if existing is None:
                    by_key[key] = claim
                else:
                    merged_ids = tuple(
                        dict.fromkeys(existing.evidence_review_ids + claim.evidence_review_ids)
                    )
                    by_key[key] = EvidenceClaim(
                        claim=existing.claim,
                        evidence_review_ids=merged_ids,
                        confidence=max(existing.confidence, claim.confidence),
                    )

        # Prefer claims seen by multiple providers when available.
        ranked = sorted(
            by_key.items(),
            key=lambda item: (-support[item[0]], -item[1].confidence, item[0]),
        )
        return tuple(claim for _, claim in ranked[:6])

    def _find_disagreements(
        self,
        analyses: list[ProviderAnalysis],
    ) -> list[AnalysisDisagreement]:
        disagreements: list[AnalysisDisagreement] = []
        if len({item.overall_sentiment for item in analyses}) > 1:
            disagreements.append(
                AnalysisDisagreement(
                    field="overall_sentiment",
                    providers=tuple(item.provider for item in analyses),
                    values=tuple(item.overall_sentiment for item in analyses),
                    detail="Providers disagreed on overall sentiment.",
                )
            )
        if len({item.recommendation for item in analyses}) > 1:
            disagreements.append(
                AnalysisDisagreement(
                    field="recommendation",
                    providers=tuple(item.provider for item in analyses),
                    values=tuple(item.recommendation for item in analyses),
                    detail="Providers disagreed on purchase recommendation.",
                )
            )

        # Claim-level: unique claims only one provider asserted.
        claim_owners: dict[str, set[str]] = {}
        for analysis in analyses:
            for claim in (*analysis.pros, *analysis.cons, *analysis.warnings):
                key = claim.claim.strip().lower()
                claim_owners.setdefault(key, set()).add(analysis.provider)
        singleton = sorted(
            key for key, owners in claim_owners.items() if len(owners) == 1
        )
        if singleton and len(analyses) > 1:
            disagreements.append(
                AnalysisDisagreement(
                    field="claims",
                    providers=tuple(sorted({p for s in claim_owners.values() for p in s})),
                    values=tuple(singleton[:8]),
                    detail="Some claims were asserted by only one provider.",
                )
            )
        return disagreements

    def _agreement_score(
        self,
        analyses: list[ProviderAnalysis],
        disagreements: list[AnalysisDisagreement],
    ) -> float:
        if len(analyses) <= 1:
            return 1.0
        penalty = 0.0
        for item in disagreements:
            if item.field in {"overall_sentiment", "recommendation"}:
                penalty += 0.18
            else:
                penalty += 0.08
        return round(max(0.0, min(1.0, 1.0 - penalty)), 3)

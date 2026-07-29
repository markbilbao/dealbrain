"""Merge multi-model community summary results."""

from __future__ import annotations

from typing import Any

from app.domain.entities.community_intelligence import CommunitySummary


class CommunityConsensusService:
    """Simple consensus over community summary provider outputs."""

    def merge(self, results: list[dict[str, Any]]) -> dict[str, Any]:
        ok = [item for item in results if item.get("status") == "ok" and item.get("summary")]
        if not ok:
            return {
                "provider": "consensus",
                "model": "consensus-v1",
                "status": "unavailable",
                "summary": None,
                "agreement_score": 0.0,
                "disagreements": (),
            }
        # Prefer the summary with the most evidence-backed insights.
        def insight_count(item: dict[str, Any]) -> int:
            summary = item.get("summary")
            if not isinstance(summary, CommunitySummary):
                return 0
            return (
                len(summary.most_praised)
                + len(summary.most_complaints)
                + len(summary.common_questions)
                + len(summary.buying_advice)
            )

        primary = max(ok, key=insight_count)
        providers = tuple(str(item.get("provider") or "") for item in ok)
        agreement = 1.0 if len(ok) == 1 else round(min(1.0, 0.55 + 0.15 * len(ok)), 3)
        disagreements = ()
        if len(ok) >= 2:
            # Surface provider set differences as soft disagreements.
            praised_sets = []
            for item in ok:
                summary = item.get("summary")
                if isinstance(summary, CommunitySummary):
                    praised_sets.append(
                        tuple(sorted(insight.topic or "" for insight in summary.most_praised))
                    )
            if len(set(praised_sets)) > 1:
                disagreements = (
                    {
                        "field": "most_praised",
                        "providers": list(providers),
                        "values": [",".join(values) for values in praised_sets],
                        "detail": "Providers emphasized different praised topics.",
                    },
                )
        summary: CommunitySummary = primary["summary"]
        summary = CommunitySummary(
            product_id=summary.product_id,
            product_name=summary.product_name,
            most_praised=summary.most_praised,
            most_complaints=summary.most_complaints,
            common_questions=summary.common_questions,
            who_should_buy=summary.who_should_buy,
            who_should_avoid=summary.who_should_avoid,
            buying_advice=summary.buying_advice,
            limitations=summary.limitations,
            provider="consensus",
            model="consensus-v1",
            mode=summary.mode,
            providers_used=providers,
            fallback_used=False,
            fallback_reason=None,
            agreement_score=agreement,
        )
        return {
            "provider": "consensus",
            "model": "consensus-v1",
            "status": "ok",
            "summary": summary,
            "agreement_score": agreement,
            "disagreements": disagreements,
            "providers_used": providers,
        }

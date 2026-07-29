"""Deterministic consensus for multi-provider shopping explanations."""

from __future__ import annotations

from typing import Any

from app.domain.entities.shopping_assistant import AssistantDisagreement


class ShoppingConsensusService:
    """Merge explanation provider outputs without provider self-grading."""

    def merge(self, results: list[dict[str, Any]]) -> dict[str, Any]:
        ok = [item for item in results if item.get("status") == "ok" and item.get("answer")]
        if not ok:
            return {
                "answer": None,
                "providers_used": (),
                "agreement_score": 0.0,
                "disagreements": (),
                "fallback_used": True,
            }

        # Prefer majority answer text when identical; else keep first ok answer
        # and report disagreements on top_recommendation claims.
        answers = [str(item.get("answer") or "") for item in ok]
        primary = answers[0]
        providers_used = tuple(str(item.get("provider")) for item in ok)

        disagreements: list[AssistantDisagreement] = []
        claim_maps: list[dict[str, str]] = []
        for item in ok:
            mapping: dict[str, str] = {}
            for claim in item.get("claims") or []:
                field = str(claim.get("field") or "")
                value = str(claim.get("value") or "")
                if field:
                    mapping[field] = value
            claim_maps.append(mapping)

        fields = sorted({field for mapping in claim_maps for field in mapping})
        for field in fields:
            values = sorted({mapping.get(field, "") for mapping in claim_maps if field in mapping})
            if len(values) > 1:
                providers = [
                    str(ok[idx].get("provider"))
                    for idx, mapping in enumerate(claim_maps)
                    if field in mapping
                ]
                disagreements.append(
                    AssistantDisagreement(
                        field=field,
                        providers=tuple(providers),
                        values=tuple(values),
                        detail=f"Providers disagree on {field}.",
                    )
                )

        agreement = 1.0
        if len(set(answers)) > 1:
            agreement -= 0.2
        agreement -= 0.12 * len(disagreements)
        agreement = max(0.0, min(1.0, agreement))

        return {
            "answer": primary,
            "providers_used": providers_used,
            "agreement_score": round(agreement, 2),
            "disagreements": tuple(disagreements),
            "fallback_used": False,
        }

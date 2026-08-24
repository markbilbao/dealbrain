"""Certified provider eligibility and deterministic selection.

Selection is capability-, market-, and source-driven. Affiliate commission,
payout, and commercial priority are never consulted.
"""

from __future__ import annotations

from collections.abc import Sequence

from app.domain.entities.research_execution import (
    DESTINATION_REEVALUATION_IMPLEMENTED,
    DESTINATION_SENSITIVE_CAPABILITIES,
    BlockedRequirement,
    ProviderEligibility,
    ResearchCapability,
    ResearchProviderStep,
    TrustedMarketContext,
)
from app.research.providers import StaticResearchProvider
from app.research.registry import ResearchProviderRegistry

_AFFILIATE_FIELDS = frozenset({"affiliate_commission_rate"})


def destination_sensitive_required(scope_has_destination: bool) -> bool:
    return scope_has_destination and not DESTINATION_REEVALUATION_IMPLEMENTED


def evaluate_provider(
    provider: StaticResearchProvider,
    *,
    capability: ResearchCapability,
    market: str | None,
    source: str | None,
) -> ProviderEligibility:
    return provider.supports(capability, market, source)


def select_certified_provider(
    registry: ResearchProviderRegistry,
    *,
    capability: ResearchCapability,
    market: str | None,
    source: str | None,
) -> tuple[StaticResearchProvider | None, tuple[ProviderEligibility, ...]]:
    """Choose one eligible provider using configured priority then provider_id.

    Equal certified providers are ordered by ``selection_priority`` ascending,
    then by stable ``provider_id``. Affiliate metadata is ignored.
    """

    audits: list[ProviderEligibility] = []
    eligible: list[StaticResearchProvider] = []
    for provider in registry.list_providers():
        _ignore_affiliate_metadata(provider)
        decision = evaluate_provider(
            provider,
            capability=capability,
            market=market,
            source=source,
        )
        audits.append(decision)
        if decision.eligible:
            eligible.append(provider)
    if not eligible:
        return None, tuple(audits)
    eligible.sort(
        key=lambda item: (item.descriptor.selection_priority, item.provider_id),
    )
    return eligible[0], tuple(audits)


def assign_capability_step(
    registry: ResearchProviderRegistry,
    *,
    capability: ResearchCapability,
    market: TrustedMarketContext | None,
    sources: Sequence[str],
    step_index: int,
    destination_sensitive: bool,
) -> tuple[
    tuple[ResearchProviderStep, ...],
    tuple[BlockedRequirement, ...],
    tuple[ProviderEligibility, ...],
]:
    """Assign certified providers for one required capability."""

    if destination_sensitive and capability in DESTINATION_SENSITIVE_CAPABILITIES:
        blocked = BlockedRequirement(
            capability=capability,
            reason="destination_support_not_ready",
            detail=(
                "Destination-sensitive cost is owned by Sprint 37. "
                "The router will not estimate shipping or taxes."
            ),
            material_to_final_cost=True,
        )
        return (), (blocked,), ()
    if market is None:
        blocked = BlockedRequirement(
            capability=capability,
            reason="missing_market_context",
            detail="Trusted market context is required and must not be fabricated.",
            material_to_final_cost=capability in DESTINATION_SENSITIVE_CAPABILITIES,
        )
        return (), (blocked,), ()

    requested_sources: tuple[str | None, ...] = tuple(sources) if sources else (None,)
    steps: list[ResearchProviderStep] = []
    blocked: list[BlockedRequirement] = []
    audits: list[ProviderEligibility] = []
    for source in requested_sources:
        provider, source_audits = select_certified_provider(
            registry,
            capability=capability,
            market=market.country_code,
            source=source,
        )
        audits.extend(source_audits)
        if provider is None:
            blocked.append(
                BlockedRequirement(
                    capability=capability,
                    reason=_blocked_reason(source_audits, source=source),
                    detail=_blocked_detail(capability, source, market.country_code),
                    material_to_final_cost=capability in DESTINATION_SENSITIVE_CAPABILITIES,
                )
            )
            continue
        cert = next(
            item
            for item in provider.descriptor.capability_certifications
            if item.capability == capability
        )
        source_identities = (source,) if source else provider.descriptor.supported_sources
        if sources:
            source_identities = tuple(item for item in source_identities if item in sources) or (
                source,
            )
        steps.append(
            ResearchProviderStep(
                step_index=step_index + len(steps),
                provider_id=provider.provider_id,
                provider_type=provider.descriptor.provider_type,
                capability=capability,
                source_identities=tuple(item for item in source_identities if item),
                market=market.country_code,
                certification_version=provider.descriptor.certification_version,
                capability_certification_version=cert.certification_version,
                selection_reason=_selection_reason(source_audits, provider.provider_id),
            )
        )
    return tuple(steps), tuple(blocked), tuple(audits)


def _selection_reason(audits: Sequence[ProviderEligibility], selected_id: str) -> str:
    eligible_ids = [item.provider_id for item in audits if item.eligible]
    if len(eligible_ids) > 1:
        return "deterministic_priority_then_provider_id"
    if selected_id in eligible_ids:
        return "certified_capability_market_source"
    return "certified_capability_market_source"


def _blocked_reason(audits: Sequence[ProviderEligibility], *, source: str | None) -> str:
    if not audits or any(item.eligible for item in audits):
        return "blocked_missing_certified_provider"
    reason_sets = [set(item.reasons) for item in audits]
    if source is not None and all("source_mismatch" in reasons for reasons in reason_sets):
        return "source_mismatch"
    if all("market_mismatch" in reasons for reasons in reason_sets):
        return "market_mismatch"
    if all(
        "capability_mismatch" in reasons or "capability_not_certified" in reasons
        for reasons in reason_sets
    ):
        return "capability_mismatch"
    if all("not_certified" in reasons for reasons in reason_sets):
        return "not_certified"
    return "blocked_missing_certified_provider"


def _blocked_detail(
    capability: ResearchCapability,
    source: str | None,
    market: str,
) -> str:
    source_label = source or "any permitted source"
    return (
        f"No certified provider for {capability.value} in {market} "
        f"from {source_label}."
    )


def _ignore_affiliate_metadata(provider: StaticResearchProvider) -> None:
    """Explicitly exclude commercial fields from selection (test seam)."""

    for field_name in _AFFILIATE_FIELDS:
        getattr(provider.descriptor, field_name, None)

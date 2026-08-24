"""Certified provider eligibility and deterministic selection.

Technical provider support and trusted certification are separate authorities.
Affiliate commission, payout, and commercial priority are never consulted.
"""

from __future__ import annotations

from collections.abc import Sequence

from app.domain.entities.research_execution import (
    DESTINATION_REEVALUATION_IMPLEMENTED,
    DESTINATION_SENSITIVE_CAPABILITIES,
    BlockedRequirement,
    ProviderEligibility,
    ResearchCapability,
    ResearchProviderCertification,
    ResearchProviderStep,
    TrustedMarketContext,
)
from app.research.certification import ResearchProviderCertificationCatalog
from app.research.providers import StaticResearchProvider
from app.research.registry import ResearchProviderRegistry

_AFFILIATE_FIELDS = frozenset({"affiliate_commission_rate"})
_POLICY_REASONS = {
    "unknown": "policy_not_allowed",
    "restricted": "policy_not_allowed",
    "prohibited": "policy_not_allowed",
}


def destination_sensitive_required(scope_has_destination: bool) -> bool:
    return scope_has_destination and not DESTINATION_REEVALUATION_IMPLEMENTED


def evaluate_provider(
    provider: StaticResearchProvider,
    catalog: ResearchProviderCertificationCatalog,
    *,
    capability: ResearchCapability,
    market: str | None,
    source: str | None,
) -> tuple[ProviderEligibility, ResearchProviderCertification | None]:
    """Require technical support AND an exact trusted certification record."""

    _ignore_affiliate_metadata(provider)
    technical = provider.supports(capability, market, source)
    reasons = list(technical.reasons)
    if reasons == ["technical_capability_market_source"]:
        reasons = []
    record: ResearchProviderCertification | None = None
    if market is not None and "missing_market_context" not in reasons:
        record, cert_reasons = _certification_decision(
            catalog,
            provider_id=provider.provider_id,
            capability=capability,
            market=market,
            source=source,
        )
        reasons.extend(cert_reasons)
    ordered = _dedupe(reasons)
    eligible = not ordered
    return (
        ProviderEligibility(
            provider_id=provider.provider_id,
            eligible=eligible,
            reasons=tuple(ordered) if ordered else ("certified_capability_market_source",),
            capability=capability,
            market=market,
            source=source,
        ),
        record if eligible else None,
    )


def select_certified_provider(
    registry: ResearchProviderRegistry,
    catalog: ResearchProviderCertificationCatalog,
    *,
    capability: ResearchCapability,
    market: str | None,
    source: str | None,
) -> tuple[
    StaticResearchProvider | None,
    ResearchProviderCertification | None,
    str | None,
    tuple[ProviderEligibility, ...],
]:
    """Choose one eligible provider using configured priority then provider_id.

    Equal certified providers are ordered by ``selection_priority`` ascending,
    then by stable ``provider_id``. Affiliate metadata is ignored.
    """

    audits: list[ProviderEligibility] = []
    eligible: list[tuple[StaticResearchProvider, ResearchProviderCertification, str | None]] = []
    for provider in registry.list_providers():
        sources_to_try: tuple[str | None, ...]
        if source is not None:
            sources_to_try = (source,)
        else:
            sources_to_try = (None, *sorted(provider.descriptor.supported_sources))
        matched: tuple[StaticResearchProvider, ResearchProviderCertification, str | None] | None
        matched = None
        for try_source in sources_to_try:
            decision, record = evaluate_provider(
                provider,
                catalog,
                capability=capability,
                market=market,
                source=try_source,
            )
            audits.append(decision)
            if decision.eligible and record is not None and matched is None:
                matched = (provider, record, try_source)
        if matched is not None:
            eligible.append(matched)
    if not eligible:
        return None, None, None, tuple(audits)
    eligible.sort(
        key=lambda item: (item[0].descriptor.selection_priority, item[0].provider_id),
    )
    chosen_provider, chosen_record, chosen_source = eligible[0]
    return chosen_provider, chosen_record, chosen_source, tuple(audits)


def assign_capability_step(
    registry: ResearchProviderRegistry,
    catalog: ResearchProviderCertificationCatalog,
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
    for requested_source in requested_sources:
        provider, record, matched_source, source_audits = select_certified_provider(
            registry,
            catalog,
            capability=capability,
            market=market.country_code,
            source=requested_source,
        )
        audits.extend(source_audits)
        if provider is None or record is None:
            blocked.append(
                BlockedRequirement(
                    capability=capability,
                    reason=_blocked_reason(source_audits, source=requested_source),
                    detail=_blocked_detail(capability, requested_source, market.country_code),
                    material_to_final_cost=capability in DESTINATION_SENSITIVE_CAPABILITIES,
                )
            )
            continue
        source_identities: tuple[str, ...]
        if requested_source:
            source_identities = (requested_source,)
        elif matched_source:
            source_identities = (matched_source,)
        else:
            source_identities = ()
        steps.append(
            ResearchProviderStep(
                step_index=step_index + len(steps),
                provider_id=provider.provider_id,
                provider_type=provider.descriptor.provider_type,
                capability=capability,
                source_identities=source_identities,
                market=market.country_code,
                certification_id=record.certification_id,
                certification_version=record.certification_version,
                selection_reason=_selection_reason(source_audits, provider.provider_id),
            )
        )
    return tuple(steps), tuple(blocked), tuple(audits)


def _certification_decision(
    catalog: ResearchProviderCertificationCatalog,
    *,
    provider_id: str,
    capability: ResearchCapability,
    market: str,
    source: str | None,
) -> tuple[ResearchProviderCertification | None, tuple[str, ...]]:
    record = catalog.lookup(
        provider_id=provider_id,
        capability=capability,
        market=market,
        source=source,
    )
    if record is not None:
        reasons: list[str] = []
        if record.status != "certified":
            reasons.append(f"certification_{record.status}")
        if record.policy != "allowed":
            reasons.append(_POLICY_REASONS.get(record.policy, "policy_not_allowed"))
        return record, tuple(reasons)
    return None, _missing_certification_reasons(
        catalog,
        provider_id=provider_id,
        capability=capability,
        market=market,
        source=source,
    )


def _missing_certification_reasons(
    catalog: ResearchProviderCertificationCatalog,
    *,
    provider_id: str,
    capability: ResearchCapability,
    market: str,
    source: str | None,
) -> tuple[str, ...]:
    records = catalog.records_for_provider(provider_id)
    if not records:
        return ("certification_missing",)
    same_capability = tuple(item for item in records if item.capability == capability)
    if not same_capability:
        return ("certification_capability_mismatch",)
    same_market = tuple(item for item in same_capability if item.market == market)
    if not same_market:
        return ("certification_market_mismatch",)
    if source is None:
        return ("certification_missing",)
    if any(item.source_scope == "exact" and item.source == source for item in same_market):
        return ("certification_missing",)
    return ("certification_source_mismatch",)


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
    if all("certification_missing" in reasons for reasons in reason_sets):
        return "certification_missing"
    for operational_reason in ("kill_switch", "circuit_open", "provider_unavailable"):
        if all(operational_reason in reasons for reasons in reason_sets):
            return operational_reason
    for status_reason in (
        "certification_revoked",
        "certification_disabled",
        "certification_pending",
        "certification_expired",
    ):
        if all(status_reason in reasons for reasons in reason_sets):
            return status_reason
    if source is not None and all(
        "source_not_supported" in reasons or "certification_source_mismatch" in reasons
        for reasons in reason_sets
    ):
        if all("source_not_supported" in reasons for reasons in reason_sets):
            return "source_not_supported"
        return "certification_source_mismatch"
    if all("provider_market_not_supported" in reasons for reasons in reason_sets):
        return "provider_market_not_supported"
    if all("certification_market_mismatch" in reasons for reasons in reason_sets):
        return "certification_market_mismatch"
    if all(
        "provider_capability_not_supported" in reasons
        or "certification_capability_mismatch" in reasons
        for reasons in reason_sets
    ):
        if all("provider_capability_not_supported" in reasons for reasons in reason_sets):
            return "provider_capability_not_supported"
        return "certification_capability_mismatch"
    if all("policy_not_allowed" in reasons for reasons in reason_sets):
        return "policy_not_allowed"
    return "blocked_missing_certified_provider"


def _blocked_detail(
    capability: ResearchCapability,
    source: str | None,
    market: str,
) -> str:
    source_label = source or "any permitted source"
    return f"No certified provider for {capability.value} in {market} from {source_label}."


def _ignore_affiliate_metadata(provider: StaticResearchProvider) -> None:
    """Explicitly exclude commercial fields from selection (test seam)."""

    for field_name in _AFFILIATE_FIELDS:
        getattr(provider.descriptor, field_name, None)


def _dedupe(reasons: Sequence[str]) -> list[str]:
    seen: set[str] = set()
    ordered: list[str] = []
    for reason in reasons:
        if reason not in seen:
            seen.add(reason)
            ordered.append(reason)
    return ordered

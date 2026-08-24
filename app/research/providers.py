"""Metadata-only research providers.

These objects declare certification and capabilities. They never call
merchants, HTTP clients, or Product Foundation fixtures.
"""

from __future__ import annotations

from app.domain.entities.research_execution import (
    CapabilityCertification,
    ProviderEligibility,
    ResearchCapability,
    ResearchProviderDescriptor,
    ResearchProviderStep,
)


class StaticResearchProvider:
    """Declared research provider used by the Sprint 31 router.

    ``execute`` is intentionally unimplemented. Test fixtures must set
    ``descriptor.test_fixture=True`` and may only be registered when the
    registry explicitly allows test providers.
    """

    def __init__(self, descriptor: ResearchProviderDescriptor) -> None:
        self._descriptor = descriptor

    @property
    def descriptor(self) -> ResearchProviderDescriptor:
        return self._descriptor

    @property
    def provider_id(self) -> str:
        return self._descriptor.provider_id

    def supports(
        self,
        capability: ResearchCapability,
        market: str | None,
        source: str | None,
    ) -> ProviderEligibility:
        reasons = list(_ineligibility_reasons(self._descriptor, capability, market, source))
        return ProviderEligibility(
            provider_id=self.provider_id,
            eligible=not reasons,
            reasons=tuple(reasons) if reasons else ("certified_capability_market_source",),
            capability=capability,
            market=market,
            source=source,
        )

    def execute(self, step: ResearchProviderStep) -> None:
        del step
        raise NotImplementedError(
            f"Provider {self.provider_id} cannot execute research in Sprint 31. "
            "Live execution is owned by Sprint 38 after Sprints 32–36 certify providers."
        )


def _ineligibility_reasons(
    descriptor: ResearchProviderDescriptor,
    capability: ResearchCapability,
    market: str | None,
    source: str | None,
) -> tuple[str, ...]:
    reasons: list[str] = []
    if descriptor.certification_status != "certified":
        reasons.append("not_certified")
    if not descriptor.is_operationally_available:
        if descriptor.kill_switch.engaged:
            reasons.append("kill_switch")
        elif not descriptor.circuit_breaker.allows_execution:
            reasons.append("circuit_open")
        else:
            reasons.append("operational_unavailable")
    if capability not in descriptor.supported_capabilities:
        reasons.append("capability_mismatch")
    cert = _capability_cert(descriptor, capability)
    if cert is None:
        reasons.append("capability_not_certified")
    else:
        if cert.policy == "unknown":
            reasons.append("policy_unknown")
        elif cert.policy == "prohibited":
            reasons.append("policy_prohibited")
        elif cert.policy == "restricted":
            reasons.append("policy_restricted")
        if market is None:
            reasons.append("missing_market_context")
        elif market not in cert.markets or market not in descriptor.supported_markets:
            reasons.append("market_mismatch")
        if source is not None and source not in cert.sources:
            reasons.append("source_mismatch")
        if source is None and cert.sources:
            # Generic (non-source-specific) requests may use a certified source.
            pass
    if source is not None and source not in descriptor.supported_sources:
        reasons.append("source_mismatch")
    # Deduplicate while preserving order.
    seen: set[str] = set()
    ordered: list[str] = []
    for reason in reasons:
        if reason not in seen:
            seen.add(reason)
            ordered.append(reason)
    return tuple(ordered)


def _capability_cert(
    descriptor: ResearchProviderDescriptor,
    capability: ResearchCapability,
) -> CapabilityCertification | None:
    for item in descriptor.capability_certifications:
        if item.capability == capability:
            return item
    return None

"""Metadata-only research providers.

Providers declare technical support only. They never certify themselves,
set routing preference, call merchants, HTTP clients, or Product Foundation
fixtures.
"""

from __future__ import annotations

from app.domain.entities.research_execution import (
    ProviderEligibility,
    ResearchCapability,
    ResearchProviderDescriptor,
    ResearchProviderStep,
)


class StaticResearchProvider:
    """Declared research provider used by the Sprint 31 router.

    ``execute`` is intentionally unimplemented. Test fixtures must set
    ``descriptor.test_fixture=True`` and may only be registered when the
    registry explicitly allows test providers. Technical support is not
    production certification or routing preference.
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
        """Return technical support only. Certification and routing are separate authorities."""

        reasons = list(
            _technical_ineligibility_reasons(self._descriptor, capability, market, source)
        )
        return ProviderEligibility(
            provider_id=self.provider_id,
            eligible=not reasons,
            reasons=tuple(reasons) if reasons else ("technical_capability_market_source",),
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


def _technical_ineligibility_reasons(
    descriptor: ResearchProviderDescriptor,
    capability: ResearchCapability,
    market: str | None,
    source: str | None,
) -> tuple[str, ...]:
    reasons: list[str] = []
    if not descriptor.is_operationally_available:
        if descriptor.kill_switch.engaged:
            reasons.append("kill_switch")
        elif not descriptor.circuit_breaker.allows_execution:
            reasons.append("circuit_open")
        else:
            reasons.append("provider_unavailable")
    if capability not in descriptor.supported_capabilities:
        reasons.append("provider_capability_not_supported")
    if market is None:
        reasons.append("missing_market_context")
    elif market not in descriptor.supported_markets:
        reasons.append("provider_market_not_supported")
    if source is not None and source not in descriptor.supported_sources:
        reasons.append("source_not_supported")
    seen: set[str] = set()
    ordered: list[str] = []
    for reason in reasons:
        if reason not in seen:
            seen.add(reason)
            ordered.append(reason)
    return tuple(ordered)

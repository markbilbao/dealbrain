"""Trusted research-provider certification decision service — Sprint 32.2.

Evidence → explicit trusted review → optional certification record.
Never: evidence → automatic certification. Never: provider → self-certification.
Does not consult routing, eligibility, commission, or live merchants.

Catalog ``register`` / ``replace`` remain lower-level trusted infrastructure
primitives. This service is the policy path. Production ``certified`` writes
also require an exact registered provider identity; documentary ``ph-*``
evidence IDs are not production identities by themselves.
"""

from __future__ import annotations

from app.domain.entities.research_certification_decision import (
    CertificationDecisionReason,
    CertificationDecisionRequest,
    CertificationDecisionResult,
    is_blocking_status,
)
from app.domain.entities.research_execution import (
    ResearchProviderCertification,
    ResearchProviderCertificationEvidence,
)
from app.research.certification import (
    ResearchProviderCertificationCatalog,
    make_research_provider_certification,
)
from app.research.certification_evidence import ResearchProviderCertificationEvidenceCatalog
from app.research.registry import ResearchProviderRegistry


class ResearchProviderCertificationDecisionService:
    """Server-owned policy path for exact certification targets."""

    def __init__(
        self,
        evidence_catalog: ResearchProviderCertificationEvidenceCatalog,
        certification_catalog: ResearchProviderCertificationCatalog,
        provider_registry: ResearchProviderRegistry | None = None,
    ) -> None:
        self._evidence = evidence_catalog
        self._certifications = certification_catalog
        self._providers = provider_registry

    def decide(self, request: CertificationDecisionRequest) -> CertificationDecisionResult:
        evidence = self._evidence.lookup(
            provider_id=request.provider_id,
            capability=request.capability,
            market=request.market,
            source=request.source,
        )
        if evidence is None:
            reason: CertificationDecisionReason = (
                "identity_mismatch"
                if self._evidence.records_for_provider(request.provider_id)
                else "evidence_missing"
            )
            return self._refuse(request, reason)

        if evidence.lookup_key() != request.lookup_key():
            return self._refuse(request, "identity_mismatch", evidence_ids=_ids(evidence))

        if (
            evidence.certification_version
            and evidence.certification_version != request.certification_version
        ):
            return self._refuse(request, "version_mismatch", evidence_ids=_ids(evidence))

        if evidence.test_fixture and not self._certifications.allows_test_certifications:
            return self._refuse(request, "fixture_forbidden", evidence_ids=_ids(evidence))

        if is_blocking_status(request.requested_status):
            return self._replace_blocking(request, evidence_ids=_ids(evidence))

        if request.requested_status == "pending":
            return self._refuse(request, "denied", evidence_ids=_ids(evidence))

        readiness = evidence.decision_readiness_reason(as_of=request.decided_at)
        if readiness is not None:
            return self._refuse(request, readiness, evidence_ids=_ids(evidence))

        if request.requested_policy not in {"allowed", "restricted"}:
            return self._refuse(request, "denied", evidence_ids=_ids(evidence))

        if request.requested_policy == "allowed" and evidence.restrictions:
            return self._refuse(
                request,
                "restrictions_unresolved",
                evidence_ids=_ids(evidence),
            )

        binding = self._production_provider_binding_reason(request)
        if binding is not None:
            return self._refuse(request, binding, evidence_ids=_ids(evidence))

        certification = make_research_provider_certification(
            provider_id=request.provider_id,
            capability=request.capability,
            market=request.market,
            source=request.source,
            source_scope=request.source_scope,
            certification_version=request.certification_version,
            status="certified",
            policy=request.requested_policy,
            test_fixture=evidence.test_fixture,
        )
        stored = self._write(certification)
        return CertificationDecisionResult(
            accepted=True,
            reason="approved",
            provider_id=request.provider_id,
            capability=request.capability,
            market=request.market,
            source=request.source,
            source_scope=request.source_scope,
            evidence_ids=_ids(evidence),
            certification=stored,
            requested_status=request.requested_status,
            requested_policy=request.requested_policy,
            reviewer=request.reviewer,
            decided_at=request.decided_at,
        )

    def _replace_blocking(
        self,
        request: CertificationDecisionRequest,
        *,
        evidence_ids: tuple[str, ...],
    ) -> CertificationDecisionResult:
        existing = self._certifications.lookup(
            provider_id=request.provider_id,
            capability=request.capability,
            market=request.market,
            source=request.source,
        )
        if existing is None:
            return self._refuse(request, "certification_missing", evidence_ids=evidence_ids)
        certification = make_research_provider_certification(
            provider_id=request.provider_id,
            capability=request.capability,
            market=request.market,
            source=request.source,
            source_scope=request.source_scope,
            certification_version=request.certification_version,
            status=request.requested_status,
            policy=request.requested_policy,
            test_fixture=existing.test_fixture,
        )
        stored = self._certifications.replace(certification)
        reason: CertificationDecisionReason = request.requested_status
        return CertificationDecisionResult(
            accepted=True,
            reason=reason,
            provider_id=request.provider_id,
            capability=request.capability,
            market=request.market,
            source=request.source,
            source_scope=request.source_scope,
            evidence_ids=evidence_ids,
            certification=stored,
            requested_status=request.requested_status,
            requested_policy=request.requested_policy,
            reviewer=request.reviewer,
            decided_at=request.decided_at,
        )

    def _production_provider_binding_reason(
        self,
        request: CertificationDecisionRequest,
    ) -> CertificationDecisionReason | None:
        """Production certified writes require a real registered provider.

        Test catalogs may omit a registry. Operational health, kill switch,
        and circuit state are not certification inputs.
        """

        if self._certifications.allows_test_certifications:
            return None
        if self._providers is None:
            return "provider_missing"
        provider = self._providers.get(request.provider_id)
        if provider is None:
            return "provider_missing"
        descriptor = provider.descriptor
        if descriptor.test_fixture:
            return "provider_fixture_forbidden"
        if request.capability not in descriptor.supported_capabilities:
            return "provider_capability_mismatch"
        if request.market not in descriptor.supported_markets:
            return "provider_market_mismatch"
        if request.source is not None and request.source not in descriptor.supported_sources:
            return "provider_source_mismatch"
        return None

    def _write(self, record: ResearchProviderCertification) -> ResearchProviderCertification:
        existing = self._certifications.lookup(
            provider_id=record.provider_id,
            capability=record.capability,
            market=record.market,
            source=record.source,
        )
        if existing is None:
            return self._certifications.register(record)
        return self._certifications.replace(record)

    def _refuse(
        self,
        request: CertificationDecisionRequest,
        reason: CertificationDecisionReason,
        *,
        evidence_ids: tuple[str, ...] = (),
    ) -> CertificationDecisionResult:
        return CertificationDecisionResult(
            accepted=False,
            reason=reason,
            provider_id=request.provider_id,
            capability=request.capability,
            market=request.market,
            source=request.source,
            source_scope=request.source_scope,
            evidence_ids=evidence_ids,
            certification=None,
            requested_status=request.requested_status,
            requested_policy=request.requested_policy,
            reviewer=request.reviewer,
            decided_at=request.decided_at,
        )


def _ids(evidence: ResearchProviderCertificationEvidence) -> tuple[str, ...]:
    if evidence.evidence_id:
        return (evidence.evidence_id,)
    return ()

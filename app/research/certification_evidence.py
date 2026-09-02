"""Trusted PiqSavi research-provider certification evidence catalog.

Stores non-secret evidence that may later support a certification decision.
Distinct from the certification catalog: evidence never authorizes planning,
eligibility, or routing. Sprint 32.1 production evidence starts empty.
"""

from __future__ import annotations

from collections.abc import Sequence
from dataclasses import replace
from datetime import date

from app.domain.entities.research_execution import (
    CertificationEvidenceCompleteness,
    CertificationSourceScope,
    ResearchCapability,
    ResearchProviderCertificationEvidence,
)
from app.research.digest import stable_sha256


class ResearchProviderCertificationEvidenceCatalog:
    """Server-owned exact evidence lookup. Production starts empty."""

    def __init__(
        self,
        records: Sequence[ResearchProviderCertificationEvidence] | None = None,
        *,
        allow_test_evidence: bool = False,
    ) -> None:
        self._allow_test_evidence = allow_test_evidence
        self._records: dict[
            tuple[str, str, str, str, str], ResearchProviderCertificationEvidence
        ] = {}
        self._order: list[tuple[str, str, str, str, str]] = []
        for record in records or ():
            self.register(record)

    @property
    def allows_test_evidence(self) -> bool:
        return self._allow_test_evidence

    def register(
        self, record: ResearchProviderCertificationEvidence
    ) -> ResearchProviderCertificationEvidence:
        if record.test_fixture and not self._allow_test_evidence:
            raise ValueError("test evidence cannot be registered in the production catalog")
        stored = record
        if not stored.evidence_id:
            stored = replace(stored, evidence_id=_evidence_id(stored))
        key = stored.lookup_key()
        if key in self._records:
            raise ValueError(
                "duplicate evidence for "
                f"{stored.provider_id}/{stored.capability.value}/"
                f"{stored.market}/{stored.source or 'source_agnostic'}"
            )
        self._order.append(key)
        self._records[key] = stored
        return stored

    def list_records(self) -> tuple[ResearchProviderCertificationEvidence, ...]:
        return tuple(self._records[key] for key in self._order)

    def records_for_provider(
        self, provider_id: str
    ) -> tuple[ResearchProviderCertificationEvidence, ...]:
        return tuple(item for item in self.list_records() if item.provider_id == provider_id)

    def lookup(
        self,
        *,
        provider_id: str,
        capability: ResearchCapability,
        market: str,
        source: str | None,
    ) -> ResearchProviderCertificationEvidence | None:
        """Exact lookup. Missing source never means every source."""

        if source is None:
            key = (provider_id, capability.value, market, "source_agnostic", "")
        else:
            key = (provider_id, capability.value, market, "exact", source)
        return self._records.get(key)

    def fingerprint(self) -> str:
        payload = [record.to_dict() for record in self.list_records()]
        return stable_sha256(
            {"kind": "research_provider_certification_evidence_catalog_v1", "records": payload}
        )


def make_research_provider_certification_evidence(
    *,
    provider_id: str,
    capability: ResearchCapability,
    market: str,
    evidence_source: str,
    source: str | None = None,
    source_scope: CertificationSourceScope = "exact",
    certification_version: str = "",
    program_reference: str = "",
    evidence_date: date | None = None,
    review_date: date | None = None,
    reviewer: str = "",
    restrictions: tuple[str, ...] = (),
    attribution_requirements: tuple[str, ...] = (),
    review_after: date | None = None,
    completeness: CertificationEvidenceCompleteness = "incomplete",
    notes: str = "",
    test_fixture: bool = True,
) -> ResearchProviderCertificationEvidence:
    record = ResearchProviderCertificationEvidence(
        provider_id=provider_id,
        capability=capability,
        market=market,
        evidence_source=evidence_source,
        source=source,
        source_scope=source_scope,
        certification_version=certification_version,
        program_reference=program_reference,
        evidence_date=evidence_date,
        review_date=review_date,
        reviewer=reviewer,
        restrictions=restrictions,
        attribution_requirements=attribution_requirements,
        review_after=review_after,
        completeness=completeness,
        notes=notes,
        test_fixture=test_fixture,
    )
    return replace(record, evidence_id=_evidence_id(record))


def production_research_provider_certification_evidence_catalog() -> (
    ResearchProviderCertificationEvidenceCatalog
):
    """Fail-closed production evidence catalog. Empty until later Sprint 32 slices."""

    return ResearchProviderCertificationEvidenceCatalog(allow_test_evidence=False)


def research_provider_certification_evidence_catalog_for_tests(
    records: Sequence[ResearchProviderCertificationEvidence],
) -> ResearchProviderCertificationEvidenceCatalog:
    """Explicit test catalog. Callers must pass records; nothing is implicit."""

    return ResearchProviderCertificationEvidenceCatalog(records, allow_test_evidence=True)


def _evidence_id(record: ResearchProviderCertificationEvidence) -> str:
    return "research-cert-evidence:" + stable_sha256(
        {
            "kind": "research_provider_certification_evidence_v1",
            "provider_id": record.provider_id,
            "capability": record.capability.value,
            "market": record.market,
            "source": record.source,
            "source_scope": record.source_scope,
            "certification_version": record.certification_version,
            "evidence_source": record.evidence_source,
            "completeness": record.completeness,
        }
    )

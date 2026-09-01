"""Trusted PiqSavi research-provider certification catalog.

Determines whether an exact provider/capability/market/source combination is
approved for production planning. Distinct from the technical provider registry
and from Sprint 32 certification evidence. Evidence records never authorize
planning. Providers cannot author these records.
"""

from __future__ import annotations

from collections.abc import Sequence
from dataclasses import replace

from app.domain.entities.research_execution import (
    CapabilityPolicyState,
    CertificationSourceScope,
    ProviderCertificationStatus,
    ResearchCapability,
    ResearchProviderCertification,
)
from app.research.digest import stable_sha256


class ResearchProviderCertificationCatalog:
    """Server-owned exact certification lookup. Production starts empty."""

    def __init__(
        self,
        records: Sequence[ResearchProviderCertification] | None = None,
        *,
        allow_test_certifications: bool = False,
    ) -> None:
        self._allow_test_certifications = allow_test_certifications
        self._records: dict[tuple[str, str, str, str, str], ResearchProviderCertification] = {}
        self._order: list[tuple[str, str, str, str, str]] = []
        for record in records or ():
            self.register(record)

    @property
    def allows_test_certifications(self) -> bool:
        return self._allow_test_certifications

    def register(self, record: ResearchProviderCertification) -> ResearchProviderCertification:
        if record.test_fixture and not self._allow_test_certifications:
            raise ValueError("test certifications cannot be registered in the production catalog")
        stored = record
        if not stored.certification_id:
            stored = replace(stored, certification_id=_certification_id(stored))
        key = stored.lookup_key()
        if key in self._records:
            raise ValueError(
                "duplicate certification for "
                f"{stored.provider_id}/{stored.capability.value}/"
                f"{stored.market}/{stored.source or 'source_agnostic'}"
            )
        self._order.append(key)
        self._records[key] = stored
        return stored

    def list_records(self) -> tuple[ResearchProviderCertification, ...]:
        return tuple(self._records[key] for key in self._order)

    def records_for_provider(self, provider_id: str) -> tuple[ResearchProviderCertification, ...]:
        return tuple(item for item in self.list_records() if item.provider_id == provider_id)

    def lookup(
        self,
        *,
        provider_id: str,
        capability: ResearchCapability,
        market: str,
        source: str | None,
    ) -> ResearchProviderCertification | None:
        """Exact lookup. Missing source never means every source."""

        if source is None:
            key = (provider_id, capability.value, market, "source_agnostic", "")
        else:
            key = (provider_id, capability.value, market, "exact", source)
        return self._records.get(key)

    def fingerprint(self) -> str:
        payload = [record.to_dict() for record in self.list_records()]
        return stable_sha256(
            {"kind": "research_provider_certification_catalog_v1", "records": payload}
        )


def make_research_provider_certification(
    *,
    provider_id: str,
    capability: ResearchCapability,
    market: str,
    certification_version: str,
    status: ProviderCertificationStatus = "certified",
    policy: CapabilityPolicyState = "allowed",
    source: str | None = None,
    source_scope: CertificationSourceScope = "exact",
    test_fixture: bool = True,
) -> ResearchProviderCertification:
    record = ResearchProviderCertification(
        provider_id=provider_id,
        capability=capability,
        market=market,
        certification_version=certification_version,
        status=status,
        policy=policy,
        source=source,
        source_scope=source_scope,
        test_fixture=test_fixture,
    )
    return replace(record, certification_id=_certification_id(record))


def production_research_provider_certification_catalog() -> ResearchProviderCertificationCatalog:
    """Fail-closed production catalog. Zero certified providers until Sprints 32–36."""

    return ResearchProviderCertificationCatalog(allow_test_certifications=False)


def research_provider_certification_catalog_for_tests(
    records: Sequence[ResearchProviderCertification],
) -> ResearchProviderCertificationCatalog:
    """Explicit test catalog. Callers must pass records; nothing is implicit."""

    return ResearchProviderCertificationCatalog(records, allow_test_certifications=True)


def _certification_id(record: ResearchProviderCertification) -> str:
    return "research-cert:" + stable_sha256(
        {
            "kind": "research_provider_certification_v1",
            "provider_id": record.provider_id,
            "capability": record.capability.value,
            "market": record.market,
            "source": record.source,
            "source_scope": record.source_scope,
            "status": record.status,
            "policy": record.policy,
            "certification_version": record.certification_version,
        }
    )

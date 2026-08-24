"""Trusted PiqSavi research-provider routing policy catalog.

Orders equally eligible certified providers. Distinct from the technical
provider registry and the certification catalog. Providers cannot author
these records. Routing preference does not grant certification.
"""

from __future__ import annotations

from collections.abc import Sequence

from app.domain.entities.research_execution import ResearchProviderRoutingPolicy
from app.research.digest import stable_sha256

_CONFIGURED_BUCKET = 0
_UNCONFIGURED_BUCKET = 1


class ResearchProviderRoutingPolicyCatalog:
    """Server-owned routing preference lookup. Production may be empty."""

    def __init__(
        self,
        records: Sequence[ResearchProviderRoutingPolicy] | None = None,
        *,
        allow_test_policies: bool = False,
    ) -> None:
        self._allow_test_policies = allow_test_policies
        self._records: dict[str, ResearchProviderRoutingPolicy] = {}
        self._order: list[str] = []
        for record in records or ():
            self.register(record)

    @property
    def allows_test_policies(self) -> bool:
        return self._allow_test_policies

    def register(self, record: ResearchProviderRoutingPolicy) -> ResearchProviderRoutingPolicy:
        if record.test_fixture and not self._allow_test_policies:
            raise ValueError("test routing policies cannot be registered in the production catalog")
        if record.provider_id in self._records:
            raise ValueError(f"duplicate routing policy for provider_id: {record.provider_id}")
        self._order.append(record.provider_id)
        self._records[record.provider_id] = record
        return record

    def list_records(self) -> tuple[ResearchProviderRoutingPolicy, ...]:
        return tuple(self._records[provider_id] for provider_id in self._order)

    def lookup(self, provider_id: str) -> ResearchProviderRoutingPolicy | None:
        return self._records.get(provider_id)

    def sort_key(self, provider_id: str) -> tuple[int, int, str]:
        """Configured priorities sort first (lower wins), then provider_id fallback."""

        record = self.lookup(provider_id)
        if record is None:
            return (_UNCONFIGURED_BUCKET, 0, provider_id)
        return (_CONFIGURED_BUCKET, record.routing_priority, provider_id)

    def fingerprint(self) -> str:
        payload = sorted(
            (
                {
                    "provider_id": record.provider_id,
                    "routing_priority": record.routing_priority,
                }
                for record in self.list_records()
            ),
            key=lambda item: item["provider_id"],
        )
        return stable_sha256(
            {"kind": "research_provider_routing_policy_catalog_v1", "records": payload}
        )


def make_research_provider_routing_policy(
    *,
    provider_id: str,
    routing_priority: int,
    test_fixture: bool = True,
) -> ResearchProviderRoutingPolicy:
    return ResearchProviderRoutingPolicy(
        provider_id=provider_id,
        routing_priority=routing_priority,
        test_fixture=test_fixture,
    )


def production_research_provider_routing_policy_catalog() -> ResearchProviderRoutingPolicyCatalog:
    """Empty production routing policy. Unconfigured providers use provider_id fallback."""

    return ResearchProviderRoutingPolicyCatalog(allow_test_policies=False)


def research_provider_routing_policy_catalog_for_tests(
    records: Sequence[ResearchProviderRoutingPolicy],
) -> ResearchProviderRoutingPolicyCatalog:
    """Explicit test catalog. Callers must pass records; nothing is implicit."""

    return ResearchProviderRoutingPolicyCatalog(records, allow_test_policies=True)

"""Sprint 31 routing-authority boundary.

Trusted server routing policy orders equally eligible certified providers.
Providers cannot choose their own preference. Routing does not certify.
"""

from __future__ import annotations

from dataclasses import fields

import pytest
from app.domain.entities.research_execution import (
    ResearchCapability,
    ResearchProviderDescriptor,
)
from app.research.routing import (
    make_research_provider_routing_policy,
    production_research_provider_routing_policy_catalog,
    research_provider_routing_policy_catalog_for_tests,
)
from app.services.research_execution import execute_research_plan

from tests.unit.test_sprint31_research_execution_router import (
    _catalog_for_registry,
    _plan,
    _provider,
    _registry,
    _routing,
)


def test_provider_descriptor_has_no_routing_priority_field() -> None:
    names = {item.name for item in fields(ResearchProviderDescriptor)}
    assert "selection_priority" not in names
    assert "routing_priority" not in names
    with pytest.raises(TypeError):
        payload = {
            "provider_id": "test-self-priority",
            "provider_type": "test",
            "supported_markets": ("PH",),
            "supported_capabilities": (ResearchCapability.CURRENT_PRICING,),
            "supported_sources": ("amazon",),
            "test_fixture": True,
            "selection_priority": 1,
        }
        ResearchProviderDescriptor(**payload)


def test_trusted_routing_policy_selects_lower_priority_first() -> None:
    registry = _registry(_provider("test-a"), _provider("test-b"))
    result = _plan(
        registry=registry,
        routing_policy=_routing(("test-a", 20), ("test-b", 10)),
    )
    plan = result.plan
    assert plan is not None
    assert {step.provider_id for step in plan.eligible_steps} == {"test-b"}
    assert all(step.selection_reason == "trusted_routing_priority" for step in plan.eligible_steps)


def test_changing_trusted_routing_policy_changes_selection_and_digest() -> None:
    registry = _registry(_provider("test-a"), _provider("test-b"))
    first = _plan(registry=registry, routing_policy=_routing(("test-a", 10), ("test-b", 20)))
    second = _plan(registry=registry, routing_policy=_routing(("test-a", 20), ("test-b", 10)))
    assert first.plan is not None and second.plan is not None
    assert {step.provider_id for step in first.plan.eligible_steps} == {"test-a"}
    assert {step.provider_id for step in second.plan.eligible_steps} == {"test-b"}
    assert first.plan.plan_digest != second.plan.plan_digest


def test_missing_routing_policy_falls_back_to_provider_id() -> None:
    registry = _registry(_provider("test-zzz"), _provider("test-aaa"))
    empty = research_provider_routing_policy_catalog_for_tests(())
    first = _plan(registry=registry, routing_policy=empty)
    second = _plan(registry=registry, routing_policy=empty)
    assert first.plan is not None and second.plan is not None
    assert {step.provider_id for step in first.plan.eligible_steps} == {"test-aaa"}
    assert first.plan.plan_digest == second.plan.plan_digest
    assert all(
        step.selection_reason == "provider_id_fallback" for step in first.plan.eligible_steps
    )


def test_partial_routing_policy_configured_providers_sort_first() -> None:
    registry = _registry(_provider("test-aaa"), _provider("test-zzz"))
    result = _plan(registry=registry, routing_policy=_routing(("test-zzz", 20)))
    plan = result.plan
    assert plan is not None
    assert {step.provider_id for step in plan.eligible_steps} == {"test-zzz"}
    assert all(step.selection_reason == "trusted_routing_priority" for step in plan.eligible_steps)


def test_commission_does_not_change_routing_policy_or_selection() -> None:
    routing = _routing(("test-aaa", 10), ("test-bbb", 10))
    first = _plan(
        registry=_registry(
            _provider("test-aaa", commission=0.99),
            _provider("test-bbb", commission=0.01),
        ),
        routing_policy=routing,
    )
    swapped = _plan(
        registry=_registry(
            _provider("test-aaa", commission=0.01),
            _provider("test-bbb", commission=0.99),
        ),
        routing_policy=routing,
    )
    assert first.plan is not None and swapped.plan is not None
    assert {step.provider_id for step in first.plan.eligible_steps} == {"test-aaa"}
    assert {step.provider_id for step in swapped.plan.eligible_steps} == {"test-aaa"}
    assert first.plan.plan_digest == swapped.plan.plan_digest
    assert routing.fingerprint() == _routing(("test-aaa", 10), ("test-bbb", 10)).fingerprint()


def test_routing_priority_does_not_certify() -> None:
    provider = _provider("test-priority-only")
    result = _plan(
        registry=_registry(provider),
        certify=False,
        routing_policy=_routing(("test-priority-only", 1)),
    )
    plan = result.plan
    assert plan is not None
    assert plan.eligible_steps == ()
    assert plan.plan_ready is False
    assert any(item.reason == "certification_missing" for item in plan.blocked_requirements)
    with pytest.raises(NotImplementedError):
        execute_research_plan(plan)


def test_certification_version_does_not_change_routing_preference() -> None:
    registry = _registry(_provider("test-a"), _provider("test-b"))
    routing = _routing(("test-a", 10), ("test-b", 20))
    v1 = _plan(
        registry=registry,
        catalog=_catalog_for_registry(registry, version="v1"),
        routing_policy=routing,
    )
    v2 = _plan(
        registry=registry,
        catalog=_catalog_for_registry(registry, version="v2"),
        routing_policy=routing,
    )
    assert v1.plan is not None and v2.plan is not None
    assert {step.provider_id for step in v1.plan.eligible_steps} == {"test-a"}
    assert {step.provider_id for step in v2.plan.eligible_steps} == {"test-a"}
    assert v1.plan.plan_digest != v2.plan.plan_digest


def test_test_routing_policy_cannot_enter_production_catalog() -> None:
    production = production_research_provider_routing_policy_catalog()
    assert production.list_records() == ()
    with pytest.raises(ValueError, match="test routing policies"):
        production.register(
            make_research_provider_routing_policy(
                provider_id="test-a",
                routing_priority=1,
                test_fixture=True,
            )
        )


def test_production_empty_routing_policy_uses_provider_id_fallback() -> None:
    registry = _registry(_provider("test-zzz"), _provider("test-aaa"))
    result = _plan(
        registry=registry,
        routing_policy=production_research_provider_routing_policy_catalog(),
    )
    plan = result.plan
    assert plan is not None
    assert plan.plan_ready is True
    assert {step.provider_id for step in plan.eligible_steps} == {"test-aaa"}
    assert all(step.selection_reason == "provider_id_fallback" for step in plan.eligible_steps)


def test_public_plan_does_not_expose_routing_priority() -> None:
    result = _plan(
        registry=_registry(_provider("test-a"), _provider("test-b")),
        routing_policy=_routing(("test-a", 7), ("test-b", 3)),
    )
    blob = str(result.to_public_dict())
    assert "routing_priority" not in blob
    assert "trusted_routing_priority" not in blob


def test_descriptor_mutation_cannot_override_trusted_routing_policy() -> None:
    routing = _routing(("test-zzz", 1), ("test-aaa", 50))
    first = _plan(
        registry=_registry(_provider("test-zzz"), _provider("test-aaa")),
        routing_policy=routing,
    )
    swapped_metadata = _plan(
        registry=_registry(
            _provider("test-zzz", commission=0.99, sources=("amazon", "shopee")),
            _provider("test-aaa", commission=0.01),
        ),
        routing_policy=routing,
    )
    assert first.plan is not None and swapped_metadata.plan is not None
    assert {step.provider_id for step in first.plan.eligible_steps} == {"test-zzz"}
    assert {step.provider_id for step in swapped_metadata.plan.eligible_steps} == {"test-zzz"}

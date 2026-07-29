"""Unit tests for Sprint 18 marketplace sync engine."""

from __future__ import annotations

from datetime import UTC, datetime

from app.domain.entities.marketplace_data import (
    ConnectorConfiguration,
    SyncJobStatus,
    SyncMode,
)
from app.marketplace.connectors.fixture import FixtureMarketplaceConnector
from app.marketplace.connectors.mock_live import MockLiveMarketplaceConnector
from app.marketplace.memory import InMemoryMarketplaceDataRepository
from app.marketplace.sync.engine import MarketplaceSyncEngine
from app.marketplace.sync.retry import SyncRetryPolicy

FIXED_NOW = datetime(2026, 7, 29, 12, 0, tzinfo=UTC)


def _repo_with_configs(*connector_ids: str) -> InMemoryMarketplaceDataRepository:
    repo = InMemoryMarketplaceDataRepository()
    for connector_id in connector_ids:
        marketplace = {
            "fixture-marketplace": "fixture",
            "mock-live-marketplace": "simulated_live",
        }.get(connector_id, "simulated_live")
        base_url = "https://simulated.dealbrain.local" if marketplace == "simulated_live" else None
        repo.save_configuration(
            ConnectorConfiguration(
                connector_id=connector_id,
                marketplace=marketplace,
                enabled=True,
                base_url=base_url,
            )
        )
    return repo


def test_full_sync_writes_fixture_offers() -> None:
    fixture = FixtureMarketplaceConnector()
    repo = _repo_with_configs(fixture.connector_id)
    engine = MarketplaceSyncEngine(repo, {fixture.connector_id: fixture}, clock=lambda: FIXED_NOW)
    job = engine.run(
        job_id="sync-full-1",
        connector_id=fixture.connector_id,
        mode=SyncMode.FULL,
    )
    assert job.status == SyncJobStatus.COMPLETED
    assert job.result is not None
    assert job.result.records_written >= 1
    assert repo.list_offers(source_mode="fixture")


def test_incremental_sync_uses_checkpoint() -> None:
    mock = MockLiveMarketplaceConnector()
    repo = _repo_with_configs(mock.connector_id)
    engine = MarketplaceSyncEngine(repo, {mock.connector_id: mock}, clock=lambda: FIXED_NOW)
    first = engine.run(
        job_id="sync-inc-1",
        connector_id=mock.connector_id,
        mode=SyncMode.FULL,
        limit=1,
    )
    assert first.status == SyncJobStatus.COMPLETED
    assert first.result is not None
    assert first.result.checkpoint is not None
    assert repo.get_checkpoint(mock.connector_id) is not None

    second = engine.run(
        job_id="sync-inc-2",
        connector_id=mock.connector_id,
        mode=SyncMode.INCREMENTAL,
        limit=1,
    )
    assert second.status in {
        SyncJobStatus.COMPLETED,
        SyncJobStatus.PARTIALLY_COMPLETED,
    }
    assert second.result is not None
    # Second page should write additional or duplicate-skip cleanly
    assert second.result.records_fetched >= 0


def test_sync_idempotency_key() -> None:
    fixture = FixtureMarketplaceConnector()
    repo = _repo_with_configs(fixture.connector_id)
    engine = MarketplaceSyncEngine(repo, {fixture.connector_id: fixture}, clock=lambda: FIXED_NOW)
    first = engine.run(
        job_id="sync-a",
        connector_id=fixture.connector_id,
        idempotency_key="same-key",
    )
    second = engine.run(
        job_id="sync-b",
        connector_id=fixture.connector_id,
        idempotency_key="same-key",
    )
    assert first.job_id == second.job_id


def test_retries_recover_from_transient_failure() -> None:
    mock = MockLiveMarketplaceConnector(fail_next=2)
    repo = _repo_with_configs(mock.connector_id)
    engine = MarketplaceSyncEngine(
        repo,
        {mock.connector_id: mock},
        clock=lambda: FIXED_NOW,
        retry_policy=SyncRetryPolicy(max_attempts=3, base_delay_seconds=0.01),
    )
    job = engine.run(job_id="sync-retry", connector_id=mock.connector_id)
    assert job.status == SyncJobStatus.COMPLETED
    assert any(e.code == "simulated_transient_failure" for e in job.errors)


def test_rate_limit_exhausts_retries() -> None:
    mock = MockLiveMarketplaceConnector(rate_limited=True)
    repo = _repo_with_configs(mock.connector_id)
    engine = MarketplaceSyncEngine(
        repo,
        {mock.connector_id: mock},
        clock=lambda: FIXED_NOW,
        retry_policy=SyncRetryPolicy(max_attempts=2, base_delay_seconds=0.01),
    )
    job = engine.run(job_id="sync-rl", connector_id=mock.connector_id)
    assert job.status == SyncJobStatus.FAILED
    assert any(e.code == "rate_limited" for e in job.errors)


def test_partial_failures_dead_letter() -> None:
    good = {
        "marketplace_product_id": "good-1",
        "title": "Good Offer",
        "sale_price": 100,
        "currency": "PHP",
        "simulated": True,
    }
    bad = {"marketplace_product_id": "bad-1", "title": "Bad Offer"}  # missing price
    mock = MockLiveMarketplaceConnector(payloads=(good, bad))
    repo = _repo_with_configs(mock.connector_id)
    engine = MarketplaceSyncEngine(repo, {mock.connector_id: mock}, clock=lambda: FIXED_NOW)
    job = engine.run(job_id="sync-partial", connector_id=mock.connector_id)
    assert job.status == SyncJobStatus.PARTIALLY_COMPLETED
    assert job.result is not None
    assert job.result.records_written == 1
    assert job.result.records_failed == 1
    assert job.result.dead_lettered == 1
    assert repo.list_dead_letters("sync-partial")


def test_retry_policy_delay_is_advisory() -> None:
    policy = SyncRetryPolicy(base_delay_seconds=0.5, max_delay_seconds=30.0)
    assert policy.delay_for_attempt(1) == 0.5
    assert policy.delay_for_attempt(2) == 1.0
    assert policy.delay_for_attempt(3) == 2.0
    decision = policy.decide(attempt=1, error_code="rate_limited")
    assert decision.should_retry is True
    decision = policy.decide(attempt=3, error_code="rate_limited")
    assert decision.should_retry is False

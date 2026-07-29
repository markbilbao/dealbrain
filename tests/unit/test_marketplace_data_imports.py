"""Unit tests for Sprint 18 marketplace CSV/JSON imports."""

from __future__ import annotations

from datetime import UTC, datetime

import pytest
from app.domain.entities.marketplace_data import ImportBatchStatus, SourceMode
from app.domain.exceptions import MarketplaceDataValidationError
from app.marketplace.connectors.fixture import FixtureMarketplaceConnector
from app.marketplace.connectors.imported import ImportedMarketplaceConnector
from app.marketplace.connectors.mock_live import MockLiveMarketplaceConnector
from app.marketplace.imports.pipeline import ImportPipeline, parse_import_payload
from app.marketplace.memory import InMemoryMarketplaceDataRepository
from app.marketplace.registry import MarketplaceConnectorRegistry
from app.marketplace.security import sanitize_csv_cell
from app.services.marketplace_data_service import MarketplaceDataService

FIXED_NOW = datetime(2026, 7, 29, 12, 0, tzinfo=UTC)

CSV_HEADER = (
    "marketplace_product_id,title,brand,model,currency,sale_price,shipping_cost,availability\n"
)


def make_service() -> MarketplaceDataService:
    repo = InMemoryMarketplaceDataRepository()
    registry = MarketplaceConnectorRegistry(
        [
            FixtureMarketplaceConnector(),
            ImportedMarketplaceConnector(),
            MockLiveMarketplaceConnector(),
        ],
        register_stubs=False,
    )
    return MarketplaceDataService(
        repo,
        registry,
        clock=lambda: FIXED_NOW,
        require_auth_for_ops=False,
    )


def test_csv_import_accepts_valid_rows() -> None:
    service = make_service()
    csv_body = CSV_HEADER + "imp-1,Imported Phone,Acme,X1,PHP,1999,50,in_stock\n"
    batch = service.import_payload(filename="offers.csv", payload=csv_body, actor="tester")
    assert batch.status == ImportBatchStatus.COMPLETED
    assert batch.source_mode == SourceMode.IMPORTED
    assert batch.records_accepted == 1
    offers = service.list_offers(source_mode="imported")
    assert len(offers) == 1
    assert offers[0].title == "Imported Phone"
    assert offers[0].source_mode == SourceMode.IMPORTED
    assert offers[0].simulated is False


def test_json_import_accepts_array() -> None:
    service = make_service()
    payload = """
    [
      {
        "marketplace_product_id": "j-1",
        "title": "JSON Headphones",
        "sale_price": 3200,
        "currency": "PHP"
      }
    ]
    """
    batch = service.import_payload(filename="offers.json", payload=payload, actor="tester")
    assert batch.status == ImportBatchStatus.COMPLETED
    assert batch.records_accepted == 1


def test_invalid_schema_rejects_rows() -> None:
    service = make_service()
    csv_body = CSV_HEADER + ",Missing Id Phone,Acme,X1,PHP,1999,50,in_stock\n"
    batch = service.import_payload(filename="bad.csv", payload=csv_body, actor="tester")
    assert batch.status == ImportBatchStatus.FAILED
    assert batch.records_rejected == 1
    errors = service.get_import_errors(batch.batch_id)
    assert errors
    assert any("marketplace_product_id" in e for e in errors[0].errors)


def test_invalid_json_raises_validation_error() -> None:
    service = make_service()
    with pytest.raises(MarketplaceDataValidationError):
        service.import_payload(filename="bad.json", payload="{not-json", actor="tester")


def test_partial_import_mixed_rows() -> None:
    service = make_service()
    csv_body = (
        CSV_HEADER
        + "ok-1,Good Row,Acme,X1,PHP,1000,0,in_stock\n"
        + ",Bad Row,Acme,X1,PHP,1000,0,in_stock\n"
        + "ok-2,Also Good,Acme,X2,PHP,2000,0,in_stock\n"
    )
    batch = service.import_payload(filename="partial.csv", payload=csv_body, actor="tester")
    assert batch.status == ImportBatchStatus.PARTIALLY_COMPLETED
    assert batch.records_accepted == 2
    assert batch.records_rejected == 1
    assert len(service.list_offers(source_mode="imported")) == 2


def test_duplicates_within_and_across_batches() -> None:
    service = make_service()
    row = "dup-1,Dup Phone,Acme,X1,PHP,1500,0,in_stock\n"
    first = service.import_payload(filename="a.csv", payload=CSV_HEADER + row, actor="tester")
    assert first.records_accepted == 1
    second = service.import_payload(
        filename="b.csv", payload=CSV_HEADER + row + row, actor="tester"
    )
    assert second.records_duplicate >= 1
    assert second.records_accepted == 0


def test_idempotency_key_returns_same_batch() -> None:
    service = make_service()
    csv_body = CSV_HEADER + "idemp-1,Idemp Phone,Acme,X1,PHP,1100,0,in_stock\n"
    first = service.import_payload(
        filename="idemp.csv",
        payload=csv_body,
        idempotency_key="import-key-1",
        actor="tester",
    )
    second = service.import_payload(
        filename="idemp.csv",
        payload=csv_body,
        idempotency_key="import-key-1",
        actor="tester",
    )
    assert first.batch_id == second.batch_id
    assert len(service.list_offers(source_mode="imported")) == 1


def test_formula_injection_sanitization() -> None:
    assert sanitize_csv_cell("=CMD()") == "'=CMD()"
    assert sanitize_csv_cell("+1+1") == "'+1+1"
    assert sanitize_csv_cell("@SUM(A1)") == "'@SUM(A1)"
    assert sanitize_csv_cell("Normal title") == "Normal title"

    # Import still accepts formula-looking titles after sanitize/parse round-trip
    pipeline = ImportPipeline()
    csv_body = CSV_HEADER + 'f-1,"=HYPERLINK(""http://evil"")",Acme,X1,PHP,999,0,in_stock\n'
    batch, records, accepted = pipeline.prepare_batch(
        batch_id="batch-formula",
        filename="formula.csv",
        payload=csv_body,
        now=FIXED_NOW,
    )
    assert batch.records_accepted == 1
    assert accepted[0]["title"].startswith("=") or accepted[0]["title"].startswith("'=")


def test_path_filename_rejected() -> None:
    with pytest.raises(MarketplaceDataValidationError):
        parse_import_payload(filename="../escape.csv", payload=CSV_HEADER + "a,b,c\n")

"""Green-only contract and integrity tests for Sprint 29 Phase 29.0."""

from __future__ import annotations

import copy
import json
from pathlib import Path

import pytest
from jsonschema import Draft202012Validator, FormatChecker
from jsonschema.exceptions import ValidationError
from scripts.validate_sprint29_phase_29_0 import (
    AUTHORITY_LOCK_PATH,
    CONTEXT_DRIFT_PATH,
    DECISION_CONTEXT_PATH,
    MOCK_DISCLOSURE,
    ROOT,
    SCHEMA_FIXTURE_PAIRS,
    Sprint29ContractError,
    aggregate_inventory,
    extract_manifest_inventory,
    load_json,
    validate_all,
    validate_architecture_authority,
    validate_context_drift_fixture,
    validate_research_fixture_boundary,
    validate_schemas_and_fixtures,
    validate_traceability,
    validate_visual_manifest,
)


def _validator(schema_name: str) -> Draft202012Validator:
    schema = load_json(ROOT / "schemas" / schema_name)
    return Draft202012Validator(schema, format_checker=FormatChecker())


def test_all_phase_29_0_schemas_and_fixtures_validate() -> None:
    result = validate_schemas_and_fixtures()
    assert result == {"schemas_validated": 6, "fixtures_validated": 9}


@pytest.mark.parametrize(
    ("schema_relative", "fixture_relatives"),
    SCHEMA_FIXTURE_PAIRS,
)
def test_every_contract_schema_is_draft_2020_12(
    schema_relative: Path,
    fixture_relatives: tuple[Path, ...],
) -> None:
    schema = load_json(ROOT / schema_relative)
    Draft202012Validator.check_schema(schema)
    assert schema["$schema"] == "https://json-schema.org/draft/2020-12/schema"
    assert fixture_relatives


def test_context_drift_fixture_is_exactly_frozen() -> None:
    validate_context_drift_fixture()
    case = load_json(ROOT / CONTEXT_DRIFT_PATH)
    context = load_json(ROOT / DECISION_CONTEXT_PATH)
    initial_ids = [item["product_id"] for item in case["initial_evaluated_products"]]
    context_ids = [item["product_id"] for item in context["evaluated_products"]]
    assert context_ids == initial_ids == case["expected_evaluated_product_ids"]
    assert case["follow_up"] == "Which one has better battery?"
    assert case["forbidden_unapproved_replacements"] == [
        {
            "product_id": "google-pixel-9-128gb",
            "display_name": "Google Pixel 9 128GB",
        }
    ]


def test_conversation_action_contract_is_a_closed_three_action_union() -> None:
    validator = _validator("sprint29-conversation-action.schema.json")
    fixture = load_json(ROOT / "tests/contracts/fixtures/sprint29-action-answer-from-evidence.json")
    unauthorized = copy.deepcopy(fixture)
    unauthorized["action"] = "replace_products_from_prompt"
    with pytest.raises(ValidationError):
        validator.validate(unauthorized)


def test_answer_from_evidence_cannot_smuggle_a_research_proposal() -> None:
    validator = _validator("sprint29-conversation-action.schema.json")
    fixture = load_json(ROOT / "tests/contracts/fixtures/sprint29-action-answer-from-evidence.json")
    fixture["research_proposal"] = {
        "proposal_id": "00000000-0000-4000-8000-000000000399",
        "question": "hidden research",
        "requested_product_ids": [],
        "status": "awaiting_explicit_confirmation",
    }
    with pytest.raises(ValidationError):
        validator.validate(fixture)


def test_research_proposal_requires_explicit_confirmation_state() -> None:
    validator = _validator("sprint29-conversation-action.schema.json")
    fixture = load_json(ROOT / "tests/contracts/fixtures/sprint29-action-propose-research.json")
    fixture["requires_research_confirmation"] = False
    with pytest.raises(ValidationError):
        validator.validate(fixture)


def test_mock_research_disclosure_is_exact_and_non_live() -> None:
    validate_research_fixture_boundary()
    validator = _validator("sprint29-research-execution.schema.json")
    fixture = load_json(ROOT / "tests/contracts/fixtures/sprint29-research-mock.json")
    assert fixture["disclosure"] == MOCK_DISCLOSURE
    assert fixture["production_eligible"] is False
    assert not any(fixture["live_claims"].values())

    altered = copy.deepcopy(fixture)
    altered["disclosure"] = "Live marketplace research complete."
    with pytest.raises(ValidationError):
        validator.validate(altered)


def test_phase_29_research_fixtures_do_not_contain_live_mode() -> None:
    fixture_names = ("sprint29-research-unavailable.json", "sprint29-research-mock.json")
    modes = {
        load_json(ROOT / "tests/contracts/fixtures" / fixture_name)["mode"]
        for fixture_name in fixture_names
    }
    assert modes == {"unavailable", "mock"}


def test_cc01_traceability_covers_all_24_future_behavioral_tests() -> None:
    validate_traceability()
    traceability = load_json(ROOT / "tests/contracts/fixtures/sprint29-contract-traceability.json")
    entries = traceability["entries"]
    assert len(entries) == 24
    assert {entry["acceptance_id"] for entry in entries} == {
        f"CC-01-{number:02d}" for number in range(1, 25)
    }
    assert {entry["status"] for entry in entries} == {"planned_not_implemented"}


def test_visual_manifest_document_and_aggregate_are_frozen() -> None:
    result = validate_visual_manifest()
    authority = load_json(ROOT / AUTHORITY_LOCK_PATH)
    assert result["manifest_sha256"] == authority["manifest_sha256"]
    assert result["approved_artifact_set_sha256"] == authority["approved_artifact_set_sha256"]
    assert result["artifact_inventory_count"] == 25
    assert result["source_artwork_files_verified"] == 0


def test_visual_manifest_aggregate_detects_inventory_tampering() -> None:
    authority = load_json(ROOT / AUTHORITY_LOCK_PATH)
    manifest_path = ROOT / authority["manifest_path"]
    entries = list(extract_manifest_inventory(manifest_path.read_text(encoding="utf-8")))
    digest, filename = entries[0]
    entries[0] = ("0" * 64 if digest != "0" * 64 else "1" * 64, filename)
    assert aggregate_inventory(tuple(entries)) != authority["approved_artifact_set_sha256"]


def test_architecture_and_protected_authority_sets_are_frozen() -> None:
    validate_architecture_authority()
    authority = load_json(ROOT / AUTHORITY_LOCK_PATH)
    assert authority["consumer_architecture"]["server"] == "FastAPI"
    assert "React" in authority["consumer_architecture"]["prohibited"]
    assert "canonical PiqScore/DealScore engine" in authority["protected_authorities"]


def test_complete_phase_29_0_validator_is_green() -> None:
    result = validate_all()
    assert result["status"] == "ok"
    assert result["schemas_validated"] == 6
    assert result["fixtures_validated"] == 9


def test_manifest_validator_fails_closed_when_document_is_missing(tmp_path: Path) -> None:
    authority = load_json(ROOT / AUTHORITY_LOCK_PATH)
    lock_target = tmp_path / AUTHORITY_LOCK_PATH
    lock_target.parent.mkdir(parents=True)
    lock_target.write_text(json.dumps(authority), encoding="utf-8")
    with pytest.raises(FileNotFoundError):
        validate_visual_manifest(tmp_path)


def test_context_drift_validator_rejects_unapproved_research(tmp_path: Path) -> None:
    context_target = tmp_path / DECISION_CONTEXT_PATH
    context_target.parent.mkdir(parents=True)
    context_target.write_text(
        (ROOT / DECISION_CONTEXT_PATH).read_text(encoding="utf-8"), encoding="utf-8"
    )
    case = load_json(ROOT / CONTEXT_DRIFT_PATH)
    case["research_explicitly_approved"] = True
    case_target = tmp_path / CONTEXT_DRIFT_PATH
    case_target.write_text(json.dumps(case), encoding="utf-8")
    with pytest.raises(Sprint29ContractError, match="cannot pre-authorize research"):
        validate_context_drift_fixture(tmp_path)

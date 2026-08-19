#!/usr/bin/env python3
"""Validate the frozen Sprint 29 Phase 29.0 contracts and visual authority."""

from __future__ import annotations

import argparse
import hashlib
import json
import re
from pathlib import Path
from typing import Any

from jsonschema import Draft202012Validator, FormatChecker

ROOT = Path(__file__).resolve().parents[1]

AUTHORITY_LOCK_PATH = Path("tests/contracts/fixtures/sprint29-authority-lock.json")
CONTEXT_DRIFT_PATH = Path("tests/contracts/fixtures/sprint29-context-drift.json")
DECISION_CONTEXT_PATH = Path("tests/contracts/fixtures/sprint29-decision-context.json")
TRACEABILITY_PATH = Path("tests/contracts/fixtures/sprint29-contract-traceability.json")

SCHEMA_FIXTURE_PAIRS = (
    (
        Path("schemas/sprint29-decision-context.schema.json"),
        (DECISION_CONTEXT_PATH,),
    ),
    (
        Path("schemas/sprint29-conversation-action.schema.json"),
        (
            Path("tests/contracts/fixtures/sprint29-action-answer-from-evidence.json"),
            Path("tests/contracts/fixtures/sprint29-action-refine-session-recommendation.json"),
            Path("tests/contracts/fixtures/sprint29-action-propose-research.json"),
        ),
    ),
    (
        Path("schemas/sprint29-research-execution.schema.json"),
        (
            Path("tests/contracts/fixtures/sprint29-research-unavailable.json"),
            Path("tests/contracts/fixtures/sprint29-research-mock.json"),
        ),
    ),
    (
        Path("schemas/sprint29-context-drift-fixture.schema.json"),
        (CONTEXT_DRIFT_PATH,),
    ),
    (
        Path("schemas/sprint29-contract-traceability.schema.json"),
        (TRACEABILITY_PATH,),
    ),
    (
        Path("schemas/sprint29-authority-lock.schema.json"),
        (AUTHORITY_LOCK_PATH,),
    ),
)

EXPECTED_CONTEXT_PRODUCTS = (
    ("apple-iphone-17-pro-max", "iPhone 17 Pro Max"),
    ("samsung-galaxy-s25-ultra-512gb", "Samsung Galaxy S25 Ultra 512GB"),
)
EXPECTED_FOLLOW_UP = "Which one has better battery?"
FORBIDDEN_REPLACEMENT = ("google-pixel-9-128gb", "Google Pixel 9 128GB")
MOCK_DISCLOSURE = "Demo research — not live marketplace data."


class Sprint29ContractError(ValueError):
    """Raised when a frozen Phase 29.0 contract or integrity check fails."""


def load_json(path: Path) -> dict[str, Any]:
    """Read one JSON object."""

    payload = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(payload, dict):
        raise Sprint29ContractError(f"expected a JSON object: {path}")
    return payload


def sha256_path(path: Path) -> str:
    """Return a file's lowercase SHA-256 digest."""

    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def extract_manifest_inventory(manifest_text: str) -> tuple[tuple[str, str], ...]:
    """Extract the approved two-column SHA-256 inventory from the manifest."""

    heading = "## Approved artifact inventory"
    if heading not in manifest_text:
        raise Sprint29ContractError("visual manifest is missing its artifact inventory")
    inventory_section = manifest_text.split(heading, maxsplit=1)[1]
    fenced_blocks = re.findall(r"```text\n(.*?)```", inventory_section, flags=re.DOTALL)
    if not fenced_blocks:
        raise Sprint29ContractError("visual manifest inventory is not a text code block")

    entries: list[tuple[str, str]] = []
    for line in fenced_blocks[0].splitlines():
        match = re.fullmatch(r"([0-9a-f]{64})  ([^\n]+)", line)
        if match is None:
            raise Sprint29ContractError(f"invalid visual manifest inventory line: {line!r}")
        entries.append((match.group(1), match.group(2)))

    if not entries:
        raise Sprint29ContractError("visual manifest inventory is empty")
    return tuple(entries)


def aggregate_inventory(entries: tuple[tuple[str, str], ...]) -> str:
    """Hash manifest lines ordered lexicographically by filename."""

    serialized = "".join(
        f"{digest}  {filename}\n" for digest, filename in sorted(entries, key=lambda item: item[1])
    )
    return hashlib.sha256(serialized.encode("utf-8")).hexdigest()


def _recorded_manifest_digest(manifest_text: str, label: str) -> str:
    match = re.search(rf"{re.escape(label)}:\s*\n`([0-9a-f]{{64}})`", manifest_text)
    if match is None:
        raise Sprint29ContractError(f"visual manifest is missing {label}")
    return match.group(1)


def validate_visual_manifest(
    repo_root: Path = ROOT,
    *,
    artwork_root: Path | None = None,
) -> dict[str, Any]:
    """Verify manifest authority, aggregate integrity, and optional source files."""

    authority_lock = load_json(repo_root / AUTHORITY_LOCK_PATH)
    manifest_path = repo_root / authority_lock["manifest_path"]
    manifest_text = manifest_path.read_text(encoding="utf-8")
    inventory = extract_manifest_inventory(manifest_text)

    actual_manifest_sha = sha256_path(manifest_path)
    if actual_manifest_sha != authority_lock["manifest_sha256"]:
        raise Sprint29ContractError("visual manifest document checksum mismatch")

    expected_status = f"**Manifest status:** {authority_lock['manifest_status']}"
    if expected_status not in manifest_text:
        raise Sprint29ContractError("visual manifest owner-approved status mismatch")

    inventory_names = [filename for _, filename in inventory]
    if inventory_names != authority_lock["approved_artifact_names"]:
        raise Sprint29ContractError("visual manifest approved inventory changed")
    if len(inventory) != authority_lock["approved_artifact_count"]:
        raise Sprint29ContractError("visual manifest artifact count mismatch")

    recorded_aggregate = _recorded_manifest_digest(manifest_text, "approved_artifact_set_sha256")
    computed_aggregate = aggregate_inventory(inventory)
    expected_aggregate = authority_lock["approved_artifact_set_sha256"]
    if recorded_aggregate != expected_aggregate or computed_aggregate != expected_aggregate:
        raise Sprint29ContractError("visual manifest artifact-set aggregate mismatch")

    legacy_match = re.search(
        r"`README_REVIEW_ONLY\.txt` remains unchanged with SHA-256:\s*\n\n"
        r"`([0-9a-f]{64})`",
        manifest_text,
    )
    if legacy_match is None or legacy_match.group(1) != authority_lock["legacy_readme_sha256"]:
        raise Sprint29ContractError("legacy visual-authority README checksum mismatch")

    artwork_verified = 0
    if artwork_root is not None:
        for expected_digest, filename in inventory:
            source_path = artwork_root / filename
            if not source_path.is_file():
                raise Sprint29ContractError(f"approved artwork is missing: {filename}")
            if sha256_path(source_path) != expected_digest:
                raise Sprint29ContractError(f"approved artwork checksum mismatch: {filename}")
            artwork_verified += 1

        legacy_path = artwork_root / "README_REVIEW_ONLY.txt"
        if not legacy_path.is_file():
            raise Sprint29ContractError("legacy visual-authority README is missing")
        if sha256_path(legacy_path) != authority_lock["legacy_readme_sha256"]:
            raise Sprint29ContractError("legacy visual-authority README source mismatch")

    return {
        "manifest_sha256": actual_manifest_sha,
        "approved_artifact_set_sha256": computed_aggregate,
        "artifact_inventory_count": len(inventory),
        "source_artwork_files_verified": artwork_verified,
    }


def validate_schemas_and_fixtures(repo_root: Path = ROOT) -> dict[str, int]:
    """Check every Phase 29.0 schema and validate every frozen fixture."""

    schema_count = 0
    fixture_count = 0
    format_checker = FormatChecker()
    for schema_relative, fixture_relatives in SCHEMA_FIXTURE_PAIRS:
        schema = load_json(repo_root / schema_relative)
        Draft202012Validator.check_schema(schema)
        validator = Draft202012Validator(schema, format_checker=format_checker)
        schema_count += 1
        for fixture_relative in fixture_relatives:
            validator.validate(load_json(repo_root / fixture_relative))
            fixture_count += 1
    return {"schemas_validated": schema_count, "fixtures_validated": fixture_count}


def validate_context_drift_fixture(repo_root: Path = ROOT) -> None:
    """Verify the owner-frozen context-drift reproduction exactly."""

    case = load_json(repo_root / CONTEXT_DRIFT_PATH)
    context = load_json(repo_root / DECISION_CONTEXT_PATH)

    initial_products = tuple(
        (item["product_id"], item["display_name"]) for item in case["initial_evaluated_products"]
    )
    context_products = tuple(
        (item["product_id"], item["display_name"]) for item in context["evaluated_products"]
    )
    expected_ids = tuple(item[0] for item in EXPECTED_CONTEXT_PRODUCTS)
    case_expected_ids = tuple(case["expected_evaluated_product_ids"])
    forbidden = tuple(
        (item["product_id"], item["display_name"])
        for item in case["forbidden_unapproved_replacements"]
    )

    if (
        initial_products != EXPECTED_CONTEXT_PRODUCTS
        or context_products != EXPECTED_CONTEXT_PRODUCTS
    ):
        raise Sprint29ContractError("frozen iPhone/Samsung evaluated set changed")
    if case_expected_ids != expected_ids:
        raise Sprint29ContractError("context-drift expected product IDs changed")
    if case["follow_up"] != EXPECTED_FOLLOW_UP:
        raise Sprint29ContractError("context-drift follow-up changed")
    if FORBIDDEN_REPLACEMENT not in forbidden:
        raise Sprint29ContractError("forbidden Google Pixel replacement is not frozen")
    if case["research_explicitly_requested"] or case["research_explicitly_approved"]:
        raise Sprint29ContractError("context-drift fixture cannot pre-authorize research")


def validate_research_fixture_boundary(repo_root: Path = ROOT) -> None:
    """Keep Phase 29 fixtures non-live and mock disclosure exact."""

    research_paths = (
        Path("tests/contracts/fixtures/sprint29-research-unavailable.json"),
        Path("tests/contracts/fixtures/sprint29-research-mock.json"),
    )
    modes: set[str] = set()
    for relative in research_paths:
        fixture = load_json(repo_root / relative)
        modes.add(fixture["mode"])
        if fixture["production_eligible"]:
            raise Sprint29ContractError("Sprint 29 research fixture cannot be production eligible")
        if any(fixture["live_claims"].values()):
            raise Sprint29ContractError("non-live research fixture contains a live claim")
        if fixture["mode"] == "mock" and fixture["disclosure"] != MOCK_DISCLOSURE:
            raise Sprint29ContractError("mock research disclosure changed")
    if modes != {"unavailable", "mock"}:
        raise Sprint29ContractError("Phase 29 research fixtures must be unavailable and mock only")


def validate_traceability(repo_root: Path = ROOT) -> None:
    """Require one unique planned behavioral test for every CC-01 criterion."""

    traceability = load_json(repo_root / TRACEABILITY_PATH)
    entries = traceability["entries"]
    expected_ids = {f"CC-01-{number:02d}" for number in range(1, 25)}
    acceptance_ids = {entry["acceptance_id"] for entry in entries}
    behavioral_test_ids = [entry["behavioral_test_id"] for entry in entries]
    if acceptance_ids != expected_ids:
        raise Sprint29ContractError("CC-01 traceability does not cover criteria 01 through 24")
    if len(behavioral_test_ids) != len(set(behavioral_test_ids)):
        raise Sprint29ContractError("CC-01 behavioral test IDs must be unique")
    for entry in entries:
        if entry["status"] != "planned_not_implemented":
            raise Sprint29ContractError("Phase 29.0 must not claim behavioral implementation")
        for artifact in entry["contract_artifacts"]:
            if not (repo_root / artifact).is_file():
                raise Sprint29ContractError(f"traceability artifact is missing: {artifact}")


def validate_architecture_authority(repo_root: Path = ROOT) -> None:
    """Verify the frozen architecture/protected-authority declarations."""

    authority = load_json(repo_root / AUTHORITY_LOCK_PATH)
    prohibited = set(authority["consumer_architecture"]["prohibited"])
    required_prohibitions = {
        "React",
        "Vite",
        "TypeScript",
        "SPA routing",
        "Node production build pipeline",
        "client-side scoring authority",
    }
    if prohibited != required_prohibitions:
        raise Sprint29ContractError("consumer architecture prohibition set changed")

    required_authorities = {
        "canonical PiqScore/DealScore engine",
        "canonical Recommendation engine",
        "affiliate-neutrality boundary",
        "existing Early Access behavior",
        "existing demo behavior",
        "approved Product Foundation artwork",
    }
    if set(authority["protected_authorities"]) != required_authorities:
        raise Sprint29ContractError("protected authority set changed")


def validate_all(
    repo_root: Path = ROOT,
    *,
    artwork_root: Path | None = None,
) -> dict[str, Any]:
    """Run the complete Phase 29.0 validation set."""

    contract_counts = validate_schemas_and_fixtures(repo_root)
    validate_context_drift_fixture(repo_root)
    validate_research_fixture_boundary(repo_root)
    validate_traceability(repo_root)
    validate_architecture_authority(repo_root)
    visual = validate_visual_manifest(repo_root, artwork_root=artwork_root)
    return {"status": "ok", **contract_counts, **visual}


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--artwork-root",
        type=Path,
        help="Optional Product Foundation source directory for full file checksum verification.",
    )
    args = parser.parse_args()
    result = validate_all(artwork_root=args.artwork_root)
    print(json.dumps(result, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

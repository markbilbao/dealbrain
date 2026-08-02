"""Sprint 25b.5f — staging immutable GitHub OIDC trust subject (static inspection)."""

from __future__ import annotations

import re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
TF_ROOT = ROOT / "infra/terraform"
DEPLOY_MODULE = TF_ROOT / "modules/github_deploy_role"
STAGING = TF_ROOT / "environments/staging"
PRODUCTION = TF_ROOT / "environments/production"
WORKFLOWS = ROOT / ".github/workflows"

CONFIRMED_OWNER_ID = "309556720"
CONFIRMED_REPO_ID = "1314423275"
IMMUTABLE_STAGING_SUB = (
    f"repo:markbilbao@{CONFIRMED_OWNER_ID}/dealbrain@{CONFIRMED_REPO_ID}:environment:staging"
)
LEGACY_STAGING_SUB = "repo:markbilbao/dealbrain:environment:staging"


def _read(path: Path) -> str:
    assert path.is_file(), f"missing required file: {path}"
    return path.read_text(encoding="utf-8")


def test_module_constructs_immutable_sub_from_owner_and_repo_ids() -> None:
    main = _read(DEPLOY_MODULE / "main.tf")
    vars_tf = _read(DEPLOY_MODULE / "variables.tf")
    assert 'variable "github_repository_owner_id"' in vars_tf
    assert 'variable "github_repository_id"' in vars_tf
    assert "use_immutable_oidc_sub" in main
    assert "github_repository_sub" in main
    assert "@${local.owner_id}/" in main or "@${local.owner_id}" in main
    assert "@${local.repo_id}" in main
    assert (
        'expected_sub = "repo:${local.github_repository_sub}:environment:${var.environment}"'
        in main
    )
    # Name-only legacy construction must not be the sole subject path.
    assert (
        'expected_sub      = "repo:${local.github_repository}:environment:${var.environment}"'
        not in main
    )


def test_staging_tfvars_example_pins_confirmed_immutable_ids() -> None:
    example = _read(STAGING / "terraform.tfvars.example")
    assert f'github_repository_owner_id = "{CONFIRMED_OWNER_ID}"' in example
    assert f'github_repository_id       = "{CONFIRMED_REPO_ID}"' in example
    assert IMMUTABLE_STAGING_SUB in example
    assert LEGACY_STAGING_SUB not in example


def test_staging_root_requires_numeric_owner_and_repo_ids() -> None:
    vars_tf = _read(STAGING / "variables.tf")
    staging_main = _read(STAGING / "main.tf")
    assert 'variable "github_repository_owner_id"' in vars_tf
    assert 'variable "github_repository_id"' in vars_tf
    # No defaults — staging must supply confirmed IDs.
    owner_block = re.search(
        r'variable "github_repository_owner_id"\s*\{(.*?)\n\}',
        vars_tf,
        re.S,
    )
    repo_block = re.search(
        r'variable "github_repository_id"\s*\{(.*?)\n\}',
        vars_tf,
        re.S,
    )
    assert owner_block is not None and "default" not in owner_block.group(1)
    assert repo_block is not None and "default" not in repo_block.group(1)
    assert "^[0-9]+$" in vars_tf or "^[0-9]+$" in vars_tf
    assert re.search(
        r"github_repository_owner_id\s*=\s*var\.github_repository_owner_id",
        staging_main,
    )
    assert re.search(
        r"github_repository_id\s*=\s*var\.github_repository_id",
        staging_main,
    )


def test_immutable_subject_contains_confirmed_ids_and_staging_suffix() -> None:
    example = _read(STAGING / "terraform.tfvars.example")
    assert CONFIRMED_OWNER_ID in example
    assert CONFIRMED_REPO_ID in example
    assert IMMUTABLE_STAGING_SUB.endswith(":environment:staging")
    assert IMMUTABLE_STAGING_SUB in example
    # Reconstruct from example values the same way the module does.
    owner = re.search(r'github_repository_owner\s*=\s*"([^"]+)"', example)
    name = re.search(r'github_repository_name\s*=\s*"([^"]+)"', example)
    owner_id = re.search(r'github_repository_owner_id\s*=\s*"([^"]+)"', example)
    repo_id = re.search(r'github_repository_id\s*=\s*"([^"]+)"', example)
    assert owner and name and owner_id and repo_id
    constructed = (
        f"repo:{owner.group(1)}@{owner_id.group(1)}/"
        f"{name.group(1)}@{repo_id.group(1)}:environment:staging"
    )
    assert constructed == IMMUTABLE_STAGING_SUB
    assert CONFIRMED_OWNER_ID in constructed
    assert CONFIRMED_REPO_ID in constructed
    assert constructed.endswith(":environment:staging")


def test_legacy_name_only_staging_subject_absent_from_staging_inputs() -> None:
    staging_texts = [
        _read(STAGING / "main.tf"),
        _read(STAGING / "variables.tf"),
        _read(STAGING / "terraform.tfvars.example"),
        _read(STAGING / "outputs.tf"),
    ]
    joined = "\n".join(staging_texts)
    assert LEGACY_STAGING_SUB not in joined
    # Module must not hard-code the legacy staging subject either.
    assert LEGACY_STAGING_SUB not in _read(DEPLOY_MODULE / "main.tf")


def test_trust_keeps_string_equals_aud_and_no_wildcard_sub() -> None:
    trust = _read(DEPLOY_MODULE / "main.tf")
    trust_section = trust.split('data "aws_iam_policy_document" "deploy_allow"')[0]
    assert 'test     = "StringEquals"' in trust_section
    assert trust_section.count('test     = "StringEquals"') >= 3
    assert 'test     = "StringLike"' not in trust_section
    assert "sts.amazonaws.com" in trust_section
    assert "token.actions.githubusercontent.com:aud" in trust_section
    assert "token.actions.githubusercontent.com:sub" in trust_section
    assert "token.actions.githubusercontent.com:repository" in trust_section
    assert "repo:*" not in trust_section
    assert 'values   = ["*"]' not in trust_section
    assert ":*:" not in trust_section
    # repository claim remains name-based owner/name local.
    assert (
        'github_repository = "${var.github_repository_owner}/${var.github_repository_name}"'
        in trust_section
    )


def test_staging_requires_immutable_ids_via_precondition() -> None:
    main = _read(DEPLOY_MODULE / "main.tf")
    assert "precondition" in main
    assert 'var.environment != "staging" || local.use_immutable_oidc_sub' in main
    assert "immutable OIDC" in main or "immutable" in main.lower()


def test_production_root_untouched_by_immutable_id_wiring() -> None:
    production_main = _read(PRODUCTION / "main.tf")
    production_vars = _read(PRODUCTION / "variables.tf")
    production_example = _read(PRODUCTION / "terraform.tfvars.example")
    for text in (production_main, production_vars, production_example):
        assert "github_repository_owner_id" not in text
        assert "github_repository_id" not in text
        assert CONFIRMED_OWNER_ID not in text
        assert CONFIRMED_REPO_ID not in text
        assert IMMUTABLE_STAGING_SUB not in text
    # Production still wires owner/name only (legacy sub path via empty ID defaults).
    assert "github_repository_owner  = var.github_repository_owner" in production_main
    assert "github_repository_name   = var.github_repository_name" in production_main
    assert 'environment = "production"' in production_main


def test_id_variables_reject_wildcards_via_numeric_validation() -> None:
    deploy_vars = _read(DEPLOY_MODULE / "variables.tf")
    staging_vars = _read(STAGING / "variables.tf")
    for text in (deploy_vars, staging_vars):
        assert "^[0-9]+$" in text or "^[0-9]+$" in text
    # Module defaults empty (production legacy path); staging has no defaults.
    assert 'default     = ""' in deploy_vars


def test_deploy_staging_workflow_unchanged_for_oidc_action_pin() -> None:
    """allowed-account-ids warning is unrelated; do not alter action pin in this fix."""
    workflow = _read(WORKFLOWS / "deploy-staging.yml")
    assert "aws-actions/configure-aws-credentials@v4" in workflow
    assert "allowed-account-ids: ${{ vars.AWS_ACCOUNT_ID }}" in workflow
    assert "audience: sts.amazonaws.com" in workflow
    assert "role-to-assume: ${{ vars.AWS_ROLE_ARN }}" in workflow

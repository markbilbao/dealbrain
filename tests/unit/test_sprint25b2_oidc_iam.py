"""Sprint 25b.2 — AWS OIDC and deploy IAM foundation tests (static inspection)."""

from __future__ import annotations

import re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
TF_ROOT = ROOT / "infra/terraform"
ACCOUNT = TF_ROOT / "account"
OIDC_MODULE = TF_ROOT / "modules/github_oidc"
DEPLOY_MODULE = TF_ROOT / "modules/github_deploy_role"
IAM_MODULE = TF_ROOT / "modules/iam"
SECRETS_MODULE = TF_ROOT / "modules/secrets"
STAGING = TF_ROOT / "environments/staging"
PRODUCTION = TF_ROOT / "environments/production"
WORKFLOWS = ROOT / ".github/workflows"

GITHUB_ENVIRONMENT_STAGING = "staging"
GITHUB_ENVIRONMENT_PRODUCTION = "production"

TOKEN_LIKE = re.compile(
    r"(?i)(ghp_[A-Za-z0-9]{20,}|github_pat_[A-Za-z0-9_]{20,}|"
    r"AKIA[0-9A-Z]{16}|aws_secret_access_key\s*=\s*\"[^\"]+\")"
)


def _read(path: Path) -> str:
    assert path.is_file(), f"missing required file: {path}"
    return path.read_text(encoding="utf-8")


def _tf_files() -> list[Path]:
    files: list[Path] = []
    for path in TF_ROOT.rglob("*"):
        if not path.is_file():
            continue
        if ".terraform" in path.parts:
            continue
        if path.suffix in {".tf", ".md"} or "tfvars" in path.name:
            files.append(path)
    return files


def _collect_tf_text() -> str:
    return "\n".join(_read(p) for p in _tf_files() if p.suffix == ".tf")


# ---------------------------------------------------------------------------
# 1–4 OIDC provider uniqueness and ownership
# ---------------------------------------------------------------------------


def test_exactly_one_oidc_provider_resource() -> None:
    matches = re.findall(
        r'resource\s+"aws_iam_openid_connect_provider"\s+"\w+"',
        _collect_tf_text(),
    )
    assert len(matches) == 1, f"expected exactly one OIDC provider resource, found {matches}"


def test_oidc_provider_owned_by_account_module() -> None:
    account_main = _read(ACCOUNT / "main.tf")
    oidc_main = _read(OIDC_MODULE / "main.tf")
    assert 'module "github_oidc"' in account_main
    assert 'source = "../modules/github_oidc"' in account_main
    assert 'resource "aws_iam_openid_connect_provider" "github"' in oidc_main
    assert "token.actions.githubusercontent.com" in oidc_main


def test_oidc_audience_is_sts_amazonaws_com() -> None:
    oidc_main = _read(OIDC_MODULE / "main.tf")
    assert 'client_id_list  = ["sts.amazonaws.com"]' in oidc_main or (
        'client_id_list = ["sts.amazonaws.com"]' in oidc_main
    )


def test_environment_roots_do_not_create_oidc_provider() -> None:
    for env_dir in (STAGING, PRODUCTION):
        text = _read(env_dir / "main.tf")
        assert "aws_iam_openid_connect_provider" not in text
        assert "modules/github_oidc" not in text


# ---------------------------------------------------------------------------
# 5–10 Trust policy contract
# ---------------------------------------------------------------------------


def test_repository_owner_and_name_are_mandatory_variables() -> None:
    deploy_vars = _read(DEPLOY_MODULE / "variables.tf")
    assert 'variable "github_repository_owner"' in deploy_vars
    assert 'variable "github_repository_name"' in deploy_vars
    assert 'variable "github_oidc_provider_arn"' in deploy_vars
    assert "must be non-empty" in deploy_vars
    # No defaults that would allow empty / wildcard trust.
    owner_block = re.search(
        r'variable "github_repository_owner"\s*\{(.*?)\n\}',
        deploy_vars,
        re.S,
    )
    assert owner_block is not None
    assert "default" not in owner_block.group(1)
    name_block = re.search(
        r'variable "github_repository_name"\s*\{(.*?)\n\}',
        deploy_vars,
        re.S,
    )
    assert name_block is not None
    assert "default" not in name_block.group(1)

    for env_dir in (STAGING, PRODUCTION):
        env_vars = _read(env_dir / "variables.tf")
        assert 'variable "github_repository_owner"' in env_vars
        assert 'variable "github_repository_name"' in env_vars
        assert 'variable "github_oidc_provider_arn"' in env_vars


def test_trust_pins_exact_repository_claim() -> None:
    trust = _read(DEPLOY_MODULE / "main.tf")
    assert "token.actions.githubusercontent.com:repository" in trust
    assert "token.actions.githubusercontent.com:aud" in trust
    assert "sts.amazonaws.com" in trust
    assert "sts:AssumeRoleWithWebIdentity" in trust
    assert (
        'github_repository = "${var.github_repository_owner}/${var.github_repository_name}"'
        in trust
    )
    # No wildcard repository subjects.
    assert "repo:*" not in trust
    assert 'repository": "*"' not in trust
    assert (
        re.search(
            r'variable\s*=\s*"token\.actions\.githubusercontent\.com:repository"[\s\S]*?values\s*=\s*\["\*"\]',
            trust,
        )
        is None
    )


def test_staging_trust_pins_environment_staging() -> None:
    trust = _read(DEPLOY_MODULE / "main.tf")
    staging_main = _read(STAGING / "main.tf")
    assert "environment:${var.environment}" in trust
    assert (
        'expected_sub      = "repo:${local.github_repository}:environment:${var.environment}"'
        in trust
    )
    assert "environment              = local.environment" in staging_main
    assert 'environment = "staging"' in staging_main
    assert GITHUB_ENVIRONMENT_STAGING == "staging"


def test_production_trust_pins_environment_production() -> None:
    production_main = _read(PRODUCTION / "main.tf")
    assert 'environment = "production"' in production_main
    assert 'module "github_deploy_role"' in production_main
    assert GITHUB_ENVIRONMENT_PRODUCTION == "production"


def test_staging_trust_cannot_assume_production() -> None:
    """Staging root pins environment=staging; module builds sub from var.environment only."""
    staging_main = _read(STAGING / "main.tf")
    deploy_main = _read(DEPLOY_MODULE / "main.tf")
    assert "environment              = local.environment" in staging_main
    assert 'environment = "staging"' in staging_main
    # Module constructs a single expected_sub — never both environments.
    assert deploy_main.count("expected_sub") >= 1
    # Staging root must not hard-code production environment subject.
    assert "environment:production" not in staging_main
    # Opposite-env deny uses opposite_environment local.
    assert (
        'opposite_environment = var.environment == "staging" ? "production" : "staging"'
        in deploy_main
    )


def test_production_trust_cannot_assume_staging() -> None:
    production_main = _read(PRODUCTION / "main.tf")
    assert 'environment = "production"' in production_main
    assert "environment:staging" not in production_main
    assert 'module "github_deploy_role"' in production_main


def test_exact_role_names() -> None:
    deploy_main = _read(DEPLOY_MODULE / "main.tf")
    assert 'role_name = "dealbrain-${var.environment}-gha-deploy"' in deploy_main
    staging_out = _read(STAGING / "outputs.tf")
    production_out = _read(PRODUCTION / "outputs.tf")
    assert "gha_deploy_role_arn" in staging_out
    assert "gha_deploy_role_name" in staging_out
    assert "gha_deploy_role_arn" in production_out
    assert "gha_deploy_role_name" in production_out


def test_max_session_duration_3600() -> None:
    deploy_main = _read(DEPLOY_MODULE / "main.tf")
    deploy_vars = _read(DEPLOY_MODULE / "variables.tf")
    assert "max_session_duration = var.max_session_duration" in deploy_main
    assert "default     = 3600" in deploy_vars
    assert "max_session_duration = 3600" in deploy_vars


def test_trust_has_no_iam_user_or_aws_principal() -> None:
    deploy_main = _read(DEPLOY_MODULE / "main.tf")
    # Trust document may only use Federated principal for OIDC.
    trust_section = deploy_main.split('data "aws_iam_policy_document" "deploy_allow"')[0]
    assert 'type        = "Federated"' in trust_section
    assert 'type        = "AWS"' not in trust_section
    assert "IAMUser" not in trust_section
    assert 'sts:AssumeRole"' not in trust_section.replace("sts:AssumeRoleWithWebIdentity", "")


# ---------------------------------------------------------------------------
# 11 Static AWS credentials forbidden
# ---------------------------------------------------------------------------


def test_no_static_aws_credential_variables_or_workflow_values() -> None:
    for path in _tf_files():
        if path.suffix != ".tf" and "tfvars" not in path.name:
            continue
        text = _read(path)
        assert "AWS_ACCESS_KEY_ID" not in text, path
        assert "AWS_SECRET_ACCESS_KEY" not in text, path
        assert "aws_access_key_id" not in text.lower() or "forbid" in text.lower()
        assert 'variable "aws_access_key' not in text.lower()
        assert 'variable "access_key' not in text.lower()

    for workflow in WORKFLOWS.glob("*.yml"):
        text = _read(workflow)
        assert "AWS_ACCESS_KEY_ID" not in text
        assert "AWS_SECRET_ACCESS_KEY" not in text
        assert "aws_access_key_id" not in text.lower()


# ---------------------------------------------------------------------------
# 12–19 Deploy permission policies
# ---------------------------------------------------------------------------


def test_deploy_roles_deny_iam_administration() -> None:
    deploy_main = _read(DEPLOY_MODULE / "main.tf")
    assert "DenyIamMutationAndPassRole" in deploy_main
    assert '"iam:*"' in deploy_main
    # No allow of IAM admin actions.
    allow_section = deploy_main.split('data "aws_iam_policy_document" "deploy_allow"')[1].split(
        'data "aws_iam_policy_document" "deploy_deny"'
    )[0]
    assert "iam:" not in allow_section


def test_deploy_roles_deny_pass_role() -> None:
    deploy_main = _read(DEPLOY_MODULE / "main.tf")
    # Covered by iam:* deny; ensure no PassRole allow exists.
    allow_section = deploy_main.split('data "aws_iam_policy_document" "deploy_allow"')[1].split(
        'data "aws_iam_policy_document" "deploy_deny"'
    )[0]
    assert "iam:PassRole" not in allow_section
    assert "PassRole" not in allow_section
    assert "DenyIamMutationAndPassRole" in deploy_main


def test_deploy_roles_cannot_read_secrets_manager_values() -> None:
    deploy_main = _read(DEPLOY_MODULE / "main.tf")
    assert "DenySecretsManagerValueAccess" in deploy_main
    assert "secretsmanager:GetSecretValue" in deploy_main
    allow_section = deploy_main.split('data "aws_iam_policy_document" "deploy_allow"')[1].split(
        'data "aws_iam_policy_document" "deploy_deny"'
    )[0]
    assert "secretsmanager:GetSecretValue" not in allow_section
    assert "secretsmanager:" not in allow_section


def test_send_command_constrained_to_approved_ssm_document() -> None:
    deploy_main = _read(DEPLOY_MODULE / "main.tf")
    assert "SendCommandApprovedDocument" in deploy_main
    assert "AWS-RunShellScript" in deploy_main
    assert "document/AWS-RunShellScript" in deploy_main
    assert "ssm:SendCommand" in deploy_main


def test_send_command_includes_environment_target_restrictions() -> None:
    deploy_main = _read(DEPLOY_MODULE / "main.tf")
    assert "SendCommandEnvironmentTaggedInstances" in deploy_main
    assert "ssm:resourceTag/Environment" in deploy_main
    assert "ssm:resourceTag/Project" in deploy_main
    assert "values   = [var.environment]" in deploy_main
    assert 'values   = ["dealbrain"]' in deploy_main


def test_staging_cannot_target_production_resources() -> None:
    deploy_main = _read(DEPLOY_MODULE / "main.tf")
    assert "DenySendCommandOppositeEnvironment" in deploy_main
    assert "DenyOppositeEnvironmentSecretArns" in deploy_main
    assert "local.opposite_environment" in deploy_main
    staging_main = _read(STAGING / "main.tf")
    assert "environment              = local.environment" in staging_main
    assert 'environment = "staging"' in staging_main


def test_production_cannot_target_staging_resources() -> None:
    production_main = _read(PRODUCTION / "main.tf")
    assert 'environment = "production"' in production_main
    deploy_main = _read(DEPLOY_MODULE / "main.tf")
    assert (
        'opposite_environment = var.environment == "staging" ? "production" : "staging"'
        in deploy_main
    )


def test_rds_create_db_snapshot_absent_or_denied() -> None:
    deploy_main = _read(DEPLOY_MODULE / "main.tf")
    allow_section = deploy_main.split('data "aws_iam_policy_document" "deploy_allow"')[1].split(
        'data "aws_iam_policy_document" "deploy_deny"'
    )[0]
    assert "rds:CreateDBSnapshot" not in allow_section
    assert "DenyRdsMutationAndSnapshot" in deploy_main
    assert "rds:CreateDBSnapshot" in deploy_main  # explicit deny
    # Describe only in allow.
    assert "rds:DescribeDBInstances" in allow_section


def test_deploy_allow_documents_star_resources_for_describe_apis() -> None:
    deploy_main = _read(DEPLOY_MODULE / "main.tf")
    assert "ObserveSsmCommands" in deploy_main
    assert "DescribeForTargetingAndHealth" in deploy_main
    assert "ec2:DescribeInstances" in deploy_main
    assert "elasticloadbalancing:DescribeTargetHealth" in deploy_main
    # Resource "*" required note appears in comments or structure.
    assert 'resources = ["*"]' in deploy_main


# Exact approved Allow action set for Sprint 25b.2 deploy roles.
# Explicit Deny statements are intentionally excluded from this comparison.
APPROVED_DEPLOY_ALLOW_ACTIONS = frozenset(
    {
        "ssm:SendCommand",
        "ssm:GetCommandInvocation",
        "ssm:ListCommands",
        "ssm:ListCommandInvocations",
        "ec2:DescribeInstances",
        "ec2:DescribeInstanceStatus",
        "elasticloadbalancing:DescribeTargetHealth",
        "rds:DescribeDBInstances",
    }
)


def _extract_deploy_allow_actions(deploy_main: str) -> set[str]:
    """Return the set of IAM actions declared in deploy_allow (Allow policy only)."""
    allow_section = deploy_main.split('data "aws_iam_policy_document" "deploy_allow"')[1].split(
        'data "aws_iam_policy_document" "deploy_deny"'
    )[0]
    # Guard: allow document must not smuggle Deny effects.
    assert re.search(r'effect\s*=\s*"Deny"', allow_section) is None
    found: set[str] = set()
    for block in re.finditer(r"actions\s*=\s*\[(.*?)\]", allow_section, re.S):
        for action in re.findall(r'"([^"]+)"', block.group(1)):
            found.add(action)
    return found


def test_deploy_allow_actions_exact_approved_set() -> None:
    """Fail if deploy_allow gains or loses any IAM action vs the approved 25b.2 set."""
    deploy_main = _read(DEPLOY_MODULE / "main.tf")
    found = _extract_deploy_allow_actions(deploy_main)
    extra = sorted(found - APPROVED_DEPLOY_ALLOW_ACTIONS)
    missing = sorted(APPROVED_DEPLOY_ALLOW_ACTIONS - found)
    assert found == APPROVED_DEPLOY_ALLOW_ACTIONS, (
        "deploy_allow action set drifted from Sprint 25b.2 approved set.\n"
        f"extra: {extra}\n"
        f"missing: {missing}"
    )
    # Deny document must remain outside the equality comparison and must exist.
    assert 'data "aws_iam_policy_document" "deploy_deny"' in deploy_main
    deny_section = deploy_main.split('data "aws_iam_policy_document" "deploy_deny"')[1]
    assert "rds:CreateDBSnapshot" in deny_section
    assert "iam:*" in deny_section


def test_deploy_denies_organizations_and_dangerous_ec2() -> None:
    deploy_main = _read(DEPLOY_MODULE / "main.tf")
    assert "DenyOrganizationsMutation" in deploy_main
    assert "organizations:*" in deploy_main
    assert "DenyDangerousEc2Mutation" in deploy_main
    assert "ec2:TerminateInstances" in deploy_main
    assert "DenyTerraformStateWrites" in deploy_main


# ---------------------------------------------------------------------------
# 20–22 Host IAM
# ---------------------------------------------------------------------------


def test_host_role_attaches_ssm_managed_instance_core() -> None:
    iam_main = _read(IAM_MODULE / "main.tf")
    assert "AmazonSSMManagedInstanceCore" in iam_main
    assert "aws_iam_role_policy_attachment" in iam_main
    assert "api_host_ssm_managed_instance" in iam_main


def test_host_secret_permissions_remain_environment_scoped() -> None:
    iam_main = _read(IAM_MODULE / "main.tf")
    assert "ReadEnvironmentSecrets" in iam_main
    assert "var.secret_arns" in iam_main
    for env in ("staging", "production"):
        main = _read(TF_ROOT / "environments" / env / "main.tf")
        assert "module.secrets.secret_arns" in main
        assert "module.rds.master_user_secret_arn" in main


def test_opposite_environment_secret_deny_remains() -> None:
    iam_main = _read(IAM_MODULE / "main.tf")
    assert "DenyOtherEnvironmentSecrets" in iam_main
    assert 'dealbrain/${var.environment == "staging" ? "production" : "staging"}/*' in iam_main
    # ECR deny preserved.
    assert "ECRPullNotUsed" in iam_main
    assert "ecr:*" in iam_main


# ---------------------------------------------------------------------------
# 23–25 GHCR secret containers
# ---------------------------------------------------------------------------


def test_ghcr_pull_secret_containers_exist_for_both_environments() -> None:
    secrets_vars = _read(SECRETS_MODULE / "variables.tf")
    assert '"ghcr_pull"' in secrets_vars
    secrets_main = _read(SECRETS_MODULE / "main.tf")
    assert "dealbrain/${var.environment}" in secrets_main
    assert "ghcr_pull" in secrets_main or "ghcr_pull" in secrets_vars
    # Both env roots use secrets module with defaults (includes ghcr_pull).
    for env_dir in (STAGING, PRODUCTION):
        assert 'module "secrets"' in _read(env_dir / "main.tf")


def test_no_secret_version_resource_for_ghcr_credentials() -> None:
    for path in TF_ROOT.rglob("*.tf"):
        if ".terraform" in path.parts:
            continue
        text = _read(path)
        assert re.search(r'resource\s+"aws_secretsmanager_secret_version"', text) is None, (
            f"secret_version resource must not exist in {path}"
        )


def test_no_real_token_like_values_in_terraform_tree() -> None:
    for path in _tf_files():
        text = _read(path)
        match = TOKEN_LIKE.search(text)
        assert match is None, f"token-like value in {path}: {match.group(0)[:20]}…"
    # Placeholder shape may appear in docs/comments only.
    secrets_vars = _read(SECRETS_MODULE / "variables.tf")
    assert "REPLACE_ME_OUT_OF_BAND" in secrets_vars


# ---------------------------------------------------------------------------
# 26–28 Workflows remain non-deploy
# ---------------------------------------------------------------------------


def test_no_deploy_workflows_exist() -> None:
    for name in ("deploy-staging.yml", "deploy-production.yml", "rollback.yml"):
        assert not (WORKFLOWS / name).is_file(), f"{name} must not exist in Sprint 25b.2"


def test_no_terraform_apply_in_github_actions() -> None:
    for workflow in WORKFLOWS.glob("*.yml"):
        text = _read(workflow)
        assert "terraform apply" not in text, workflow.name
        assert "terraform destroy" not in text, workflow.name


def test_ci_and_build_image_free_of_aws_oidc_deployment() -> None:
    for name in ("ci.yml", "build-image.yml"):
        text = _read(WORKFLOWS / name).lower()
        for needle in (
            "role-to-assume",
            "configure-aws-credentials",
            "aws-actions/configure-aws",
            "secretsmanager:getsecretvalue",
            "ssm:sendcommand",
        ):
            assert needle not in text, f"{name} contains deploy OIDC behavior: {needle}"
        # id-token write would be needed for OIDC deploy — must remain absent.
        assert "id-token: write" not in text
        assert "id-token:\n      write" not in text


# ---------------------------------------------------------------------------
# 29–31 Documentation / architecture lock
# ---------------------------------------------------------------------------


def test_architecture_lock_updates_are_additive() -> None:
    lock = _read(ROOT / "docs/architecture/ARCHITECTURE_LOCK.md")
    assert "Sprint 25" in lock
    assert "25b.2" in lock or "Sprint 25b.2" in lock
    assert "OIDC" in lock
    # Must not remove prior ownership.
    assert "Sprint 23" in lock
    assert "Sprint 24" in lock
    assert "DealScore" in lock


def test_github_environment_hard_gate_documentation_exists() -> None:
    docs = [
        ROOT / "docs/SPRINT_25B2_OIDC_IAM_IMPLEMENTATION.md",
        ROOT / "docs/architecture/SPRINT_25B2_AWS_OIDC_AND_DEPLOY_IAM.md",
        ROOT / "docs/DEPLOYMENT.md",
        ROOT / "docs/PRODUCTION.md",
    ]
    joined = "\n".join(_read(p) for p in docs if p.is_file())
    assert "required reviewers" in joined.lower() or "required reviewer" in joined.lower()
    assert "main" in joined
    assert "deployment branch" in joined.lower() or "deployment branches" in joined.lower()
    assert "administrator bypass" in joined.lower() or "admin bypass" in joined.lower()
    assert "staging" in joined
    assert "production" in joined
    assert "operationally approved" in joined.lower() or "operational approval" in joined.lower()


def test_production_reviewer_and_main_only_requirements_documented() -> None:
    impl = _read(ROOT / "docs/SPRINT_25B2_OIDC_IAM_IMPLEMENTATION.md")
    assert "production" in impl.lower()
    assert "required reviewers" in impl.lower()
    assert "main" in impl
    assert "bypass" in impl.lower()
    assert GITHUB_ENVIRONMENT_STAGING in impl
    assert GITHUB_ENVIRONMENT_PRODUCTION in impl


def test_implementation_doc_distinguishes_repo_vs_live() -> None:
    impl = _read(ROOT / "docs/SPRINT_25B2_OIDC_IAM_IMPLEMENTATION.md")
    assert "repository" in impl.lower()
    assert "not operationally approved" in impl.lower() or "repository-complete" in impl.lower()
    # Must not claim live apply.
    assert "resources were created in aws" not in impl.lower()
    assert "roles were assumed" not in impl.lower()


def test_account_root_documents_import_path() -> None:
    expected = "module.github_oidc.aws_iam_openid_connect_provider.github[0]"
    readme = _read(ACCOUNT / "README.md")
    assert "terraform import" in readme
    assert expected in readme
    assert "oidc-provider/token.actions.githubusercontent.com" in readme
    # Module-level docs must use the same non-count-indexed module address.
    oidc_vars = _read(OIDC_MODULE / "variables.tf")
    assert expected in oidc_vars
    assert "module.github_oidc[0]" not in oidc_vars
    account_vars = _read(ACCOUNT / "variables.tf")
    assert expected in account_vars


def test_prevent_destroy_on_oidc_provider() -> None:
    oidc_main = _read(OIDC_MODULE / "main.tf")
    assert "prevent_destroy" in oidc_main


def test_thumbprint_derived_from_tls_certificate() -> None:
    oidc_main = _read(OIDC_MODULE / "main.tf")
    assert 'data "tls_certificate"' in oidc_main
    assert "sha1_fingerprint" in oidc_main

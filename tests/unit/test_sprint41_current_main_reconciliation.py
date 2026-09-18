"""Sprint 41 current-main reconciliation contracts. No production mutation."""

from __future__ import annotations

import json
from pathlib import Path

import yaml

ROOT = Path(__file__).resolve().parents[2]
MATRIX_PATH = ROOT / "tests/contracts/fixtures/sprint41-acceptance-matrix.json"
RECONCILIATION = ROOT / "docs/roadmap/evidence/SPRINT_41_CURRENT_MAIN_RECONCILIATION_2026-09-18.md"
CDN_PROPOSAL = ROOT / "docs/roadmap/evidence/SPRINT_41_CDN_WAF_DECISION_PROPOSAL_2026-09-18.md"
DEPLOY6_EVIDENCE = ROOT / "docs/roadmap/evidence/PRODUCTION_DEPLOY_6_EVIDENCE_2026-09-15.json"
SPRINT_41 = ROOT / "docs/roadmap/sprints/SPRINT_41_PRODUCTION_ENVIRONMENT_DEPLOY.md"
SPRINTS_README = ROOT / "docs/roadmap/sprints/README.md"
MASTER = ROOT / "docs/roadmap/GLOBAL_PUBLIC_BETA_MASTER_ROADMAP.md"
GAP = ROOT / "docs/roadmap/GAP_INVENTORY.md"
EXT = ROOT / "docs/roadmap/EXTERNAL_DEPENDENCY_REGISTER.md"
ALB_TF = ROOT / "infra/terraform/modules/alb/main.tf"
DEPLOY_WF = ROOT / ".github/workflows/deploy-production.yml"
ROLLBACK_WF = ROOT / ".github/workflows/rollback-production.yml"
STAGING_DEPLOY_WF = ROOT / ".github/workflows/deploy-staging.yml"
IAM_TF = ROOT / "infra/terraform/modules/iam/main.tf"
GHA_ROLE_TF = ROOT / "infra/terraform/modules/github_deploy_role/main.tf"
PROD_TF = ROOT / "infra/terraform/environments/production/main.tf"
STAGING_TF = ROOT / "infra/terraform/environments/staging/main.tf"
ASSEMBLE = ROOT / "scripts/deploy/host/assemble-runtime-env.py"
PROD_COMPOSE = ROOT / "infra/compose/docker-compose.production.yml"
PROD_DEPLOY_RB = ROOT / "docs/runbooks/PRODUCTION_DEPLOY.md"
PROD_ROLLBACK_RB = ROOT / "docs/runbooks/PRODUCTION_ROLLBACK.md"

EXPECTED_MAIN = "4a4fe65fa7438c75208a0052f52b77f929ee3903"
EXPECTED_LIVE_SHA = "3c514943a8a0ec34d1df97d5a329d3acb4a86e07"
EXPECTED_INSTANCE = "i-0e49ddadd4ecc772d"
EXPECTED_DIGEST = "sha256:e55021f1e07bae5f2fc8a3bab038c71dc28ccad5cdc5abe76760f0cb8b942d90"
VERDICT = (
    "SPRINT 41 PARTIALLY COMPLETE — PRODUCTION LIVE; ROLLBACK VALIDATION, "
    "WWW CANONICALIZATION, CDN/WAF OWNER DECISION, STAGING PRESERVATION, "
    "AND LIVE IAM SIMULATION REMAIN OPEN"
)
REQUIRED_ENTRY_COUNT = 28
FORBIDDEN_COMPLETE_PHRASES = (
    "SPRINT 41 COMPLETE / CLOSED",
    "SPRINT 41 COMPLETE",
    "IMPLEMENTATION COMPLETE — EVIDENCE GAPS REMAIN",
)


def _matrix() -> dict:
    return json.loads(MATRIX_PATH.read_text(encoding="utf-8"))


def _read(path: Path) -> str:
    assert path.is_file(), f"missing {path}"
    return path.read_text(encoding="utf-8")


def test_reconciliation_records_starting_sha_verdict_and_no_mutation() -> None:
    text = _read(RECONCILIATION)
    assert EXPECTED_MAIN in text
    assert VERDICT in text
    assert "no production mutation occurred" in text.lower()
    assert "Rollback Production #1" in text or "Rollback Production #1" in text
    assert "not** rollback validation" in text.lower() or "not validation" in text.lower()
    assert "HTTP **200**" in text
    assert "www.piqsavi.com" in text
    assert (
        "OWNER DECISION PROPOSAL" in _read(CDN_PROPOSAL)
        or "not recorded as accepted" in _read(CDN_PROPOSAL).lower()
    )
    assert (
        "Do not trigger" in text
        or "Do not trigger rollback" in text.lower()
        or ("not trigger rollback" in text.lower())
    )
    for phrase in (
        "SPRINT 42 COMPLETE",
        "SPRINT 43 COMPLETE",
        "SPRINT 44 COMPLETE",
        "SPRINT 45 COMPLETE",
    ):
        assert phrase not in text


def test_acceptance_matrix_locks_open_gaps_and_completed_rows() -> None:
    matrix = _matrix()
    assert matrix["audit_baseline_sha"] == EXPECTED_MAIN
    assert matrix["sprint_closed"] is False
    assert matrix["sprints_42_45_closed"] is False
    assert matrix["production_mutation_performed"] is False
    assert matrix["rollback_validated_against_successful_release"] is False
    assert matrix["accidental_rollback_1_counted_as_validation"] is False
    assert matrix["www_redirects_to_apex"] is False
    assert matrix["cdn_waf_decision_recorded"] is False
    assert matrix["cdn_waf_decision_proposal_only"] is True
    assert matrix["live_iam_simulation_filed"] is False
    assert matrix["staging_currently_green"] is False
    assert matrix["live_production_git_sha"] == EXPECTED_LIVE_SHA
    assert matrix["live_production_instance_id"] == EXPECTED_INSTANCE
    assert matrix["status"] == VERDICT
    entries = matrix["entries"]
    assert len(entries) == REQUIRED_ENTRY_COUNT
    assert [row["id"] for row in entries] == list(range(1, REQUIRED_ENTRY_COUNT + 1))
    by_id = {row["id"]: row for row in entries}

    open_rows = {11, 12, 14, 15, 16, 22, 23, 27, 28}
    for row_id in open_rows:
        assert by_id[row_id]["verified_complete"] is False, row_id
        assert by_id[row_id]["incomplete"] is True, row_id

    complete_rows = {
        1,
        2,
        3,
        4,
        5,
        6,
        7,
        8,
        9,
        10,
        13,
        17,
        18,
        19,
        20,
        21,
        24,
        25,
        26,
    }
    for row_id in complete_rows:
        row = by_id[row_id]
        assert row["verified_complete"] is True, row_id
        assert row["code_config_present"] is True, row_id
        assert row["real_environment_exists"] is True, row_id
        assert row["production_evidence_exists"] is True, row_id

    assert by_id[22]["code_config_present"] is False
    assert by_id[23]["name"] == "CDN/WAF decision"
    assert by_id[12]["name"] == "Production rollback workflow"
    assert by_id[28]["name"] == "operational rollback proof"
    assert by_id[16]["production_evidence_exists"] is False
    assert by_id[14]["production_evidence_exists"] is False


def test_sprint_41_doc_is_partially_complete_not_closed() -> None:
    text = _read(SPRINT_41)
    assert "not** COMPLETE / CLOSED" in text or "not COMPLETE / CLOSED" in text.lower()
    for phrase in FORBIDDEN_COMPLETE_PHRASES:
        assert phrase not in text
    assert "**Status:** Planned" not in text
    assert "`www` redirects to canonical apex" in text
    assert "**not** validated" in text.lower()
    readme = _read(SPRINTS_README)
    assert "PARTIALLY COMPLETE" in readme
    sprint41_readme = readme.split("SPRINT_41_PRODUCTION_ENVIRONMENT_DEPLOY.md")[1][:400]
    assert "COMPLETE / CLOSED" not in sprint41_readme


def test_deploy_and_rollback_workflows_remain_and_do_not_apply_terraform() -> None:
    deploy = _read(DEPLOY_WF)
    rollback = _read(ROLLBACK_WF)
    assert STAGING_DEPLOY_WF.is_file()
    parsed_deploy = yaml.safe_load(deploy)
    parsed_rollback = yaml.safe_load(rollback)
    assert parsed_deploy["name"] == "Deploy Production"
    assert parsed_rollback["name"] == "Rollback Production"
    assert "environment: production" in deploy
    assert "environment: production" in rollback
    assert "DealBrain-ProductionDeploy" in deploy
    assert "DealBrain-ProductionRollback" in rollback
    assert "no terraform apply" in deploy.lower()
    assert "no terraform apply" in rollback.lower()
    assert "run: terraform apply" not in deploy
    assert "run: terraform apply" not in rollback
    assert "production-release-mutation" in deploy
    assert "production-release-mutation" in rollback
    assert "workflow_dispatch:" in deploy
    assert "workflow_dispatch:" in rollback


def test_alb_has_http_https_redirect_but_no_www_host_redirect() -> None:
    alb = _read(ALB_TF)
    assert 'protocol    = "HTTPS"' in alb
    assert "HTTP_301" in alb
    assert 'port        = "443"' in alb
    lowered = alb.lower()
    assert "www.piqsavi.com" not in lowered
    assert "host-header" not in lowered
    assert "host_header" not in lowered


def test_isolation_policies_and_assembler_refuse_opposite_secrets() -> None:
    iam = _read(IAM_TF)
    gha = _read(GHA_ROLE_TF)
    assemble = _read(ASSEMBLE)
    prod = _read(PROD_TF)
    staging = _read(STAGING_TF)
    assert "DenyOtherEnvironmentSecrets" in iam
    assert 'dealbrain/${var.environment == "staging" ? "production" : "staging"}/*' in iam
    assert "DenyOppositeEnvironmentSecretArns" in gha
    assert "DenySendCommandOppositeEnvironment" in gha
    assert "DenySecretsManagerValueAccess" in gha
    assert 'environment = "production"' in prod
    assert 'environment = "staging"' in staging
    prod_tfvars = ROOT / "infra/terraform/environments/production/terraform.tfvars.example"
    staging_tfvars = ROOT / "infra/terraform/environments/staging/terraform.tfvars.example"
    assert "10.20.0.0/16" in _read(prod_tfvars)
    assert "10.10.0.0/16" in _read(staging_tfvars)
    assert "refusing to read production secrets on staging host" in assemble
    assert "refusing to read staging secrets on production host" in assemble
    assert 'PRODUCTION_PUBLIC_BASE_URL = "https://piqsavi.com"' in assemble
    assert 'PRODUCTION_TRUSTED_HOSTS = "piqsavi.com,www.piqsavi.com"' in assemble
    assert "production/terraform.tfstate" in _read(ROOT / "infra/terraform/README.md")
    assert "staging/terraform.tfstate" in _read(ROOT / "infra/terraform/README.md")


def test_production_compose_same_origin_and_awslogs_without_stream_prefix() -> None:
    compose = _read(PROD_COMPOSE)
    assert "PUBLIC_APP_BASE_URL: ${PUBLIC_APP_BASE_URL:-https://piqsavi.com}" in compose
    assert "TRUSTED_HOSTS: ${TRUSTED_HOSTS:-piqsavi.com,www.piqsavi.com}" in compose
    assert "awslogs-stream-prefix" not in compose
    assert 'tag: "{{.Name}}"' in compose
    assert "/dealbrain/production/api" in compose


def test_deploy6_evidence_is_production_ok_without_secrets() -> None:
    evidence = json.loads(_read(DEPLOY6_EVIDENCE))
    assert evidence["final_status"] == "production_ok"
    assert evidence["git_sha"] == EXPECTED_LIVE_SHA
    assert evidence["ec2_instance_id"] == EXPECTED_INSTANCE
    assert evidence["image_digest"] == EXPECTED_DIGEST
    assert evidence["aws_account_id"] == "941035169846"
    assert evidence["aws_region"] == "us-east-1"
    assert evidence["alb_target_healthy"] is True
    blob = json.dumps(evidence)
    for forbidden in ("RESEND_API_KEY", "APP_SECRET_KEY", "password", "SecretString"):
        assert forbidden not in blob


def test_cdn_waf_proposal_is_not_an_accepted_decision() -> None:
    proposal = _read(CDN_PROPOSAL)
    recon = _read(RECONCILIATION)
    sprint = _read(SPRINT_41)
    assert "OWNER DECISION PROPOSAL" in proposal
    assert "not recorded as accepted" in proposal.lower()
    assert "CDN/WAF owner decision recorded" in recon or "CDN/WAF owner decision recorded" in sprint
    assert "OPEN" in recon
    assert "accepted decision" in proposal.lower() or "not recorded as accepted" in proposal.lower()
    assert "CloudFront" in proposal
    assert "Do not treat the proposal as an accepted decision" in recon


def test_runbooks_exist_and_forbid_reconciliation_dispatch() -> None:
    deploy_rb = _read(PROD_DEPLOY_RB)
    rollback_rb = _read(PROD_ROLLBACK_RB)
    assert "does not authorize a deploy" in deploy_rb.lower()
    assert "does not authorize a rollback" in rollback_rb.lower()
    assert "not** be counted as successful rollback validation" in rollback_rb.lower() or (
        "must **not** be counted" in rollback_rb
    )
    assert "34879465584" in rollback_rb


def test_master_gap_and_ext_register_are_current_without_closing_later_sprints() -> None:
    master = _read(MASTER)
    gap = _read(GAP)
    ext = _read(EXT)
    assert VERDICT in master or "PARTIALLY COMPLETE" in master
    assert "Sprint 42" in master
    assert "**COMPLETE / CLOSED**" not in master.split("| 42 |")[1][:120]
    assert "2026-09-18 Sprint 41 current-main reconciliation addendum" in gap
    assert "does **not** close Sprint 41" in gap or "does **not** mark Sprint 41 COMPLETE" in gap
    for ext_id in ("EXT-11", "EXT-12", "EXT-13", "EXT-14"):
        assert ext_id in ext
    assert "`provisioned`" in ext
    assert "2026-09-18 Sprint 41 production reconciliation addendum" in ext
    # Historical 2026-09-11 not-applied sentences remain as history.
    assert "Not applied. No live RDS" in ext

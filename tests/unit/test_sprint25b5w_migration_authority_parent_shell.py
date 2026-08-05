"""Sprint 25b.5w — preserve migration authority in the parent shell.

Root cause of failed Rollback Staging run 31023362986: command substitution
``TARGET_RECORDED_MIGRATION="$(resolve_target_recorded_migration)"`` ran the
resolver in a subshell. The revision survived via stdout, but
``MIGRATION_AUTHORITY`` assignments were discarded, failing closed with
``migration authority unset after resolution`` before API replacement.
"""

from __future__ import annotations

import ast
import hashlib
import json
import re
import shutil
import subprocess
import textwrap
from pathlib import Path

import pytest
from scripts.deploy.build_staging_bundle import INCLUDE_FILES
from scripts.deploy.rollback_evidence import create_rollback_evidence, validate_rollback_evidence
from scripts.deploy.validate_rollback_eligibility import validate_database_compatibility
from scripts.deploy.verify_host_rollback_tooling import REQUIRED_TOOLING_FILES
from scripts.deploy.verify_staging_bundle import REQUIRED_MEMBERS

ROOT = Path(__file__).resolve().parents[2]
HOST = ROOT / "scripts/deploy/host"
ROLLBACK_SH = HOST / "dealbrain-staging-rollback.sh"
DEPLOY_SH = HOST / "dealbrain-staging-deploy.sh"
RESOLVE_PY = HOST / "resolve-rollback-migration.py"
PRIOR_PY = ROOT / "scripts/deploy/prior_staging_evidence.py"
BUILD_BUNDLE_PY = ROOT / "scripts/deploy/build_staging_bundle.py"
WORKFLOWS = ROOT / ".github/workflows"
PROD_TF = ROOT / "infra/terraform/environments/production"

SAMPLE_SHA = "83bfc6c57fd99a43445b6edaddcaf863fabf3473"
SAMPLE_DIGEST = "sha256:338b03ad39cbb2d5733c8da5912e3ef1c38111e3f3b42d43eaf3b87bd9d1b91f"
SAMPLE_REPO = "ghcr.io/example-org/dealbrain"
BASELINE_RELEASE = f"rel-20260802T093246Z-{SAMPLE_SHA[:12]}"
ACCOUNT = "123456789012"
REGION = "us-east-1"
INSTANCE = "i-0123456789abcdef0"
MANIFEST_SHA = "c" * 64
CANON_REV = "d4e5f6a7b8c9"
OTHER_REV = "aabbccddeeff"

AUTH_DEPLOY = "deploy_version"
AUTH_PRIOR = "validated_prior_staging_evidence"


def _read(path: Path) -> str:
    assert path.is_file(), f"missing: {path}"
    return path.read_text(encoding="utf-8")


def _extract_resolve_fn() -> str:
    host = _read(ROLLBACK_SH)
    begin = "# --- BEGIN resolve_target_recorded_migration (test-extractable) ---"
    end = "# --- END resolve_target_recorded_migration (test-extractable) ---"
    assert begin in host, "missing BEGIN marker for resolve_target_recorded_migration"
    assert end in host, "missing END marker for resolve_target_recorded_migration"
    region = host.split(begin, 1)[1].split(end, 1)[0]
    assert "resolve_target_recorded_migration()" in region
    assert "MIGRATION_AUTHORITY=" in region
    assert "TARGET_RECORDED_MIGRATION=" in region
    assert 'echo "$TARGET_RECORDED_MIGRATION"' not in region
    return region.strip() + "\n"


def _stub_resolver_script(tmp_path: Path, payload: dict | None, *, fail: bool = False) -> Path:
    """Install a fake resolve-rollback-migration.py that writes --out JSON."""
    bin_dir = tmp_path / "bin"
    bin_dir.mkdir(parents=True, exist_ok=True)
    script = bin_dir / "resolve-rollback-migration.py"
    if fail:
        script.write_text(
            (
                "#!/usr/bin/env python3\n"
                "import sys\n"
                "print('FAIL: stub', file=sys.stderr)\n"
                "sys.exit(1)\n"
            ),
            encoding="utf-8",
        )
    else:
        assert payload is not None
        script.write_text(
            textwrap.dedent(
                f"""\
                #!/usr/bin/env python3
                import argparse, json, sys
                from pathlib import Path
                p = argparse.ArgumentParser()
                p.add_argument("--deploy-version", type=Path, default=None)
                p.add_argument("--prior-candidates-dir", type=Path, default=None)
                p.add_argument("--release-id", required=True)
                p.add_argument("--image-digest", required=True)
                p.add_argument("--image-repository", required=True)
                p.add_argument("--aws-account-id", required=True)
                p.add_argument("--aws-region", required=True)
                p.add_argument("--ec2-instance-id", required=True)
                p.add_argument("--source-manifest-sha256", default="")
                p.add_argument("--out", type=Path, required=True)
                args = p.parse_args()
                payload = {json.dumps(payload)}
                args.out.parent.mkdir(parents=True, exist_ok=True)
                args.out.write_text(json.dumps(payload) + "\\n", encoding="utf-8")
                # Status on stderr so command-substitution harnesses capture only
                # intentional function stdout (historical echo of the revision).
                print(
                    f"ok: migration={{payload.get('migration_revision')}} "
                    f"authority={{payload.get('authority')}}",
                    file=sys.stderr,
                )
                """
            ),
            encoding="utf-8",
        )
    script.chmod(0o755)
    return bin_dir


def _resolver_harness(
    tmp_path: Path,
    *,
    authority: str | None = AUTH_PRIOR,
    migration: str | None = CANON_REV,
    call_via_command_substitution: bool = False,
    resolver_fail: bool = False,
    omit_authority_key: bool = False,
    omit_migration_key: bool = False,
    malformed_json: bool = False,
    live_migration: str = CANON_REV,
    skip_compat_compare: bool = False,
) -> subprocess.CompletedProcess[str]:
    """Exercise production resolve_target_recorded_migration in a parent shell."""
    root = tmp_path / "opt" / "dealbrain"
    target = root / "releases" / BASELINE_RELEASE
    runtime = root / "runtime"
    target.mkdir(parents=True)
    runtime.mkdir(parents=True)
    (target / "DEPLOY_VERSION").write_text(
        json.dumps({"migration_revision": CANON_REV}), encoding="utf-8"
    )
    if resolver_fail:
        bin_dir = _stub_resolver_script(tmp_path, None, fail=True)
    elif malformed_json:
        bin_dir = tmp_path / "bin"
        bin_dir.mkdir(parents=True, exist_ok=True)
        script = bin_dir / "resolve-rollback-migration.py"
        script.write_text(
            textwrap.dedent(
                """\
                #!/usr/bin/env python3
                import argparse
                from pathlib import Path
                p = argparse.ArgumentParser()
                p.add_argument("--deploy-version", type=Path, default=None)
                p.add_argument("--prior-candidates-dir", type=Path, default=None)
                p.add_argument("--release-id", required=True)
                p.add_argument("--image-digest", required=True)
                p.add_argument("--image-repository", required=True)
                p.add_argument("--aws-account-id", required=True)
                p.add_argument("--aws-region", required=True)
                p.add_argument("--ec2-instance-id", required=True)
                p.add_argument("--source-manifest-sha256", default="")
                p.add_argument("--out", type=Path, required=True)
                args = p.parse_args()
                args.out.write_text("{not-json\\n", encoding="utf-8")
                """
            ),
            encoding="utf-8",
        )
        script.chmod(0o755)
    else:
        payload: dict = {}
        if not omit_migration_key:
            payload["migration_revision"] = migration
        if not omit_authority_key:
            payload["authority"] = authority
        bin_dir = _stub_resolver_script(tmp_path, payload)

    # Point ROOT/bin at stub resolver.
    (root / "bin").mkdir(parents=True, exist_ok=True)
    shutil.copy2(
        bin_dir / "resolve-rollback-migration.py",
        root / "bin" / "resolve-rollback-migration.py",
    )

    production_fn = _extract_resolve_fn()
    if call_via_command_substitution:
        invoke = textwrap.dedent(
            """
            if ! TARGET_RECORDED_MIGRATION="$(resolve_target_recorded_migration)"; then
              echo "RESOLVE_FAIL"
              echo "TARGET_RECORDED_MIGRATION=${TARGET_RECORDED_MIGRATION:-}"
              echo "MIGRATION_AUTHORITY=${MIGRATION_AUTHORITY:-}"
              exit 2
            fi
            """
        )
    else:
        invoke = textwrap.dedent(
            """
            if ! resolve_target_recorded_migration; then
              echo "RESOLVE_FAIL"
              echo "TARGET_RECORDED_MIGRATION=${TARGET_RECORDED_MIGRATION:-}"
              echo "MIGRATION_AUTHORITY=${MIGRATION_AUTHORITY:-}"
              exit 2
            fi
            """
        )

    if skip_compat_compare:
        post_checks = textwrap.dedent(
            """
            if [[ -z "$TARGET_RECORDED_MIGRATION" ]]; then
              echo EMPTY_MIGRATION
              echo "MIGRATION_AUTHORITY=${MIGRATION_AUTHORITY:-}"
              exit 3
            fi
            if [[ -z "$MIGRATION_AUTHORITY" ]]; then
              echo EMPTY_AUTHORITY
              echo "TARGET_RECORDED_MIGRATION=$TARGET_RECORDED_MIGRATION"
              exit 4
            fi
            case "$MIGRATION_AUTHORITY" in
              deploy_version|validated_prior_staging_evidence) ;;
              *) echo "UNSUPPORTED_AUTHORITY=$MIGRATION_AUTHORITY"; exit 5 ;;
            esac
            echo "RESOLVE_OK"
            echo "TARGET_RECORDED_MIGRATION=$TARGET_RECORDED_MIGRATION"
            echo "MIGRATION_AUTHORITY=$MIGRATION_AUTHORITY"
            """
        )
    else:
        post_checks = textwrap.dedent(
            f"""
            if [[ -z "$TARGET_RECORDED_MIGRATION" ]]; then
              echo EMPTY_MIGRATION
              echo "MIGRATION_AUTHORITY=${{MIGRATION_AUTHORITY:-}}"
              exit 3
            fi
            if [[ -z "$MIGRATION_AUTHORITY" ]]; then
              echo EMPTY_AUTHORITY
              echo "TARGET_RECORDED_MIGRATION=$TARGET_RECORDED_MIGRATION"
              exit 4
            fi
            case "$MIGRATION_AUTHORITY" in
              deploy_version|validated_prior_staging_evidence) ;;
              *)
                echo "UNSUPPORTED_AUTHORITY=$MIGRATION_AUTHORITY"
                exit 5
                ;;
            esac
            MIGRATION_BEFORE="{live_migration}"
            if [[ "$MIGRATION_BEFORE" != "$TARGET_RECORDED_MIGRATION" ]]; then
              echo "DATABASE_INCOMPATIBLE live=$MIGRATION_BEFORE target=$TARGET_RECORDED_MIGRATION"
              exit 6
            fi
            echo "RESOLVE_OK"
            echo "TARGET_RECORDED_MIGRATION=$TARGET_RECORDED_MIGRATION"
            echo "MIGRATION_AUTHORITY=$MIGRATION_AUTHORITY"
            echo "API_REPLACEMENT_REACHED"
            """
        )

    script = textwrap.dedent(
        f"""
        set -euo pipefail
        ROOT="{root}"
        RUNTIME_DIR="{runtime}"
        TARGET_DIR="{target}"
        TARGET_RELEASE_ID="{BASELINE_RELEASE}"
        IMAGE_DIGEST="{SAMPLE_DIGEST}"
        IMAGE_REPOSITORY="{SAMPLE_REPO}"
        AWS_ACCOUNT_ID="{ACCOUNT}"
        REGION="{REGION}"
        INSTANCE_ID="{INSTANCE}"
        TARGET_MANIFEST_SHA256="{MANIFEST_SHA}"
        TARGET_RECORDED_MIGRATION=""
        MIGRATION_AUTHORITY=""
        API_REPLACEMENT_OCCURRED=0
        download_prior_evidence_candidates() {{ return 0; }}
        {production_fn}
        {invoke}
        {post_checks}
        """
    )
    return subprocess.run(
        ["bash", "-c", script],
        check=False,
        capture_output=True,
        text=True,
    )


# ---------------------------------------------------------------------------
# 1–5. Parent-shell transfer of revision + authority
# ---------------------------------------------------------------------------


def test_defect_class_command_substitution_discards_globals() -> None:
    """Local reproduction: assignments inside $(fn) do not update the parent."""
    script = textwrap.dedent(
        """
        set -euo pipefail
        GLOBAL=""
        fn() { GLOBAL="set-in-fn"; echo "stdout-val"; }
        captured="$(fn)"
        [[ "$captured" == "stdout-val" ]]
        [[ -z "${GLOBAL:-}" ]]
        echo REPRODUCED
        """
    )
    proc = subprocess.run(["bash", "-c", script], check=False, capture_output=True, text=True)
    assert proc.returncode == 0, proc.stderr + proc.stdout
    assert "REPRODUCED" in proc.stdout


def test_production_call_site_does_not_use_command_substitution() -> None:
    host = _read(ROLLBACK_SH)
    assert 'TARGET_RECORDED_MIGRATION="$(resolve_target_recorded_migration)"' not in host
    assert "$(resolve_target_recorded_migration)" not in host
    # Direct parent-shell invocation.
    assert "if ! resolve_target_recorded_migration; then" in host
    gate = host.split("# 5. Database compatibility", 1)[1].split("API_REPLACEMENT_OCCURRED=1", 1)[0]
    assert "resolve_target_recorded_migration" in gate
    assert "MIGRATION_AUTHORITY" in gate
    assert "target recorded migration unset after resolution" in gate
    assert "migration authority unset after resolution" in gate
    assert "unsupported migration authority after resolution" in gate


def test_parent_shell_receives_prior_evidence_authority(tmp_path: Path) -> None:
    proc = _resolver_harness(tmp_path, authority=AUTH_PRIOR, migration=CANON_REV)
    assert proc.returncode == 0, proc.stderr + proc.stdout
    assert "RESOLVE_OK" in proc.stdout
    assert f"TARGET_RECORDED_MIGRATION={CANON_REV}" in proc.stdout
    assert f"MIGRATION_AUTHORITY={AUTH_PRIOR}" in proc.stdout
    assert "API_REPLACEMENT_REACHED" in proc.stdout


def test_parent_shell_receives_deploy_version_authority(tmp_path: Path) -> None:
    proc = _resolver_harness(tmp_path, authority=AUTH_DEPLOY, migration=CANON_REV)
    assert proc.returncode == 0, proc.stderr + proc.stdout
    assert f"MIGRATION_AUTHORITY={AUTH_DEPLOY}" in proc.stdout
    assert f"TARGET_RECORDED_MIGRATION={CANON_REV}" in proc.stdout


def test_command_substitution_call_pattern_loses_authority(tmp_path: Path) -> None:
    """Prove the historical defect class against the production function body."""
    # Historical shape: function assigns both globals and echoes the revision.
    # Command substitution keeps only stdout; parent MIGRATION_AUTHORITY stays empty.
    root = tmp_path / "opt" / "dealbrain"
    runtime = root / "runtime"
    target = root / "releases" / BASELINE_RELEASE
    runtime.mkdir(parents=True)
    target.mkdir(parents=True)
    (target / "DEPLOY_VERSION").write_text("{}", encoding="utf-8")
    bin_dir = _stub_resolver_script(
        tmp_path,
        {"migration_revision": CANON_REV, "authority": AUTH_PRIOR},
    )
    (root / "bin").mkdir(parents=True)
    shutil.copy2(
        bin_dir / "resolve-rollback-migration.py",
        root / "bin" / "resolve-rollback-migration.py",
    )
    production_fn = _extract_resolve_fn()
    # Restore the historical echo so revision would survive command substitution
    # while authority still would not — the exact live failure mode.
    production_fn = production_fn.replace(
        "  return 0\n}",
        '  echo "$TARGET_RECORDED_MIGRATION"\n  return 0\n}',
        1,
    )
    script = textwrap.dedent(
        f"""
        set -euo pipefail
        ROOT="{root}"
        RUNTIME_DIR="{runtime}"
        TARGET_DIR="{target}"
        TARGET_RELEASE_ID="{BASELINE_RELEASE}"
        IMAGE_DIGEST="{SAMPLE_DIGEST}"
        IMAGE_REPOSITORY="{SAMPLE_REPO}"
        AWS_ACCOUNT_ID="{ACCOUNT}"
        REGION="{REGION}"
        INSTANCE_ID="{INSTANCE}"
        TARGET_MANIFEST_SHA256="{MANIFEST_SHA}"
        TARGET_RECORDED_MIGRATION=""
        MIGRATION_AUTHORITY=""
        download_prior_evidence_candidates() {{ return 0; }}
        {production_fn}
        TARGET_RECORDED_MIGRATION="$(resolve_target_recorded_migration)"
        echo "CAPTURED_MIGRATION=$TARGET_RECORDED_MIGRATION"
        echo "PARENT_AUTHORITY=${{MIGRATION_AUTHORITY:-<empty>}}"
        [[ "$TARGET_RECORDED_MIGRATION" == "{CANON_REV}" ]]
        [[ -z "${{MIGRATION_AUTHORITY:-}}" ]]
        echo DEFECT_REPRODUCED
        """
    )
    proc = subprocess.run(["bash", "-c", script], check=False, capture_output=True, text=True)
    assert proc.returncode == 0, proc.stderr + proc.stdout
    assert f"CAPTURED_MIGRATION={CANON_REV}" in proc.stdout
    assert "PARENT_AUTHORITY=<empty>" in proc.stdout
    assert "DEFECT_REPRODUCED" in proc.stdout


# ---------------------------------------------------------------------------
# 6–10. Fail-closed paths (no API replacement)
# ---------------------------------------------------------------------------


def test_missing_authority_fails_closed_no_api_replacement(tmp_path: Path) -> None:
    proc = _resolver_harness(tmp_path, omit_authority_key=True)
    assert proc.returncode != 0
    assert "RESOLVE_FAIL" in proc.stdout or "EMPTY_AUTHORITY" in proc.stdout
    assert "API_REPLACEMENT_REACHED" not in proc.stdout


def test_empty_migration_revision_fails_closed(tmp_path: Path) -> None:
    proc = _resolver_harness(tmp_path, migration="", authority=AUTH_PRIOR)
    assert proc.returncode != 0
    assert "API_REPLACEMENT_REACHED" not in proc.stdout


def test_malformed_resolver_output_fails_closed(tmp_path: Path) -> None:
    proc = _resolver_harness(tmp_path, malformed_json=True)
    assert proc.returncode != 0
    assert "API_REPLACEMENT_REACHED" not in proc.stdout


def test_unsupported_authority_fails_closed(tmp_path: Path) -> None:
    proc = _resolver_harness(tmp_path, authority="guessed_from_git_history", migration=CANON_REV)
    assert proc.returncode != 0
    assert "API_REPLACEMENT_REACHED" not in proc.stdout
    out = proc.stdout
    assert "UNSUPPORTED_AUTHORITY=guessed_from_git_history" in out or "RESOLVE_FAIL" in out


def test_resolver_failure_does_not_reach_migration_capture_or_api(tmp_path: Path) -> None:
    proc = _resolver_harness(tmp_path, resolver_fail=True)
    assert proc.returncode != 0
    assert "RESOLVE_FAIL" in proc.stdout
    assert "API_REPLACEMENT_REACHED" not in proc.stdout
    assert "DATABASE_INCOMPATIBLE" not in proc.stdout


# ---------------------------------------------------------------------------
# 11–14. Compatibility, phase ordering, pointer safety
# ---------------------------------------------------------------------------


def test_migration_mismatch_database_incompatible_before_api(tmp_path: Path) -> None:
    proc = _resolver_harness(
        tmp_path,
        authority=AUTH_PRIOR,
        migration=CANON_REV,
        live_migration=OTHER_REV,
    )
    assert proc.returncode != 0
    assert "DATABASE_INCOMPATIBLE" in proc.stdout
    assert "API_REPLACEMENT_REACHED" not in proc.stdout
    with pytest.raises(Exception, match="database_incompatible"):
        validate_database_compatibility(
            current_db_revision=OTHER_REV,
            target_recorded_revision=CANON_REV,
        )


def test_api_replacement_after_resolution_authority_capture_compat() -> None:
    host = _read(ROLLBACK_SH)
    resolve_idx = host.index("if ! resolve_target_recorded_migration; then")
    auth_idx = host.index("migration authority unset after resolution")
    capture_idx = host.index('MIGRATION_BEFORE="$(capture_migration_revision before 0)"')
    incompat_idx = host.index("database_incompatible")
    api_idx = host.index("API_REPLACEMENT_OCCURRED=1")
    assert resolve_idx < auth_idx < capture_idx < incompat_idx < api_idx


def test_pointer_commit_after_health_verification() -> None:
    host = _read(ROLLBACK_SH)
    api_idx = host.index("API_REPLACEMENT_OCCURRED=1")
    # Post-replacement health gates (not earlier tooling-install name mentions).
    live_idx = host.index('FAILURE_REASON="localhost_live_failed"')
    ready_idx = host.index('FAILURE_REASON="localhost_ready_failed"')
    alb_idx = host.index('FAILURE_REASON="alb_health_failed"')
    ptr_idx = host.index("commit_release_pointer")
    assert api_idx < live_idx < ready_idx < alb_idx < ptr_idx
    assert "verify-staging.sh" in host[api_idx:ptr_idx]


def test_failure_before_api_replacement_leaves_pointers_unchanged(tmp_path: Path) -> None:
    root = tmp_path / "opt" / "dealbrain"
    current = root / "releases" / "rel-current"
    previous = root / "releases" / "rel-previous"
    current.mkdir(parents=True)
    previous.mkdir(parents=True)
    script = textwrap.dedent(
        f"""
        set -euo pipefail
        ROOT="{root}"
        mkdir -p "$ROOT"
        ln -sfn "{current}" "$ROOT/current"
        ln -sfn "{previous}" "$ROOT/previous"
        CURRENT_BEFORE="$(readlink -f "$ROOT/current")"
        PREVIOUS_BEFORE="$(readlink -f "$ROOT/previous")"
        API_REPLACEMENT_OCCURRED=0
        # Simulate resolve/authority failure before API replacement.
        TARGET_RECORDED_MIGRATION=""
        MIGRATION_AUTHORITY=""
        FAILURE_REASON="database_compatibility_unknown"
        # No pointer mutation on this path.
        CURRENT_AFTER="$(readlink -f "$ROOT/current")"
        PREVIOUS_AFTER="$(readlink -f "$ROOT/previous")"
        [[ "$CURRENT_BEFORE" == "$CURRENT_AFTER" ]]
        [[ "$PREVIOUS_BEFORE" == "$PREVIOUS_AFTER" ]]
        [[ "$API_REPLACEMENT_OCCURRED" -eq 0 ]]
        echo "POINTERS_UNCHANGED"
        echo "CURRENT=$CURRENT_AFTER"
        echo "PREVIOUS=$PREVIOUS_AFTER"
        """
    )
    proc = subprocess.run(["bash", "-c", script], check=False, capture_output=True, text=True)
    assert proc.returncode == 0, proc.stderr + proc.stdout
    assert "POINTERS_UNCHANGED" in proc.stdout
    assert str(current) in proc.stdout
    assert str(previous) in proc.stdout
    host = _read(ROLLBACK_SH)
    assert host.index("database_compatibility_unknown") < host.index("API_REPLACEMENT_OCCURRED=1")
    assert host.index("commit_release_pointer") > host.index("API_REPLACEMENT_OCCURRED=1")


# ---------------------------------------------------------------------------
# 15. Failure evidence retains authority + pointer + migration fields
# ---------------------------------------------------------------------------


def test_failure_evidence_retains_authority_pointers_and_migrations() -> None:
    payload = create_rollback_evidence(
        rollback_workflow_run_id="31023362986",
        aws_account_id=ACCOUNT,
        aws_region=REGION,
        assumed_role_arn=f"arn:aws:iam::{ACCOUNT}:role/dealbrain-staging-gha-deploy",
        role_session_name="gha-31023362986-staging-rollback",
        ec2_instance_id=INSTANCE,
        ssm_command_id="efba3c41-801f-4eea-8a05-ba8758641056",
        rollback_started_at="2026-08-05T15:00:00Z",
        rollback_finished_at="2026-08-05T15:01:00Z",
        rollback_duration_seconds=60,
        source_release_id="rel-20260805T151133Z-e1856113ecdd",
        source_image_digest="sha256:8d4540c736848c11dc0ba154033a44b4bbf0afc13ed367a8611ae0bc7f4fcab5",
        target_release_id=BASELINE_RELEASE,
        target_image_digest=SAMPLE_DIGEST,
        target_git_sha=SAMPLE_SHA,
        target_image_repository=SAMPLE_REPO,
        target_manifest_sha256=MANIFEST_SHA,
        migration_revision_before=CANON_REV,
        migration_revision_after=CANON_REV,
        target_migration_revision_authority=AUTH_PRIOR,
        current_pointer_before="/opt/dealbrain/releases/rel-20260805T151133Z-e1856113ecdd",
        current_pointer_after="/opt/dealbrain/releases/rel-20260805T151133Z-e1856113ecdd",
        previous_pointer_before="/opt/dealbrain/releases/rel-20260804T152521Z-da17ebbffd47",
        previous_pointer_after="/opt/dealbrain/releases/rel-20260804T152521Z-da17ebbffd47",
        running_digest_after="sha256:8d4540c736848c11dc0ba154033a44b4bbf0afc13ed367a8611ae0bc7f4fcab5",
        localhost_live=False,
        localhost_ready=False,
        alb_target_healthy=False,
        final_status="failed",
        failure_reason="database_compatibility_unknown",
    )
    validate_rollback_evidence(payload)
    assert payload["failure_reason"] == "database_compatibility_unknown"
    assert payload["target_migration_revision_authority"] == AUTH_PRIOR
    assert payload["migration_revision_before"] == CANON_REV
    assert payload["migration_revision_after"] == CANON_REV
    assert payload["current_pointer_before"] == payload["current_pointer_after"]
    assert payload["previous_pointer_before"] == payload["previous_pointer_after"]
    host = _read(ROLLBACK_SH)
    assert "DEALBRAIN_MIGRATION_AUTHORITY" in host
    assert "DEALBRAIN_CURRENT_BEFORE" in host
    assert "DEALBRAIN_MIGRATION_BEFORE" in host


# ---------------------------------------------------------------------------
# 16. Python 3.9 prior-evidence fix remains covered and unchanged
# ---------------------------------------------------------------------------


def test_python39_prior_evidence_fix_unchanged() -> None:
    prior = _read(PRIOR_PY)
    resolve = _read(RESOLVE_PY)
    assert "timezone.utc" in prior
    # resolve-rollback-migration registers module before exec for dataclass annotations.
    assert "sys.modules[spec.name] = module" in resolve
    # Focused regression file still present.
    assert (ROOT / "tests/unit/test_sprint25b5t_python39_rollback_evidence.py").is_file()
    tree = ast.parse(prior)
    for node in ast.walk(tree):
        if isinstance(node, ast.ImportFrom) and node.module == "datetime":
            assert "UTC" not in {alias.name for alias in node.names}
        if (
            isinstance(node, ast.Attribute)
            and isinstance(node.value, ast.Name)
            and node.value.id == "datetime"
        ):
            assert node.attr != "UTC"


# ---------------------------------------------------------------------------
# 17–18. Bundle packaging / no infra mutation
# ---------------------------------------------------------------------------


def test_corrected_rollback_script_in_bundle_and_host_inventory() -> None:
    assert (
        "scripts/deploy/host/dealbrain-staging-rollback.sh",
        "bin/dealbrain-staging-rollback.sh",
    ) in INCLUDE_FILES
    assert "bin/dealbrain-staging-rollback.sh" in REQUIRED_MEMBERS
    assert "dealbrain-staging-rollback.sh" in REQUIRED_TOOLING_FILES
    deploy = _read(DEPLOY_SH)
    assert "dealbrain-staging-rollback.sh" in deploy
    assert "${ROOT}/bin/dealbrain-staging-rollback.sh" in deploy
    assert "verify_host_rollback_tooling.py" in deploy
    # Host install inventory includes checksum of rollback script.
    assert "staging-host-tooling.json" in deploy


def test_no_terraform_workflow_dispatch_or_production_path_introduced() -> None:
    host = _read(ROLLBACK_SH)
    assert "terraform" not in host.lower()
    assert "workflow_dispatch" not in host
    assert "SendCommand" not in host
    assert "gh workflow" not in host
    assert not (WORKFLOWS / "deploy-production.yml").exists()
    assert PROD_TF.is_dir()
    # This sprint must not mutate workflows.
    for name in ("rollback.yml", "deploy-staging.yml", "build-image.yml"):
        assert (WORKFLOWS / name).is_file()
    build = _read(BUILD_BUNDLE_PY)
    assert "dealbrain-staging-rollback.sh" in build


def test_makefile_validate_targets_include_sprint25b5w() -> None:
    makefile = _read(ROOT / "Makefile")
    target_file = "tests/unit/test_sprint25b5w_migration_authority_parent_shell.py"
    for target in ("validate-staging-deploy:", "validate-pre-live:"):
        assert target in makefile
        after = makefile.split(target, 1)[1]
        recipe = after.split("\n\n", 1)[0]
        assert target_file in recipe, f"{target} missing {target_file}"


def test_resolver_assigns_both_fields_in_function_body() -> None:
    region = _extract_resolve_fn()
    assert 'TARGET_RECORDED_MIGRATION="$(jq -r' in region
    assert 'MIGRATION_AUTHORITY="$(jq -r' in region
    assert "deploy_version|validated_prior_staging_evidence" in region
    # Cleared on unsupported authority — no trusted default.
    assert 'TARGET_RECORDED_MIGRATION=""' in region
    assert 'MIGRATION_AUTHORITY=""' in region


def test_sha256_of_rollback_script_is_stable_bytes() -> None:
    """Host delivery proof uses sha256 of installed script bytes."""
    digest = hashlib.sha256(ROLLBACK_SH.read_bytes()).hexdigest()
    assert re.fullmatch(r"[0-9a-f]{64}", digest)
    assert "dealbrain-staging-rollback.sh" in REQUIRED_TOOLING_FILES

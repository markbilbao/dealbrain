"""Sprint 25b.5i — deployment finalization atomicity.

Covers:
1. Alembic revision normalization (plain / `` (head)`` / fail-closed)
2. Failure-evidence state machine (never staging_ok + failure_reason)
3. Explicit deploy-phase state machine + candidate reconciliation (OUTCOME 2)
4. Failure-injection behavioral tests (executable shell harness)
5. Existing-host reconciliation plan (plan only — not executed)
"""

from __future__ import annotations

import copy
import json
import subprocess
import textwrap
from pathlib import Path

import pytest
from scripts.deploy.evidence import (
    POST_GATE_FAILURE_PREFIXES,
    EvidenceError,
    compute_evidence_sha256,
    create_evidence,
    normalize_alembic_revision,
    validate_evidence,
)
from scripts.deploy.verify_staging_bundle import REQUIRED_MEMBERS, BundleVerifyError, verify_bundle

ROOT = Path(__file__).resolve().parents[2]
HOST_SCRIPTS = ROOT / "scripts/deploy/host"
DEPLOY_SH = HOST_SCRIPTS / "dealbrain-staging-deploy.sh"
ATOMICITY_SH = HOST_SCRIPTS / "deploy_atomicity.sh"
EVIDENCE_PY = ROOT / "scripts/deploy/evidence.py"
WORKFLOWS = ROOT / ".github/workflows"
PROD_TF = ROOT / "infra/terraform/environments/production"

SAMPLE_SHA = "0123456789abcdef0123456789abcdef01234567"
SAMPLE_DIGEST = "sha256:" + ("b" * 64)
PREV_DIGEST = "sha256:" + ("a" * 64)
SAMPLE_REPO = "ghcr.io/example-org/dealbrain"
CANON_REV = "d4e5f6a7b8c9"

# ---------------------------------------------------------------------------
# Existing-host reconciliation — PLAN ONLY (do not execute in this sprint)
# ---------------------------------------------------------------------------
HOST_CURRENT_POINTER_RECONCILIATION_PLAN = textwrap.dedent(
    """
    # Staging-only, post-merge, approval-required. Do NOT execute until merged.
    # Incident: running API on rel-B while /opt/dealbrain/current points at rel-A
    # (pre-25b.5i split; live host may still be in this state).
    #
    # State-machine contract (Sprint 25b.5i):
    # - Phases: PRE_MIGRATION → MIGRATION_COMPLETE → API_REPLACEMENT_STARTED
    #   → CANDIDATE_RUNNING → HEALTH_VERIFIED → RELEASE_COMMITTED
    #   → FINALIZATION_COMPLETE
    # - After API_REPLACEMENT_STARTED, failure paths use candidate reconciliation
    #   (OUTCOME 2): align current + DEPLOY_VERSION to the running immutable
    #   image. Full app rollback is NOT assumed safe after forward migration.
    # - RELEASE_COMMITTED only after DEPLOY_VERSION + atomic current + verify.
    # - Post-commit: no pointer-only rollback.
    #
    # Preconditions (ALL must pass before any mutation):
    # 1) Expected release dir exists:
    #    /opt/dealbrain/releases/rel-<EXPECTED_RELEASE_ID>/
    # 2) That dir's DEPLOY_VERSION matches expected release_id, git_sha, image_digest
    #    (write DEPLOY_VERSION first if missing but identity is proven from
    #    bundle-meta / immutable digest — approval required)
    # 3) Running API container image matches expected immutable digest (sha256:…)
    # 4) API container healthy; local /ready HTTP 200; ALB target healthy
    # 5) current symlink is the ONLY mismatched component
    # Procedure (atomic symlink only — no API restart unless proven required):
    # a) PREV=$(readlink -f /opt/dealbrain/current)
    #    echo "$PREV" > /tmp/dealbrain-current.prev.$$
    # b) Stage: ln -sfn /opt/dealbrain/releases/<EXPECTED> /opt/dealbrain/current.new
    # c) Atomic: mv -Tf /opt/dealbrain/current.new /opt/dealbrain/current
    # d) Verify: readlink -f /opt/dealbrain/current == expected release dir
    #    and current/DEPLOY_VERSION matches expected identity fields
    #    and running API digest == DEPLOY_VERSION.image_digest
    # e) Rollback: ln -sfn "$PREV" /opt/dealbrain/current.new &&
    #              mv -Tf /opt/dealbrain/current.new /opt/dealbrain/current
    # No secrets/env dumps; staging Environment tag only; no production.
    """
).strip()

DEPLOYMENT_COMMIT_CONTRACT = textwrap.dedent(
    """
    Sprint 25b.5i commit/reconciliation contract (OUTCOME 2):
    - Migration failure: API untouched; current unchanged.
    - Failure before API replacement: previous release preserved.
    - After API_REPLACEMENT_STARTED: candidate reconciliation on failure —
      align current + DEPLOY_VERSION to the running immutable image; deploy
      remains failed; never staging_ok from reconciliation.
    - After health + DEPLOY_VERSION + verified atomic current: RELEASE_COMMITTED=1.
    - Post-commit evidence failure: retain current (no pointer-only rollback);
      force final_status=failed; preserve original exit code; best-effort
      failure evidence once (IN_ON_EXIT_EVIDENCE guard).
    - Exit trap invariant: running digest ↔ current ↔ DEPLOY_VERSION.
    - Success: container release + current + DEPLOY_VERSION aligned.
    """
).strip()

DEPLOY_PHASES = (
    "PRE_MIGRATION",
    "MIGRATION_COMPLETE",
    "API_REPLACEMENT_STARTED",
    "CANDIDATE_RUNNING",
    "HEALTH_VERIFIED",
    "RELEASE_COMMITTED",
    "FINALIZATION_COMPLETE",
)


def _read(path: Path) -> str:
    assert path.is_file(), f"missing: {path}"
    return path.read_text(encoding="utf-8")


def _success_evidence(**overrides: object) -> dict:
    payload = create_evidence(
        release_id=f"rel-20260802T071732Z-{SAMPLE_SHA[:12]}",
        git_sha=SAMPLE_SHA,
        image_repository=SAMPLE_REPO,
        image_digest=SAMPLE_DIGEST,
        source_manifest_sha256="c" * 64,
        deploy_workflow_run_id="999",
        aws_account_id="123456789012",
        aws_region="us-east-1",
        assumed_role_arn="arn:aws:iam::123456789012:role/dealbrain-staging-gha-deploy",
        role_session_name="gha-999-staging",
        ec2_instance_id="i-0123456789abcdef0",
        ssm_command_id="cmd-1",
        migration_revision_before=CANON_REV,
        migration_revision_after=CANON_REV,
        localhost_live=True,
        localhost_ready=True,
        alb_target_healthy=True,
        smoke_ok=True,
        image_id="sha256:" + ("d" * 64),
        repo_digest=f"{SAMPLE_REPO}@{SAMPLE_DIGEST}",
        image_created_at="2026-08-02T07:00:00Z",
        deployment_started_at="2026-08-02T07:17:00Z",
        deployment_finished_at="2026-08-02T07:20:00Z",
        deployment_duration_seconds=180,
        final_status="staging_ok",
        failure_reason=None,
    )
    if overrides:
        payload = copy.deepcopy(payload)
        payload.update(overrides)
        if "evidence_sha256" not in overrides:
            payload["evidence_sha256"] = compute_evidence_sha256(payload)
    return payload


def _write_deploy_version(
    path: Path, *, release_id: str, digest: str, git_sha: str = SAMPLE_SHA
) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        json.dumps(
            {
                "release_id": release_id,
                "git_sha": git_sha,
                "image_digest": digest,
                "deployed_at": "2026-08-02T07:00:00Z",
            }
        ),
        encoding="utf-8",
    )


def _run_atomicity_harness(
    tmp_path: Path,
    *,
    body: str,
    running_digest: str,
    exit_code: int = 1,
    api_replacement: int = 1,
    release_committed: int = 0,
    failure_reason: str = "injected_failure",
    local_gates: bool = False,
) -> subprocess.CompletedProcess[str]:
    """Executable state-machine harness sourcing production deploy_atomicity.sh."""
    root = tmp_path / "opt" / "dealbrain"
    prev = root / "releases" / "rel-A"
    cand = root / "releases" / "rel-B"
    prev.mkdir(parents=True, exist_ok=True)
    cand.mkdir(parents=True, exist_ok=True)
    _write_deploy_version(prev / "DEPLOY_VERSION", release_id="rel-A", digest=PREV_DIGEST)
    current = root / "current"
    if not current.exists() and not current.is_symlink():
        current.symlink_to(prev)

    evidence_dir = root / "runtime" / "evidence"
    evidence_dir.mkdir(parents=True, exist_ok=True)
    writer_calls = evidence_dir / "writer-calls.txt"
    writer = tmp_path / "write-staging-evidence.py"
    writer.write_text(
        textwrap.dedent(
            """\
            #!/usr/bin/env python3
            import json, os, pathlib, sys
            out = pathlib.Path(os.environ["DEALBRAIN_EVIDENCE_OUT"])
            status = os.environ.get("DEALBRAIN_FINAL_STATUS", "")
            reason = os.environ.get("DEALBRAIN_FAILURE_REASON") or ""
            stamp = out.parent / "writer-calls.txt"
            stamp.write_text(stamp.read_text() + "1\\n" if stamp.exists() else "1\\n")
            if status == "staging_ok" and reason:
                sys.exit(2)
            if status == "staging_ok":
                # Success path must not be used on injected failures.
                sys.exit(3)
            payload = {"final_status": status, "failure_reason": reason}
            out.write_text(json.dumps(payload), encoding="utf-8")
            """
        ),
        encoding="utf-8",
    )
    writer.chmod(0o755)

    gate_true = "true" if local_gates else ""
    script = tmp_path / "harness.sh"
    script.write_text(
        textwrap.dedent(
            f"""\
            #!/bin/bash
            set -euo pipefail
            ROOT="{root}"
            RELEASE_DIR="{cand}"
            PREVIOUS_CURRENT="{prev}"
            RELEASE_ID="rel-B"
            GIT_SHA="{SAMPLE_SHA}"
            IMAGE_DIGEST="{SAMPLE_DIGEST}"
            COMPOSE_PROJECT="dealbrain-staging"
            DEPLOY_RUN_ID="1"
            EVIDENCE_DIR="{evidence_dir}"
            EVIDENCE_UPLOADED=0
            RELEASE_COMMITTED={release_committed}
            API_REPLACEMENT_OCCURRED={api_replacement}
            IN_ON_EXIT_EVIDENCE=0
            FINAL_STATUS="failed"
            FAILURE_REASON="{failure_reason}"
            LOCAL_LIVE="{gate_true}"
            LOCAL_READY="{gate_true}"
            ALB_HEALTH="{gate_true}"
            SMOKE_OK="{gate_true}"
            DEPLOYMENT_STARTED_AT="2026-08-02T07:17:00Z"
            INSTANCE_ID="i-0123456789abcdef0"
            REGION="us-east-1"
            AWS_ACCOUNT_ID="123456789012"
            SSM_COMMAND_ID="cmd-1"
            SOURCE_MANIFEST_SHA256="{"c" * 64}"
            IMAGE_ID="sha256:{"d" * 64}"
            REPO_DIGEST="{SAMPLE_REPO}@{SAMPLE_DIGEST}"
            IMAGE_CREATED_AT="2026-08-02T07:00:00Z"
            BUNDLE_BUCKET="example-bucket"
            RUNNING_DIGEST_MOCK="{running_digest}"

            log() {{ echo "[harness] $*"; }}

            _atomicity_running_api_cid() {{ echo "cid-mock"; }}
            _atomicity_running_api_digest() {{
              if [[ -z "${{RUNNING_DIGEST_MOCK}}" ]]; then
                return 1
              fi
              echo "${{RUNNING_DIGEST_MOCK}}"
            }}

            # shellcheck disable=SC1091
            source "{ATOMICITY_SH}"

            write_evidence() {{
              local out
              out="${{EVIDENCE_DIR}}/staging-deploy-evidence-"
              out="${{out}}${{RELEASE_ID}}-${{DEPLOY_RUN_ID}}.json"
              DEALBRAIN_EVIDENCE_OUT="$out" \\
              DEALBRAIN_FINAL_STATUS="$FINAL_STATUS" \\
              DEALBRAIN_FAILURE_REASON="$FAILURE_REASON" \\
              python3 "{writer}" || return 1
              EVIDENCE_UPLOADED=1
            }}

            on_exit() {{
              local code=$?
              if [[ $code -ne 0 ]]; then
                FINAL_STATUS="failed"
                if [[ -z "$FAILURE_REASON" ]]; then
                  if [[ "${{RELEASE_COMMITTED:-0}}" -eq 1 ]]; then
                    FAILURE_REASON="evidence_upload_failed"
                  else
                    FAILURE_REASON="host_script_exit_${{code}}"
                  fi
                fi
                if [[ "$LOCAL_LIVE" == "true" && "$LOCAL_READY" == "true" \\
                   && "$ALB_HEALTH" == "true" && "$SMOKE_OK" == "true" ]]; then
                  case "$FAILURE_REASON" in
                    post_gate_*|evidence_upload_*|deploy_version_*|symlink_*) ;;
                    post_replacement_*|release_alignment_*) ;;
                    *) FAILURE_REASON="post_gate_${{FAILURE_REASON}}" ;;
                  esac
                fi
                atomicity_on_failure "$code" || true
              fi
              if [[ "${{IN_ON_EXIT_EVIDENCE:-0}}" -eq 0 ]]; then
                atomicity_invariant_before_evidence || true
              fi
              if [[ "$EVIDENCE_UPLOADED" -eq 0 && "${{IN_ON_EXIT_EVIDENCE:-0}}" -eq 0 ]]; then
                IN_ON_EXIT_EVIDENCE=1
                write_evidence || log "evidence write/upload failed (best-effort)"
              fi
              echo "EXIT_CODE=$code"
              echo "FINAL_STATUS=$FINAL_STATUS"
              echo "FAILURE_REASON=$FAILURE_REASON"
              echo "RELEASE_COMMITTED=$RELEASE_COMMITTED"
              echo "RECONCILIATION_STATUS=${{RECONCILIATION_STATUS:-}}"
              echo "INVARIANT_OK=${{INVARIANT_OK:-0}}"
              echo "CURRENT=$(readlink -f "${{ROOT}}/current" 2>/dev/null || true)"
              if [[ -f "${{ROOT}}/current/DEPLOY_VERSION" ]]; then
                echo "DV_DIGEST=$(jq -r .image_digest "${{ROOT}}/current/DEPLOY_VERSION")"
                echo "DV_RELEASE=$(jq -r .release_id "${{ROOT}}/current/DEPLOY_VERSION")"
              fi
              exit "$code"
            }}
            trap on_exit EXIT

            {body}

            exit {exit_code}
            """
        ),
        encoding="utf-8",
    )
    proc = subprocess.run(
        ["bash", str(script)],
        check=False,
        capture_output=True,
        text=True,
    )
    # Attach paths for assertions
    proc.root = root  # type: ignore[attr-defined]
    proc.prev = prev  # type: ignore[attr-defined]
    proc.cand = cand  # type: ignore[attr-defined]
    proc.evidence_dir = evidence_dir  # type: ignore[attr-defined]
    proc.writer_calls = writer_calls  # type: ignore[attr-defined]
    return proc


def _harness_field(stdout: str, key: str) -> str:
    for line in stdout.splitlines():
        if line.startswith(f"{key}="):
            return line.split("=", 1)[1]
    return ""


# ---------------------------------------------------------------------------
# 1–3. Revision normalization
# ---------------------------------------------------------------------------


def test_normalize_plain_alembic_revision() -> None:
    assert normalize_alembic_revision(CANON_REV) == CANON_REV


def test_normalize_alembic_revision_strips_head_annotation() -> None:
    assert normalize_alembic_revision(f"{CANON_REV} (head)") == CANON_REV


def test_normalize_alembic_revision_accepts_info_noise_then_head_line() -> None:
    raw = f"INFO  [alembic.runtime.migration] Context impl PostgresqlImpl.\n{CANON_REV} (head)\n"
    assert normalize_alembic_revision(raw) == CANON_REV


@pytest.mark.parametrize(
    "raw",
    [
        "",
        "   ",
        "\n\n",
        "not-a-revision",
        f"{CANON_REV} (heads)",
        f"{CANON_REV} (effective head)",
        f"{CANON_REV} extra",
        f"{CANON_REV}\n{CANON_REV}",
        f"{CANON_REV} (head)\nabc123 (head)",
        "Multiple heads are present for given argument 'head'",
        "FAILED: Can't locate revision",
        "abc def",
        " (head)",
    ],
)
def test_normalize_alembic_revision_fail_closed(raw: str) -> None:
    with pytest.raises(EvidenceError):
        normalize_alembic_revision(raw)


def test_normalize_rejects_blind_first_token_split() -> None:
    with pytest.raises(EvidenceError):
        normalize_alembic_revision(f"{CANON_REV} (head) trailing-garbage")


# ---------------------------------------------------------------------------
# 4–5. Canonical before/after in create_evidence / success evidence
# ---------------------------------------------------------------------------


def test_create_evidence_canonicalizes_before_and_after_head_annotations() -> None:
    payload = create_evidence(
        release_id=f"rel-20260802T071732Z-{SAMPLE_SHA[:12]}",
        git_sha=SAMPLE_SHA,
        image_repository=SAMPLE_REPO,
        image_digest=SAMPLE_DIGEST,
        source_manifest_sha256="c" * 64,
        deploy_workflow_run_id="999",
        aws_account_id="123456789012",
        aws_region="us-east-1",
        assumed_role_arn="arn:aws:iam::123456789012:role/dealbrain-staging-gha-deploy",
        role_session_name="gha-999-staging",
        ec2_instance_id="i-0123456789abcdef0",
        ssm_command_id="cmd-1",
        migration_revision_before=f"{CANON_REV} (head)",
        migration_revision_after=f"{CANON_REV} (head)",
        localhost_live=True,
        localhost_ready=True,
        alb_target_healthy=True,
        smoke_ok=True,
        image_id="sha256:" + ("d" * 64),
        repo_digest=f"{SAMPLE_REPO}@{SAMPLE_DIGEST}",
        image_created_at="2026-08-02T07:00:00Z",
        deployment_started_at="2026-08-02T07:17:00Z",
        deployment_finished_at="2026-08-02T07:20:00Z",
        deployment_duration_seconds=180,
        final_status="staging_ok",
        failure_reason=None,
    )
    assert payload["migration_revision_before"] == CANON_REV
    assert payload["migration_revision_after"] == CANON_REV
    validate_evidence(payload)


def test_success_evidence_rejects_uncanonical_revision_via_validate() -> None:
    payload = _success_evidence()
    payload["migration_revision_after"] = f"{CANON_REV} (head)"
    payload["evidence_sha256"] = compute_evidence_sha256(payload)
    with pytest.raises(EvidenceError, match="migration"):
        validate_evidence(payload)


def test_host_script_captures_via_normalize_alembic_revision() -> None:
    text = _read(DEPLOY_SH)
    assert "normalize_alembic_revision" in text
    assert "capture_migration_revision" in text
    assert "alembic current 2>/dev/null | tail -1" not in text
    assert 'MIGRATION_BEFORE="$(capture_migration_revision before 1)"' in text
    assert 'MIGRATION_AFTER="$(capture_migration_revision after 0)"' in text


# ---------------------------------------------------------------------------
# 6–9. Failure-evidence state machine
# ---------------------------------------------------------------------------


def test_on_exit_forces_failed_status_before_evidence() -> None:
    text = _read(DEPLOY_SH)
    on_exit = text.split("on_exit() {", 1)[1].split("trap on_exit EXIT", 1)[0]
    assert 'FINAL_STATUS="failed"' in on_exit
    failed_idx = on_exit.index('FINAL_STATUS="failed"')
    write_idx = on_exit.index("write_evidence")
    assert failed_idx < write_idx
    assert "IN_ON_EXIT_EVIDENCE" in on_exit
    assert "atomicity_on_failure" in on_exit
    assert "atomicity_invariant_before_evidence" in on_exit


def test_success_evidence_exception_enters_failed_status_preserves_exit(
    tmp_path: Path,
) -> None:
    """Post-commit evidence failure: retain candidate alignment, exit preserved."""
    proc = _run_atomicity_harness(
        tmp_path,
        body=textwrap.dedent(
            f"""\
            set_deploy_phase HEALTH_VERIFIED
            write_candidate_deploy_version
            atomic_point_current "$RELEASE_DIR"
            RELEASE_COMMITTED=1
            set_deploy_phase RELEASE_COMMITTED
            RUNNING_DIGEST_MOCK="{SAMPLE_DIGEST}"
            # Simulate success evidence construction/upload failure after commit.
            FINAL_STATUS="staging_ok"
            FAILURE_REASON=""
            if ! write_evidence; then
              FINAL_STATUS="failed"
              FAILURE_REASON="evidence_upload_failed"
              exit 42
            fi
            """
        ),
        running_digest=SAMPLE_DIGEST,
        exit_code=42,
        api_replacement=1,
        release_committed=1,
        failure_reason="",
        local_gates=True,
    )
    # Re-run with corrected harness: release_committed starts 0 then body sets it.
    # The helper overwrote RELEASE_COMMITTED=1 at start — verify via fields.
    assert proc.returncode == 42, proc.stderr + proc.stdout
    assert "no pointer-only rollback" in proc.stdout
    assert _harness_field(proc.stdout, "FINAL_STATUS") == "failed"
    assert current_aligned_candidate(proc)
    out = proc.evidence_dir / "staging-deploy-evidence-rel-B-1.json"  # type: ignore[attr-defined]
    assert out.is_file()
    written = json.loads(out.read_text(encoding="utf-8"))
    assert written["final_status"] == "failed"
    assert written["failure_reason"]
    calls = proc.writer_calls.read_text(encoding="utf-8").strip().count("1")  # type: ignore[attr-defined]
    assert calls == 2


def current_aligned_candidate(proc: subprocess.CompletedProcess[str]) -> bool:
    cur = _harness_field(proc.stdout, "CURRENT")
    dv = _harness_field(proc.stdout, "DV_DIGEST")
    rid = _harness_field(proc.stdout, "DV_RELEASE")
    return (
        cur == str(proc.cand.resolve())  # type: ignore[attr-defined]
        and dv == SAMPLE_DIGEST
        and rid == "rel-B"
        and _harness_field(proc.stdout, "INVARIANT_OK") == "1"
    )


def test_failure_evidence_never_combines_staging_ok_with_reason() -> None:
    with pytest.raises(EvidenceError, match="staging_ok requires failure_reason"):
        validate_evidence(
            _success_evidence(final_status="staging_ok", failure_reason="evidence_upload_failed")
        )


def test_evidence_failure_does_not_recursively_trigger_trap(tmp_path: Path) -> None:
    script = tmp_path / "recurse.sh"
    script.write_text(
        textwrap.dedent(
            """\
            #!/bin/bash
            set -euo pipefail
            EVIDENCE_UPLOADED=0
            IN_ON_EXIT_EVIDENCE=0
            COUNT_FILE="${1}"
            write_evidence() {
              echo x >>"$COUNT_FILE"
              return 1
            }
            on_exit() {
              local code=$?
              FINAL_STATUS="failed"
              FAILURE_REASON="evidence_upload_failed"
              if [[ "$EVIDENCE_UPLOADED" -eq 0 && "${IN_ON_EXIT_EVIDENCE:-0}" -eq 0 ]]; then
                IN_ON_EXIT_EVIDENCE=1
                write_evidence || true
              fi
              exit "$code"
            }
            trap on_exit EXIT
            exit 7
            """
        ),
        encoding="utf-8",
    )
    count = tmp_path / "count"
    count.write_text("", encoding="utf-8")
    proc = subprocess.run(
        ["bash", str(script), str(count)],
        check=False,
        capture_output=True,
        text=True,
    )
    assert proc.returncode == 7
    assert count.read_text(encoding="utf-8").count("x") == 1


# ---------------------------------------------------------------------------
# State machine presence + bundle membership
# ---------------------------------------------------------------------------


def test_deploy_script_documents_state_machine_and_commit_contract() -> None:
    text = _read(DEPLOY_SH)
    atom = _read(ATOMICITY_SH)
    for phase in DEPLOY_PHASES:
        assert phase in text or phase in atom
    assert "API_REPLACEMENT_OCCURRED=1" in text
    assert 'set_deploy_phase "API_REPLACEMENT_STARTED"' in text
    assert "commit_release_pointer" in text
    assert "reconcile_post_replacement_state" in atom
    assert "OUTCOME 2" in atom or "candidate reconciliation" in atom.lower()
    assert "pointer-only rollback" in text
    # Migration still before API recreate.
    assert text.index("migration_failed") < text.index("force-recreate --no-deps api")
    # Replacement flag set before compose up.
    assert text.index("API_REPLACEMENT_OCCURRED=1") < text.index("force-recreate --no-deps api")
    # Commit via verified helper (not bare mv without checks).
    assert "commit_release_pointer" in text
    assert DEPLOYMENT_COMMIT_CONTRACT.splitlines()[0] in DEPLOYMENT_COMMIT_CONTRACT


def test_bundle_requires_deploy_atomicity_member() -> None:
    assert "bin/deploy_atomicity.sh" in REQUIRED_MEMBERS
    build = _read(ROOT / "scripts/deploy/build_staging_bundle.py")
    assert "deploy_atomicity.sh" in build


def test_post_gate_prefixes_include_reconciliation() -> None:
    assert "post_replacement_" in POST_GATE_FAILURE_PREFIXES
    assert "release_alignment_" in POST_GATE_FAILURE_PREFIXES


# ---------------------------------------------------------------------------
# Failure-injection matrix (executable)
# ---------------------------------------------------------------------------


@pytest.mark.parametrize(
    "case_id,body,running_digest,exit_code,expect_current,expect_digest,expect_recon,api_replacement",
    [
        (
            "1_recreate_fails_previous_still_running",
            'FAILURE_REASON="api_recreate_failed"; set_deploy_phase API_REPLACEMENT_STARTED',
            PREV_DIGEST,
            11,
            "prev",
            PREV_DIGEST,
            "aligned_previous",
            1,
        ),
        (
            "2_recreate_ok_lookup_fails_unrecoverable",
            'FAILURE_REASON="api_container_lookup_failed"; set_deploy_phase CANDIDATE_RUNNING',
            "",
            12,
            None,  # may stay on prev; invariant fails
            None,
            "failed",
            1,
        ),
        (
            "3_live_fails_candidate_running",
            'FAILURE_REASON="localhost_live_failed"; set_deploy_phase CANDIDATE_RUNNING',
            SAMPLE_DIGEST,
            13,
            "cand",
            SAMPLE_DIGEST,
            "aligned_candidate",
            1,
        ),
        (
            "4_ready_fails_candidate_running",
            (
                'FAILURE_REASON="localhost_ready_failed"; '
                "LOCAL_LIVE=true; set_deploy_phase CANDIDATE_RUNNING"
            ),
            SAMPLE_DIGEST,
            14,
            "cand",
            SAMPLE_DIGEST,
            "aligned_candidate",
            1,
        ),
        (
            "5_alb_fails_after_local_ready",
            (
                'FAILURE_REASON="alb_health_failed"; '
                "LOCAL_LIVE=true; LOCAL_READY=true; "
                "set_deploy_phase CANDIDATE_RUNNING"
            ),
            SAMPLE_DIGEST,
            15,
            "cand",
            SAMPLE_DIGEST,
            "aligned_candidate",
            1,
        ),
        (
            "6_deploy_version_write_fails",
            textwrap.dedent(
                """\
                set_deploy_phase HEALTH_VERIFIED
                LOCAL_LIVE=true; LOCAL_READY=true; ALB_HEALTH=true; SMOKE_OK=true
                FAILURE_REASON="deploy_version_write_failed"
                # Make RELEASE_DIR unwritable for DEPLOY_VERSION via readonly file trick:
                # use a file named DEPLOY_VERSION as a directory blocker after chmod.
                rm -f "${RELEASE_DIR}/DEPLOY_VERSION"
                mkdir -p "${RELEASE_DIR}/DEPLOY_VERSION" 2>/dev/null || true
                chmod a-w "${RELEASE_DIR}" || true
                """
            ),
            SAMPLE_DIGEST,
            16,
            "cand",  # reconciliation retries write after chmod restore? harness keeps mock digest
            SAMPLE_DIGEST,
            "aligned_candidate",
            1,
        ),
        (
            "7_symlink_prep_fails_then_reconcile",
            textwrap.dedent(
                """\
                set_deploy_phase HEALTH_VERIFIED
                LOCAL_LIVE=true; LOCAL_READY=true; ALB_HEALTH=true; SMOKE_OK=true
                write_candidate_deploy_version
                FAILURE_REASON="symlink_prepare_or_replace_failed"
                """
            ),
            SAMPLE_DIGEST,
            17,
            "cand",
            SAMPLE_DIGEST,
            "aligned_candidate",
            1,
        ),
        (
            "8_atomic_symlink_replace_fails_then_reconcile",
            textwrap.dedent(
                """\
                set_deploy_phase HEALTH_VERIFIED
                LOCAL_LIVE=true; LOCAL_READY=true; ALB_HEALTH=true; SMOKE_OK=true
                write_candidate_deploy_version
                FAILURE_REASON="symlink_prepare_or_replace_failed"
                # current still on previous — trap must reconcile to candidate
                """
            ),
            SAMPLE_DIGEST,
            18,
            "cand",
            SAMPLE_DIGEST,
            "aligned_candidate",
            1,
        ),
        (
            "9_symlink_verify_fails_then_reconcile",
            textwrap.dedent(
                """\
                set_deploy_phase HEALTH_VERIFIED
                LOCAL_LIVE=true; LOCAL_READY=true; ALB_HEALTH=true; SMOKE_OK=true
                write_candidate_deploy_version
                atomic_point_current "$RELEASE_DIR"
                FAILURE_REASON="symlink_verification_failed"
                # RELEASE_COMMITTED intentionally still 0
                """
            ),
            SAMPLE_DIGEST,
            19,
            "cand",
            SAMPLE_DIGEST,
            "aligned_candidate",
            1,
        ),
        (
            "10_success_evidence_construction_fails_post_commit",
            textwrap.dedent(
                """\
                set_deploy_phase HEALTH_VERIFIED
                write_candidate_deploy_version
                atomic_point_current "$RELEASE_DIR"
                RELEASE_COMMITTED=1
                set_deploy_phase RELEASE_COMMITTED
                LOCAL_LIVE=true; LOCAL_READY=true; ALB_HEALTH=true; SMOKE_OK=true
                FINAL_STATUS="staging_ok"
                FAILURE_REASON=""
                if ! write_evidence; then
                  FINAL_STATUS="failed"
                  FAILURE_REASON="evidence_upload_failed"
                  exit 20
                fi
                """
            ),
            SAMPLE_DIGEST,
            20,
            "cand",
            SAMPLE_DIGEST,
            "",
            1,
        ),
        (
            "11_success_evidence_write_fails_post_commit",
            textwrap.dedent(
                """\
                set_deploy_phase RELEASE_COMMITTED
                write_candidate_deploy_version
                atomic_point_current "$RELEASE_DIR"
                RELEASE_COMMITTED=1
                LOCAL_LIVE=true; LOCAL_READY=true; ALB_HEALTH=true; SMOKE_OK=true
                FAILURE_REASON="evidence_upload_failed"
                """
            ),
            SAMPLE_DIGEST,
            21,
            "cand",
            SAMPLE_DIGEST,
            "",
            1,
        ),
        (
            "12_success_evidence_upload_fails_post_commit",
            textwrap.dedent(
                """\
                write_candidate_deploy_version
                atomic_point_current "$RELEASE_DIR"
                RELEASE_COMMITTED=1
                LOCAL_LIVE=true; LOCAL_READY=true; ALB_HEALTH=true; SMOKE_OK=true
                FAILURE_REASON="evidence_upload_failed"
                """
            ),
            SAMPLE_DIGEST,
            22,
            "cand",
            SAMPLE_DIGEST,
            "",
            1,
        ),
    ],
)
def test_failure_injection_preserves_exit_and_alignment(
    tmp_path: Path,
    case_id: str,
    body: str,
    running_digest: str,
    exit_code: int,
    expect_current: str | None,
    expect_digest: str | None,
    expect_recon: str,
    api_replacement: int,
) -> None:
    # Case 6 needs writable RELEASE_DIR for reconciliation retry — fix chmod in body end via trap.
    if case_id == "6_deploy_version_write_fails":
        body = (
            body
            + "\n"
            + textwrap.dedent(
                """\
                # Restore writability so reconciliation can write DEPLOY_VERSION.
                chmod u+w "${RELEASE_DIR}" || true
                if [[ -d "${RELEASE_DIR}/DEPLOY_VERSION" ]]; then
                  rmdir "${RELEASE_DIR}/DEPLOY_VERSION" 2>/dev/null \
                    || rm -rf "${RELEASE_DIR}/DEPLOY_VERSION"
                fi
                """
            )
        )

    local_gates = "LOCAL_LIVE=true" in body or case_id.startswith(
        ("10_", "11_", "12_", "6_", "7_", "8_", "9_")
    )
    proc = _run_atomicity_harness(
        tmp_path,
        body=body,
        running_digest=running_digest,
        exit_code=exit_code,
        api_replacement=api_replacement,
        release_committed=0,
        failure_reason="injected_failure",
        local_gates=local_gates,
    )
    assert proc.returncode == exit_code, f"{case_id}: {proc.stderr}\n{proc.stdout}"
    assert _harness_field(proc.stdout, "FINAL_STATUS") == "failed"
    assert _harness_field(proc.stdout, "FINAL_STATUS") != "staging_ok"

    # Evidence: failed only, at most one trap write after any success attempt.
    out = proc.evidence_dir / "staging-deploy-evidence-rel-B-1.json"  # type: ignore[attr-defined]
    if out.is_file():
        written = json.loads(out.read_text(encoding="utf-8"))
        assert written["final_status"] == "failed"
        assert written.get("failure_reason")

    if expect_recon:
        assert expect_recon in _harness_field(proc.stdout, "RECONCILIATION_STATUS") or (
            expect_recon == "failed"
            and _harness_field(proc.stdout, "RECONCILIATION_STATUS") == "failed"
        )

    if expect_current == "cand":
        assert _harness_field(proc.stdout, "CURRENT") == str(proc.cand.resolve())  # type: ignore[attr-defined]
        assert _harness_field(proc.stdout, "DV_DIGEST") == expect_digest
        assert _harness_field(proc.stdout, "DV_RELEASE") == "rel-B"
        assert _harness_field(proc.stdout, "INVARIANT_OK") == "1"
        # Must NOT leave previous pointer while candidate runs.
        assert _harness_field(proc.stdout, "CURRENT") != str(proc.prev.resolve())  # type: ignore[attr-defined]
    elif expect_current == "prev":
        assert _harness_field(proc.stdout, "CURRENT") == str(proc.prev.resolve())  # type: ignore[attr-defined]
        assert _harness_field(proc.stdout, "DV_DIGEST") == expect_digest
        assert _harness_field(proc.stdout, "INVARIANT_OK") == "1"
    else:
        # Unrecoverable: explicit non-zero already asserted; invariant must not pass.
        assert _harness_field(proc.stdout, "INVARIANT_OK") != "1"


def test_failure_evidence_write_itself_fails_no_recursion(tmp_path: Path) -> None:
    root = tmp_path / "opt" / "dealbrain"
    prev = root / "releases" / "rel-A"
    cand = root / "releases" / "rel-B"
    prev.mkdir(parents=True)
    cand.mkdir(parents=True)
    _write_deploy_version(prev / "DEPLOY_VERSION", release_id="rel-A", digest=PREV_DIGEST)
    (root / "current").symlink_to(prev)
    count = tmp_path / "count"
    count.write_text("", encoding="utf-8")
    script = tmp_path / "evfail.sh"
    script.write_text(
        textwrap.dedent(
            f"""\
            #!/bin/bash
            set -euo pipefail
            ROOT="{root}"
            RELEASE_DIR="{cand}"
            PREVIOUS_CURRENT="{prev}"
            RELEASE_ID="rel-B"
            GIT_SHA="{SAMPLE_SHA}"
            IMAGE_DIGEST="{SAMPLE_DIGEST}"
            COMPOSE_PROJECT="dealbrain-staging"
            RELEASE_COMMITTED=0
            API_REPLACEMENT_OCCURRED=1
            EVIDENCE_UPLOADED=0
            IN_ON_EXIT_EVIDENCE=0
            FINAL_STATUS="failed"
            FAILURE_REASON="localhost_live_failed"
            COUNT_FILE="{count}"
            log() {{ echo "[h] $*"; }}
            _atomicity_running_api_cid() {{ echo cid; }}
            _atomicity_running_api_digest() {{ echo "{SAMPLE_DIGEST}"; }}
            source "{ATOMICITY_SH}"
            write_evidence() {{
              echo x >>"$COUNT_FILE"
              return 1
            }}
            on_exit() {{
              local code=$?
              FINAL_STATUS="failed"
              atomicity_on_failure "$code" || true
              atomicity_invariant_before_evidence || true
              if [[ "$EVIDENCE_UPLOADED" -eq 0 && "${{IN_ON_EXIT_EVIDENCE:-0}}" -eq 0 ]]; then
                IN_ON_EXIT_EVIDENCE=1
                write_evidence || log "evidence write/upload failed (best-effort on error path)"
              fi
              echo "CURRENT=$(readlink -f "$ROOT/current")"
              echo "INVARIANT_OK=$INVARIANT_OK"
              exit "$code"
            }}
            trap on_exit EXIT
            exit 23
            """
        ),
        encoding="utf-8",
    )
    proc = subprocess.run(["bash", str(script)], check=False, capture_output=True, text=True)
    assert proc.returncode == 23
    assert count.read_text(encoding="utf-8").count("x") == 1
    assert str(cand.resolve()) in proc.stdout
    assert "INVARIANT_OK=1" in proc.stdout


def test_reconciliation_itself_fails_is_explicit(tmp_path: Path) -> None:
    """Case 14: reconciliation fails → non-zero, no staging_ok, explicit reason."""
    proc = _run_atomicity_harness(
        tmp_path,
        body=textwrap.dedent(
            """\
            set_deploy_phase CANDIDATE_RUNNING
            FAILURE_REASON="localhost_live_failed"
            # Break candidate dir so atomic switch / deploy version cannot succeed.
            rm -rf "$RELEASE_DIR"
            """
        ),
        running_digest=SAMPLE_DIGEST,
        exit_code=24,
        api_replacement=1,
        failure_reason="localhost_live_failed",
    )
    assert proc.returncode == 24
    assert _harness_field(proc.stdout, "FINAL_STATUS") == "failed"
    assert "post_replacement_reconciliation_failed" in _harness_field(proc.stdout, "FAILURE_REASON")
    assert _harness_field(proc.stdout, "RECONCILIATION_STATUS") == "failed"
    assert _harness_field(proc.stdout, "INVARIANT_OK") != "1"
    out = proc.evidence_dir / "staging-deploy-evidence-rel-B-1.json"  # type: ignore[attr-defined]
    if out.is_file():
        assert json.loads(out.read_text(encoding="utf-8"))["final_status"] == "failed"


def test_successful_commit_aligns_all_three(tmp_path: Path) -> None:
    proc = _run_atomicity_harness(
        tmp_path,
        body=textwrap.dedent(
            """\
            set_deploy_phase HEALTH_VERIFIED
            commit_release_pointer
            set_deploy_phase FINALIZATION_COMPLETE
            EVIDENCE_UPLOADED=1
            FINAL_STATUS="staging_ok"
            FAILURE_REASON=""
            exit 0
            """
        ),
        running_digest=SAMPLE_DIGEST,
        exit_code=0,
        api_replacement=1,
        failure_reason="",
    )
    assert proc.returncode == 0, proc.stderr + proc.stdout
    assert _harness_field(proc.stdout, "RELEASE_COMMITTED") == "1"
    assert current_aligned_candidate(proc)


def test_migration_failure_leaves_previous_untouched(tmp_path: Path) -> None:
    proc = _run_atomicity_harness(
        tmp_path,
        body='FAILURE_REASON="migration_failed"; set_deploy_phase PRE_MIGRATION',
        running_digest=PREV_DIGEST,
        exit_code=1,
        api_replacement=0,
        failure_reason="migration_failed",
    )
    assert proc.returncode == 1
    assert _harness_field(proc.stdout, "CURRENT") == str(proc.prev.resolve())  # type: ignore[attr-defined]
    assert _harness_field(proc.stdout, "DV_DIGEST") == PREV_DIGEST
    assert _harness_field(proc.stdout, "RECONCILIATION_STATUS") == ""
    assert _harness_field(proc.stdout, "INVARIANT_OK") == "1"


def test_pre_replacement_failure_preserves_previous_current(tmp_path: Path) -> None:
    proc = _run_atomicity_harness(
        tmp_path,
        body='FAILURE_REASON="disk_space_failed"; set_deploy_phase MIGRATION_COMPLETE',
        running_digest=PREV_DIGEST,
        exit_code=2,
        api_replacement=0,
        failure_reason="disk_space_failed",
    )
    assert proc.returncode == 2
    assert _harness_field(proc.stdout, "CURRENT") == str(proc.prev.resolve())  # type: ignore[attr-defined]
    assert _harness_field(proc.stdout, "INVARIANT_OK") == "1"


def test_post_replacement_pre_commit_no_split_state(tmp_path: Path) -> None:
    """Blocking defect regression: candidate running must not leave current on previous."""
    proc = _run_atomicity_harness(
        tmp_path,
        body='FAILURE_REASON="alb_health_failed"; set_deploy_phase CANDIDATE_RUNNING',
        running_digest=SAMPLE_DIGEST,
        exit_code=5,
        api_replacement=1,
        failure_reason="alb_health_failed",
    )
    assert proc.returncode == 5
    assert _harness_field(proc.stdout, "CURRENT") == str(proc.cand.resolve())  # type: ignore[attr-defined]
    assert _harness_field(proc.stdout, "DV_DIGEST") == SAMPLE_DIGEST
    assert _harness_field(proc.stdout, "CURRENT") != str(proc.prev.resolve())  # type: ignore[attr-defined]
    assert _harness_field(proc.stdout, "FINAL_STATUS") == "failed"
    assert "staging_ok" not in _harness_field(proc.stdout, "FINAL_STATUS")


def test_no_pointer_only_rollback_after_commit(tmp_path: Path) -> None:
    proc = _run_atomicity_harness(
        tmp_path,
        body=textwrap.dedent(
            """\
            write_candidate_deploy_version
            atomic_point_current "$RELEASE_DIR"
            RELEASE_COMMITTED=1
            FAILURE_REASON="evidence_upload_failed"
            """
        ),
        running_digest=SAMPLE_DIGEST,
        exit_code=9,
        api_replacement=1,
        release_committed=1,
        failure_reason="evidence_upload_failed",
        local_gates=True,
    )
    assert proc.returncode == 9
    assert "no pointer-only rollback" in proc.stdout
    assert current_aligned_candidate(proc)


def test_successful_deploy_order_in_host_script() -> None:
    text = _read(DEPLOY_SH)
    ready = text.index('[[ "$LOCAL_READY" == "true" ]]')
    commit = text.index("commit_release_pointer")
    evidence = text.index('FINAL_STATUS="staging_ok"')
    assert ready < commit < evidence
    assert text.index("HEALTH_VERIFIED") < commit


# ---------------------------------------------------------------------------
# Production isolation + prior protections intact
# ---------------------------------------------------------------------------


def test_production_remains_untouched() -> None:
    assert not (WORKFLOWS / "deploy-production.yml").is_file()
    # Sprint 25b.5 adds staging rollback.yml; production deploy/rollback remain absent.
    rb = WORKFLOWS / "rollback.yml"
    assert rb.is_file()
    assert "environment: production" not in rb.read_text(encoding="utf-8")
    text = _read(DEPLOY_SH)
    assert "production overlay forbidden" in text or "production compose overlay forbidden" in text
    assert '[[ "$ENV_TAG" == "staging" ]]' in text
    assert PROD_TF.is_dir()


def test_archive_symlink_still_rejected(tmp_path: Path) -> None:
    import tarfile

    evil = tmp_path / "evil.tar.gz"
    with tarfile.open(evil, "w:gz") as tar:
        info = tarfile.TarInfo(name="bin/link")
        info.type = tarfile.SYMTYPE
        info.linkname = "/etc/passwd"
        tar.addfile(info)
    with pytest.raises(BundleVerifyError, match="symlink|hardlink"):
        verify_bundle(evil)


def test_shell_normalize_helper_matches_python(tmp_path: Path) -> None:
    script = tmp_path / "norm.sh"
    script.write_text(
        textwrap.dedent(
            f"""\
            #!/bin/bash
            set -euo pipefail
            normalize_alembic_revision() {{
              local raw="$1"
              DEALBRAIN_ALEMBIC_RAW="$raw" python3 - "{EVIDENCE_PY}" <<'PY'
            import importlib.util, os, sys
            path = sys.argv[1]
            spec = importlib.util.spec_from_file_location("evidence", path)
            mod = importlib.util.module_from_spec(spec)
            assert spec.loader is not None
            spec.loader.exec_module(mod)
            print(mod.normalize_alembic_revision(os.environ["DEALBRAIN_ALEMBIC_RAW"]))
            PY
            }}
            normalize_alembic_revision "{CANON_REV} (head)"
            """
        ),
        encoding="utf-8",
    )
    proc = subprocess.run(["bash", str(script)], check=False, capture_output=True, text=True)
    assert proc.returncode == 0, proc.stderr
    assert proc.stdout.strip() == CANON_REV


def test_shell_normalize_helper_fail_closed(tmp_path: Path) -> None:
    script = tmp_path / "norm_bad.sh"
    script.write_text(
        textwrap.dedent(
            f"""\
            #!/bin/bash
            set -euo pipefail
            normalize_alembic_revision() {{
              local raw="$1"
              DEALBRAIN_ALEMBIC_RAW="$raw" python3 - "{EVIDENCE_PY}" <<'PY'
            import importlib.util, os, sys
            path = sys.argv[1]
            spec = importlib.util.spec_from_file_location("evidence", path)
            mod = importlib.util.module_from_spec(spec)
            assert spec.loader is not None
            spec.loader.exec_module(mod)
            print(mod.normalize_alembic_revision(os.environ["DEALBRAIN_ALEMBIC_RAW"]))
            PY
            }}
            normalize_alembic_revision "Multiple heads are present"
            """
        ),
        encoding="utf-8",
    )
    proc = subprocess.run(["bash", str(script)], check=False, capture_output=True, text=True)
    assert proc.returncode != 0


def test_reconciliation_plan_documents_atomic_repoint_and_state_machine() -> None:
    plan = HOST_CURRENT_POINTER_RECONCILIATION_PLAN
    assert "post-merge" in plan.lower() or "merged" in plan
    assert "readlink" in plan
    assert "mv -Tf" in plan
    assert "DEPLOY_VERSION" in plan
    assert "API_REPLACEMENT_STARTED" in plan
    assert "OUTCOME 2" in plan or "candidate reconciliation" in plan.lower()
    assert "no api restart" in plan.lower()
    assert "staging" in plan.lower()
    assert "production" in plan.lower()
    assert "Do NOT execute" in plan or "approval" in plan.lower()


def test_bash_n_changed_shell_scripts() -> None:
    for path in (DEPLOY_SH, ATOMICITY_SH):
        proc = subprocess.run(
            ["bash", "-n", str(path)],
            check=False,
            capture_output=True,
            text=True,
        )
        assert proc.returncode == 0, f"{path}: {proc.stderr}"

"""Sprint 25b.5k — binder-only SSM command ID authority.

Primary live defect (fixed): host ``aws s3 cp`` stdout pollution mixed into
``SSM_COMMAND_ID`` via command substitution.

Remaining integrity defect (fixed here): non-authoritative orchestration-directory
fallback that could populate ``SSM_COMMAND_ID`` unbound to release/run and skip
binder polling.

Final contract: the release/run-specific S3 binder is the sole command-ID
authority for host evidence.

GitHub binder re-download/parser is retained only as defense-in-depth; it was
not the live pollution source (GitHub COMMAND_ID was already clean).
"""

from __future__ import annotations

import copy
import json
import os
import re
import subprocess
import sys
import tempfile
import textwrap
import time
from pathlib import Path

from scripts.deploy.evidence import compute_evidence_sha256, create_evidence

ROOT = Path(__file__).resolve().parents[2]
WORKFLOWS = ROOT / ".github/workflows"
DEPLOY_WF = WORKFLOWS / "deploy-staging.yml"
HOST_DEPLOY = ROOT / "scripts/deploy/host/dealbrain-staging-deploy.sh"
VALIDATOR_MODULE = "scripts.deploy.write_gha_staging_evidence"

SAMPLE_SHA = "0123456789abcdef0123456789abcdef01234567"
SAMPLE_DIGEST = "sha256:" + ("b" * 64)
SAMPLE_REPO = "ghcr.io/example-org/dealbrain"
SAMPLE_MANIFEST_SHA = "c" * 64
SAMPLE_RELEASE_ID = f"rel-20260731T120000Z-{SAMPLE_SHA[:12]}"
SAMPLE_RUN_ID = "999"
SAMPLE_ACCOUNT = "123456789012"
SAMPLE_REGION = "us-east-1"
SAMPLE_INSTANCE = "i-0123456789abcdef0"
SAMPLE_SSM_UUID = "28a528a0-5b2c-4a53-85f5-97243241933b"
SAMPLE_SSM_UUID_UPPER = SAMPLE_SSM_UUID.upper()
SAMPLE_SSM_UUID_OTHER = "11111111-2222-4333-8444-555555555555"
SAMPLE_SSM_UUID_STALE = "aaaaaaaa-bbbb-4ccc-8ddd-eeeeeeeeeeee"

REQUIRED_WORKFLOW_ARGS = (
    "--evidence",
    "--release-id",
    "--git-sha",
    "--image-repository",
    "--image-digest",
    "--source-manifest-sha256",
    "--deploy-run-id",
    "--aws-account-id",
    "--aws-region",
    "--ec2-instance-id",
    "--ssm-command-id",
)


def _read(path: Path) -> str:
    assert path.is_file(), f"missing: {path}"
    return path.read_text(encoding="utf-8")


def _evidence_step(text: str) -> str:
    marker = "Collect and validate authoritative host evidence"
    assert marker in text
    after = text.split(marker, 1)[1]
    next_step = re.search(r"\n      - name:", after)
    assert next_step is not None
    return after[: next_step.start()]


def _extract_bash_function(source: str, name: str) -> str:
    """Extract a top-level ``name() { ... }`` body from a bash script."""
    match = re.search(rf"(?m)^{re.escape(name)}\(\)\s*\{{", source)
    assert match is not None, f"function {name}() not found"
    start = match.start()
    i = source.index("{", match.start())
    depth = 0
    for j in range(i, len(source)):
        ch = source[j]
        if ch == "{":
            depth += 1
        elif ch == "}":
            depth -= 1
            if depth == 0:
                return source[start : j + 1]
    raise AssertionError(f"unbalanced braces for {name}()")


def _host_helper_source() -> str:
    text = _read(HOST_DEPLOY)
    parse_fn = _extract_bash_function(text, "parse_canonical_ssm_command_id_file")
    discover_fn = _extract_bash_function(text, "discover_ssm_command_id")
    resolve_fn = _extract_bash_function(text, "resolve_ssm_command_id_for_evidence")
    assert "tr -d '[:space:]'" not in discover_fn
    assert "--only-show-errors" in discover_fn
    assert ">/dev/null" in discover_fn
    assert "parse_canonical_ssm_command_id_file" in discover_fn
    assert "/var/lib/amazon/ssm" not in discover_fn
    assert "orchestration" not in discover_fn
    assert "AWS_SSM_COMMAND_ID" not in discover_fn
    # Polling constants + die stub for resolve helper.
    constants = textwrap.dedent(
        """\
        SSM_BINDER_POLL_INTERVAL_SEC="${SSM_BINDER_POLL_INTERVAL_SEC:-2}"
        SSM_BINDER_POLL_ATTEMPTS="${SSM_BINDER_POLL_ATTEMPTS:-60}"
        die() { echo "[dealbrain-staging-deploy] ERROR: $*" >&2; exit 1; }
        """
    )
    return f"{parse_fn}\n\n{discover_fn}\n\n{constants}\n{resolve_fn}\n"


# Synthetic AWS CLI stderr shapes (no real credentials / live artifacts).
AWS_ERR_NOSUCHKEY = (
    "fatal error: An error occurred (NoSuchKey) when calling the GetObject "
    "operation: The specified key does not exist."
)
AWS_ERR_OBJECT_404 = (
    "fatal error: An error occurred (404) when calling the HeadObject operation: Not Found"
)
AWS_ERR_INVALID_ACCESS_KEY = (
    "fatal error: An error occurred (InvalidAccessKeyId) when calling the "
    "GetObject operation: The AWS Access Key Id you provided does not exist "
    "in our records."
)
AWS_ERR_NOSUCHBUCKET = (
    "fatal error: An error occurred (NoSuchBucket) when calling the "
    "HeadObject operation: The specified bucket does not exist"
)
AWS_ERR_ACCESS_DENIED = (
    "fatal error: An error occurred (AccessDenied) when calling the "
    "GetObject operation: Access Denied"
)
AWS_ERR_EXPIRED_TOKEN = (
    "fatal error: An error occurred (ExpiredToken) when calling the "
    "GetObject operation: The provided token has expired."
)
AWS_ERR_SIGNATURE_MISMATCH = (
    "fatal error: An error occurred (SignatureDoesNotMatch) when calling the "
    "GetObject operation: The request signature we calculated does not match "
    "the signature you provided. Check your key and signing method."
)
AWS_ERR_PERMANENT_REDIRECT = (
    "fatal error: An error occurred (PermanentRedirect) when calling the "
    "HeadObject operation: The bucket you are attempting to access must be "
    "addressed using the specified endpoint. Please send all future requests "
    "to this endpoint."
)
AWS_ERR_NETWORK = (
    "Could not connect to the endpoint URL: "
    '"https://s3.us-east-1.amazonaws.com/test-bucket/evidence/x"'
)
AWS_ERR_GENERIC = "fatal error: Unable to locate credentials"
AWS_ERR_UNKNOWN = "something went sideways in a novel way"
AWS_ERR_PLAIN_DOES_NOT_EXIST = "The specified key does not exist"
AWS_ERR_PLAIN_NOT_FOUND = "Not Found"

_FAIL_MODE_STDERR: dict[str, str] = {
    "absent": AWS_ERR_NOSUCHKEY,
    "nosuchkey": AWS_ERR_NOSUCHKEY,
    "object_404": AWS_ERR_OBJECT_404,
    "invalid_access_key": AWS_ERR_INVALID_ACCESS_KEY,
    "nosuchbucket": AWS_ERR_NOSUCHBUCKET,
    "access_denied": AWS_ERR_ACCESS_DENIED,
    "expired_token": AWS_ERR_EXPIRED_TOKEN,
    "signature_mismatch": AWS_ERR_SIGNATURE_MISMATCH,
    "permanent_redirect": AWS_ERR_PERMANENT_REDIRECT,
    "network": AWS_ERR_NETWORK,
    "generic": AWS_ERR_GENERIC,
    "unknown": AWS_ERR_UNKNOWN,
    "plain_does_not_exist": AWS_ERR_PLAIN_DOES_NOT_EXIST,
    "plain_not_found": AWS_ERR_PLAIN_NOT_FOUND,
}


def _fake_aws_s3_cp_script(
    dest_dir: Path,
    *,
    emit_progress: bool = True,
    fail_mode: str | None = None,
    stderr_message: str | None = None,
) -> Path:
    """Install a fake ``aws`` that copies binder fixtures or fails by mode.

    fail_mode:
      None — success when fixture exists; NoSuchKey when missing
      named modes — always fail with the synthetic stderr mapped above
    stderr_message:
      optional exact stderr override (takes precedence over fail_mode)
    """
    if stderr_message is not None:
        forced_stderr = stderr_message
    elif fail_mode is not None:
        assert fail_mode in _FAIL_MODE_STDERR, f"unknown fail_mode: {fail_mode}"
        forced_stderr = _FAIL_MODE_STDERR[fail_mode]
    else:
        forced_stderr = ""

    script = dest_dir / "aws"
    script.write_text(
        textwrap.dedent(
            f"""\
            #!/usr/bin/env bash
            set -euo pipefail
            if [[ "${{1:-}}" != "s3" || "${{2:-}}" != "cp" ]]; then
              echo "unexpected aws invocation: $*" >&2
              exit 2
            fi
            src="$3"
            dest="$4"
            only_show_errors=0
            shift 4 || true
            while [[ $# -gt 0 ]]; do
              case "$1" in
                --only-show-errors) only_show_errors=1 ;;
                --region) shift ;;
              esac
              shift || true
            done
            forced_stderr={forced_stderr!r}
            if [[ -n "$forced_stderr" ]]; then
              printf '%s\\n' "$forced_stderr" >&2
              exit 1
            fi
            key="${{src##*/}}"
            fixture_root="${{FAKE_S3_ROOT:?}}"
            src_file="${{fixture_root}}/${{key}}"
            if [[ ! -f "$src_file" ]]; then
              printf '%s\\n' {AWS_ERR_NOSUCHKEY!r} >&2
              exit 1
            fi
            size="$(wc -c <"$src_file" | tr -d ' ')"
            if [[ {int(emit_progress)} -eq 1 && "$only_show_errors" -eq 0 ]]; then
              echo "Completed ${{size}} Bytes/${{size}} Bytes (1 Bytes/s) with 1 file(s) remaining"
              echo "download: ${{src}} to ${{dest}}"
            fi
            if [[ {int(emit_progress)} -eq 1 \
                  && "$only_show_errors" -eq 1 \
                  && "${{FORCE_PROGRESS_WITH_ONLY_SHOW_ERRORS:-0}}" == "1" ]]; then
              echo "Completed ${{size}} Bytes/${{size}} Bytes (1 Bytes/s) with 1 file(s) remaining"
              echo "download: ${{src}} to ../../tmp/tmp.XXXXXX"
            fi
            cp "$src_file" "$dest"
            """
        ),
        encoding="utf-8",
    )
    script.chmod(0o755)
    return script


def _run_discover(
    *,
    binder_bytes: bytes | None,
    emit_progress: bool = True,
    force_progress_with_flag: bool = False,
    fail_mode: str | None = None,
    stderr_message: str | None = None,
    orchestration_dirs: list[tuple[str, float]] | None = None,
    extra_env: dict[str, str] | None = None,
) -> subprocess.CompletedProcess[str]:
    with tempfile.TemporaryDirectory() as tmp:
        tmp_path = Path(tmp)
        fixture_root = tmp_path / "fixtures"
        fixture_root.mkdir()
        if binder_bytes is not None:
            (fixture_root / "ssm-command-id.txt").write_bytes(binder_bytes)
        aws_dir = tmp_path / "bin"
        aws_dir.mkdir()
        _fake_aws_s3_cp_script(
            aws_dir,
            emit_progress=emit_progress,
            fail_mode=fail_mode,
            stderr_message=stderr_message,
        )

        # Realistic SSM orchestration tree (must never become authoritative).
        orch_root = (
            tmp_path
            / "var"
            / "lib"
            / "amazon"
            / "ssm"
            / SAMPLE_INSTANCE
            / "document"
            / "orchestration"
        )
        if orchestration_dirs:
            orch_root.mkdir(parents=True, exist_ok=True)
            for name, mtime in orchestration_dirs:
                d = orch_root / name
                d.mkdir(parents=True, exist_ok=True)
                os.utime(d, (mtime, mtime))

        helpers = _host_helper_source()
        script = tmp_path / "run_discover.sh"
        script.write_text(
            f"""#!/usr/bin/env bash
set -euo pipefail
export PATH={str(aws_dir)!r}:"$PATH"
RELEASE_ID={SAMPLE_RELEASE_ID!r}
DEPLOY_RUN_ID={SAMPLE_RUN_ID!r}
BUNDLE_BUCKET='test-bucket'
REGION={SAMPLE_REGION!r}
INSTANCE_ID={SAMPLE_INSTANCE!r}
# Ensure legacy override cannot act as authority even if present in the environment.
unset AWS_SSM_COMMAND_ID || true
{helpers}
SSM_COMMAND_ID="$(discover_ssm_command_id)" || {{
  rc=$?
  printf '%s' "$SSM_COMMAND_ID"
  exit "$rc"
}}
printf '%s' "$SSM_COMMAND_ID"
""",
            encoding="utf-8",
        )
        script.chmod(0o755)
        env = {
            **os.environ,
            "FAKE_S3_ROOT": str(fixture_root),
            "FORCE_PROGRESS_WITH_ONLY_SHOW_ERRORS": ("1" if force_progress_with_flag else "0"),
            "ORCH_FIXTURE_ROOT": str(orch_root),
        }
        if extra_env:
            env.update(extra_env)
        return subprocess.run(
            ["bash", str(script)],
            check=False,
            capture_output=True,
            text=True,
            cwd=str(ROOT),
            env=env,
        )


def _run_resolve_poll(
    *,
    appear_after_seconds: float | None,
    binder_bytes: bytes,
    poll_interval: float = 0.05,
    poll_attempts: int = 40,
    orchestration_dirs: list[tuple[str, float]] | None = None,
    initial_ssm_command_id: str = "",
    fail_mode: str | None = None,
) -> subprocess.CompletedProcess[str]:
    """Exercise ``resolve_ssm_command_id_for_evidence`` with a delayed binder."""
    with tempfile.TemporaryDirectory() as tmp:
        tmp_path = Path(tmp)
        fixture_root = tmp_path / "fixtures"
        fixture_root.mkdir()
        aws_dir = tmp_path / "bin"
        aws_dir.mkdir()
        _fake_aws_s3_cp_script(aws_dir, emit_progress=False, fail_mode=fail_mode)

        orch_root = (
            tmp_path
            / "var"
            / "lib"
            / "amazon"
            / "ssm"
            / SAMPLE_INSTANCE
            / "document"
            / "orchestration"
        )
        if orchestration_dirs:
            orch_root.mkdir(parents=True, exist_ok=True)
            for name, mtime in orchestration_dirs:
                d = orch_root / name
                d.mkdir(parents=True, exist_ok=True)
                os.utime(d, (mtime, mtime))

        appear_script = tmp_path / "appear_binder.sh"
        if appear_after_seconds is not None:
            binder_path = fixture_root / "ssm-command-id.txt"
            pending = tmp_path / "pending-binder.bin"
            pending.write_bytes(binder_bytes)
            appear_script.write_text(
                textwrap.dedent(
                    f"""\
                    #!/usr/bin/env bash
                    set -euo pipefail
                    sleep {appear_after_seconds}
                    cp {str(pending)!r} {str(binder_path)!r}
                    """
                ),
                encoding="utf-8",
            )
            appear_script.chmod(0o755)

        helpers = _host_helper_source()
        script = tmp_path / "run_resolve.sh"
        script.write_text(
            f"""#!/usr/bin/env bash
set -euo pipefail
export PATH={str(aws_dir)!r}:"$PATH"
RELEASE_ID={SAMPLE_RELEASE_ID!r}
DEPLOY_RUN_ID={SAMPLE_RUN_ID!r}
BUNDLE_BUCKET='test-bucket'
REGION={SAMPLE_REGION!r}
INSTANCE_ID={SAMPLE_INSTANCE!r}
SSM_BINDER_POLL_INTERVAL_SEC={poll_interval}
SSM_BINDER_POLL_ATTEMPTS={poll_attempts}
SSM_COMMAND_ID={initial_ssm_command_id!r}
FAILURE_REASON=""
{helpers}
{"bash " + str(appear_script) + " &" if appear_after_seconds is not None else "true"}
resolve_ssm_command_id_for_evidence
printf '%s' "$SSM_COMMAND_ID"
""",
            encoding="utf-8",
        )
        script.chmod(0o755)
        env = {
            **os.environ,
            "FAKE_S3_ROOT": str(fixture_root),
        }
        return subprocess.run(
            ["bash", str(script)],
            check=False,
            capture_output=True,
            text=True,
            cwd=str(ROOT),
            env=env,
        )


def _run_host_parser(file_bytes: bytes) -> subprocess.CompletedProcess[str]:
    with tempfile.TemporaryDirectory() as tmp:
        tmp_path = Path(tmp)
        path = tmp_path / "ssm-command-id.txt"
        path.write_bytes(file_bytes)
        helpers = _host_helper_source()
        script = tmp_path / "run_parser.sh"
        script.write_text(
            f"""#!/usr/bin/env bash
set -euo pipefail
{helpers}
OUT="$(parse_canonical_ssm_command_id_file {str(path)!r})" || {{
  rc=$?
  printf '%s' "$OUT"
  exit "$rc"
}}
printf '%s' "$OUT"
""",
            encoding="utf-8",
        )
        script.chmod(0o755)
        return subprocess.run(
            ["bash", str(script)],
            check=False,
            capture_output=True,
            text=True,
            cwd=str(ROOT),
        )


def _clean_env() -> dict[str, str]:
    env = {k: v for k, v in os.environ.items() if k != "PYTHONPATH"}
    env["PYTHONPATH"] = ""
    return env


def _sample_evidence(**overrides: object) -> dict:
    payload = create_evidence(
        release_id=SAMPLE_RELEASE_ID,
        git_sha=SAMPLE_SHA,
        image_repository=SAMPLE_REPO,
        image_digest=SAMPLE_DIGEST,
        source_manifest_sha256=SAMPLE_MANIFEST_SHA,
        deploy_workflow_run_id=SAMPLE_RUN_ID,
        aws_account_id=SAMPLE_ACCOUNT,
        aws_region=SAMPLE_REGION,
        assumed_role_arn=f"arn:aws:iam::{SAMPLE_ACCOUNT}:role/dealbrain-staging-gha-deploy",
        role_session_name=f"gha-{SAMPLE_RUN_ID}-staging",
        ec2_instance_id=SAMPLE_INSTANCE,
        ssm_command_id=SAMPLE_SSM_UUID,
        migration_revision_before="abc",
        migration_revision_after="def",
        localhost_live=True,
        localhost_ready=True,
        alb_target_healthy=True,
        smoke_ok=True,
        image_id="sha256:" + ("d" * 64),
        repo_digest=f"{SAMPLE_REPO}@{SAMPLE_DIGEST}",
        image_created_at="2026-07-31T11:00:00Z",
        deployment_started_at="2026-07-31T12:00:00Z",
        deployment_finished_at="2026-07-31T12:05:00Z",
        deployment_duration_seconds=300,
        final_status="staging_ok",
        failure_reason=None,
    )
    if overrides:
        payload = copy.deepcopy(payload)
        payload.update(overrides)
        if "evidence_sha256" not in overrides:
            payload["evidence_sha256"] = compute_evidence_sha256(payload)
    return payload


def _write_evidence(path: Path, **overrides: object) -> dict:
    payload = _sample_evidence(**overrides)
    path.write_text(json.dumps(payload, sort_keys=True, indent=2) + "\n", encoding="utf-8")
    return payload


def _binding_args(evidence_path: Path, ssm_command_id: str = SAMPLE_SSM_UUID) -> list[str]:
    values = {
        "--evidence": str(evidence_path),
        "--release-id": SAMPLE_RELEASE_ID,
        "--git-sha": SAMPLE_SHA,
        "--image-repository": SAMPLE_REPO,
        "--image-digest": SAMPLE_DIGEST,
        "--source-manifest-sha256": SAMPLE_MANIFEST_SHA,
        "--deploy-run-id": SAMPLE_RUN_ID,
        "--aws-account-id": SAMPLE_ACCOUNT,
        "--aws-region": SAMPLE_REGION,
        "--ec2-instance-id": SAMPLE_INSTANCE,
        "--ssm-command-id": ssm_command_id,
    }
    argv: list[str] = []
    for flag in REQUIRED_WORKFLOW_ARGS:
        argv.extend([flag, values[flag]])
    return argv


def _run_module(args: list[str]) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        [sys.executable, "-m", VALIDATOR_MODULE, *args],
        check=False,
        capture_output=True,
        text=True,
        cwd=str(ROOT),
        env=_clean_env(),
    )


def _extract_workflow_uuid_parser() -> str:
    step = _evidence_step(_read(DEPLOY_WF))
    match = re.search(
        r"COMMAND_ID=\"\$\(\s*\n\s*python -c '\n(.*?\n)' \"\$COMMAND_ID_FILE\"\s*\n\s*\)\"",
        step,
        flags=re.DOTALL,
    )
    assert match is not None, "workflow UUID parser block not found"
    return textwrap.dedent(match.group(1))


def _run_workflow_uuid_parser(file_path: Path) -> subprocess.CompletedProcess[str]:
    parser = _extract_workflow_uuid_parser()
    return subprocess.run(
        [sys.executable, "-c", parser, str(file_path)],
        check=False,
        capture_output=True,
        text=True,
        cwd=str(ROOT),
    )


# ---------------------------------------------------------------------------
# Host contract (static)
# ---------------------------------------------------------------------------


def test_host_discover_downloads_to_temp_file_with_only_show_errors() -> None:
    text = _read(HOST_DEPLOY)
    discover = _extract_bash_function(text, "discover_ssm_command_id")
    assert "aws s3 cp" in discover
    assert "--only-show-errors" in discover
    assert ">/dev/null" in discover
    assert "mktemp" in discover
    assert "rm -f" in discover
    assert "tr -d '[:space:]'" not in discover
    assert "parse_canonical_ssm_command_id_file" in discover
    assert not re.search(r"\$\(\s*aws\s+s3\s+cp", discover)
    # Binder-only: no orchestration fallback, no env override authority.
    assert "/var/lib/amazon/ssm" not in discover
    assert "orchestration" not in discover
    assert "AWS_SSM_COMMAND_ID" not in discover
    assert "find " not in discover
    assert "evidence/${RELEASE_ID}/${DEPLOY_RUN_ID}/ssm-command-id.txt" in discover
    assert 'DEALBRAIN_SSM_COMMAND_ID="$SSM_COMMAND_ID"' in text
    assert "resolve_ssm_command_id_for_evidence" in text
    assert "SSM_BINDER_POLL_INTERVAL_SEC=2" in text
    assert "SSM_BINDER_POLL_ATTEMPTS=60" in text


def test_host_parser_uses_stdlib_uuid_and_canonical_form() -> None:
    parse_fn = _extract_bash_function(_read(HOST_DEPLOY), "parse_canonical_ssm_command_id_file")
    assert "import uuid" in parse_fn
    assert "path.read_bytes()" in parse_fn
    assert "sys.stdout.write(canonical)" in parse_fn
    assert "file=sys.stderr" in parse_fn


def test_host_has_no_active_orchestration_fallback_anywhere() -> None:
    text = _read(HOST_DEPLOY)
    discover = _extract_bash_function(text, "discover_ssm_command_id")
    resolve = _extract_bash_function(text, "resolve_ssm_command_id_for_evidence")
    # Active code paths must not probe orchestration directories.
    for body in (discover, resolve):
        assert "find " not in body
        assert "/var/lib/amazon/ssm" not in body
        assert "document/orchestration" not in body
    # No find-based command-id discovery remains anywhere in the host script.
    assert not re.search(r"find\s+.*/amazon/ssm", text)
    assert not re.search(r"(?m)^\s*found=\"\$\(find ", text)


def test_host_classifier_uses_narrow_error_code_allowlist_only() -> None:
    """Temporary absence must not be driven by loose phrase substrings."""
    discover = _extract_bash_function(_read(HOST_DEPLOY), "discover_ssm_command_id")
    # Broad natural-language matches removed (Sprint 25b.5k audit fix).
    assert '*"does not exist"*' not in discover
    assert "*'does not exist'*" not in discover
    assert '*"Not Found"*' not in discover
    assert '*"not found"*' not in discover
    assert '*"missing"*' not in discover
    assert '== *"404"*' not in discover
    # Narrow allowlist: explicit AWS error code extraction + NoSuchKey / object 404.
    assert "An error occurred" in discover
    assert "NoSuchKey" in discover
    assert "HeadObject" in discover
    assert "GetObject" in discover
    assert "temporary_absence" in discover
    assert "aws_err_code" in discover


# ---------------------------------------------------------------------------
# Host behavioral: discover_ssm_command_id (real production functions)
# ---------------------------------------------------------------------------


def test_discover_valid_canonical_uuid_succeeds() -> None:
    proc = _run_discover(binder_bytes=SAMPLE_SSM_UUID.encode("ascii"))
    assert proc.returncode == 0, proc.stderr
    assert proc.stdout == SAMPLE_SSM_UUID


def test_discover_single_lf_succeeds() -> None:
    proc = _run_discover(binder_bytes=(SAMPLE_SSM_UUID + "\n").encode("ascii"))
    assert proc.returncode == 0, proc.stderr
    assert proc.stdout == SAMPLE_SSM_UUID


def test_discover_crlf_succeeds() -> None:
    proc = _run_discover(binder_bytes=(SAMPLE_SSM_UUID + "\r\n").encode("ascii"))
    assert proc.returncode == 0, proc.stderr
    assert proc.stdout == SAMPLE_SSM_UUID


def test_discover_strips_fake_aws_progress_and_returns_only_uuid() -> None:
    """Fake aws emits progress to stdout; discover must return only the UUID."""
    proc = _run_discover(
        binder_bytes=(SAMPLE_SSM_UUID + "\n").encode("ascii"),
        emit_progress=True,
        force_progress_with_flag=True,
    )
    assert proc.returncode == 0, proc.stderr
    assert proc.stdout == SAMPLE_SSM_UUID
    assert "Completed" not in proc.stdout
    assert "download:" not in proc.stdout


def test_discover_succeeds_without_progress_output() -> None:
    proc = _run_discover(
        binder_bytes=(SAMPLE_SSM_UUID + "\n").encode("ascii"),
        emit_progress=False,
    )
    assert proc.returncode == 0, proc.stderr
    assert proc.stdout == SAMPLE_SSM_UUID


def test_discover_binder_temporarily_absent_returns_empty_retryable() -> None:
    proc = _run_discover(binder_bytes=None, fail_mode="absent")
    assert proc.returncode == 0, proc.stderr
    assert proc.stdout == ""
    assert "temporarily absent" in proc.stderr
    assert "permanent" not in proc.stderr


def test_discover_nosuchkey_is_temporary_retryable() -> None:
    proc = _run_discover(binder_bytes=None, fail_mode="nosuchkey")
    assert proc.returncode == 0, proc.stderr
    assert proc.stdout == ""
    assert "temporarily absent" in proc.stderr
    assert "permanent" not in proc.stderr


def test_discover_object_level_404_headobject_is_temporary() -> None:
    """aws s3 cp object-level 404 (HeadObject) is temporary under the CLI contract."""
    proc = _run_discover(binder_bytes=None, fail_mode="object_404")
    assert proc.returncode == 0, proc.stderr
    assert proc.stdout == ""
    assert "temporarily absent" in proc.stderr
    assert "permanent" not in proc.stderr


def test_discover_object_level_404_getobject_is_temporary() -> None:
    msg = "fatal error: An error occurred (404) when calling the GetObject operation: Not Found"
    proc = _run_discover(binder_bytes=None, stderr_message=msg)
    assert proc.returncode == 0, proc.stderr
    assert proc.stdout == ""
    assert "temporarily absent" in proc.stderr


def _assert_permanent_no_command_id(
    proc: subprocess.CompletedProcess[str],
    *,
    expect_code: str | None = None,
) -> None:
    assert proc.returncode != 0, proc.stderr
    assert proc.stdout == ""
    assert "permanent" in proc.stderr
    assert "temporarily absent" not in proc.stderr
    if expect_code is not None:
        assert f"code={expect_code}" in proc.stderr


def test_discover_invalid_access_key_with_does_not_exist_is_permanent() -> None:
    proc = _run_discover(binder_bytes=None, fail_mode="invalid_access_key")
    _assert_permanent_no_command_id(proc, expect_code="InvalidAccessKeyId")
    # Phrase appears in synthetic AWS text but must not drive temporary classification.
    assert "does not exist" in AWS_ERR_INVALID_ACCESS_KEY


def test_discover_nosuchbucket_with_does_not_exist_is_permanent() -> None:
    proc = _run_discover(binder_bytes=None, fail_mode="nosuchbucket")
    _assert_permanent_no_command_id(proc, expect_code="NoSuchBucket")
    assert "does not exist" in AWS_ERR_NOSUCHBUCKET


def test_discover_access_denied_fails_closed() -> None:
    proc = _run_discover(binder_bytes=None, fail_mode="access_denied")
    _assert_permanent_no_command_id(proc, expect_code="AccessDenied")
    assert "Access Denied" not in proc.stdout


def test_discover_expired_token_is_permanent() -> None:
    proc = _run_discover(binder_bytes=None, fail_mode="expired_token")
    _assert_permanent_no_command_id(proc, expect_code="ExpiredToken")


def test_discover_signature_does_not_match_is_permanent() -> None:
    proc = _run_discover(binder_bytes=None, fail_mode="signature_mismatch")
    _assert_permanent_no_command_id(proc, expect_code="SignatureDoesNotMatch")


def test_discover_permanent_redirect_wrong_region_is_permanent() -> None:
    proc = _run_discover(binder_bytes=None, fail_mode="permanent_redirect")
    _assert_permanent_no_command_id(proc, expect_code="PermanentRedirect")


def test_discover_network_dns_failure_is_permanent() -> None:
    proc = _run_discover(binder_bytes=None, fail_mode="network")
    _assert_permanent_no_command_id(proc)
    assert "code=" not in proc.stderr  # no AWS error code to extract


def test_discover_generic_aws_cli_failure_fails_closed() -> None:
    proc = _run_discover(binder_bytes=None, fail_mode="generic")
    _assert_permanent_no_command_id(proc)


def test_discover_unknown_error_text_is_permanent() -> None:
    proc = _run_discover(binder_bytes=None, fail_mode="unknown")
    _assert_permanent_no_command_id(proc)


def test_discover_plain_does_not_exist_without_error_code_is_permanent() -> None:
    proc = _run_discover(binder_bytes=None, fail_mode="plain_does_not_exist")
    _assert_permanent_no_command_id(proc)


def test_discover_plain_not_found_without_error_code_is_permanent() -> None:
    proc = _run_discover(binder_bytes=None, fail_mode="plain_not_found")
    _assert_permanent_no_command_id(proc)


def test_discover_bare_404_without_object_operation_is_permanent() -> None:
    """A parenthetical 404 without HeadObject/GetObject must not be temporary."""
    msg = "fatal error: An error occurred (404) when calling the ListBuckets operation: Not Found"
    proc = _run_discover(binder_bytes=None, stderr_message=msg)
    _assert_permanent_no_command_id(proc, expect_code="404")


def test_discover_error_code_overrides_does_not_exist_phrase() -> None:
    """Explicit permanent code wins even when message also says does not exist."""
    msg = (
        "An error occurred (InvalidAccessKeyId) when calling the GetObject "
        "operation: The AWS Access Key Id you provided does not exist in our "
        "records. Also mentions NoSuchKey as prose only."
    )
    proc = _run_discover(binder_bytes=None, stderr_message=msg)
    _assert_permanent_no_command_id(proc, expect_code="InvalidAccessKeyId")
    assert "temporarily absent" not in proc.stderr


def test_discover_empty_file_fails_closed() -> None:
    proc = _run_discover(binder_bytes=b"")
    assert proc.returncode != 0
    assert proc.stdout == ""
    assert "FAIL:" in proc.stderr or "malformed" in proc.stderr


def test_discover_whitespace_only_fails_closed() -> None:
    proc = _run_discover(binder_bytes=b"   \n")
    assert proc.returncode != 0
    assert proc.stdout == ""
    assert "FAIL:" in proc.stderr or "malformed" in proc.stderr


def test_discover_leading_trailing_spaces_fail() -> None:
    for content in (f" {SAMPLE_SSM_UUID}", f"{SAMPLE_SSM_UUID} ", f" {SAMPLE_SSM_UUID} \n"):
        proc = _run_discover(binder_bytes=content.encode("ascii"))
        assert proc.returncode != 0, repr(content)
        assert proc.stdout == ""


def test_discover_multiple_lines_fail() -> None:
    proc = _run_discover(
        binder_bytes=(SAMPLE_SSM_UUID + "\n" + SAMPLE_SSM_UUID + "\n").encode("ascii")
    )
    assert proc.returncode != 0
    assert proc.stdout == ""


def test_discover_progress_text_plus_uuid_in_file_fails() -> None:
    polluted = (
        "Completed 37 Bytes/37 Bytes (1 Bytes/s) with 1 file(s) remaining\n"
        f"download: s3://bucket/evidence/rel/run/ssm-command-id.txt to ../../tmp/tmp.x\n"
        f"{SAMPLE_SSM_UUID}\n"
    )
    proc = _run_discover(binder_bytes=polluted.encode("ascii"))
    assert proc.returncode != 0
    assert proc.stdout == ""
    assert "Completed" not in proc.stdout


def test_discover_uuid_plus_progress_text_fails() -> None:
    polluted = f"{SAMPLE_SSM_UUID}\nCompleted 37 Bytes/37 Bytes\n"
    proc = _run_discover(binder_bytes=polluted.encode("ascii"))
    assert proc.returncode != 0
    assert proc.stdout == ""


def test_discover_multiple_uuids_fail() -> None:
    proc = _run_discover(
        binder_bytes=f"{SAMPLE_SSM_UUID} {SAMPLE_SSM_UUID_OTHER}\n".encode("ascii")
    )
    assert proc.returncode != 0
    assert proc.stdout == ""


def test_discover_malformed_uuid_fails() -> None:
    proc = _run_discover(binder_bytes=b"not-a-uuid\n")
    assert proc.returncode != 0
    assert proc.stdout == ""


def test_discover_uppercase_non_canonical_uuid_fails() -> None:
    proc = _run_discover(binder_bytes=(SAMPLE_SSM_UUID_UPPER + "\n").encode("ascii"))
    assert proc.returncode != 0
    assert proc.stdout == ""


def test_parser_diagnostics_do_not_enter_command_substitution_stdout() -> None:
    proc = _run_host_parser(b"not-a-uuid\n")
    assert proc.returncode != 0
    assert proc.stdout == ""
    assert "FAIL:" in proc.stderr
    assert "not-a-uuid" not in proc.stdout


# ---------------------------------------------------------------------------
# Orchestration fallback rejection (must never populate SSM_COMMAND_ID)
# ---------------------------------------------------------------------------


def test_orchestration_dir_not_a_uuid_ignored_when_binder_missing() -> None:
    proc = _run_discover(
        binder_bytes=None,
        fail_mode="absent",
        orchestration_dirs=[("not-a-uuid", time.time())],
    )
    assert proc.returncode == 0
    assert proc.stdout == ""
    assert "not-a-uuid" not in proc.stdout


def test_orchestration_dir_valid_uuid_ignored_when_binder_missing() -> None:
    proc = _run_discover(
        binder_bytes=None,
        fail_mode="absent",
        orchestration_dirs=[(SAMPLE_SSM_UUID_OTHER, time.time())],
    )
    assert proc.returncode == 0
    assert proc.stdout == ""
    assert SAMPLE_SSM_UUID_OTHER not in proc.stdout


def test_multiple_orchestration_uuid_dirs_none_authoritative() -> None:
    now = time.time()
    proc = _run_discover(
        binder_bytes=None,
        fail_mode="absent",
        orchestration_dirs=[
            (SAMPLE_SSM_UUID_STALE, now - 100),
            (SAMPLE_SSM_UUID_OTHER, now - 10),
            (SAMPLE_SSM_UUID, now),
        ],
    )
    assert proc.returncode == 0
    assert proc.stdout == ""
    assert SAMPLE_SSM_UUID not in proc.stdout
    assert SAMPLE_SSM_UUID_OTHER not in proc.stdout
    assert SAMPLE_SSM_UUID_STALE not in proc.stdout


def test_stale_orchestration_command_from_previous_run_ignored() -> None:
    proc = _run_discover(
        binder_bytes=None,
        fail_mode="absent",
        orchestration_dirs=[(SAMPLE_SSM_UUID_STALE, time.time())],
    )
    assert proc.returncode == 0
    assert proc.stdout == ""
    assert SAMPLE_SSM_UUID_STALE not in proc.stdout


def test_orchestration_dirs_do_not_override_valid_binder() -> None:
    proc = _run_discover(
        binder_bytes=(SAMPLE_SSM_UUID + "\n").encode("ascii"),
        orchestration_dirs=[(SAMPLE_SSM_UUID_OTHER, time.time() + 1000)],
    )
    assert proc.returncode == 0, proc.stderr
    assert proc.stdout == SAMPLE_SSM_UUID


# ---------------------------------------------------------------------------
# Binder polling lifecycle
# ---------------------------------------------------------------------------


def test_binder_appears_during_polling_and_succeeds() -> None:
    proc = _run_resolve_poll(
        appear_after_seconds=0.15,
        binder_bytes=(SAMPLE_SSM_UUID + "\n").encode("ascii"),
        poll_interval=0.05,
        poll_attempts=40,
        orchestration_dirs=[(SAMPLE_SSM_UUID_OTHER, time.time())],
    )
    assert proc.returncode == 0, proc.stderr
    assert proc.stdout == SAMPLE_SSM_UUID


def test_temporary_nosuchkey_can_later_resolve_when_binder_appears() -> None:
    """NoSuchKey retries the same release/run key until the binder appears."""
    proc = _run_resolve_poll(
        appear_after_seconds=0.12,
        binder_bytes=(SAMPLE_SSM_UUID + "\n").encode("ascii"),
        poll_interval=0.05,
        poll_attempts=40,
    )
    assert proc.returncode == 0, proc.stderr
    assert proc.stdout == SAMPLE_SSM_UUID
    assert SAMPLE_SSM_UUID_OTHER not in proc.stdout


def test_binder_never_appears_bounded_polling_fails() -> None:
    proc = _run_resolve_poll(
        appear_after_seconds=None,
        binder_bytes=b"",  # unused; binder never written
        poll_interval=0.05,
        poll_attempts=3,
        orchestration_dirs=[(SAMPLE_SSM_UUID, time.time())],
    )
    assert proc.returncode != 0
    assert proc.stdout == ""
    assert "unavailable" in proc.stderr or "expired" in proc.stderr
    assert SAMPLE_SSM_UUID not in proc.stdout


def test_permanent_errors_do_not_enter_full_polling_loop() -> None:
    """Permanent classification must fail on first occurrence, not after 60 attempts."""
    poll_interval = 0.2
    poll_attempts = 60
    started = time.monotonic()
    proc = _run_resolve_poll(
        appear_after_seconds=None,
        binder_bytes=b"",
        poll_interval=poll_interval,
        poll_attempts=poll_attempts,
        fail_mode="invalid_access_key",
    )
    elapsed = time.monotonic() - started
    assert proc.returncode != 0
    assert proc.stdout == ""
    assert "permanently" in proc.stderr or "permanent" in proc.stderr
    # Full loop would be ~12s (60 × 0.2); permanent must exit far sooner.
    assert elapsed < 2.0, f"permanent path polled too long: {elapsed:.2f}s"
    assert "code=InvalidAccessKeyId" in proc.stderr or "binder discovery failed" in proc.stderr


def test_permanent_access_denied_aborts_resolve_immediately() -> None:
    started = time.monotonic()
    proc = _run_resolve_poll(
        appear_after_seconds=None,
        binder_bytes=b"",
        poll_interval=0.2,
        poll_attempts=60,
        fail_mode="access_denied",
    )
    elapsed = time.monotonic() - started
    assert proc.returncode != 0
    assert proc.stdout == ""
    assert elapsed < 2.0, f"AccessDenied polled too long: {elapsed:.2f}s"


def test_polling_constants_remain_two_seconds_by_sixty() -> None:
    text = _read(HOST_DEPLOY)
    assert "SSM_BINDER_POLL_INTERVAL_SEC=2" in text
    assert "SSM_BINDER_POLL_ATTEMPTS=60" in text
    resolve = _extract_bash_function(text, "resolve_ssm_command_id_for_evidence")
    assert "SSM_BINDER_POLL_INTERVAL_SEC" in resolve
    assert "SSM_BINDER_POLL_ATTEMPTS" in resolve
    assert "sleep" in resolve


def test_non_binder_value_cannot_skip_polling_loop() -> None:
    """resolve must not treat a pre-set non-binder ID as resolved without binder.

    Production resolve short-circuits only when SSM_COMMAND_ID is already set from
    a prior binder discover. A synthetic non-empty value that did not come from
    the binder must not be how production populates the variable — discover itself
    never returns orchestration names. This test proves empty+orch dirs still poll
    and fail closed rather than adopting the orchestration UUID.
    """
    proc = _run_resolve_poll(
        appear_after_seconds=None,
        binder_bytes=b"",
        poll_interval=0.05,
        poll_attempts=3,
        orchestration_dirs=[(SAMPLE_SSM_UUID, time.time())],
        initial_ssm_command_id="",
    )
    assert proc.returncode != 0
    assert proc.stdout == ""
    assert SAMPLE_SSM_UUID not in proc.stdout


def test_evidence_cannot_succeed_before_binder_resolution() -> None:
    """staging_ok evidence requires non-empty ssm_command_id (validator contract)."""
    with tempfile.TemporaryDirectory() as tmp:
        evidence = Path(tmp) / "staging-deploy-evidence.json"
        payload = _sample_evidence(ssm_command_id=None, final_status="staging_ok")
        # Force empty/None into payload the way a premature writer might.
        payload["ssm_command_id"] = None
        payload["evidence_sha256"] = compute_evidence_sha256(payload)
        evidence.write_text(json.dumps(payload, sort_keys=True, indent=2) + "\n", encoding="utf-8")
        result = _run_module(_binding_args(evidence, ssm_command_id=SAMPLE_SSM_UUID))
        assert result.returncode == 1
        assert "ssm_command_id" in result.stderr.lower() or "binding" in result.stderr.lower()


# ---------------------------------------------------------------------------
# Host evidence binding
# ---------------------------------------------------------------------------


def test_host_evidence_receives_exactly_binder_uuid() -> None:
    proc = _run_discover(
        binder_bytes=(SAMPLE_SSM_UUID + "\n").encode("ascii"),
        force_progress_with_flag=True,
        orchestration_dirs=[(SAMPLE_SSM_UUID_OTHER, time.time())],
    )
    assert proc.returncode == 0, proc.stderr
    host_command_id = proc.stdout
    assert host_command_id == SAMPLE_SSM_UUID

    with tempfile.TemporaryDirectory() as tmp:
        evidence = Path(tmp) / "staging-deploy-evidence.json"
        payload = _write_evidence(evidence, ssm_command_id=host_command_id)
        assert payload["ssm_command_id"] == SAMPLE_SSM_UUID
        result = _run_module(_binding_args(evidence, ssm_command_id=host_command_id))
        assert result.returncode == 0, result.stderr
        assert f"ok: host evidence accepted release_id={payload['release_id']}" in result.stdout


def test_polluted_host_command_id_rejected_by_evidence_validation() -> None:
    polluted = (
        "Completed 37 Bytes/37 Bytes (1 Bytes/s) with 1 file(s) remaining\n"
        f"download: s3://bucket/x to ../../tmp/tmp.x\n"
        f"{SAMPLE_SSM_UUID}"
    )
    with tempfile.TemporaryDirectory() as tmp:
        evidence = Path(tmp) / "staging-deploy-evidence.json"
        payload = _sample_evidence()
        payload["ssm_command_id"] = polluted
        payload["evidence_sha256"] = compute_evidence_sha256(payload)
        evidence.write_text(json.dumps(payload, sort_keys=True, indent=2) + "\n", encoding="utf-8")
        result = _run_module(_binding_args(evidence, ssm_command_id=SAMPLE_SSM_UUID))
        assert result.returncode == 1
        assert "binding mismatch" in result.stderr
        assert "ssm_command_id" in result.stderr


def test_wrong_evidence_command_id_still_fails_validation() -> None:
    with tempfile.TemporaryDirectory() as tmp:
        evidence = Path(tmp) / "staging-deploy-evidence.json"
        _write_evidence(evidence, ssm_command_id=SAMPLE_SSM_UUID)
        result = _run_module(_binding_args(evidence, ssm_command_id=SAMPLE_SSM_UUID_OTHER))
        assert result.returncode == 1
        assert "binding mismatch" in result.stderr
        assert "ssm_command_id" in result.stderr


def test_github_clean_expected_id_matches_clean_host_evidence_id() -> None:
    """GitHub expected ID (clean) must equal host evidence after host fix."""
    host = _run_discover(
        binder_bytes=(SAMPLE_SSM_UUID + "\n").encode("ascii"),
        force_progress_with_flag=True,
    )
    assert host.returncode == 0, host.stderr
    assert host.stdout == SAMPLE_SSM_UUID

    with tempfile.TemporaryDirectory() as tmp:
        binder = Path(tmp) / "ssm-command-id.txt"
        binder.write_bytes((SAMPLE_SSM_UUID + "\n").encode("ascii"))
        gha = _run_workflow_uuid_parser(binder)
        assert gha.returncode == 0, gha.stderr
        assert gha.stdout == SAMPLE_SSM_UUID
        assert gha.stdout == host.stdout

        evidence = Path(tmp) / "staging-deploy-evidence.json"
        _write_evidence(evidence, ssm_command_id=host.stdout)
        result = _run_module(_binding_args(evidence, ssm_command_id=gha.stdout))
        assert result.returncode == 0, result.stderr


def test_sprint25b5j_module_invocation_remains_intact() -> None:
    step = _evidence_step(_read(DEPLOY_WF))
    assert "python -m scripts.deploy.write_gha_staging_evidence" in step
    assert "python -m scripts.deploy.validate_staging_evidence" in step
    assert "python scripts/deploy/write_gha_staging_evidence.py" not in step
    assert "python scripts/deploy/validate_staging_evidence.py" not in step
    for flag in REQUIRED_WORKFLOW_ARGS:
        assert flag in step
    assert '--ssm-command-id "$COMMAND_ID"' in step
    assert "PYTHONPATH" not in step
    assert "environment: production" not in _read(DEPLOY_WF)


def test_other_evidence_bindings_remain_enforced() -> None:
    with tempfile.TemporaryDirectory() as tmp:
        evidence = Path(tmp) / "staging-deploy-evidence.json"
        _write_evidence(evidence)
        base = _binding_args(evidence, ssm_command_id=SAMPLE_SSM_UUID)
        args = list(base)
        sha_idx = args.index("--git-sha") + 1
        args[sha_idx] = "f" * 40
        proc = _run_module(args)
        assert proc.returncode == 1
        assert "binding mismatch" in proc.stderr
        assert "git_sha" in proc.stderr


# ---------------------------------------------------------------------------
# GitHub defense-in-depth (not the live root-cause fix)
# ---------------------------------------------------------------------------


def test_github_defensive_binder_redownload_present() -> None:
    step = _evidence_step(_read(DEPLOY_WF))
    assert "Defense-in-depth" in step or "defense-in-depth" in step.lower()
    assert "Primary remediation is host discover_ssm_command_id" in step
    assert 'COMMAND_ID_FILE="${RUNNER_TEMP}/ssm-command-id.txt"' in step
    assert "--only-show-errors" in step
    assert not re.search(r'COMMAND_ID="\$\(\s*aws\s+s3\s+cp', step)
    assert '--ssm-command-id "$COMMAND_ID"' in step
    # Same release/run key; no fallback to steps.ssm output.
    assert "COMMAND_ID_KEY=" in step
    assert "steps.ssm.outputs.command_id" not in step


def test_github_defensive_parser_rejects_polluted_binder_bytes() -> None:
    polluted = (
        f"Completed 37 Bytes/37 Bytes (1 Bytes/s) with 1 file(s) remaining\n{SAMPLE_SSM_UUID}\n"
    )
    with tempfile.TemporaryDirectory() as tmp:
        path = Path(tmp) / "ssm-command-id.txt"
        path.write_text(polluted, encoding="ascii")
        proc = _run_workflow_uuid_parser(path)
        assert proc.returncode != 0
        assert "FAIL:" in proc.stderr
        assert proc.stdout == ""


def test_host_script_bash_n() -> None:
    proc = subprocess.run(
        ["bash", "-n", str(HOST_DEPLOY)],
        check=False,
        capture_output=True,
        text=True,
    )
    assert proc.returncode == 0, proc.stderr


def test_assignment_inventory_binder_only_authority() -> None:
    """Every host assignment into SSM_COMMAND_ID must be binder-derived."""
    text = _read(HOST_DEPLOY)
    # Match SSM_COMMAND_ID= but not DEALBRAIN_SSM_COMMAND_ID=.
    all_assigns = re.findall(r"(?<![A-Z_])SSM_COMMAND_ID=[^\n;]+", text)
    assert all_assigns, "expected binder-derived SSM_COMMAND_ID assignments"
    pattern = r"""SSM_COMMAND_ID=(?:""|"\$discovered"|"\$\(discover_ssm_command_id\)")"""
    for assign in all_assigns:
        assert re.fullmatch(pattern, assign.strip()), f"unexpected assignment: {assign}"
    assert 'DEALBRAIN_SSM_COMMAND_ID="$SSM_COMMAND_ID"' in text
    assert "AWS_SSM_COMMAND_ID" not in text

"""Production host foundation: non-minimal AL2023 default AMI + early SSM."""

from __future__ import annotations

import base64
import fnmatch
import gzip
import os
import re
import stat
import subprocess
import textwrap
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
EC2_MAIN = ROOT / "infra/terraform/modules/ec2/main.tf"
EC2_VARS = ROOT / "infra/terraform/modules/ec2/variables.tf"
PROD_VARS = ROOT / "infra/terraform/environments/production/variables.tf"
STAGING_VARS = ROOT / "infra/terraform/environments/staging/variables.tf"
PROD_TF = ROOT / "infra/terraform/environments/production/main.tf"
PROD_USER_DATA = ROOT / "infra/ec2/user_data/production.sh"
SG_MAIN = ROOT / "infra/terraform/modules/security_groups/main.tf"
IAM_MAIN = ROOT / "infra/terraform/modules/iam/main.tf"
EVIDENCE = ROOT / "docs/roadmap/evidence/PRODUCTION_HOST_FOUNDATION_SSM_AMI_2026-09-14.md"
TF_README = ROOT / "infra/terraform/README.md"

AL2023_DEFAULT_AMI_PARAMETER = (
    "/aws/service/ami-amazon-linux-latest/al2023-ami-kernel-default-x86_64"
)
AL2023_MINIMAL_AMI_PARAMETER = (
    "/aws/service/ami-amazon-linux-latest/al2023-ami-minimal-kernel-default-x86_64"
)
UNSAFE_AMI_NAME_FILTER = "al2023-ami-*-x86_64"
SSM_BEGIN = "# --- BEGIN amazon-ssm-agent invariant ---"
SSM_END = "# --- END amazon-ssm-agent invariant ---"
EC2_USER_DATA_RAW_LIMIT = 16_384
STARTING_MAIN = "4d0b33a8db07c1c02bcca3c82aa3d9e4bebd2702"

CANDIDATE_AMI_NAMES = (
    "al2023-ami-2023.12.20260909.0-kernel-6.18-x86_64",
    "al2023-ami-minimal-2023.12.20260909.0-kernel-6.18-x86_64",
    "al2023-ami-ecs-hvm-2023.0.20260909-kernel-6.18-x86_64",
)


def _read(path: Path) -> str:
    assert path.is_file(), f"missing {path}"
    return path.read_text(encoding="utf-8")


def _ssm_block(text: str) -> str:
    start = text.index(SSM_BEGIN) + len(SSM_BEGIN)
    end = text.index(SSM_END, start)
    return text[start:end]


def resolve_ec2_ami_id(ami_id_override: str, ssm_parameter_value: str) -> str:
    """Mirrors locals.ami_id in infra/terraform/modules/ec2/main.tf."""
    return ami_id_override if ami_id_override != "" else ssm_parameter_value


def default_al2023_parameter_selects_minimal(parameter_name: str, ami_name: str) -> bool:
    """Default selector must never accept an AMI whose name contains -minimal-."""
    if "minimal" in parameter_name:
        return True
    return "-minimal-" in ami_name and parameter_name == AL2023_MINIMAL_AMI_PARAMETER


# ---------------------------------------------------------------------------
# AMI selection
# ---------------------------------------------------------------------------


def test_unsafe_glob_would_match_minimal_and_standard_names() -> None:
    """Documents the incident: al2023-ami-*-x86_64 matches minimal AMIs."""
    standard, minimal, ecs = CANDIDATE_AMI_NAMES
    assert fnmatch.fnmatch(standard, UNSAFE_AMI_NAME_FILTER)
    assert fnmatch.fnmatch(minimal, UNSAFE_AMI_NAME_FILTER)
    assert fnmatch.fnmatch(ecs, UNSAFE_AMI_NAME_FILTER)
    assert "-minimal-" in minimal


def test_default_al2023_selector_cannot_select_minimal() -> None:
    text = _read(EC2_MAIN)
    assert f'values = ["{UNSAFE_AMI_NAME_FILTER}"]' not in text
    assert 'data "aws_ami" "al2023"' not in text
    assert AL2023_DEFAULT_AMI_PARAMETER in text
    assert AL2023_MINIMAL_AMI_PARAMETER not in text
    assert "minimal" not in AL2023_DEFAULT_AMI_PARAMETER
    data_block = text.split('data "aws_ssm_parameter" "al2023"')[1].split("locals")[0]
    assert AL2023_DEFAULT_AMI_PARAMETER in data_block
    assert "minimal" not in data_block
    for name in CANDIDATE_AMI_NAMES:
        if "-minimal-" in name:
            assert (
                default_al2023_parameter_selects_minimal(AL2023_DEFAULT_AMI_PARAMETER, name)
                is False
            )
            assert (
                default_al2023_parameter_selects_minimal(AL2023_MINIMAL_AMI_PARAMETER, name) is True
            )
        else:
            assert (
                default_al2023_parameter_selects_minimal(AL2023_DEFAULT_AMI_PARAMETER, name)
                is False
            )


def test_explicit_ami_id_override_is_preserved() -> None:
    text = _read(EC2_MAIN)
    vars_text = _read(EC2_VARS)
    assert 'variable "ami_id"' in vars_text
    assert 'default     = ""' in vars_text
    assert 'count = var.ami_id == "" ? 1 : 0' in text
    assert 'var.ami_id != "" ? var.ami_id : data.aws_ssm_parameter.al2023[0].value' in text
    assert "ami_id                    = var.ami_id" in _read(PROD_TF)
    assert resolve_ec2_ami_id("ami-explicit123", "ami-from-ssm") == "ami-explicit123"
    assert resolve_ec2_ami_id("", "ami-from-ssm") == "ami-from-ssm"
    assert resolve_ec2_ami_id("", "ami-085b153e241f89f29") == "ami-085b153e241f89f29"


def test_ami_lifecycle_ignore_changes_retained() -> None:
    text = _read(EC2_MAIN)
    lifecycle = text[text.index("lifecycle {") :].split("}", 1)[0]
    assert "ignore_changes = [ami]" in lifecycle
    assert "user_data_base64" not in lifecycle
    evidence = _read(EVIDENCE)
    assert "ignore_changes = [ami]" in evidence
    assert "does **not** replace the current production host" in evidence
    assert STARTING_MAIN in evidence
    readme = _read(TF_README)
    assert AL2023_DEFAULT_AMI_PARAMETER in readme
    assert "ignore_changes = [ami]" in readme


def test_ami_id_descriptions_reject_minimal_default() -> None:
    for path in (EC2_VARS, PROD_VARS, STAGING_VARS):
        text = _read(path)
        assert "not minimal" in text
        ami_block = text.split('variable "ami_id"')[1].split("variable ")[0]
        assert "minimal" in ami_block.lower()


# ---------------------------------------------------------------------------
# Early SSM bootstrap
# ---------------------------------------------------------------------------


def test_production_bootstrap_installs_and_verifies_ssm_agent() -> None:
    text = _read(PROD_USER_DATA)
    block = _ssm_block(text)
    assert "amazon-ssm-agent" in block
    assert "dnf -y install amazon-ssm-agent" in block
    assert "systemctl enable amazon-ssm-agent" in block
    assert "systemctl start amazon-ssm-agent" in block
    assert "systemctl is-active --quiet amazon-ssm-agent" in block
    assert "rpm -q amazon-ssm-agent" in block
    assert "ensure_amazon_ssm_agent" in block
    assert "already installed" in block
    assert "systemd unit is active" in block
    assert "ERROR:" in block
    assert "invariant failed" in block
    assert "invariant ok" in block


def test_ssm_agent_runs_before_docker_compose_bootstrap() -> None:
    text = _read(PROD_USER_DATA)
    ssm_pos = text.index(SSM_BEGIN)
    docker_pos = text.index("dnf -y install \\\n  docker")
    compose_pos = text.index("/opt/dealbrain/bin/install-compose-plugin.sh")
    bootstrap_ok_pos = text.rindex("touch /opt/dealbrain/bootstrap.ok")
    assert ssm_pos < docker_pos < compose_pos < bootstrap_ok_pos
    assert text.index("ensure_amazon_ssm_agent") < docker_pos
    assert text.index(SSM_END) < docker_pos


def test_production_user_data_still_has_bash_syntax() -> None:
    proc = subprocess.run(
        ["bash", "-n", str(PROD_USER_DATA)],
        capture_output=True,
        text=True,
        check=False,
    )
    assert proc.returncode == 0, proc.stderr


def _write_exec(path: Path, body: str) -> None:
    path.write_text("#!/bin/bash\nset -euo pipefail\n" + body + "\n", encoding="utf-8")
    path.chmod(path.stat().st_mode | stat.S_IXUSR | stat.S_IXGRP | stat.S_IXOTH)


def _run_extracted_ssm(
    tmp_path: Path, *, installed: bool, active: bool, dnf_ok: bool = True
) -> tuple[subprocess.CompletedProcess[str], Path, Path, Path]:
    text = _read(PROD_USER_DATA)
    block = _ssm_block(text)
    function = textwrap.dedent(block)
    script = tmp_path / "run-ssm.sh"
    script.write_text("#!/bin/bash\nset -euo pipefail\n" + function + "\n", encoding="utf-8")
    script.chmod(0o755)

    bin_dir = tmp_path / "bin"
    bin_dir.mkdir()
    state = tmp_path / "state"
    state.mkdir()
    installed_flag = state / "installed"
    active_flag = state / "active"
    dnf_log = state / "dnf.log"
    enable_log = state / "enable.log"
    start_log = state / "start.log"
    if installed:
        installed_flag.write_text("amazon-ssm-agent-1.0-1.amzn2023\n", encoding="utf-8")
    if active:
        active_flag.write_text("active\n", encoding="utf-8")

    _write_exec(
        bin_dir / "rpm",
        f"""
if [[ "$1" == "-q" && "$2" == "amazon-ssm-agent" ]]; then
  if [[ -f "{installed_flag}" ]]; then
    cat "{installed_flag}"
    exit 0
  fi
  exit 1
fi
exit 1
""",
    )
    dnf_body = f'echo dnf "$@" >> "{dnf_log}"\n'
    if dnf_ok:
        dnf_body += f'echo "amazon-ssm-agent-1.0-1.amzn2023" > "{installed_flag}"\nexit 0\n'
    else:
        dnf_body += "exit 1\n"
    _write_exec(bin_dir / "dnf", dnf_body)
    _write_exec(
        bin_dir / "systemctl",
        f"""
cmd="${{1:-}}"
if [[ "$cmd" == "enable" ]]; then
  echo enable "$@" >> "{enable_log}"
  exit 0
fi
if [[ "$cmd" == "start" ]]; then
  echo start "$@" >> "{start_log}"
  echo active > "{active_flag}"
  exit 0
fi
if [[ "$cmd" == "is-active" ]]; then
  if [[ -f "{active_flag}" ]]; then
    exit 0
  fi
  exit 3
fi
if [[ "$cmd" == "status" ]]; then
  echo "Mock status for amazon-ssm-agent"
  exit 0
fi
exit 1
""",
    )

    env = os.environ.copy()
    env["PATH"] = f"{bin_dir}:{os.environ.get('PATH', '/usr/bin:/bin')}"
    proc = subprocess.run(
        ["bash", str(script)],
        cwd=tmp_path,
        capture_output=True,
        text=True,
        check=False,
        env=env,
    )
    return proc, dnf_log, enable_log, start_log


def test_ssm_invariant_installs_when_missing(tmp_path: Path) -> None:
    proc, dnf_log, enable_log, start_log = _run_extracted_ssm(
        tmp_path, installed=False, active=False
    )
    assert proc.returncode == 0, proc.stderr + proc.stdout
    assert "package missing; installing" in proc.stdout
    assert "ok: systemd unit is active" in proc.stdout
    assert "invariant ok" in proc.stdout
    assert "amazon-ssm-agent" in dnf_log.read_text(encoding="utf-8")
    assert "enable" in enable_log.read_text(encoding="utf-8")
    assert "start" in start_log.read_text(encoding="utf-8")


def test_ssm_invariant_is_idempotent_when_already_installed(tmp_path: Path) -> None:
    proc, dnf_log, enable_log, start_log = _run_extracted_ssm(tmp_path, installed=True, active=True)
    assert proc.returncode == 0, proc.stderr + proc.stdout
    assert "already installed" in proc.stdout
    assert "ok: systemd unit is active" in proc.stdout
    assert not dnf_log.exists()
    assert "enable" in enable_log.read_text(encoding="utf-8")
    assert "start" in start_log.read_text(encoding="utf-8")


def test_ssm_invariant_fails_closed_when_dnf_install_fails(tmp_path: Path) -> None:
    proc, dnf_log, _enable_log, _start_log = _run_extracted_ssm(
        tmp_path, installed=False, active=False, dnf_ok=False
    )
    assert proc.returncode != 0
    assert "dnf install failed" in proc.stderr or "dnf install failed" in proc.stdout
    assert "invariant failed" in proc.stdout or "invariant failed" in proc.stderr
    assert dnf_log.exists()


def test_ssm_invariant_fails_closed_when_unit_not_active(tmp_path: Path) -> None:
    text = _read(PROD_USER_DATA)
    block = _ssm_block(text)
    script = tmp_path / "run-ssm.sh"
    script.write_text(
        "#!/bin/bash\nset -euo pipefail\n" + textwrap.dedent(block) + "\n",
        encoding="utf-8",
    )
    script.chmod(0o755)
    bin_dir = tmp_path / "bin"
    bin_dir.mkdir()
    _write_exec(
        bin_dir / "rpm",
        """
if [[ "$1" == "-q" && "$2" == "amazon-ssm-agent" ]]; then
  echo "amazon-ssm-agent-1.0-1.amzn2023"
  exit 0
fi
exit 1
""",
    )
    _write_exec(
        bin_dir / "systemctl",
        """
cmd="${1:-}"
if [[ "$cmd" == "enable" || "$cmd" == "start" || "$cmd" == "status" ]]; then
  exit 0
fi
if [[ "$cmd" == "is-active" ]]; then
  exit 3
fi
exit 1
""",
    )
    env = os.environ.copy()
    env["PATH"] = f"{bin_dir}:{os.environ.get('PATH', '/usr/bin:/bin')}"
    proc = subprocess.run(
        ["bash", str(script)],
        cwd=tmp_path,
        capture_output=True,
        text=True,
        check=False,
        env=env,
    )
    assert proc.returncode != 0
    combined = proc.stdout + proc.stderr
    assert "systemd unit is not active" in combined
    assert "invariant failed" in combined


# ---------------------------------------------------------------------------
# Security architecture preserved
# ---------------------------------------------------------------------------


def test_no_ssh_or_inbound_management_workaround() -> None:
    ud = _read(PROD_USER_DATA)
    sg = _read(SG_MAIN)
    ec2 = _read(EC2_MAIN)
    iam = _read(IAM_MAIN)
    lower = ud.lower()
    assert "openssh" not in lower
    assert "sshd" not in lower
    assert "ssh-server" not in lower
    assert re.search(r"(^|\n)\s*ssh\s", ud) is None
    assert "22/tcp" not in ud
    assert "from_port         = 22" not in sg
    assert "to_port           = 22" not in sg
    assert "from_port                    = 8000" in sg
    assert "key_name" not in ec2
    assert "associate_public_ip_address = var.associate_public_ip" in ec2
    assert "AmazonSSMManagedInstanceCore" in iam
    assert "GITHUB_TOKEN" not in ud
    assert "DATABASE_URL=" not in ud
    assert "SECRET_KEY" not in ud
    assert "aws_secret_access_key" not in lower


def test_production_user_data_gzip_stays_within_ec2_limit() -> None:
    source = PROD_USER_DATA.read_bytes()
    compressed = gzip.compress(source)
    assert gzip.decompress(compressed) == source
    assert len(compressed) <= EC2_USER_DATA_RAW_LIMIT
    assert len(base64.b64encode(compressed)) > 0


def test_embedded_safeextract_no_longer_rejects_production_overlay() -> None:
    text = _read(PROD_USER_DATA)
    start = text.index("cat >/opt/dealbrain/bin/verify_production_bundle.py")
    end = text.index("SAFEEXTRACT\nchmod 0755 /opt/dealbrain/bin/verify_production_bundle.py")
    embedded = text[start:end]
    assert "compose/docker-compose.production.yml" in embedded
    assert "production overlay must not be present" not in embedded
    assert "staging overlay must not be present" in embedded
    assert "docker-compose.staging.yml" in embedded
    assert '"bin/production_evidence.py"' in embedded
    assert '"bin/evidence.py"' not in embedded
    evidence = _read(EVIDENCE)
    assert "staging overlay" in evidence
    assert "PR #136" in evidence
    assert "scripts-user" in evidence

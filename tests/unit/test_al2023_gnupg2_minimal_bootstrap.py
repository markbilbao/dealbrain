"""AL2023 bootstrap must keep gnupg2-minimal; never force full gnupg2."""

from __future__ import annotations

import gzip
import os
import re
import shutil
import stat
import subprocess
import textwrap
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[2]
PROD_USER_DATA = ROOT / "infra/ec2/user_data/production.sh"
STAGING_USER_DATA = ROOT / "infra/ec2/user_data/staging.sh"
COMPOSE_INSTALLER = ROOT / "scripts/deploy/host/install-compose-plugin.sh"
EVIDENCE = ROOT / "docs/roadmap/evidence/PRODUCTION_BOOTSTRAP_GNUPG2_MINIMAL_CONFLICT_2026-09-14.md"

GPG_BEGIN = "# --- BEGIN gpg prerequisite ---"
GPG_END = "# --- END gpg prerequisite ---"
SSM_BEGIN = "# --- BEGIN amazon-ssm-agent invariant ---"
SSM_END = "# --- END amazon-ssm-agent invariant ---"
EXPECTED_DOCKER_GPG_FP = "060A61C51B558A7F742B77AAC52FEB6B621E9F35"
SPACED_DOCKER_GPG_FP = "060A 61C5 1B55 8A7F 742B 77AA C52F EB6B 621E 9F35"
STARTING_MAIN = "630c175612e36e8fff0da537cfc2a7eaddb7d0d7"
EC2_USER_DATA_RAW_LIMIT = 16_384

REQUIRED_RUNTIME_PACKAGES = (
    "docker",
    "awscli",
    "jq",
    "python3",
    "tar",
    "gzip",
    "findutils",
    "util-linux",
    "coreutils",
)

BOOTSTRAP_SCRIPTS = (
    pytest.param(PROD_USER_DATA, id="production"),
    pytest.param(STAGING_USER_DATA, id="staging"),
)


def _read(path: Path) -> str:
    assert path.is_file(), f"missing {path}"
    return path.read_text(encoding="utf-8")


def _runtime_dnf_install_block(text: str) -> str:
    start = text.index("dnf -y install \\\n  docker")
    lines: list[str] = []
    for line in text[start:].splitlines():
        lines.append(line)
        if not line.rstrip().endswith("\\"):
            break
    return "\n".join(lines)


def _runtime_packages(text: str) -> list[str]:
    packages: list[str] = []
    for line in _runtime_dnf_install_block(text).splitlines()[1:]:
        pkg = line.strip().rstrip("\\").strip()
        if pkg:
            packages.append(pkg)
    return packages


def _gpg_block(text: str) -> str:
    start = text.index(GPG_BEGIN) + len(GPG_BEGIN)
    end = text.index(GPG_END, start)
    return text[start:end]


def _dnf_installs_full_gnupg2(text: str) -> bool:
    return re.search(r"dnf\s+-y\s+install\s+gnupg2(?:\s|$)", text) is not None


def _write_exec(path: Path, body: str) -> None:
    path.write_text("#!/bin/bash\nset -euo pipefail\n" + body + "\n", encoding="utf-8")
    path.chmod(path.stat().st_mode | stat.S_IXUSR | stat.S_IXGRP | stat.S_IXOTH)


def _run_ensure_gpg(
    tmp_path: Path,
    source: Path,
    *,
    gpg_present: bool,
    dnf_ok: bool = True,
    install_provides_gpg: bool = True,
) -> tuple[subprocess.CompletedProcess[str], Path]:
    block = textwrap.dedent(_gpg_block(_read(source)))
    script = tmp_path / "run-gpg.sh"
    script.write_text("#!/bin/bash\nset -euo pipefail\n" + block + "\n", encoding="utf-8")
    script.chmod(0o755)

    bin_dir = tmp_path / "bin"
    bin_dir.mkdir()
    dnf_log = tmp_path / "dnf.log"
    _write_exec(bin_dir / "date", 'printf "1970-01-01T00:00:00Z"\n')
    dnf_body = f'printf "dnf %s\\n" "$*" >> "{dnf_log}"\n'
    if not dnf_ok:
        dnf_body += "exit 1\n"
    elif install_provides_gpg:
        gpg_path = bin_dir / "gpg"
        dnf_body += (
            f'printf "%s\\n" "#!/bin/bash" "exit 0" > "{gpg_path}"\n'
            f'chmod 0755 "{gpg_path}"\n'
            "exit 0\n"
        )
    else:
        dnf_body += "exit 0\n"
    _write_exec(bin_dir / "dnf", dnf_body)
    chmod_src = shutil.which("chmod")
    assert chmod_src is not None
    os.symlink(chmod_src, bin_dir / "chmod")
    if gpg_present:
        _write_exec(bin_dir / "gpg", "exit 0\n")

    bash = shutil.which("bash")
    assert bash is not None
    env = os.environ.copy()
    env["PATH"] = str(bin_dir)
    proc = subprocess.run(
        [bash, str(script)],
        cwd=tmp_path,
        capture_output=True,
        text=True,
        check=False,
        env=env,
    )
    return proc, dnf_log


@pytest.mark.parametrize("script", BOOTSTRAP_SCRIPTS)
def test_bootstrap_does_not_unconditionally_install_full_gnupg2(script: Path) -> None:
    text = _read(script)
    packages = _runtime_packages(text)
    assert packages == list(REQUIRED_RUNTIME_PACKAGES)
    assert "gnupg2" not in packages
    assert "gnupg2-minimal" not in packages
    assert not _dnf_installs_full_gnupg2(text)
    block = _gpg_block(text)
    assert "command -v gpg" in block
    assert "dnf -y install gnupg2-minimal" in block
    assert "if command -v gpg" in block
    assert block.index("if command -v gpg") < block.index("dnf -y install gnupg2-minimal")
    assert "already present; keeping AL2023 provider package" in block


@pytest.mark.parametrize("script", BOOTSTRAP_SCRIPTS)
def test_present_gpg_skips_package_replacement(tmp_path: Path, script: Path) -> None:
    proc, dnf_log = _run_ensure_gpg(tmp_path, script, gpg_present=True, dnf_ok=False)
    assert proc.returncode == 0, proc.stderr + proc.stdout
    assert "already present; keeping AL2023 provider package" in proc.stdout
    assert "prerequisite ok" in proc.stdout
    assert not dnf_log.exists()


@pytest.mark.parametrize("script", BOOTSTRAP_SCRIPTS)
def test_missing_gpg_installs_gnupg2_minimal_not_full_gnupg2(tmp_path: Path, script: Path) -> None:
    proc, dnf_log = _run_ensure_gpg(tmp_path, script, gpg_present=False, dnf_ok=True)
    assert proc.returncode == 0, proc.stderr + proc.stdout
    assert "installing AL2023 gnupg2-minimal" in proc.stdout
    logged = dnf_log.read_text(encoding="utf-8")
    assert "gnupg2-minimal" in logged
    assert re.search(r"(^|\s)gnupg2(\s|$)", logged) is None
    assert "--allowerasing" not in logged


@pytest.mark.parametrize("script", BOOTSTRAP_SCRIPTS)
def test_gpg_prerequisite_fails_closed_when_still_missing(tmp_path: Path, script: Path) -> None:
    proc, dnf_log = _run_ensure_gpg(
        tmp_path, script, gpg_present=False, dnf_ok=True, install_provides_gpg=False
    )
    assert proc.returncode != 0
    combined = proc.stdout + proc.stderr
    assert "gpg missing after prerequisite handling" in combined
    assert "prerequisite failed" in combined
    assert dnf_log.exists()


@pytest.mark.parametrize("script", BOOTSTRAP_SCRIPTS)
def test_gpg_prerequisite_fails_closed_when_dnf_install_fails(tmp_path: Path, script: Path) -> None:
    proc, dnf_log = _run_ensure_gpg(tmp_path, script, gpg_present=False, dnf_ok=False)
    assert proc.returncode != 0
    combined = proc.stdout + proc.stderr
    assert "dnf install gnupg2-minimal failed" in combined
    assert "prerequisite failed" in combined
    assert dnf_log.exists()


@pytest.mark.parametrize("script", BOOTSTRAP_SCRIPTS)
def test_command_v_gpg_verification_remains_after_docker_start(script: Path) -> None:
    text = _read(script)
    after_docker = text.split("systemctl start docker", 1)[1]
    pre_embed = after_docker.split("<< 'COMPOSEPLUGIN'", 1)[0]
    assert "command -v gpg >/dev/null" in pre_embed
    assert "command -v docker >/dev/null" in pre_embed
    assert "command -v aws >/dev/null" in pre_embed
    assert "command -v jq >/dev/null" in pre_embed
    assert "command -v python3 >/dev/null" in pre_embed


@pytest.mark.parametrize("script", BOOTSTRAP_SCRIPTS)
def test_no_package_erasure_or_signature_bypass(script: Path) -> None:
    text = _read(script)
    installer = _read(COMPOSE_INSTALLER)
    for blob in (text, installer):
        assert "--allowerasing" not in blob
        assert "--nodeps" not in blob
        assert "rpm --nodeps" not in blob
        assert "dnf remove" not in blob
        assert "dnf -y remove" not in blob
        assert "gpgcheck=0" not in blob
        assert "repo_gpgcheck=0" not in blob


def test_compose_gpg_security_contracts_unchanged() -> None:
    installer = _read(COMPOSE_INSTALLER)
    staging = _read(STAGING_USER_DATA)
    production = _read(PROD_USER_DATA)
    marker_open = "<< 'COMPOSEPLUGIN'\n"
    marker_close = "\nCOMPOSEPLUGIN\n"
    start = staging.index(marker_open) + len(marker_open)
    end = staging.index(marker_close, start)
    embedded = staging[start:end]
    assert embedded.rstrip("\n") == installer.rstrip("\n")

    fn_start = installer.index("verify_and_import_docker_gpg()")
    fn_body = installer[fn_start : installer.index("\ninstall_plugin()", fn_start)]
    assert EXPECTED_DOCKER_GPG_FP in installer
    assert SPACED_DOCKER_GPG_FP in installer
    assert "gpg --show-keys" in installer
    assert "extract_primary_fingerprints" in installer
    assert "fingerprint mismatch" in fn_body
    assert fn_body.index("fingerprint mismatch") < fn_body.index("rpm --import")
    assert "exactly one primary" in fn_body
    assert fn_body.index("exactly one primary") < fn_body.index("rpm --import")
    assert "gpgcheck=1" in installer
    assert "repo_gpgcheck=1" in installer
    assert (
        "includepkgs=docker-compose-plugin" in installer or "includepkgs=${PLUGIN_PKG}" in installer
    )
    assert "enabled=0" in installer
    assert 'dnf -y install "$PLUGIN_PKG"' in installer
    assert "dnf -y install docker-ce" not in installer
    assert "get.docker.com" not in installer
    assert "github.com/docker/compose/releases" not in installer
    for blob in (installer, staging, production):
        assert EXPECTED_DOCKER_GPG_FP in blob
        assert "gpgcheck=1" in blob
        assert "repo_gpgcheck=1" in blob
        assert "command -v gpg" in blob
        assert not _dnf_installs_full_gnupg2(blob)


def test_production_ssm_invariant_remains_before_package_and_docker() -> None:
    text = _read(PROD_USER_DATA)
    ssm_pos = text.index(SSM_BEGIN)
    ssm_end = text.index(SSM_END)
    pkg_pos = text.index("dnf -y install \\\n  docker")
    gpg_pos = text.index(GPG_BEGIN)
    docker_enable = text.index("systemctl enable docker")
    compose_pos = text.index("/opt/dealbrain/bin/install-compose-plugin.sh")
    bootstrap_ok = text.rindex("touch /opt/dealbrain/bootstrap.ok")
    assert ssm_pos < ssm_end < pkg_pos < gpg_pos < docker_enable < compose_pos < bootstrap_ok
    assert text.index("ensure_amazon_ssm_agent") < pkg_pos
    assert "amazon-ssm-agent" in text[ssm_pos:ssm_end]


@pytest.mark.parametrize("script", BOOTSTRAP_SCRIPTS)
def test_required_runtime_packages_and_update_policy_unchanged(script: Path) -> None:
    text = _read(script)
    assert "dnf -y update || true" in text
    block = _runtime_dnf_install_block(text)
    for pkg in REQUIRED_RUNTIME_PACKAGES:
        assert pkg in block
    assert "systemctl enable docker" in text
    assert "systemctl start docker" in text
    assert text.index("dnf -y update || true") < text.index("dnf -y install \\\n  docker")
    assert text.index(GPG_END) < text.index("systemctl enable docker")


@pytest.mark.parametrize("script", BOOTSTRAP_SCRIPTS)
def test_user_data_gzip_stays_within_ec2_limit(script: Path) -> None:
    source = script.read_bytes()
    compressed = gzip.compress(source)
    assert gzip.decompress(compressed) == source
    assert len(compressed) <= EC2_USER_DATA_RAW_LIMIT


def test_runtime_failure_is_documented() -> None:
    evidence = _read(EVIDENCE)
    assert STARTING_MAIN in evidence
    assert "gnupg2-minimal" in evidence
    assert "i-0994a8ce7a650535e" in evidence
    assert "bootstrap.ok" in evidence
    assert "conflicts with gnupg2" in evidence or "conflict" in evidence
    assert "before Docker" in evidence or "before docker" in evidence.lower()
    assert "NO AWS MUTATION" in evidence
    prod = _read(PROD_USER_DATA)
    staging = _read(STAGING_USER_DATA)
    assert "gnupg2-minimal" in prod
    assert "gnupg2-minimal" in staging

"""Sprint 25b.5b — staging EC2 replacement-plan blockers (gzip user_data + SG ASCII)."""

from __future__ import annotations

import base64
import gzip
import hashlib
import re
import shutil
import subprocess
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
USER_DATA = ROOT / "infra/ec2/user_data/staging.sh"
COMPOSE_INSTALLER = ROOT / "scripts/deploy/host/install-compose-plugin.sh"
EC2_MODULE = ROOT / "infra/terraform/modules/ec2"
STAGING_TF = ROOT / "infra/terraform/environments/staging"
PROD_TF = ROOT / "infra/terraform/environments/production"
SG_MODULE = ROOT / "infra/terraform/modules/security_groups/main.tf"

# EC2 user-data raw (decoded) size limit.
EC2_USER_DATA_RAW_LIMIT = 16_384


def _read(path: Path) -> str:
    assert path.is_file(), f"missing: {path}"
    return path.read_text(encoding="utf-8")


def test_staging_user_data_gzip_within_ec2_limit_and_round_trips() -> None:
    source = USER_DATA.read_bytes()
    assert len(source) > EC2_USER_DATA_RAW_LIMIT, (
        "fixture expects plaintext staging.sh to exceed the EC2 raw limit "
        f"({len(source)} > {EC2_USER_DATA_RAW_LIMIT}); otherwise compression is unused"
    )

    compressed = gzip.compress(source)
    b64 = base64.b64encode(compressed)
    decompressed = gzip.decompress(compressed)

    assert decompressed == source
    assert hashlib.sha256(decompressed).digest() == hashlib.sha256(source).digest()
    assert len(compressed) <= EC2_USER_DATA_RAW_LIMIT
    assert len(b64) > 0

    # Terraform-native base64gzip (provider-free fixture) must match source bytes.
    if shutil.which("terraform") is None:
        return

    with tempfile.TemporaryDirectory(prefix="dealbrain-b64gzip-") as tmp:
        tmp_path = Path(tmp)
        script = tmp_path / "staging.sh"
        script.write_bytes(source)
        (tmp_path / "main.tf").write_text(
            'output "b64" {\n  value = base64gzip(file("${path.module}/staging.sh"))\n}\n',
            encoding="utf-8",
        )
        init = subprocess.run(
            ["terraform", "init", "-backend=false", "-input=false"],
            cwd=tmp_path,
            capture_output=True,
            text=True,
            check=False,
        )
        assert init.returncode == 0, init.stderr
        apply = subprocess.run(
            ["terraform", "apply", "-auto-approve", "-input=false"],
            cwd=tmp_path,
            capture_output=True,
            text=True,
            check=False,
        )
        assert apply.returncode == 0, apply.stderr
        out = subprocess.run(
            ["terraform", "output", "-raw", "b64"],
            cwd=tmp_path,
            capture_output=True,
            text=True,
            check=False,
        )
        assert out.returncode == 0, out.stderr
        tf_b64 = out.stdout.strip()
        assert re.fullmatch(r"[A-Za-z0-9+/]+=*", tf_b64), tf_b64[:80]
        tf_gz = base64.b64decode(tf_b64)
        assert len(tf_gz) <= EC2_USER_DATA_RAW_LIMIT
        assert gzip.decompress(tf_gz) == source
        assert (
            hashlib.sha256(gzip.decompress(tf_gz)).hexdigest() == hashlib.sha256(source).hexdigest()
        )


def test_terraform_uses_user_data_base64_not_plain_user_data() -> None:
    staging = _read(STAGING_TF / "main.tf")
    ec2_main = _read(EC2_MODULE / "main.tf")
    ec2_vars = _read(EC2_MODULE / "variables.tf")

    assert "base64gzip(file(" in staging
    assert "user_data_base64" in staging
    assert "staging_user_data_base64" in staging
    assert re.search(r"^\s*user_data\s*=", staging, re.MULTILINE) is None

    assert "user_data_base64" in ec2_main
    assert re.search(r"^\s*user_data\s*=", ec2_main, re.MULTILINE) is None
    assert 'variable "user_data_base64"' in ec2_vars
    assert 'variable "user_data"' not in ec2_vars
    assert re.search(r"\bvar\.user_data\b", ec2_main) is None
    assert "var.user_data_base64" in ec2_main


def test_compose_installer_security_controls_preserved_in_source_script() -> None:
    ud = _read(USER_DATA)
    installer = _read(COMPOSE_INSTALLER)

    for needle in (
        "docker-compose-plugin",
        "060A61C51B558A7F742B77AAC52FEB6B621E9F35",
        "gpgcheck=1",
        "repo_gpgcheck=1",
        "includepkgs=docker-compose-plugin",
    ):
        assert needle in installer

    assert "--allowerasing" not in installer
    assert "--allowerasing" not in ud
    assert "install-compose-plugin.sh" in ud
    assert "docker compose version >/dev/null" in ud
    assert "touch /opt/dealbrain/bootstrap.ok" in ud
    assert ud.index("docker compose version >/dev/null") < ud.index(
        "touch /opt/dealbrain/bootstrap.ok"
    )
    for forbidden in (
        "https://github.com/docker/compose/releases",
        "curl -fsSL https://get.docker.com",
        "dnf -y install docker-ce",
    ):
        assert forbidden not in ud
        assert forbidden not in installer


def test_security_group_descriptions_are_ascii_hyphen_only() -> None:
    text = _read(SG_MODULE)
    description_lines = [
        line for line in text.splitlines() if re.search(r"^\s*description\s*=", line)
    ]
    assert description_lines, "expected security-group description attributes"
    for line in description_lines:
        assert line.isascii(), f"non-ASCII in security-group description: {line!r}"
        assert "\u2014" not in line and "\u2013" not in line
        if "DealBrain" in line:
            assert " - " in line


def test_production_untouched_by_compressed_user_data() -> None:
    prod = _read(PROD_TF / "main.tf")
    assert "user_data" not in prod
    assert "user_data_base64" not in prod
    assert "base64gzip" not in prod
    assert "staging_user_data" not in prod
    assert "install-compose-plugin" not in prod
    assert 'module "security_groups"' in prod
    assert "../../modules/security_groups" in prod

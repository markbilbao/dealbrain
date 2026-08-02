#!/usr/bin/env python3
"""Build a deterministic staging release bundle (Sprint 25b.3).

Includes only staging compose overlays, host deploy scripts, the validated
original release manifest, and bundle-meta.json. Never includes production
compose, secrets, credentials, .env, Terraform state, or Git metadata.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import shutil
import sys
import tarfile
import tempfile
from datetime import UTC, datetime
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]

BUNDLE_SCHEMA_VERSION = 1

INCLUDE_FILES: tuple[tuple[str, str], ...] = (
    ("infra/compose/docker-compose.base.yml", "compose/docker-compose.base.yml"),
    ("infra/compose/docker-compose.staging.yml", "compose/docker-compose.staging.yml"),
    ("scripts/deploy/host/dealbrain-staging-deploy.sh", "bin/dealbrain-staging-deploy.sh"),
    ("scripts/deploy/host/deploy_atomicity.sh", "bin/deploy_atomicity.sh"),
    ("scripts/deploy/host/assemble-runtime-env.py", "bin/assemble-runtime-env.py"),
    ("scripts/deploy/host/ghcr-login.sh", "bin/ghcr-login.sh"),
    ("scripts/deploy/host/verify-staging.sh", "bin/verify-staging.sh"),
    ("scripts/deploy/host/write-staging-evidence.py", "bin/write-staging-evidence.py"),
    ("scripts/deploy/evidence.py", "bin/evidence.py"),
    ("scripts/deploy/log_redaction.py", "bin/log_redaction.py"),
    ("scripts/deploy/alb_target_health.py", "bin/alb_target_health.py"),
    ("scripts/deploy/verify_staging_bundle.py", "bin/verify_staging_bundle.py"),
    ("scripts/deploy/probe_checks.py", "bin/probe_checks.py"),
    ("schemas/staging-deploy-evidence.schema.json", "bin/staging-deploy-evidence.schema.json"),
)

FORBIDDEN_NAMES = (
    "docker-compose.production.yml",
    ".env",
    "terraform.tfstate",
    ".git",
    "credentials",
)


class BundleError(ValueError):
    """Raised when bundle creation fails closed."""


def _sha256_file(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()


def _utc_now_z() -> str:
    return datetime.now(UTC).strftime("%Y-%m-%dT%H:%M:%SZ")


def build_bundle(
    *,
    manifest_path: Path,
    out_dir: Path,
    rds_nonsecret: dict | None = None,
    alb_nonsecret: dict | None = None,
) -> tuple[Path, Path, dict]:
    with manifest_path.open(encoding="utf-8") as handle:
        manifest = json.load(handle)

    release_id = manifest["release_id"]
    git_sha = manifest["git_sha"]
    image_repository = manifest["image_repository"]
    image_digest = manifest["image_digest"]
    source_manifest_sha256 = manifest["manifest_sha256"]

    out_dir.mkdir(parents=True, exist_ok=True)
    staging = Path(tempfile.mkdtemp(prefix="dealbrain-bundle-"))
    try:
        for src_rel, dst_rel in INCLUDE_FILES:
            src = ROOT / src_rel
            if not src.is_file():
                raise BundleError(f"missing required bundle source: {src_rel}")
            dst = staging / dst_rel
            dst.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(src, dst)
            # Ensure scripts are executable in the archive.
            if dst_rel.startswith("bin/") and dst.suffix in {"", ".sh", ".py"}:
                mode = dst.stat().st_mode
                dst.chmod(mode | 0o111)

        # Original validated manifest (copy only — never mutate).
        man_dst = staging / "manifest" / "release-manifest.json"
        man_dst.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(manifest_path, man_dst)

        if rds_nonsecret is not None:
            (staging / "manifest" / "rds-nonsecret.json").write_text(
                json.dumps(rds_nonsecret, indent=2, sort_keys=True) + "\n",
                encoding="utf-8",
            )
        if alb_nonsecret is not None:
            (staging / "manifest" / "alb-nonsecret.json").write_text(
                json.dumps(alb_nonsecret, indent=2, sort_keys=True) + "\n",
                encoding="utf-8",
            )

        # Fail closed if production overlay somehow present.
        prod = staging / "compose" / "docker-compose.production.yml"
        if prod.exists():
            raise BundleError("production compose overlay must not be in staging bundle")

        for path in staging.rglob("*"):
            name = path.name.lower()
            for forbidden in FORBIDDEN_NAMES:
                if forbidden in name:
                    raise BundleError(f"forbidden path in bundle staging area: {path}")

        file_checksums: dict[str, str] = {}
        for path in sorted(staging.rglob("*")):
            if path.is_file():
                rel = path.relative_to(staging).as_posix()
                file_checksums[rel] = _sha256_file(path)

        meta = {
            "schema_version": BUNDLE_SCHEMA_VERSION,
            "release_id": release_id,
            "git_sha": git_sha,
            "image_repository": image_repository,
            "image_digest": image_digest,
            "source_manifest_sha256": source_manifest_sha256,
            "file_checksums": file_checksums,
            "created_at": _utc_now_z(),
        }
        meta_path = staging / "bundle-meta.json"
        meta_path.write_text(json.dumps(meta, indent=2, sort_keys=True) + "\n", encoding="utf-8")
        # Include meta checksum in a second pass map written into meta itself.
        file_checksums["bundle-meta.json"] = _sha256_file(meta_path)
        meta["file_checksums"] = file_checksums
        meta_path.write_text(json.dumps(meta, indent=2, sort_keys=True) + "\n", encoding="utf-8")

        # Deterministic tar.gz: sorted names, fixed mtime/uid/gid.
        tarball = out_dir / "bundle.tar.gz"
        fixed_mtime = 0

        def _filter(tarinfo: tarfile.TarInfo) -> tarfile.TarInfo:
            tarinfo.uid = 0
            tarinfo.gid = 0
            tarinfo.uname = "root"
            tarinfo.gname = "root"
            tarinfo.mtime = fixed_mtime
            return tarinfo

        with tarfile.open(tarball, "w:gz", compresslevel=9, format=tarfile.PAX_FORMAT) as tar:
            for path in sorted(staging.rglob("*")):
                if path.is_file():
                    arcname = path.relative_to(staging).as_posix()
                    tar.add(path, arcname=arcname, filter=_filter)

        checksum = _sha256_file(tarball)
        checksum_path = out_dir / "bundle.sha256"
        checksum_path.write_text(f"{checksum}  bundle.tar.gz\n", encoding="utf-8")

        # Persist final meta alongside artifacts for workflow convenience.
        (out_dir / "bundle-meta.json").write_text(
            json.dumps(meta, indent=2, sort_keys=True) + "\n", encoding="utf-8"
        )
        return tarball, checksum_path, meta
    finally:
        shutil.rmtree(staging, ignore_errors=True)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--manifest", type=Path, required=True)
    parser.add_argument("--out-dir", type=Path, required=True)
    parser.add_argument("--rds-nonsecret", type=Path, default=None)
    parser.add_argument("--alb-nonsecret", type=Path, default=None)
    args = parser.parse_args(argv)

    rds = None
    alb = None
    if args.rds_nonsecret:
        rds = json.loads(args.rds_nonsecret.read_text(encoding="utf-8"))
    if args.alb_nonsecret:
        alb = json.loads(args.alb_nonsecret.read_text(encoding="utf-8"))

    try:
        tarball, checksum_path, meta = build_bundle(
            manifest_path=args.manifest,
            out_dir=args.out_dir,
            rds_nonsecret=rds,
            alb_nonsecret=alb,
        )
    except BundleError as exc:
        print(f"FAIL: {exc}", file=sys.stderr)
        return 1

    print(
        json.dumps(
            {
                "bundle": str(tarball),
                "checksum_file": str(checksum_path),
                "checksum": checksum_path.read_text(encoding="utf-8").split()[0],
                "release_id": meta["release_id"],
            },
            sort_keys=True,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

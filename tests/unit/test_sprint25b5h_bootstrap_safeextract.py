"""Sprint 25b.5h — bootstrap SAFEEXTRACT Python 3.9 extractor compatibility.

Extracts and executes the embedded verifier from ``infra/ec2/user_data/staging.sh``
and proves behavioral parity with ``scripts/deploy/verify_staging_bundle.py``.

Host repair (plan only — do not execute against live EC2):
  Read-only diagnostics first (Python version, filter= support, installed
  verifier fallback presence, harmless self-test). Repair only after merge,
  from the approved commit/artifact with checksum, backup, atomic install,
  syntax check, self-test, and rollback. See module constants below.
"""

from __future__ import annotations

import hashlib
import inspect
import io
import json
import re
import subprocess
import tarfile
import textwrap
from pathlib import Path
from types import ModuleType

import pytest
from scripts.deploy.build_staging_bundle import build_bundle
from scripts.deploy.verify_staging_bundle import (
    REQUIRED_MEMBERS as CANONICAL_REQUIRED,
)
from scripts.deploy.verify_staging_bundle import (
    BundleVerifyError as CanonicalBundleVerifyError,
)
from scripts.deploy.verify_staging_bundle import (
    verify_bundle as canonical_verify_bundle,
)
from scripts.release.manifest import create_built_manifest

ROOT = Path(__file__).resolve().parents[2]
STAGING_SH = ROOT / "infra/ec2/user_data/staging.sh"
CANONICAL_PY = ROOT / "scripts/deploy/verify_staging_bundle.py"
HOST_VERIFY_SH = ROOT / "scripts/deploy/host/verify-staging.sh"

SAMPLE_SHA = "0123456789abcdef0123456789abcdef01234567"
SAMPLE_DIGEST = "sha256:" + ("b" * 64)
SAMPLE_REPO = "ghcr.io/example-org/dealbrain"

# Extraction-contract markers that must appear in both implementations.
EXTRACT_CONTRACT_MARKERS = (
    'filter="data"',
    "_is_unsupported_filter_typeerror",
    "unexpected keyword argument",
    "extract path escaped destination",
    "symlink/hardlink rejected",
    "special file rejected",
    "path traversal rejected",
    "absolute path rejected",
    "setuid/setgid/sticky mode rejected",
    "duplicate archive member",
    "forbidden member in bundle",
    "bundle checksum mismatch",
    "missing required member",
)

# Rollback-specific members ship via Deploy Staging schema-2 bundles only.
ROLLBACK_ONLY_REQUIRED_MEMBERS = (
    "bin/dealbrain-staging-rollback.sh",
    "bin/rollback_evidence.py",
    "bin/write-staging-rollback-evidence.py",
    "bin/prior_staging_evidence.py",
    "bin/verify_host_rollback_tooling.py",
    "bin/resolve-rollback-migration.py",
    "bin/staging-rollback-evidence.schema.json",
)

# Pre-PR #40 / Sprint 25b.5h bootstrap REQUIRED_MEMBERS (no rollback tooling).
BOOTSTRAP_BASELINE_REQUIRED_MEMBERS = (
    "compose/docker-compose.base.yml",
    "compose/docker-compose.staging.yml",
    "bin/dealbrain-staging-deploy.sh",
    "bin/deploy_atomicity.sh",
    "bin/assemble-runtime-env.py",
    "bin/ghcr-login.sh",
    "bin/verify-staging.sh",
    "bin/alb_target_health.py",
    "bin/evidence.py",
    "bin/write-staging-evidence.py",
    "bin/staging-deploy-evidence.schema.json",
    "bin/log_redaction.py",
    "manifest/release-manifest.json",
    "bundle-meta.json",
)

# ---------------------------------------------------------------------------
# Existing-host read-only diagnostic + conditional atomic repair (PLAN ONLY)
# ---------------------------------------------------------------------------
HOST_READONLY_DIAGNOSTIC_PLAN = textwrap.dedent(
    """
    # Read-only diagnostics (SSM/SSH). Do not mutate the host.
    python3 --version
    python3 - <<'PY'
    import inspect, tarfile, pathlib
    sig = inspect.signature(tarfile.TarFile.extract)
    print("filter_in_signature=", "filter" in sig.parameters)
    path = pathlib.Path("/opt/dealbrain/bin/verify_staging_bundle.py")
    text = path.read_text(encoding="utf-8") if path.is_file() else ""
    print("installed=", path.is_file())
    print("has_fallback=", "_is_unsupported_filter_typeerror" in text or (
        "TypeError" in text and "filter" in text and "tar.extract" in text
        and text.count("tar.extract(") >= 2
    ))
    print("has_filter_data=", 'filter="data"' in text or "filter='data'" in text)
    PY
    # Harmless self-test: build/copy a tiny valid staging bundle onto the host
    # and run verify with --checksum (temp dest under /tmp). Expect exit 0.
    # If already healthy: STOP — no repair required.
    """
).strip()

HOST_CONDITIONAL_ATOMIC_REPAIR_PLAN = textwrap.dedent(
    """
    # Execute ONLY after repository fix is approved and merged.
    # Source: approved merged commit OR verified release artifact (never
    # unreviewed local working-tree bytes). Verify sha256 before install.
    # 1) Backup existing verifier to a timestamped .bak beside it.
    # 2) Stage: install -o root -g root -m 0755 SRC \\
    #           /opt/dealbrain/bin/.verify_staging_bundle.py.new
    # 3) Atomic rename of the staged file onto verify_staging_bundle.py
    # 4) python3 -m py_compile /opt/dealbrain/bin/verify_staging_bundle.py
    # 5) Harmless extract self-test (temp bundle + --extract-to under /tmp)
    # 6) Rollback: restore .bak if self-test fails
    # No secrets/DB/env dumps; no API restart unless proven required; no prod.
    """
).strip()


def _built_manifest() -> dict:
    return create_built_manifest(
        git_sha=SAMPLE_SHA,
        image_repository=SAMPLE_REPO,
        image_digest=SAMPLE_DIGEST,
        build_workflow_run_id="111",
        test_workflow_run_id="222",
        created_at="2026-08-02T12:00:00Z",
        release_id=f"rel-20260802T120000Z-{SAMPLE_SHA[:12]}",
    )


def _extract_safeextract_source() -> str:
    text = STAGING_SH.read_text(encoding="utf-8")
    marker = "cat >/opt/dealbrain/bin/verify_staging_bundle.py << 'SAFEEXTRACT'\n"
    start = text.index(marker) + len(marker)
    end = text.index("\nSAFEEXTRACT\n", start)
    source = text[start:end]
    assert source.startswith("#!/usr/bin/env python3"), "SAFEEXTRACT shebang missing"
    return source


def _load_embedded_verifier() -> ModuleType:
    source = _extract_safeextract_source()
    module = ModuleType("dealbrain_bootstrap_safeextract")
    compiled = compile(source, "<SAFEEXTRACT:staging.sh>", "exec")
    exec(compiled, module.__dict__)  # noqa: S102 — intentional behavioral load
    return module


def _build_valid_bundle(tmp: Path) -> tuple[Path, str, dict]:
    man_path = tmp / "release-manifest.json"
    man_path.write_text(json.dumps(_built_manifest()), encoding="utf-8")
    out = tmp / "out"
    tarball, checksum_path, meta = build_bundle(manifest_path=man_path, out_dir=out)
    checksum = checksum_path.read_text(encoding="utf-8").split()[0]
    return tarball, checksum, meta


def _force_filter_typeerror(monkeypatch: pytest.MonkeyPatch, *, module: ModuleType) -> list[dict]:
    """Simulate runtime without filter= support on the embedded module's tarfile."""
    calls: list[dict] = []
    real_extract = module.tarfile.TarFile.extract

    def fake_extract(self, member, path="", set_attrs=True, *, filter=None):  # noqa: A002
        calls.append({"name": member.name, "filter": filter, "path": str(path)})
        if filter is not None:
            raise TypeError("extract() got an unexpected keyword argument 'filter'")
        return real_extract(self, member, path=path, set_attrs=set_attrs)

    monkeypatch.setattr(module.tarfile.TarFile, "extract", fake_extract)
    return calls


def _malicious_tarball(
    tmp: Path,
    member_name: str,
    *,
    link_type: str | None = None,
    linkname: str | None = None,
) -> Path:
    tar_path = tmp / f"evil-{hashlib.sha256(member_name.encode()).hexdigest()[:10]}.tar.gz"
    with tarfile.open(tar_path, "w:gz") as tar:
        if link_type == "symlink":
            info = tarfile.TarInfo(name=member_name)
            info.type = tarfile.SYMTYPE
            info.linkname = linkname or "/etc/passwd"
            tar.addfile(info)
        elif link_type == "hardlink":
            data = b"x"
            base = tarfile.TarInfo(name="bin/harmless.txt")
            base.size = len(data)
            tar.addfile(base, fileobj=io.BytesIO(data))
            link = tarfile.TarInfo(name=member_name)
            link.type = tarfile.LNKTYPE
            link.linkname = linkname or "bin/harmless.txt"
            tar.addfile(link)
        elif link_type == "chr":
            info = tarfile.TarInfo(name=member_name)
            info.type = tarfile.CHRTYPE
            info.devmajor = 1
            info.devminor = 3
            tar.addfile(info)
        elif link_type == "fifo":
            info = tarfile.TarInfo(name=member_name)
            info.type = tarfile.FIFOTYPE
            tar.addfile(info)
        else:
            data = b"evil"
            info = tarfile.TarInfo(name=member_name)
            info.size = len(data)
            tar.addfile(info, fileobj=io.BytesIO(data))
    return tar_path


# ---------------------------------------------------------------------------
# Inventory / contract markers
# ---------------------------------------------------------------------------


def test_bootstrap_inventory_only_staging_user_data_embeds_verifier() -> None:
    """Active bootstrap install path for /opt/dealbrain/bin/verify_staging_bundle.py."""
    text = STAGING_SH.read_text(encoding="utf-8")
    assert "cat >/opt/dealbrain/bin/verify_staging_bundle.py << 'SAFEEXTRACT'" in text
    assert text.count("<< 'SAFEEXTRACT'") == 1
    # Release path copies canonical verifier after successful extract (not bootstrap).
    deploy = (ROOT / "scripts/deploy/host/dealbrain-staging-deploy.sh").read_text(encoding="utf-8")
    assert "verify_staging_bundle.py" in deploy
    # Bundle packaging embeds the canonical script.
    build = (ROOT / "scripts/deploy/build_staging_bundle.py").read_text(encoding="utf-8")
    assert "scripts/deploy/verify_staging_bundle.py" in build


def test_extract_contract_markers_present_in_both_copies() -> None:
    embedded = _extract_safeextract_source()
    canonical = CANONICAL_PY.read_text(encoding="utf-8")
    for marker in EXTRACT_CONTRACT_MARKERS:
        assert marker in embedded, f"bootstrap missing marker: {marker}"
        assert marker in canonical, f"canonical missing marker: {marker}"
    assert "extractall(" not in embedded
    assert "extractall(" not in canonical


def test_embedded_safeextract_parses_and_loads() -> None:
    source = _extract_safeextract_source()
    compile(source, "<SAFEEXTRACT>", "exec")
    mod = _load_embedded_verifier()
    assert callable(mod.extract_validated_bundle)
    assert callable(mod.validate_archive_members)
    assert callable(mod._extract_members)
    assert callable(mod._is_unsupported_filter_typeerror)


# ---------------------------------------------------------------------------
# Behavioral: modern + Python 3.9 fallback on embedded SAFEEXTRACT
# ---------------------------------------------------------------------------


def test_embedded_modern_filter_path_extracts_valid_bundle(tmp_path: Path) -> None:
    mod = _load_embedded_verifier()
    tarball, checksum, meta = _build_valid_bundle(tmp_path)
    dest = tmp_path / "release"
    result = mod.extract_validated_bundle(
        tarball,
        dest,
        expected_checksum=checksum,
        expected_release_id=meta["release_id"],
        expected_digest=meta["image_digest"],
    )
    assert result["checksum"] == checksum
    assert (dest / "bundle-meta.json").is_file()
    assert (dest / "bin/dealbrain-staging-deploy.sh").is_file()

    sig = inspect.signature(tarfile.TarFile.extract)
    if "filter" in sig.parameters:
        calls: list[dict] = []
        real_extract = mod.tarfile.TarFile.extract

        def tracking_extract(self, member, path="", set_attrs=True, *, filter=None):  # noqa: A002
            calls.append({"filter": filter})
            return real_extract(self, member, path=path, set_attrs=set_attrs, filter=filter)

        mod.tarfile.TarFile.extract = tracking_extract  # type: ignore[method-assign]
        dest2 = tmp_path / "release2"
        mod.extract_validated_bundle(
            tarball,
            dest2,
            expected_checksum=checksum,
            expected_release_id=meta["release_id"],
        )
        assert any(c["filter"] == "data" for c in calls)


def test_embedded_python39_fallback_extracts_per_member(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    mod = _load_embedded_verifier()
    calls = _force_filter_typeerror(monkeypatch, module=mod)
    tarball, checksum, meta = _build_valid_bundle(tmp_path)
    dest = tmp_path / "release"
    result = mod.extract_validated_bundle(
        tarball,
        dest,
        expected_checksum=checksum,
        expected_release_id=meta["release_id"],
        expected_digest=meta["image_digest"],
    )
    assert result["checksum"] == checksum
    assert any(c["filter"] == "data" for c in calls)
    assert any(c["filter"] is None for c in calls)
    # Per-member only — never extractall.
    assert "extractall" not in _extract_safeextract_source()
    assert (dest / "manifest/release-manifest.json").is_file()


def test_embedded_fallback_rejects_unsafe_corpus(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    mod = _load_embedded_verifier()
    _force_filter_typeerror(monkeypatch, module=mod)
    cases = [
        ("../escape", None, "traversal|absolute|unexpected"),
        ("/absolute/path", None, "absolute|unexpected"),
        ("C:/Windows/System32/evil", None, "absolute"),
        ("D:\\Windows\\evil", None, "absolute"),
        ("bin/link", "symlink", "symlink|hardlink"),
        ("bin/hard", "hardlink", "symlink|hardlink"),
        ("bin/link-escape", "symlink", "symlink|hardlink"),
        ("bin/hard-escape", "hardlink", "symlink|hardlink"),
        ("bin/evil-chr", "chr", "special file"),
        ("bin/evil-fifo", "fifo", "special file"),
        ("compose/docker-compose.production.yml", None, "forbidden|production"),
        ("unexpected/top.txt", None, "unexpected"),
    ]
    linkname_map = {
        "bin/link-escape": "../../etc/passwd",
        "bin/hard-escape": "../../etc/passwd",
    }
    for name, link_type, match in cases:
        evil = _malicious_tarball(
            tmp_path,
            name,
            link_type=link_type,
            linkname=linkname_map.get(name),
        )
        with pytest.raises(mod.BundleVerifyError, match=match):
            mod.extract_validated_bundle(
                evil,
                tmp_path / f"dest-{hashlib.sha256(name.encode()).hexdigest()[:8]}",
                expected_checksum=hashlib.sha256(evil.read_bytes()).hexdigest(),
            )


def test_embedded_fallback_rejects_destination_escape(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    mod = _load_embedded_verifier()
    _force_filter_typeerror(monkeypatch, module=mod)
    dest = tmp_path / "dest"
    dest.mkdir()
    with tarfile.open(tmp_path / "x.tar.gz", "w:gz") as tar:
        data = b"x"
        info = tarfile.TarInfo(name="bin/ok.txt")
        info.size = len(data)
        tar.addfile(info, fileobj=io.BytesIO(data))
    with tarfile.open(tmp_path / "x.tar.gz", "r:gz") as tar:
        members = list(tar.getmembers())
        members[0].name = "../escape.txt"
        with pytest.raises(mod.BundleVerifyError, match="escaped destination"):
            mod._extract_members(tar, dest, members)


def test_embedded_checksum_and_required_members_enforced(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    mod = _load_embedded_verifier()
    _force_filter_typeerror(monkeypatch, module=mod)
    tarball, checksum, meta = _build_valid_bundle(tmp_path)
    with pytest.raises(mod.BundleVerifyError, match="checksum mismatch"):
        mod.extract_validated_bundle(
            tarball,
            tmp_path / "bad",
            expected_checksum="0" * 64,
        )
    # Incomplete: drop a required member from a crafted archive that otherwise
    # looks like a layout (reuse valid tarball but wrong expected release).
    with pytest.raises(mod.BundleVerifyError, match="release_id mismatch"):
        mod.extract_validated_bundle(
            tarball,
            tmp_path / "bad-rid",
            expected_checksum=checksum,
            expected_release_id="rel-not-this",
        )
    # Corrupted file checksum inside meta: mutate a file after building is hard;
    # instead strip required member by building a minimal incomplete archive.
    incomplete = tmp_path / "incomplete.tar.gz"
    with tarfile.open(incomplete, "w:gz") as tar:
        meta_bytes = json.dumps(
            {
                "schema_version": 1,
                "release_id": meta["release_id"],
                "git_sha": SAMPLE_SHA,
                "image_repository": SAMPLE_REPO,
                "image_digest": SAMPLE_DIGEST,
                "source_manifest_sha256": "a" * 64,
                "file_checksums": {"bundle-meta.json": "x"},
                "created_at": "2026-08-02T12:00:00Z",
            }
        ).encode()
        info = tarfile.TarInfo(name="bundle-meta.json")
        info.size = len(meta_bytes)
        tar.addfile(info, fileobj=io.BytesIO(meta_bytes))
        # Allowed top-level but missing required files.
        data = b"compose"
        cinfo = tarfile.TarInfo(name="compose/docker-compose.base.yml")
        cinfo.size = len(data)
        tar.addfile(cinfo, fileobj=io.BytesIO(data))
    with pytest.raises(mod.BundleVerifyError, match="missing required member"):
        mod.extract_validated_bundle(
            incomplete,
            tmp_path / "incomplete-out",
            expected_checksum=hashlib.sha256(incomplete.read_bytes()).hexdigest(),
            expected_release_id=meta["release_id"],
        )


def test_embedded_unrelated_typeerror_fail_closed(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    mod = _load_embedded_verifier()
    real_extract = mod.tarfile.TarFile.extract

    def fake_extract(self, member, path="", set_attrs=True, *, filter=None):  # noqa: A002
        if filter is not None:
            raise TypeError("simulated tar corruption during extract")
        return real_extract(self, member, path=path, set_attrs=set_attrs)

    monkeypatch.setattr(mod.tarfile.TarFile, "extract", fake_extract)
    tarball, checksum, meta = _build_valid_bundle(tmp_path)
    with pytest.raises(TypeError, match="simulated tar corruption"):
        mod.extract_validated_bundle(
            tarball,
            tmp_path / "dest",
            expected_checksum=checksum,
            expected_release_id=meta["release_id"],
        )


def test_previous_no_fallback_safeextract_would_fail(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Regression guard: the old single-call filter= path fails under 3.9 sim."""
    source = _extract_safeextract_source()
    # Strip the narrow fallback to recreate the pre-fix bootstrap extractor.
    old_extract = textwrap.dedent(
        """
        def _extract_members(tar, dest, members):
            dest = dest.resolve()
            for member in members:
                target = (dest / member.name).resolve()
                try:
                    target.relative_to(dest)
                except ValueError as exc:
                    raise BundleVerifyError(
                        f"extract path escaped destination: {member.name}"
                    ) from exc
                tar.extract(member, path=dest, filter="data")
        """
    ).strip()
    patched = re.sub(
        r"def _is_unsupported_filter_typeerror\(exc: TypeError\) -> bool:.*?"
        r"def extract_validated_bundle",
        old_extract + "\n\n\ndef extract_validated_bundle",
        source,
        count=1,
        flags=re.S,
    )
    assert "_is_unsupported_filter_typeerror" not in patched
    assert 'filter="data"' in patched
    old_mod = ModuleType("dealbrain_bootstrap_safeextract_old")
    exec(compile(patched, "<SAFEEXTRACT:old>", "exec"), old_mod.__dict__)  # noqa: S102

    calls = _force_filter_typeerror(monkeypatch, module=old_mod)
    tarball, checksum, meta = _build_valid_bundle(tmp_path)
    with pytest.raises(TypeError, match="unexpected keyword argument"):
        old_mod.extract_validated_bundle(
            tarball,
            tmp_path / "dest",
            expected_checksum=checksum,
            expected_release_id=meta["release_id"],
        )
    assert any(c["filter"] == "data" for c in calls)
    assert not any(c["filter"] is None for c in calls)


# ---------------------------------------------------------------------------
# Canonical ↔ bootstrap accept/reject parity on a security corpus
# ---------------------------------------------------------------------------


def test_canonical_bootstrap_security_corpus_parity(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    mod = _load_embedded_verifier()
    # Force fallback on both via their respective tarfile modules.
    import scripts.deploy.verify_staging_bundle as canon_mod

    def _patch(module: ModuleType) -> None:
        real_extract = module.tarfile.TarFile.extract

        def fake_extract(self, member, path="", set_attrs=True, *, filter=None):  # noqa: A002
            if filter is not None:
                raise TypeError("extract() got an unexpected keyword argument 'filter'")
            return real_extract(self, member, path=path, set_attrs=set_attrs)

        monkeypatch.setattr(module.tarfile.TarFile, "extract", fake_extract)

    _patch(mod)
    _patch(canon_mod)

    corpus: list[tuple[str, str | None, bool]] = [
        ("../escape", None, False),
        ("/absolute/path", None, False),
        ("bin/link", "symlink", False),
        ("bin/hard", "hardlink", False),
        ("bin/evil-chr", "chr", False),
        ("bin/evil-fifo", "fifo", False),
        ("compose/docker-compose.production.yml", None, False),
        ("unexpected/top.txt", None, False),
    ]
    for name, link_type, _accept in corpus:
        evil = _malicious_tarball(tmp_path, name, link_type=link_type)
        digest = hashlib.sha256(evil.read_bytes()).hexdigest()
        with pytest.raises((mod.BundleVerifyError, Exception)):
            mod.extract_validated_bundle(
                evil, tmp_path / f"e-{name.replace('/', '_')}", expected_checksum=digest
            )
        with pytest.raises(CanonicalBundleVerifyError):
            canonical_verify_bundle(evil, expected_checksum=digest)

    # Valid bundle accepted by both.
    tarball, checksum, meta = _build_valid_bundle(tmp_path)
    canon = canonical_verify_bundle(
        tarball,
        expected_checksum=checksum,
        expected_release_id=meta["release_id"],
    )
    dest = tmp_path / "parity-ok"
    embedded = mod.extract_validated_bundle(
        tarball,
        dest,
        expected_checksum=checksum,
        expected_release_id=meta["release_id"],
        expected_digest=meta["image_digest"],
    )
    assert canon["meta"]["release_id"] == embedded["meta"]["release_id"]
    assert canon["checksum"] == embedded["checksum"]


def test_required_members_aligned_with_canonical() -> None:
    """Bootstrap keeps the pre-PR baseline; rollback members stay bundle-only."""
    mod = _load_embedded_verifier()
    assert frozenset(mod.REQUIRED_MEMBERS) == frozenset(BOOTSTRAP_BASELINE_REQUIRED_MEMBERS)
    assert frozenset(mod.REQUIRED_MEMBERS).issubset(frozenset(CANONICAL_REQUIRED))
    for rel in ROLLBACK_ONLY_REQUIRED_MEMBERS:
        assert rel not in mod.REQUIRED_MEMBERS
        assert rel in CANONICAL_REQUIRED
    # Canonical schema-2 still requires full host tooling including rollback.
    assert frozenset(CANONICAL_REQUIRED) - frozenset(mod.REQUIRED_MEMBERS) == frozenset(
        ROLLBACK_ONLY_REQUIRED_MEMBERS
    )


def test_host_repair_plan_constants_document_contracts() -> None:
    assert "python3 --version" in HOST_READONLY_DIAGNOSTIC_PLAN
    assert "filter_in_signature" in HOST_READONLY_DIAGNOSTIC_PLAN
    assert "/opt/dealbrain/bin/verify_staging_bundle.py" in HOST_READONLY_DIAGNOSTIC_PLAN
    assert "approved merged commit" in HOST_CONDITIONAL_ATOMIC_REPAIR_PLAN
    plan = HOST_CONDITIONAL_ATOMIC_REPAIR_PLAN
    assert "Atomic rename" in plan or "atomic" in plan.lower()
    assert "Rollback" in plan
    assert "unreviewed local working-tree" in plan


@pytest.mark.skipif(
    not (ROOT / ".tools/python/cpython-3.9-macos-aarch64-none/bin/python3.9").is_file(),
    reason="workspace CPython 3.9 not available",
)
def test_real_python39_loads_embedded_safeextract(tmp_path: Path) -> None:
    py39 = ROOT / ".tools/python/cpython-3.9-macos-aarch64-none/bin/python3.9"
    source_path = tmp_path / "safeextract_mod.py"
    source_path.write_text(_extract_safeextract_source(), encoding="utf-8")
    probe = tmp_path / "probe_safeextract.py"
    probe.write_text(
        textwrap.dedent(
            f"""
            import importlib.util
            import inspect
            import tarfile
            from pathlib import Path

            path = Path({str(source_path)!r})
            spec = importlib.util.spec_from_file_location("safeextract_mod", path)
            mod = importlib.util.module_from_spec(spec)
            assert spec.loader is not None
            spec.loader.exec_module(mod)
            assert callable(mod.extract_validated_bundle)
            assert callable(mod._is_unsupported_filter_typeerror)
            assert not mod._is_unsupported_filter_typeerror(TypeError("other"))
            assert mod._is_unsupported_filter_typeerror(
                TypeError("extract() got an unexpected keyword argument 'filter'")
            )
            print("ok", "filter" in inspect.signature(tarfile.TarFile.extract).parameters)
            """
        ),
        encoding="utf-8",
    )
    proc = subprocess.run(
        [str(py39), str(probe)],
        check=False,
        capture_output=True,
        text=True,
    )
    assert proc.returncode == 0, proc.stderr
    assert proc.stdout.strip().startswith("ok")


def test_setuid_rejected_by_embedded(tmp_path: Path) -> None:
    mod = _load_embedded_verifier()
    for mode, label in (
        (0o4755, "setuid"),
        (0o2755, "setgid"),
        (0o1755, "sticky"),
    ):
        tar_path = tmp_path / f"{label}.tar.gz"
        with tarfile.open(tar_path, "w:gz") as tar:
            data = b"x"
            info = tarfile.TarInfo(name=f"bin/{label}.sh")
            info.size = len(data)
            info.mode = mode
            tar.addfile(info, fileobj=io.BytesIO(data))
        with pytest.raises(mod.BundleVerifyError, match="setuid|setgid|sticky"):
            mod.extract_validated_bundle(
                tar_path,
                tmp_path / f"out-{label}",
                expected_checksum=hashlib.sha256(tar_path.read_bytes()).hexdigest(),
            )


def test_duplicate_normalized_path_rejected_by_embedded(tmp_path: Path) -> None:
    mod = _load_embedded_verifier()
    tar_path = tmp_path / "dup.tar.gz"
    with tarfile.open(tar_path, "w:gz") as tar:
        data = b"x"
        for _ in range(2):
            info = tarfile.TarInfo(name="bin/dup.sh")
            info.size = len(data)
            tar.addfile(info, fileobj=io.BytesIO(data))
    with pytest.raises(mod.BundleVerifyError, match="duplicate archive member"):
        mod.extract_validated_bundle(
            tar_path,
            tmp_path / "out-dup",
            expected_checksum=hashlib.sha256(tar_path.read_bytes()).hexdigest(),
        )


def test_windows_absolute_path_rejected_by_embedded(tmp_path: Path) -> None:
    mod = _load_embedded_verifier()
    for name in ("C:/Windows/System32/evil", "D:\\Temp\\evil"):
        evil = _malicious_tarball(tmp_path, name)
        with pytest.raises(mod.BundleVerifyError, match="absolute"):
            mod.extract_validated_bundle(
                evil,
                tmp_path / f"out-{hashlib.sha256(name.encode()).hexdigest()[:8]}",
                expected_checksum=hashlib.sha256(evil.read_bytes()).hexdigest(),
            )


def test_staging_sh_bash_syntax() -> None:
    proc = subprocess.run(
        ["bash", "-n", str(STAGING_SH)],
        check=False,
        capture_output=True,
        text=True,
    )
    assert proc.returncode == 0, proc.stderr
    proc2 = subprocess.run(
        ["bash", "-n", str(HOST_VERIFY_SH)],
        check=False,
        capture_output=True,
        text=True,
    )
    assert proc2.returncode == 0, proc2.stderr

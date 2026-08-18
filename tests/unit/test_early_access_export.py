"""CSV formula neutralization for the operator Early Access export."""

from __future__ import annotations

import stat
from datetime import UTC, datetime
from pathlib import Path

import pytest
import scripts.export_early_access as export_module
from scripts.export_early_access import ROOT, csv_cell, write_private_export


def test_normal_text_unchanged() -> None:
    assert csv_cell("Ada Lovelace") == "Ada Lovelace"
    assert csv_cell("ada@example.com") == "ada@example.com"
    assert csv_cell("early_access_landing") == "early_access_landing"
    assert csv_cell("hello-world") == "hello-world"


def test_formula_prefixes_are_neutralized() -> None:
    assert csv_cell("=1+1") == "'=1+1"
    assert csv_cell("+SUM(A1:A2)") == "'+SUM(A1:A2)"
    assert csv_cell("-2+3") == "'-2+3"
    assert csv_cell("@SUM(1,2)") == "'@SUM(1,2)"


def test_leading_whitespace_before_formula_is_neutralized() -> None:
    assert csv_cell("  =1+1") == "'  =1+1"
    assert csv_cell("\t+SUM(A1:A2)") == "'\t+SUM(A1:A2)"
    assert csv_cell("\n@SUM(1,2)") == "'\n@SUM(1,2)"


def test_empty_and_none_remain_safe() -> None:
    assert csv_cell(None) == ""
    assert csv_cell("") == ""


def test_unicode_text_remains_intact() -> None:
    assert csv_cell("Åland Islands") == "Åland Islands"
    assert csv_cell("José María") == "José María"
    assert csv_cell("東京") == "東京"


def test_timestamps_are_not_prefixed() -> None:
    stamp = datetime(2026, 8, 17, 10, 0, tzinfo=UTC)
    assert csv_cell(stamp) == stamp.isoformat()


def test_private_export_is_owner_only_and_refuses_overwrite(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    destination = tmp_path / "early-access.csv"

    def _write(out) -> int:  # noqa: ANN001
        out.write("email\nqa@example.com\n")
        return 0

    monkeypatch.setattr(export_module, "export_rows", _write)
    assert write_private_export(destination) == 0
    assert stat.S_IMODE(destination.stat().st_mode) == 0o600
    assert destination.read_text(encoding="utf-8") == "email\nqa@example.com\n"
    with pytest.raises(FileExistsError):
        write_private_export(destination)


def test_private_export_refuses_repository_destination() -> None:
    with pytest.raises(ValueError, match="outside the repository"):
        write_private_export(ROOT / "early-access-private.csv")


def test_private_export_refuses_symlink_destination(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    target = tmp_path / "symlink-target.csv"
    destination = tmp_path / "early-access.csv"
    destination.symlink_to(target)

    monkeypatch.setattr(export_module, "export_rows", lambda _out: 0)
    with pytest.raises(ValueError, match="symlink"):
        write_private_export(destination)
    assert not target.exists()


def test_private_export_removes_partial_file_on_failure(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    destination = tmp_path / "partial.csv"

    def _fail(out) -> int:  # noqa: ANN001
        out.write("partial PII")
        raise RuntimeError("database unavailable")

    monkeypatch.setattr(export_module, "export_rows", _fail)
    with pytest.raises(RuntimeError, match="database unavailable"):
        write_private_export(destination)
    assert not destination.exists()

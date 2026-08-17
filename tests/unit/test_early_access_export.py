"""CSV formula neutralization for the operator Early Access export."""

from __future__ import annotations

from datetime import UTC, datetime

from scripts.export_early_access import csv_cell


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

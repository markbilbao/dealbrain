"""Unit tests for Sprint 24 shared API primitives."""

from __future__ import annotations

import pytest
from app.schemas.api_common import (
    SORT_ALLOWLIST_NOTIFICATIONS,
    apply_sort,
    build_pagination_meta,
    parse_sort,
    resolve_skip_offset,
    slice_page,
)
from fastapi import HTTPException


def test_resolve_skip_only() -> None:
    assert resolve_skip_offset(skip=10, offset=None) == 10


def test_resolve_offset_only() -> None:
    assert resolve_skip_offset(skip=None, offset=7) == 7


def test_resolve_neither_uses_default() -> None:
    assert resolve_skip_offset(skip=None, offset=None, default=0) == 0


def test_resolve_both_equal() -> None:
    assert resolve_skip_offset(skip=5, offset=5) == 5


def test_resolve_both_conflict_raises() -> None:
    with pytest.raises(HTTPException) as exc:
        resolve_skip_offset(skip=1, offset=2)
    assert exc.value.status_code == 422


def test_parse_sort_allowlist() -> None:
    dirs = parse_sort("-created_at,severity", SORT_ALLOWLIST_NOTIFICATIONS)
    assert [(d.field, d.descending) for d in dirs] == [
        ("created_at", True),
        ("severity", False),
    ]


def test_parse_sort_rejects_unknown() -> None:
    with pytest.raises(HTTPException) as exc:
        parse_sort("commission", SORT_ALLOWLIST_NOTIFICATIONS)
    assert exc.value.status_code == 422


def test_apply_sort_and_slice() -> None:
    rows = [
        {"created_at": "2024-01-01", "name": "b"},
        {"created_at": "2024-02-01", "name": "a"},
        {"created_at": "2024-03-01", "name": "c"},
    ]
    sorted_rows = apply_sort(rows, parse_sort("-created_at", {"created_at"}))
    assert sorted_rows[0]["name"] == "c"
    page, meta = slice_page(sorted_rows, offset=1, limit=1)
    assert page[0]["name"] == "a"
    assert meta.total == 3
    assert meta.has_more is True


def test_build_pagination_meta_has_more_from_total() -> None:
    meta = build_pagination_meta(limit=10, offset=0, total=25, page_len=10)
    assert meta.has_more is True

"""Shared API contract primitives (Sprint 24).

These helpers standardize pagination, filtering, and sorting at the HTTP
boundary without changing domain decision logic. All additions are optional /
additive for existing clients.
"""

from __future__ import annotations

from collections.abc import Mapping, Sequence
from typing import Any, TypeVar

from fastapi import HTTPException, status
from pydantic import BaseModel, Field

T = TypeVar("T")


class PaginationMeta(BaseModel):
    """Additive collection pagination metadata.

    Attached only where dual-run / additive response fields are safe.
    """

    limit: int = Field(description="Effective page size")
    offset: int = Field(description="Effective offset (0-based)")
    total: int | None = Field(
        default=None,
        description="Total matching rows when cheap to compute; omit otherwise",
    )
    has_more: bool | None = Field(
        default=None,
        description="True when more rows exist beyond this page",
    )


class SortDirective(BaseModel):
    """Parsed sort token."""

    field: str
    descending: bool = False


def build_pagination_meta(
    *,
    limit: int,
    offset: int,
    total: int | None = None,
    page_len: int | None = None,
    has_more: bool | None = None,
) -> PaginationMeta:
    """Build pagination metadata with a sensible ``has_more`` default."""
    if has_more is None:
        if total is not None:
            has_more = (offset + (page_len if page_len is not None else 0)) < total
        elif page_len is not None:
            has_more = page_len >= limit
    return PaginationMeta(limit=limit, offset=offset, total=total, has_more=has_more)


def resolve_skip_offset(
    *,
    skip: int | None = None,
    offset: int | None = None,
    default: int = 0,
) -> int:
    """Resolve ``skip`` / ``offset`` aliases with explicit precedence.

    Rules (Sprint 24):
    - If only ``skip`` is supplied → use ``skip``
    - If only ``offset`` is supplied → use ``offset``
    - If both are supplied and equal → use that value
    - If both are supplied and differ → 422 validation error
    - If neither is supplied → ``default``
    """
    skip_set = skip is not None
    offset_set = offset is not None
    if skip_set and offset_set:
        if skip != offset:
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                detail=(
                    "Conflicting pagination aliases: skip and offset must be equal "
                    f"when both are supplied (got skip={skip}, offset={offset})."
                ),
            )
        return int(skip)  # type: ignore[arg-type]
    if offset_set:
        return int(offset)  # type: ignore[arg-type]
    if skip_set:
        return int(skip)  # type: ignore[arg-type]
    return default


def parse_sort(
    sort: str | None,
    allowlist: Sequence[str] | set[str] | frozenset[str],
) -> list[SortDirective]:
    """Parse ``sort=field,-other`` against an endpoint allowlist.

    Unknown fields raise HTTP 422. Empty / omitted sort returns [].
    """
    if sort is None or not str(sort).strip():
        return []
    allowed = {field.lower() for field in allowlist}
    directives: list[SortDirective] = []
    for raw in str(sort).split(","):
        token = raw.strip()
        if not token:
            continue
        descending = token.startswith("-")
        field = token[1:] if descending else token
        field = field.strip()
        if not field:
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                detail="Invalid sort token: empty field name.",
            )
        if field.lower() not in allowed:
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                detail=(
                    f"Unsupported sort field {field!r}. "
                    f"Allowed: {', '.join(sorted(allowed))}."
                ),
            )
        directives.append(SortDirective(field=field.lower(), descending=descending))
    return directives


def apply_sort(
    items: Sequence[T],
    directives: Sequence[SortDirective],
    *,
    accessors: Mapping[str, Any] | None = None,
) -> list[T]:
    """Stable multi-key sort for presentation lists.

    ``accessors`` maps field name → callable(item) -> comparable value.
    When omitted, attributes / mapping keys matching the field are used.
    """
    if not directives:
        return list(items)

    def _value(item: T, field: str) -> Any:
        if accessors and field in accessors:
            return accessors[field](item)
        if isinstance(item, Mapping):
            return item.get(field)
        if hasattr(item, field):
            return getattr(item, field)
        if hasattr(item, "model_dump"):
            dumped = item.model_dump()  # type: ignore[attr-defined]
            return dumped.get(field)
        return None

    result = list(items)
    # Apply right-to-left for stable multi-key ordering.
    for directive in reversed(directives):
        result.sort(
            key=lambda item, f=directive.field: (
                _value(item, f) is None,
                _value(item, f),
            ),
            reverse=directive.descending,
        )
    return result


def slice_page(
    items: Sequence[T],
    *,
    offset: int,
    limit: int,
) -> tuple[list[T], PaginationMeta]:
    """Apply offset/limit to an in-memory sequence and build pagination meta."""
    total = len(items)
    page = list(items[offset : offset + limit])
    return page, build_pagination_meta(
        limit=limit, offset=offset, total=total, page_len=len(page)
    )


# Presentation-sort allowlists (endpoint-owned fields only).
SORT_ALLOWLIST_NOTIFICATIONS: frozenset[str] = frozenset({"created_at", "severity"})
SORT_ALLOWLIST_ALERT_EVENTS: frozenset[str] = frozenset({"created_at"})
SORT_ALLOWLIST_PRODUCTS: frozenset[str] = frozenset({"created_at", "brand", "category"})
SORT_ALLOWLIST_WATCHLIST_HISTORY: frozenset[str] = frozenset({"created_at"})
SORT_ALLOWLIST_WATCHLISTS: frozenset[str] = frozenset({"created_at", "name", "status"})
SORT_ALLOWLIST_LEGACY_ALERTS: frozenset[str] = frozenset({"created_at"})
SORT_ALLOWLIST_MERCHANT_AUDIT: frozenset[str] = frozenset({"created_at"})
SORT_ALLOWLIST_COLLECTION_RUNS: frozenset[str] = frozenset({"started_at", "created_at"})
SORT_ALLOWLIST_AFFILIATE_LINKS: frozenset[str] = frozenset({"created_at"})

# Ranking / neutrality-sensitive surfaces — caller sort is forbidden.
SORT_PROHIBITED_PATH_PREFIXES: tuple[str, ...] = (
    "/api/v1/dealscore/",
    "/api/v1/recommendations/",
    "/api/v1/marketplace/search",
    "/api/v1/shopping-assistant/",
)

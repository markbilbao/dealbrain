"""FastAPI dependencies for Sprint 24 API contract helpers."""

from __future__ import annotations

from fastapi import Query

from app.schemas.api_common import resolve_skip_offset


def products_pagination(
    skip: int | None = Query(
        default=None,
        ge=0,
        deprecated=True,
        description="Deprecated alias for offset — kept for Sprint 1–23 clients",
    ),
    offset: int | None = Query(
        default=None,
        ge=0,
        description="Canonical pagination offset (0-based). Alias of skip.",
    ),
    limit: int = Query(default=100, ge=1, le=500),
) -> tuple[int, int]:
    """Return ``(limit, effective_offset)`` for ``GET /products``."""
    return limit, resolve_skip_offset(skip=skip, offset=offset, default=0)

"""Deterministic collection identifiers (no random UUID generation)."""

from __future__ import annotations

import hashlib
from datetime import datetime


def make_collection_run_id(
    *,
    query: str,
    marketplaces: tuple[str, ...] | list[str],
    observed_at: datetime,
    suffix: str = "",
) -> str:
    """Build a stable run identifier from injected inputs.

    Identical query, marketplace set, observed_at, and suffix always produce
    the same identifier.
    """
    markets = ",".join(sorted(m.strip().lower() for m in marketplaces))
    stamp = observed_at.isoformat()
    material = f"{query.strip().lower()}|{markets}|{stamp}|{suffix}"
    digest = hashlib.sha256(material.encode("utf-8")).hexdigest()[:24]
    return f"colrun_{digest}"


def make_marketplace_result_id(*, run_id: str, marketplace: str) -> str:
    """Deterministic per-marketplace result id derived from the parent run."""
    market = marketplace.strip().lower()
    digest = hashlib.sha256(f"{run_id}|{market}".encode()).hexdigest()[:16]
    return f"{run_id}:{market}:{digest}"


def make_job_id(
    *,
    query: str,
    marketplaces: tuple[str, ...] | list[str],
    interval_seconds: int,
    created_at: datetime,
) -> str:
    """Build a stable job identifier from injected job definition fields."""
    markets = ",".join(sorted(m.strip().lower() for m in marketplaces))
    material = f"{query.strip().lower()}|{markets}|{interval_seconds}|{created_at.isoformat()}"
    digest = hashlib.sha256(material.encode("utf-8")).hexdigest()[:20]
    return f"coljob_{digest}"

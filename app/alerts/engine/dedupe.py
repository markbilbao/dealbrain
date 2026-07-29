"""Dedupe key builders and observation fingerprint helpers — Sprint 19.

Used by :class:`app.alerts.engine.evaluator.AlertEvaluationEngine` and by
callers persisting :class:`~app.domain.entities.alerts.AlertEvent` records so
the same underlying occurrence (e.g. the same price drop) is never re-raised
across repeated evaluation passes.
"""

from __future__ import annotations

import hashlib
from typing import Any

from app.domain.entities.alerts import AlertConditionType

# Curated observation fields that participate in the fingerprint by default.
# Keeping this list stable and small means unrelated payload noise (e.g. a
# scraped page title) never perturbs dedupe behavior.
DEFAULT_FINGERPRINT_FIELDS: tuple[str, ...] = (
    "price",
    "previous_price",
    "inventory",
    "availability",
    "seller",
    "marketplace",
    "freshness_status",
    "dealscore",
)


def _condition_value(condition_type: AlertConditionType | str) -> str:
    if isinstance(condition_type, AlertConditionType):
        return condition_type.value
    return str(condition_type)


def _stable_repr(value: Any) -> str:
    """Render a value deterministically regardless of dict ordering or float precision."""
    if isinstance(value, float):
        return f"{value:.6f}"
    if isinstance(value, bool):
        return "true" if value else "false"
    if isinstance(value, (list, tuple, set, frozenset)):
        return "[" + ",".join(_stable_repr(v) for v in sorted(value, key=str)) + "]"
    if isinstance(value, dict):
        return "{" + ",".join(f"{k}={_stable_repr(v)}" for k, v in sorted(value.items())) + "}"
    return str(value)


def observation_fingerprint(
    observation: dict[str, Any],
    condition_type: AlertConditionType | str,
    *,
    fields: tuple[str, ...] | None = None,
) -> str:
    """Stable SHA-256 hash of key observation fields plus the condition type.

    Two evaluation passes over an unchanged observation (for the same
    condition type) always produce the same fingerprint; any change to a
    participating field changes it.
    """
    selected = fields or DEFAULT_FINGERPRINT_FIELDS
    parts = [f"condition={_condition_value(condition_type)}"]
    parts.extend(f"{name}={_stable_repr(observation.get(name))}" for name in selected)
    canonical = "|".join(parts)
    return hashlib.sha256(canonical.encode("utf-8")).hexdigest()


def build_dedupe_key(
    *,
    user_id: str,
    condition_type: AlertConditionType | str,
    rule_id: str | None = None,
    watchlist_id: str | None = None,
    item_id: str | None = None,
    fingerprint: str | None = None,
) -> str:
    """Build a stable key identifying one specific alert occurrence.

    Combines scope identifiers with the condition type and, when supplied,
    an observation fingerprint. Two calls with identical arguments always
    produce an identical key, regardless of call order or process restarts.
    """
    segments = [
        f"user={user_id}",
        f"rule={rule_id or '-'}",
        f"watchlist={watchlist_id or '-'}",
        f"item={item_id or '-'}",
        f"condition={_condition_value(condition_type)}",
    ]
    if fingerprint is not None:
        segments.append(f"fp={fingerprint}")
    return "|".join(segments)


def build_dedupe_key_for_event(
    *,
    user_id: str,
    condition_type: AlertConditionType | str,
    observation: dict[str, Any],
    rule_id: str | None = None,
    watchlist_id: str | None = None,
    item_id: str | None = None,
) -> str:
    """Convenience wrapper combining :func:`observation_fingerprint` and
    :func:`build_dedupe_key` for the common "one event per observation
    change" case.
    """
    fingerprint = observation_fingerprint(observation, condition_type)
    return build_dedupe_key(
        user_id=user_id,
        condition_type=condition_type,
        rule_id=rule_id,
        watchlist_id=watchlist_id,
        item_id=item_id,
        fingerprint=fingerprint,
    )

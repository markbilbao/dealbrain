"""Deterministic hashing for research execution planning."""

from __future__ import annotations

import hashlib
import json
from typing import Any


def stable_sha256(value: Any) -> str:
    encoded = json.dumps(
        value,
        ensure_ascii=False,
        separators=(",", ":"),
        sort_keys=True,
    ).encode("utf-8")
    return hashlib.sha256(encoded).hexdigest()

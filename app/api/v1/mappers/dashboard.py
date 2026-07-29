"""Map User Dashboard payloads (Sprint 19) to HTTP schemas.

``UserDashboardService.get_dashboard_dict`` already returns a plain,
JSON-shaped dict (``UserDashboard.to_dict()`` plus a ``personalization``
key) whose structure matches :class:`UserDashboardResponse` field-for-field,
so this mapper simply validates/wraps it rather than re-deriving the shape
from domain objects.
"""

from __future__ import annotations

from typing import Any

from app.schemas.dashboard import UserDashboardResponse


def to_dashboard_response(payload: dict[str, Any]) -> UserDashboardResponse:
    return UserDashboardResponse(**payload)

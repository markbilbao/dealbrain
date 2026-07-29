"""In-memory launch ops store — config export snapshots and checklist state."""

from __future__ import annotations

from copy import deepcopy
from dataclasses import dataclass
from datetime import UTC, datetime
from typing import Any
from uuid import uuid4


@dataclass
class ConfigSnapshot:
    snapshot_id: str
    created_at: datetime
    environment: str
    payload: dict[str, Any]
    label: str = ""


@dataclass
class ChecklistItem:
    item_id: str
    title: str
    category: str
    completed: bool = False
    notes: str = ""


DEFAULT_CHECKLIST: tuple[tuple[str, str, str], ...] = (
    ("cfg-env", "Environment profiles configured (dev/staging/production)", "configuration"),
    ("cfg-flags", "Feature flags reviewed for beta launch", "configuration"),
    ("cfg-secrets", "No production secrets in demo env files", "security"),
    ("ops-health", "Health / ready / live probes verified", "monitoring"),
    ("ops-logs", "Structured logging enabled; secrets redacted", "monitoring"),
    ("sec-headers", "Security headers enabled (CSP, HSTS, frame options)", "security"),
    ("sec-rate", "Rate limiting enabled for auth and high-traffic APIs", "security"),
    ("sec-errors", "Standardized API error responses verified", "security"),
    ("docs-openapi", "OpenAPI / Swagger descriptions reviewed", "documentation"),
    ("docs-launch", "LAUNCH_CHECKLIST / DEPLOYMENT / PRODUCTION docs present", "documentation"),
    ("demo-personas", "Demo launcher personas switch correctly", "demo"),
    ("demo-ui", "System Status and Admin Monitoring demo panels work", "demo"),
    ("perf-cache", "Performance cache reduces duplicate read work", "performance"),
    ("backup-guide", "Backup and restore guides reviewed", "operations"),
    ("compat", "Prior sprint tests still pass; ranking unchanged", "validation"),
)


class InMemoryLaunchStore:
    """Process-scoped launch readiness store (demo only)."""

    def __init__(self) -> None:
        self._snapshots: dict[str, ConfigSnapshot] = {}
        self._checklist: dict[str, ChecklistItem] = {
            item_id: ChecklistItem(item_id=item_id, title=title, category=category)
            for item_id, title, category in DEFAULT_CHECKLIST
        }
        self._imported_payload: dict[str, Any] | None = None

    def save_snapshot(
        self,
        payload: dict[str, Any],
        *,
        environment: str,
        label: str = "",
        clock: datetime | None = None,
    ) -> ConfigSnapshot:
        snap = ConfigSnapshot(
            snapshot_id=f"cfg-{uuid4().hex[:12]}",
            created_at=clock or datetime.now(UTC),
            environment=environment,
            payload=deepcopy(payload),
            label=label,
        )
        self._snapshots[snap.snapshot_id] = snap
        return snap

    def get_snapshot(self, snapshot_id: str) -> ConfigSnapshot | None:
        return self._snapshots.get(snapshot_id)

    def list_snapshots(self) -> list[ConfigSnapshot]:
        return sorted(self._snapshots.values(), key=lambda s: s.created_at, reverse=True)

    def import_payload(self, payload: dict[str, Any]) -> dict[str, Any]:
        self._imported_payload = deepcopy(payload)
        return deepcopy(payload)

    def last_import(self) -> dict[str, Any] | None:
        return deepcopy(self._imported_payload) if self._imported_payload else None

    def list_checklist(self) -> list[ChecklistItem]:
        return [self._checklist[k] for k in sorted(self._checklist)]

    def update_checklist(
        self,
        item_id: str,
        *,
        completed: bool | None = None,
        notes: str | None = None,
    ) -> ChecklistItem:
        item = self._checklist.get(item_id)
        if item is None:
            raise KeyError(item_id)
        if completed is not None:
            item.completed = completed
        if notes is not None:
            item.notes = notes
        return item

    def checklist_summary(self) -> dict[str, Any]:
        items = self.list_checklist()
        done = sum(1 for i in items if i.completed)
        return {
            "total": len(items),
            "completed": done,
            "remaining": len(items) - done,
            "percent_complete": round(100.0 * done / len(items), 1) if items else 0.0,
            "items": [
                {
                    "item_id": i.item_id,
                    "title": i.title,
                    "category": i.category,
                    "completed": i.completed,
                    "notes": i.notes,
                }
                for i in items
            ],
        }

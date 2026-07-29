"""Configuration export/import for launch backup rehearsal (Sprint 22)."""

from __future__ import annotations

from typing import Any

from app.core.config import Settings, settings
from app.core.validation import exportable_settings, validate_settings
from app.domain.exceptions import LaunchNotFoundError, LaunchValidationError
from app.launch.memory import InMemoryLaunchStore


class LaunchConfigService:
    """Configuration export / import for backup rehearsal (no secrets)."""

    def __init__(self, store: InMemoryLaunchStore, *, cfg: Settings | None = None) -> None:
        self._store = store
        self._cfg = cfg or settings

    def export_config(self, *, label: str = "") -> dict[str, Any]:
        payload = exportable_settings(self._cfg)
        validation = validate_settings(self._cfg)
        snap = self._store.save_snapshot(
            payload,
            environment=self._cfg.app_env,
            label=label or f"export-{self._cfg.app_env}",
        )
        return {
            "snapshot_id": snap.snapshot_id,
            "created_at": snap.created_at.isoformat(),
            "environment": snap.environment,
            "label": snap.label,
            "payload": snap.payload,
            "validation": {
                "ok": validation.ok,
                "errors": list(validation.errors),
                "warnings": list(validation.warnings),
            },
            "note": "Secrets are redacted. This is a configuration export, not a DB backup.",
        }

    def list_exports(self) -> list[dict[str, Any]]:
        return [
            {
                "snapshot_id": s.snapshot_id,
                "created_at": s.created_at.isoformat(),
                "environment": s.environment,
                "label": s.label,
            }
            for s in self._store.list_snapshots()
        ]

    def get_export(self, snapshot_id: str) -> dict[str, Any]:
        snap = self._store.get_snapshot(snapshot_id)
        if snap is None:
            raise LaunchNotFoundError("config_snapshot", snapshot_id)
        return {
            "snapshot_id": snap.snapshot_id,
            "created_at": snap.created_at.isoformat(),
            "environment": snap.environment,
            "label": snap.label,
            "payload": snap.payload,
        }

    def import_config(self, payload: dict[str, Any]) -> dict[str, Any]:
        if not isinstance(payload, dict) or not payload:
            raise LaunchValidationError("Import payload must be a non-empty object")
        # Never apply secrets or mutate live Settings — store for review only.
        forbidden = {"openai_api_key", "anthropic_api_key", "gemini_api_key", "database_url"}
        cleaned = {k: v for k, v in payload.items() if k not in forbidden}
        stored = self._store.import_payload(cleaned)
        return {
            "imported": True,
            "keys": sorted(stored.keys()),
            "applied_to_runtime": False,
            "note": (
                "Import stored for review only. Restart with env files to apply. "
                "Secrets were stripped and runtime Settings were not mutated."
            ),
            "payload": stored,
        }

    def checklist(self) -> dict[str, Any]:
        return self._store.checklist_summary()

    def update_checklist_item(
        self,
        item_id: str,
        *,
        completed: bool | None = None,
        notes: str | None = None,
    ) -> dict[str, Any]:
        try:
            item = self._store.update_checklist(item_id, completed=completed, notes=notes)
        except KeyError as exc:
            raise LaunchNotFoundError("checklist_item", item_id) from exc
        return {
            "item_id": item.item_id,
            "title": item.title,
            "category": item.category,
            "completed": item.completed,
            "notes": item.notes,
            "summary": self._store.checklist_summary(),
        }

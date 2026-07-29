"""Demo launcher persona switching (Sprint 22)."""

from __future__ import annotations

from typing import Any

from app.core.config import Settings, settings
from app.domain.exceptions import LaunchValidationError
from app.launch.fixtures import DemoLauncherState, list_personas


class LaunchDemoService:
    """Persona switching for the demo launcher."""

    def __init__(self, state: DemoLauncherState, *, cfg: Settings | None = None) -> None:
        self._state = state
        self._cfg = cfg or settings

    def status(self) -> dict[str, Any]:
        if not self._cfg.demo_launcher_enabled:
            return {"enabled": False, "message": "Demo launcher disabled"}
        snap = self._state.snapshot()
        snap["enabled"] = True
        snap["seeded_data"] = {
            "users": ["alex@dealbrain.demo", "jordan@dealbrain.demo"],
            "merchants": ["org-techhaven", "org-gadgetgrove"],
            "affiliate_merchants": ["merchant-amazon-us"],
            "note": "Seeded by prior sprints; Sprint 22 adds persona switching only.",
        }
        return snap

    def list_personas(self) -> list[dict[str, Any]]:
        return [
            {
                "persona": p.persona,
                "label": p.label,
                "description": p.description,
                "auth_header": p.auth_header,
                "organization_id": p.organization_id,
                "capabilities": list(p.capabilities),
            }
            for p in list_personas()
        ]

    def switch(self, persona: str) -> dict[str, Any]:
        if not self._cfg.demo_launcher_enabled:
            raise LaunchValidationError("Demo launcher is disabled")
        allowed = {p.persona for p in list_personas()}
        if persona not in allowed:
            raise LaunchValidationError(
                f"Unknown persona '{persona}'. Choose one of: {', '.join(sorted(allowed))}"
            )
        profile = self._state.switch(persona)  # type: ignore[arg-type]
        return self.status() | {
            "switched_to": profile.persona,
            "label": profile.label,
        }

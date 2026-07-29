"""Demo launcher personas and seeded session context (Sprint 22)."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Literal

DemoPersona = Literal["anonymous", "registered", "merchant", "admin"]


@dataclass(frozen=True, slots=True)
class DemoPersonaProfile:
    persona: DemoPersona
    label: str
    description: str
    auth_header: str | None
    organization_id: str | None = None
    user_email: str | None = None
    capabilities: tuple[str, ...] = ()
    seeded_hints: tuple[str, ...] = ()


DEMO_PERSONAS: tuple[DemoPersonaProfile, ...] = (
    DemoPersonaProfile(
        persona="anonymous",
        label="Anonymous User",
        description="Browse public search, DealScore, and recommendations without auth.",
        auth_header=None,
        capabilities=("search", "dealscore", "recommendations", "price_history"),
        seeded_hints=("No Authorization header required for public endpoints.",),
    ),
    DemoPersonaProfile(
        persona="registered",
        label="Registered User",
        description="Demo user platform account with watchlists and saved items.",
        auth_header="Bearer demo-session-alex",
        user_email="alex@dealbrain.demo",
        capabilities=(
            "profile",
            "watchlists",
            "alerts",
            "notifications",
            "dashboard",
            "saved_items",
        ),
        seeded_hints=(
            "Use POST /api/v1/auth/login with alex@dealbrain.demo / DemoPass123!",
            "Or send Authorization: Bearer demo-session-alex when seeded.",
        ),
    ),
    DemoPersonaProfile(
        persona="merchant",
        label="Merchant",
        description="TechHaven owner — product submissions, offers, campaigns (demo).",
        auth_header="Bearer demo-token-techhaven-owner",
        organization_id="org-techhaven",
        capabilities=(
            "merchant_profile",
            "product_submissions",
            "offers",
            "promotions",
            "campaigns",
            "analytics",
        ),
        seeded_hints=(
            "Organization: org-techhaven",
            "Merchant tools never alter organic DealScore or ranking.",
        ),
    ),
    DemoPersonaProfile(
        persona="admin",
        label="Admin",
        description="Internal admin — merchant review + launch monitoring dashboard.",
        auth_header="Bearer demo-token-internal-admin",
        organization_id="org-techhaven",
        capabilities=(
            "merchant_admin_review",
            "launch_dashboard",
            "feature_flags",
            "system_status",
            "config_export",
        ),
        seeded_hints=(
            "INTERNAL_ADMIN can review merchant submissions only.",
            "Launch dashboard aggregates demo metrics — no production secrets.",
        ),
    ),
)


@dataclass
class DemoLauncherState:
    """Mutable process-scoped demo launcher selection."""

    active_persona: DemoPersona = "anonymous"
    notes: list[str] = field(default_factory=list)

    def switch(self, persona: DemoPersona) -> DemoPersonaProfile:
        profile = get_persona(persona)
        self.active_persona = persona
        self.notes.append(f"Switched to {profile.label}")
        return profile

    def current(self) -> DemoPersonaProfile:
        return get_persona(self.active_persona)

    def snapshot(self) -> dict[str, Any]:
        profile = self.current()
        return {
            "active_persona": profile.persona,
            "label": profile.label,
            "description": profile.description,
            "auth_header": profile.auth_header,
            "organization_id": profile.organization_id,
            "user_email": profile.user_email,
            "capabilities": list(profile.capabilities),
            "seeded_hints": list(profile.seeded_hints),
            "personas": [
                {
                    "persona": p.persona,
                    "label": p.label,
                    "description": p.description,
                }
                for p in DEMO_PERSONAS
            ],
            "recent_notes": list(self.notes[-10:]),
        }


def get_persona(persona: DemoPersona) -> DemoPersonaProfile:
    for profile in DEMO_PERSONAS:
        if profile.persona == persona:
            return profile
    raise KeyError(persona)


def list_personas() -> list[DemoPersonaProfile]:
    return list(DEMO_PERSONAS)

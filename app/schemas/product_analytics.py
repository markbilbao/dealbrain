"""Browser analytics event request. Server-owned fields are not accepted."""

from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, ConfigDict


class ProductAnalyticsEventRequest(BaseModel):
    """Known client fields. Unknown and forbidden extras are rejected by the service."""

    model_config = ConfigDict(extra="allow")

    event_name: str
    event_id: str | None = None
    surface: str | None = None
    action_type: str | None = None
    turn_number: int | None = None
    evidence_count: int | None = None
    latency_band: str | None = None
    freshness_band: str | None = None
    error_code: str | None = None
    outcome: str | None = None
    decision_id: str | None = None

    def client_payload(self) -> dict[str, object]:
        """Build the command payload for schema validation.

        Declared optional fields left unset are omitted. ``model_dump(exclude_none=True)``
        also drops unknown extras whose value is null, so those extras are restored
        afterwards and still fail validation.
        """

        extra = self.__pydantic_extra__ or {}
        payload = self.model_dump(exclude_none=True)
        payload.update(extra)
        return payload


class ProductAnalyticsEventResponse(BaseModel):
    model_config = ConfigDict(extra="forbid")

    result: Literal[
        "recorded",
        "duplicate",
        "suppressed_no_consent",
        "schema_rejected",
        "identity_conflict",
    ]
    event_id: str | None = None
    reason: str | None = None

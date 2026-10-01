"""Feedback report API models. The stored message is not returned."""

from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, ConfigDict


class FeedbackReportResponse(BaseModel):
    model_config = ConfigDict(extra="forbid")

    report_id: str
    status: Literal["received"]
    category: str
    duplicate: bool = False
    analytics_status: str


class FeedbackReportCreate(BaseModel):
    """Known report fields. Unknown extras are rejected by the feedback service."""

    model_config = ConfigDict(extra="allow")

    category: str
    message: str = ""
    decision_id: str | None = None
    product_id: str | None = None
    surface: str | None = None
    context_version: int | None = None
    client_submission_id: str | None = None

    def client_payload(self) -> dict[str, object]:
        payload = self.model_dump()
        extra = self.__pydantic_extra__ or {}
        payload.update(extra)
        return payload

"""Affiliate disclosure application service — Sprint 20.

Serves affiliate / merchant / regional / FTC placeholder disclosures.
Not legal advice — demo copy only.
"""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import replace
from datetime import UTC, datetime
from typing import Any
from uuid import uuid4

from app.affiliate.disclosure.texts import combined_disclosure_text, select_disclosures
from app.domain.entities.affiliate import AffiliateDisclosure
from app.domain.exceptions import AffiliateDisclosureNotFoundError, AffiliateValidationError
from app.domain.interfaces.affiliate_repository import AffiliateDisclosureRepository


class AffiliateDisclosureService:
    """CRUD and selection for disclosure text records."""

    def __init__(
        self,
        repository: AffiliateDisclosureRepository,
        *,
        clock: Callable[[], datetime] | None = None,
        id_factory: Callable[[], str] | None = None,
    ) -> None:
        self._repository = repository
        self._clock = clock or (lambda: datetime.now(UTC))
        self._id_factory = id_factory or (lambda: str(uuid4()))

    def list_disclosures(
        self,
        *,
        region: str | None = None,
        merchant_id: str | None = None,
        disclosure_type: str | None = None,
        active_only: bool = True,
    ) -> list[AffiliateDisclosure]:
        return self._repository.list_disclosures(
            region=region,
            merchant_id=merchant_id,
            disclosure_type=disclosure_type,
            active_only=active_only,
        )

    def get_disclosure(self, disclosure_id: str) -> AffiliateDisclosure:
        disclosure = self._repository.get_disclosure(disclosure_id)
        if disclosure is None:
            raise AffiliateDisclosureNotFoundError(disclosure_id)
        return disclosure

    def resolve(
        self,
        *,
        region: str | None = None,
        merchant_id: str | None = None,
        include_general: bool = True,
        include_ftc: bool = True,
    ) -> dict[str, Any]:
        """Return selected disclosures plus a combined text block for UIs."""
        all_active = self._repository.list_disclosures(active_only=True)
        selected = select_disclosures(
            all_active,
            region=region,
            merchant_id=merchant_id,
            include_general=include_general,
            include_ftc=include_ftc,
        )
        return {
            "disclosures": selected,
            "combined_text": combined_disclosure_text(selected),
            "region": region,
            "merchant_id": merchant_id,
            "ftc_placeholder": any(d.ftc_placeholder for d in selected),
            "disclaimer": (
                "Disclosure text is a demo placeholder and is not legal advice. "
                "No real affiliate network compliance workflow is implemented."
            ),
        }

    def create_disclosure(
        self,
        *,
        disclosure_type: str,
        text: str,
        region: str | None = None,
        merchant_id: str | None = None,
        locale: str = "en",
        ftc_placeholder: bool = True,
        active: bool = True,
        disclosure_id: str | None = None,
    ) -> AffiliateDisclosure:
        cleaned_type = (disclosure_type or "").strip()
        cleaned_text = (text or "").strip()
        if not cleaned_type:
            raise AffiliateValidationError("disclosure_type is required.")
        if not cleaned_text:
            raise AffiliateValidationError("disclosure text is required.")
        stamp = self._clock()
        disclosure = AffiliateDisclosure(
            disclosure_id=disclosure_id or f"disc-{self._id_factory()}",
            disclosure_type=cleaned_type,
            text=cleaned_text,
            region=region.upper() if region else None,
            merchant_id=merchant_id,
            locale=locale or "en",
            created_at=stamp,
            updated_at=stamp,
            ftc_placeholder=ftc_placeholder,
            active=active,
        )
        return self._repository.save_disclosure(disclosure)

    def update_disclosure(
        self,
        disclosure_id: str,
        *,
        text: str | None = None,
        active: bool | None = None,
        region: str | None = None,
        locale: str | None = None,
    ) -> AffiliateDisclosure:
        disclosure = self.get_disclosure(disclosure_id)
        updates: dict[str, Any] = {"updated_at": self._clock()}
        if text is not None:
            cleaned = text.strip()
            if not cleaned:
                raise AffiliateValidationError("disclosure text is required.")
            updates["text"] = cleaned
        if active is not None:
            updates["active"] = active
        if region is not None:
            updates["region"] = region.upper() if region else None
        if locale is not None:
            updates["locale"] = locale
        return self._repository.save_disclosure(replace(disclosure, **updates))

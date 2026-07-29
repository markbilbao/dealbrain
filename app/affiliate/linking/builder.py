"""Pure affiliate link URL builder — Sprint 20.

Applies merchant tracking templates and validates URLs. Never ranks products
or reads DealScore. Commission values are attached as estimates only after a
product has already been selected by the recommendation engine.
"""

from __future__ import annotations

import re
from urllib.parse import parse_qsl, urlencode, urlparse, urlunparse

from app.domain.entities.affiliate import AffiliateMerchant, CommissionType
from app.domain.exceptions import AffiliateValidationError

_ALLOWED_SCHEMES = frozenset({"http", "https"})
_TEMPLATE_TOKEN = re.compile(r"\{([a-zA-Z_][a-zA-Z0-9_]*)\}")


class AffiliateLinkBuilder:
    """Build affiliate URLs from merchant templates (pure, no I/O)."""

    def validate_url(self, url: str) -> str:
        """Validate and normalize an http(s) URL. Raises on invalid input."""
        cleaned = (url or "").strip()
        if not cleaned:
            raise AffiliateValidationError("URL is required.")
        parsed = urlparse(cleaned)
        if parsed.scheme.lower() not in _ALLOWED_SCHEMES:
            raise AffiliateValidationError("URL must use http or https.")
        if not parsed.netloc:
            raise AffiliateValidationError("URL must include a host.")
        return cleaned

    def apply_template(
        self,
        merchant: AffiliateMerchant,
        *,
        product_ref: str,
        campaign_id: str | None = None,
        sub_id: str | None = None,
        click_id: str | None = None,
        extra: dict[str, str] | None = None,
    ) -> str:
        """Substitute placeholder tokens in the merchant tracking template."""
        values: dict[str, str] = {
            "product_ref": product_ref or "DEMO_PRODUCT",
            "campaign_id": campaign_id or "DEMO_CAMPAIGN",
            "sub_id": sub_id or "DEMO_SUB",
            "click_id": click_id or "DEMO_CLICK",
            "merchant_id": merchant.merchant_id,
            "marketplace": merchant.marketplace.value,
        }
        if extra:
            values.update({k: str(v) for k, v in extra.items()})

        def _replace(match: re.Match[str]) -> str:
            key = match.group(1)
            return values.get(key, match.group(0))

        rendered = _TEMPLATE_TOKEN.sub(_replace, merchant.tracking_template)
        return self.validate_url(rendered)

    def attach_tracking_params(
        self,
        url: str,
        *,
        campaign_id: str | None = None,
        sub_id: str | None = None,
        click_id: str | None = None,
        extra_params: dict[str, str] | None = None,
    ) -> str:
        """Append / override tracking query parameters on an existing URL."""
        validated = self.validate_url(url)
        parsed = urlparse(validated)
        params = dict(parse_qsl(parsed.query, keep_blank_values=True))
        if campaign_id:
            params["campaign_id"] = campaign_id
        if sub_id:
            params["sub_id"] = sub_id
        if click_id:
            params["click_id"] = click_id
        if extra_params:
            params.update({k: str(v) for k, v in extra_params.items()})
        new_query = urlencode(params)
        return urlunparse(parsed._replace(query=new_query))

    def build_deep_link(
        self,
        merchant: AffiliateMerchant,
        *,
        destination_url: str,
        campaign_id: str | None = None,
        sub_id: str | None = None,
        click_id: str | None = None,
    ) -> str:
        """Wrap a destination URL with merchant tracking when deep links are enabled."""
        destination = self.validate_url(destination_url)
        if not merchant.deep_link_supported:
            raise AffiliateValidationError(
                f"Merchant {merchant.merchant_id} does not support deep links."
            )
        # Prefer template when product_ref can be derived from path; otherwise
        # attach tracking params onto the destination directly.
        product_ref = self._product_ref_from_url(destination) or "deep-link"
        try:
            templated = self.apply_template(
                merchant,
                product_ref=product_ref,
                campaign_id=campaign_id,
                sub_id=sub_id,
                click_id=click_id,
            )
            # Preserve destination as `url` / `dest` query for deep-link demos.
            return self.attach_tracking_params(
                templated,
                extra_params={"dest": destination},
            )
        except AffiliateValidationError:
            return self.attach_tracking_params(
                destination,
                campaign_id=campaign_id,
                sub_id=sub_id,
                click_id=click_id,
                extra_params={"aff_merchant": merchant.merchant_id},
            )

    def estimate_commission(
        self,
        merchant: AffiliateMerchant,
        *,
        order_value: float | None = None,
    ) -> float:
        """Estimate demo commission. Never used for ranking."""
        if merchant.commission_type is CommissionType.FIXED:
            return round(float(merchant.commission_value), 4)
        base = float(order_value) if order_value is not None and order_value > 0 else 100.0
        return round(base * (float(merchant.commission_value) / 100.0), 4)

    @staticmethod
    def _product_ref_from_url(url: str) -> str | None:
        path = urlparse(url).path.strip("/")
        if not path:
            return None
        segment = path.split("/")[-1]
        return segment or None

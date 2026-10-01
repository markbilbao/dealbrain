"""Engineering product TTL for Sprint 39.1 analytics storage.

ENGINEERING / PRODUCT TTL. NOT LEGAL RETENTION.

No purge job runs from this constant. Counsel still owns legal retention.
The horizon is long enough for DAU and MAU if a later slice enforces expiry.
"""

from __future__ import annotations

# Days a first-party analytics preference or subject cookie may live.
# Event rows are not deleted by this constant in Sprint 39.1.
PRODUCT_ANALYTICS_ENGINEERING_TTL_DAYS = 400

PRODUCT_ANALYTICS_ENGINEERING_TTL_SECONDS = PRODUCT_ANALYTICS_ENGINEERING_TTL_DAYS * 24 * 60 * 60

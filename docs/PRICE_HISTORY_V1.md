"""Price History Foundation — trend and statistics formulas.

Sprint 7 documents the deterministic rules used by
``app.intelligence.price_history.statistics``.

Trend threshold
---------------
Default: ``PRICE_TREND_THRESHOLD_PERCENT = 2.0``

Minimum observations for a trend other than ``insufficient_data``: **3**.

Trend formula
-------------
1. Sort snapshots by ``(observed_at ASC, marketplace, listing_id, snapshot_id)``.
2. If count < 3 → ``insufficient_data``.
3. Split at ``mid = count // 2`` into earlier / recent halves.
4. Compare mean total cost of recent vs earlier:
   ``delta_pct = ((recent_avg - earlier_avg) / earlier_avg) * 100``
5. ``rising`` if ``delta_pct > threshold``;
   ``falling`` if ``delta_pct < -threshold``;
   otherwise ``stable``.

Statistics wording
------------------
Use “Lowest recorded price in the available DealBrain history.”
Never claim “lowest ever,” future forecasts, or currency conversion.
"""

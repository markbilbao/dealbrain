"""Alert evaluation and notification orchestration.

Generates alerts for price drops, target price, DealScore improvements, and
historical lows. Uses mock notifications only — no email/SMS/push delivery.
"""

from __future__ import annotations

from collections.abc import Callable, Sequence
from dataclasses import replace
from datetime import UTC, datetime
from uuid import uuid4

from app.domain.entities.watchlist import (
    Alert,
    AlertEvaluationResult,
    AlertStatus,
    AlertType,
    NotificationReceipt,
    WatchlistItem,
)
from app.domain.exceptions import (
    AlertNotFoundError,
    DealScoreValidationError,
    PriceHistoryValidationError,
    WatchlistNotFoundError,
    WatchlistValidationError,
)
from app.domain.interfaces.notification_service import NotificationService
from app.domain.interfaces.watchlist_repository import AlertRepository, WatchlistRepository
from app.services.deal_recommendation_service import DealRecommendationService
from app.services.price_history_service import PriceHistoryService


class AlertService:
    """Evaluate watchlist items and manage generated alerts."""

    def __init__(
        self,
        repository: WatchlistRepository,
        alert_repository: AlertRepository,
        *,
        price_history_service: PriceHistoryService,
        notification_service: NotificationService,
        deal_recommendation_service: DealRecommendationService | None = None,
        clock: Callable[[], datetime] | None = None,
        id_factory: Callable[[], str] | None = None,
    ) -> None:
        self._repository = repository
        self._alerts = alert_repository
        self._price_history = price_history_service
        self._notifications = notification_service
        self._deal_recommendation = deal_recommendation_service
        self._clock = clock or (lambda: datetime.now(UTC))
        self._id_factory = id_factory or (lambda: str(uuid4()))

    def get_alert(self, alert_id: str) -> Alert:
        alert = self._alerts.get_alert(alert_id)
        if alert is None:
            raise AlertNotFoundError(alert_id)
        return alert

    def list_alerts(
        self,
        *,
        watchlist_id: str | None = None,
        item_id: str | None = None,
        alert_type: str | None = None,
        status: str | None = None,
        limit: int = 50,
    ) -> list[Alert]:
        if watchlist_id is not None and self._repository.get_watchlist(watchlist_id) is None:
            raise WatchlistNotFoundError(watchlist_id)
        if limit < 1:
            raise WatchlistValidationError("limit must be at least 1.")
        return self._alerts.list_alerts(
            watchlist_id=watchlist_id,
            item_id=item_id,
            alert_type=alert_type,
            status=status,
            limit=limit,
        )

    def acknowledge_alert(self, alert_id: str) -> Alert:
        alert = self.get_alert(alert_id)
        updated = replace(alert, status=AlertStatus.ACKNOWLEDGED)
        return self._alerts.save_alert(updated)

    def dismiss_alert(self, alert_id: str) -> Alert:
        alert = self.get_alert(alert_id)
        updated = replace(alert, status=AlertStatus.DISMISSED)
        return self._alerts.save_alert(updated)

    async def evaluate_all(self) -> AlertEvaluationResult:
        """Evaluate every enabled watchlist and return created alerts."""
        watchlists = self._repository.list_watchlists(enabled=True)
        return await self._evaluate_watchlists([w.watchlist_id for w in watchlists])

    async def evaluate_watchlist(self, watchlist_id: str) -> AlertEvaluationResult:
        watchlist = self._repository.get_watchlist(watchlist_id)
        if watchlist is None:
            raise WatchlistNotFoundError(watchlist_id)
        if not watchlist.enabled:
            stamp = self._clock()
            return AlertEvaluationResult(
                watchlist_ids=(watchlist_id,),
                items_checked=0,
                alerts_created=(),
                notifications=(),
                evaluated_at=stamp,
            )
        return await self._evaluate_watchlists([watchlist_id])

    async def _evaluate_watchlists(
        self,
        watchlist_ids: Sequence[str],
    ) -> AlertEvaluationResult:
        stamp = self._clock()
        created: list[Alert] = []
        notifications: list[NotificationReceipt] = []
        items_checked = 0

        for watchlist_id in watchlist_ids:
            items = self._repository.list_items(watchlist_id=watchlist_id, enabled=True)
            for item in items:
                items_checked += 1
                new_alerts = await self._evaluate_item(item, evaluated_at=stamp)
                for alert in new_alerts:
                    saved = self._alerts.save_alert(alert)
                    receipt = self._notifications.notify(saved)
                    notified = replace(
                        saved,
                        status=AlertStatus.NOTIFIED,
                        notified_at=receipt.created_at,
                    )
                    saved = self._alerts.save_alert(notified)
                    created.append(saved)
                    notifications.append(receipt)

        return AlertEvaluationResult(
            watchlist_ids=tuple(watchlist_ids),
            items_checked=items_checked,
            alerts_created=tuple(created),
            notifications=tuple(notifications),
            evaluated_at=stamp,
        )

    async def _evaluate_item(
        self,
        item: WatchlistItem,
        *,
        evaluated_at: datetime,
    ) -> list[Alert]:
        alerts: list[Alert] = []
        current_price: float | None = None
        historical_low: float | None = None
        currency = item.currency
        observation_count = 0

        try:
            history = await self._price_history.get_product_history(
                item.canonical_product_id
            )
        except PriceHistoryValidationError:
            history = None

        if history is not None and history.statistics is not None:
            stats = history.statistics
            current_price = stats.current_total_cost
            historical_low = stats.lowest_recorded_total_cost
            currency = stats.currency
            observation_count = stats.observation_count

        current_dealscore = await self._resolve_dealscore(item)

        if current_price is not None:
            if (
                item.last_known_price is not None
                and current_price < item.last_known_price
            ):
                drop = round(item.last_known_price - current_price, 2)
                alerts.append(
                    self._build_alert(
                        item,
                        alert_type=AlertType.PRICE_DROP,
                        message=(
                            f"Price dropped by {currency} {drop:.2f} "
                            f"({item.last_known_price:.2f} → {current_price:.2f})."
                        ),
                        previous_value=item.last_known_price,
                        current_value=current_price,
                        currency=currency,
                        dealscore=current_dealscore,
                        created_at=evaluated_at,
                    )
                )

            if item.target_price is not None and current_price <= item.target_price:
                alerts.append(
                    self._build_alert(
                        item,
                        alert_type=AlertType.TARGET_PRICE_REACHED,
                        message=(
                            f"Target price reached: {currency} {current_price:.2f} "
                            f"≤ target {item.target_price:.2f}."
                        ),
                        previous_value=item.target_price,
                        current_value=current_price,
                        currency=currency,
                        dealscore=current_dealscore,
                        created_at=evaluated_at,
                    )
                )

            if (
                historical_low is not None
                and observation_count >= 2
                and current_price <= historical_low
            ):
                is_new_low = (
                    item.last_historical_low is None
                    or current_price < item.last_historical_low
                    or (
                        current_price == historical_low
                        and (
                            item.last_known_price is None
                            or current_price < item.last_known_price
                        )
                    )
                )
                if is_new_low:
                    alerts.append(
                        self._build_alert(
                            item,
                            alert_type=AlertType.HISTORICAL_LOW,
                            message=(
                                f"New historical low detected: {currency} "
                                f"{current_price:.2f} "
                                "(lowest recorded in available DealBrain history)."
                            ),
                            previous_value=item.last_historical_low,
                            current_value=current_price,
                            currency=currency,
                            dealscore=current_dealscore,
                            created_at=evaluated_at,
                        )
                    )

        if (
            current_dealscore is not None
            and item.last_known_dealscore is not None
            and current_dealscore > item.last_known_dealscore
        ):
            alerts.append(
                self._build_alert(
                    item,
                    alert_type=AlertType.DEALSCORE_IMPROVED,
                    message=(
                        f"DealScore improved from {item.last_known_dealscore:.1f} "
                        f"to {current_dealscore:.1f}."
                    ),
                    previous_value=item.last_known_dealscore,
                    current_value=current_dealscore,
                    currency=currency,
                    dealscore=current_dealscore,
                    created_at=evaluated_at,
                )
            )

        # Persist baseline for the next evaluation pass.
        self._repository.save_item(
            replace(
                item,
                last_known_price=(
                    current_price if current_price is not None else item.last_known_price
                ),
                last_known_dealscore=(
                    current_dealscore
                    if current_dealscore is not None
                    else item.last_known_dealscore
                ),
                last_historical_low=(
                    historical_low
                    if historical_low is not None
                    else item.last_historical_low
                ),
                updated_at=evaluated_at,
            )
        )
        return alerts

    async def _resolve_dealscore(self, item: WatchlistItem) -> float | None:
        if self._deal_recommendation is None:
            return item.last_known_dealscore
        query = (item.search_query or item.product_label or "").strip()
        if not query:
            return item.last_known_dealscore
        try:
            ranking = self._deal_recommendation.recommend(query)
        except DealScoreValidationError:
            return item.last_known_dealscore
        if ranking.recommended is None:
            return item.last_known_dealscore
        return ranking.recommended.deal_score.score

    def _build_alert(
        self,
        item: WatchlistItem,
        *,
        alert_type: AlertType,
        message: str,
        previous_value: float | None,
        current_value: float | None,
        currency: str | None,
        dealscore: float | None,
        created_at: datetime,
    ) -> Alert:
        return Alert(
            alert_id=self._id_factory(),
            watchlist_id=item.watchlist_id,
            item_id=item.item_id,
            canonical_product_id=item.canonical_product_id,
            alert_type=alert_type,
            message=message,
            previous_value=previous_value,
            current_value=current_value,
            currency=currency,
            dealscore=dealscore,
            status=AlertStatus.PENDING,
            created_at=created_at,
            notified_at=None,
        )

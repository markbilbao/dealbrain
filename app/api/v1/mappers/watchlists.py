"""Map Watchlists & Alerts domain objects to HTTP schemas."""

from __future__ import annotations

from app.core.public_brand import present_consumer_text
from app.domain.entities.watchlist import (
    Alert,
    AlertEvaluationResult,
    NotificationReceipt,
    Watchlist,
    WatchlistHistoryEntry,
    WatchlistItem,
    WatchlistItemSnapshot,
)
from app.schemas.watchlists import (
    AlertEvaluationResponse,
    AlertPayload,
    NotificationReceiptPayload,
    WatchlistHistoryEntryPayload,
    WatchlistItemPayload,
    WatchlistPayload,
)


def to_watchlist_payload(watchlist: Watchlist, *, item_count: int = 0) -> WatchlistPayload:
    return WatchlistPayload(
        watchlist_id=watchlist.watchlist_id,
        name=watchlist.name,
        owner_id=watchlist.owner_id,
        description=watchlist.description,
        enabled=watchlist.enabled,
        created_at=watchlist.created_at.isoformat(),
        updated_at=(watchlist.updated_at or watchlist.created_at).isoformat(),
        item_count=item_count,
        is_default=watchlist.is_default,
        status=watchlist.status.value,
        paused_at=watchlist.paused_at.isoformat() if watchlist.paused_at else None,
        archived_at=watchlist.archived_at.isoformat() if watchlist.archived_at else None,
        preferred_sellers=list(watchlist.preferred_sellers),
        preferred_marketplaces=list(watchlist.preferred_marketplaces),
    )


def to_history_payload(entry: WatchlistHistoryEntry) -> WatchlistHistoryEntryPayload:
    return WatchlistHistoryEntryPayload(
        history_id=entry.history_id,
        watchlist_id=entry.watchlist_id,
        event_type=entry.event_type,
        description=entry.description,
        created_at=entry.created_at.isoformat(),
        actor_id=entry.actor_id,
        item_id=entry.item_id,
        metadata=dict(entry.metadata) if entry.metadata else {},
    )


def to_item_payload(
    item: WatchlistItem,
    *,
    snapshot: WatchlistItemSnapshot | None = None,
) -> WatchlistItemPayload:
    current_price = snapshot.current_price if snapshot else None
    historical_low = snapshot.historical_low if snapshot else None
    dealscore = snapshot.dealscore if snapshot else item.last_known_dealscore
    observed_currency = snapshot.currency if snapshot else None
    observation_count = snapshot.observation_count if snapshot else 0
    price_available = snapshot.price_available if snapshot else False
    return WatchlistItemPayload(
        item_id=item.item_id,
        watchlist_id=item.watchlist_id,
        canonical_product_id=item.canonical_product_id,
        product_label=item.product_label,
        target_price=item.target_price,
        currency=item.currency,
        search_query=item.search_query,
        last_known_price=item.last_known_price,
        last_known_dealscore=item.last_known_dealscore,
        last_historical_low=item.last_historical_low,
        enabled=item.enabled,
        created_at=item.created_at.isoformat(),
        updated_at=(item.updated_at or item.created_at).isoformat(),
        current_price=current_price,
        historical_low=historical_low,
        dealscore=dealscore,
        observed_currency=observed_currency,
        observation_count=observation_count,
        price_available=price_available,
        marketplace_offer_id=item.marketplace_offer_id,
        notes=item.notes,
        item_kind=item.item_kind.value,
        monitoring_paused=item.monitoring_paused,
        preferred_sellers=list(item.preferred_sellers),
        preferred_marketplaces=list(item.preferred_marketplaces),
    )


def to_snapshot_payload(snapshot: WatchlistItemSnapshot) -> WatchlistItemPayload:
    return to_item_payload(snapshot.item, snapshot=snapshot)


def to_alert_payload(alert: Alert) -> AlertPayload:
    return AlertPayload(
        alert_id=alert.alert_id,
        watchlist_id=alert.watchlist_id,
        item_id=alert.item_id,
        canonical_product_id=alert.canonical_product_id,
        alert_type=alert.alert_type.value,
        message=present_consumer_text(alert.message),
        previous_value=alert.previous_value,
        current_value=alert.current_value,
        currency=alert.currency,
        dealscore=alert.dealscore,
        status=alert.status.value,
        created_at=alert.created_at.isoformat(),
        notified_at=alert.notified_at.isoformat() if alert.notified_at else None,
    )


def to_notification_payload(receipt: NotificationReceipt) -> NotificationReceiptPayload:
    return NotificationReceiptPayload(
        notification_id=receipt.notification_id,
        alert_id=receipt.alert_id,
        channel=receipt.channel.value,
        status=receipt.status.value,
        created_at=receipt.created_at.isoformat(),
        detail=receipt.detail,
    )


def to_evaluation_response(result: AlertEvaluationResult) -> AlertEvaluationResponse:
    return AlertEvaluationResponse(
        watchlist_ids=list(result.watchlist_ids),
        items_checked=result.items_checked,
        alerts_count=len(result.alerts_created),
        alerts_created=[to_alert_payload(a) for a in result.alerts_created],
        notifications=[to_notification_payload(n) for n in result.notifications],
        evaluated_at=result.evaluated_at.isoformat(),
    )

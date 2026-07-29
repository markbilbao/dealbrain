"""Alert Rules & Alert Events API endpoints — Sprint 19.

Rule-driven, user-owned alerting layered on top of the Sprint 10
``/alerts`` acknowledge/dismiss surface (kept unchanged in
``app.api.v1.endpoints.watchlists``). All notification delivery remains
mock/simulated — no real email, SMS, or push transport exists.

Route ordering: ``rules_router`` (``/alerts/rules``...) and
``evaluate_router`` (``/alerts/evaluate``, ``/alerts/events``) must be
registered in ``app.api.v1.router`` *before* the Sprint 10
``watchlists.alerts_router`` (``/alerts/{alert_id}``), otherwise FastAPI
would match ``/alerts/rules`` and ``/alerts/evaluate`` against the
Sprint 10 ``{alert_id}`` path parameter first.
"""

from __future__ import annotations

from fastapi import APIRouter, Depends, Header, HTTPException, Query, status

from app.api.v1.endpoints.auth import extract_bearer_token
from app.api.v1.mappers.alerts_v2 import to_evaluate_response, to_event_payload, to_rule_payload
from app.core.config import settings
from app.core.dependencies import (
    get_alert_evaluation_service,
    get_alert_event_repository,
    get_alert_rule_service,
    get_user_platform_service,
)
from app.domain.entities.alerts import AlertCondition, AlertConditionType
from app.domain.exceptions import (
    AlertRuleNotFoundError,
    AlertRuleValidationError,
    UserPlatformAuthError,
    WatchlistNotFoundError,
    WatchlistOwnershipError,
)
from app.domain.interfaces.alert_rule_repository import AlertEventRepository
from app.schemas.alerts_v2 import (
    AlertEvaluateRequest,
    AlertEventListResponse,
    AlertRuleCreateRequest,
    AlertRuleEvaluateResponse,
    AlertRuleListResponse,
    AlertRulePayload,
    AlertRuleUpdateRequest,
)
from app.services.alert_evaluation_service import AlertEvaluationService
from app.services.alert_rule_service import AlertRuleService
from app.services.user_platform_service import UserPlatformService

rules_router = APIRouter(prefix="/alerts/rules")
evaluate_router = APIRouter(prefix="/alerts")


def _map_error(exc: Exception) -> HTTPException:
    if isinstance(exc, AlertRuleValidationError):
        return HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=exc.message)
    if isinstance(exc, WatchlistOwnershipError):
        return HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail=str(exc))
    if isinstance(exc, (AlertRuleNotFoundError, WatchlistNotFoundError)):
        return HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc))
    return HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=str(exc))


def _resolve_actor(
    authorization: str | None,
    user_platform: UserPlatformService,
    *,
    fallback_user_id: str | None = None,
) -> str | None:
    """Resolve the authenticated actor's user id.

    Mirrors ``app.api.v1.endpoints.watchlists._resolve_actor``: when
    ``settings.watchlists_require_auth`` is True, a bearer token is required
    and any ``fallback_user_id`` from the request body is ignored. When
    False (Sprint 10-style demo/test mode), falls back to
    ``fallback_user_id`` for anonymous, body-supplied identity.
    """
    token = extract_bearer_token(authorization)
    if token is None:
        if settings.watchlists_require_auth:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED, detail="Authentication required."
            )
        return fallback_user_id
    try:
        user = user_platform.require_user(token)
    except UserPlatformAuthError as exc:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail=exc.message) from exc
    return user.user_id


def _require_actor(actor: str | None) -> str:
    if not actor:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED, detail="Authentication required."
        )
    return actor


def _conditions_from_payloads(payloads: list) -> list[AlertCondition]:
    conditions: list[AlertCondition] = []
    for payload in payloads:
        try:
            condition_type = AlertConditionType(payload.condition_type)
        except ValueError as exc:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Invalid condition_type: {payload.condition_type!r}",
            ) from exc
        conditions.append(
            AlertCondition(
                condition_type=condition_type,
                threshold_value=payload.threshold_value,
                threshold_percent=payload.threshold_percent,
                comparison=payload.comparison,
            )
        )
    return conditions


@rules_router.get(
    "",
    response_model=AlertRuleListResponse,
    summary="List the authenticated user's alert rules",
)
async def list_rules(
    watchlist_id: str | None = None,
    item_id: str | None = None,
    enabled: bool | None = None,
    authorization: str | None = Header(default=None),
    service: AlertRuleService = Depends(get_alert_rule_service),
    user_platform: UserPlatformService = Depends(get_user_platform_service),
) -> AlertRuleListResponse:
    actor = _resolve_actor(authorization, user_platform)
    rules = service.list_rules(
        user_id=actor, watchlist_id=watchlist_id, item_id=item_id, enabled=enabled
    )
    return AlertRuleListResponse(rules=[to_rule_payload(r) for r in rules])


@rules_router.post(
    "",
    response_model=AlertRulePayload,
    status_code=status.HTTP_201_CREATED,
    summary="Create an alert rule",
)
async def create_rule(
    body: AlertRuleCreateRequest,
    authorization: str | None = Header(default=None),
    service: AlertRuleService = Depends(get_alert_rule_service),
    user_platform: UserPlatformService = Depends(get_user_platform_service),
) -> AlertRulePayload:
    actor = _require_actor(
        _resolve_actor(authorization, user_platform, fallback_user_id=body.user_id)
    )
    try:
        rule = service.create_rule(
            user_id=actor,
            name=body.name,
            conditions=_conditions_from_payloads(body.conditions),
            watchlist_id=body.watchlist_id,
            item_id=body.item_id,
            enabled=body.enabled,
            status=_rule_status(body.status),
            cooldown_seconds=body.cooldown_seconds,
            repeat_policy=_repeat_policy(body.repeat_policy),
            severity=_severity(body.severity),
            timezone=body.timezone,
            channel_preferences=_channels(body.channel_preferences),
        )
    except (AlertRuleValidationError, WatchlistNotFoundError, WatchlistOwnershipError) as exc:
        raise _map_error(exc) from exc
    return to_rule_payload(rule)


@rules_router.get(
    "/{rule_id}",
    response_model=AlertRulePayload,
    summary="Get an alert rule",
)
async def get_rule(
    rule_id: str,
    authorization: str | None = Header(default=None),
    service: AlertRuleService = Depends(get_alert_rule_service),
    user_platform: UserPlatformService = Depends(get_user_platform_service),
) -> AlertRulePayload:
    actor = _resolve_actor(authorization, user_platform)
    try:
        rule = service.get_rule(rule_id, user_id=actor)
    except AlertRuleNotFoundError as exc:
        raise _map_error(exc) from exc
    return to_rule_payload(rule)


@rules_router.put(
    "/{rule_id}",
    response_model=AlertRulePayload,
    summary="Update an alert rule",
)
async def update_rule(
    rule_id: str,
    body: AlertRuleUpdateRequest,
    authorization: str | None = Header(default=None),
    service: AlertRuleService = Depends(get_alert_rule_service),
    user_platform: UserPlatformService = Depends(get_user_platform_service),
) -> AlertRulePayload:
    actor = _resolve_actor(authorization, user_platform)
    try:
        # ``AlertRuleService.update_rule`` distinguishes "not supplied" (its
        # own module-private ``_UNSET`` default) from "explicitly cleared to
        # None" for ``watchlist_id``/``item_id`` via identity comparison —
        # only include these kwargs at all when the request actually wants
        # to change them, so the service's own default sentinel applies
        # otherwise.
        scope_kwargs: dict[str, object] = {}
        if body.clear_watchlist_id:
            scope_kwargs["watchlist_id"] = None
        elif body.watchlist_id is not None:
            scope_kwargs["watchlist_id"] = body.watchlist_id
        if body.clear_item_id:
            scope_kwargs["item_id"] = None
        elif body.item_id is not None:
            scope_kwargs["item_id"] = body.item_id

        rule = service.update_rule(
            rule_id,
            user_id=actor,
            name=body.name,
            conditions=_conditions_from_payloads(body.conditions)
            if body.conditions is not None
            else None,
            enabled=body.enabled,
            status=_rule_status(body.status) if body.status is not None else None,
            cooldown_seconds=body.cooldown_seconds,
            repeat_policy=_repeat_policy(body.repeat_policy)
            if body.repeat_policy is not None
            else None,
            severity=_severity(body.severity) if body.severity is not None else None,
            timezone=body.timezone,
            channel_preferences=(
                _channels(body.channel_preferences)
                if body.channel_preferences is not None
                else None
            ),
            **scope_kwargs,
        )
    except (
        AlertRuleValidationError,
        AlertRuleNotFoundError,
        WatchlistNotFoundError,
        WatchlistOwnershipError,
    ) as exc:
        raise _map_error(exc) from exc
    return to_rule_payload(rule)


@rules_router.delete(
    "/{rule_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Delete an alert rule",
)
async def delete_rule(
    rule_id: str,
    authorization: str | None = Header(default=None),
    service: AlertRuleService = Depends(get_alert_rule_service),
    user_platform: UserPlatformService = Depends(get_user_platform_service),
) -> None:
    actor = _resolve_actor(authorization, user_platform)
    try:
        service.delete_rule(rule_id, user_id=actor)
    except AlertRuleNotFoundError as exc:
        raise _map_error(exc) from exc


@evaluate_router.post(
    "/evaluate",
    response_model=AlertRuleEvaluateResponse,
    summary="Manually evaluate alert rules (Sprint 19)",
)
async def evaluate_rules(
    body: AlertEvaluateRequest,
    authorization: str | None = Header(default=None),
    rule_service: AlertRuleService = Depends(get_alert_rule_service),
    evaluation_service: AlertEvaluationService = Depends(get_alert_evaluation_service),
    user_platform: UserPlatformService = Depends(get_user_platform_service),
) -> AlertRuleEvaluateResponse:
    actor = _require_actor(
        _resolve_actor(authorization, user_platform, fallback_user_id=body.user_id)
    )
    try:
        if body.rule_id is not None:
            rule = rule_service.get_rule(body.rule_id, user_id=actor)
            summary = await evaluation_service.evaluate_rules([rule])
        elif body.watchlist_id is not None:
            # Ownership of the watchlist is enforced by evaluate_watchlist's
            # rule lookup (rules are already scoped to the requesting user
            # via list_rules(user_id=...) at creation time).
            rules = rule_service.list_rules(
                user_id=actor, watchlist_id=body.watchlist_id, enabled=True
            )
            summary = await evaluation_service.evaluate_rules(rules)
        else:
            summary = await evaluation_service.evaluate_for_user(actor)
    except (AlertRuleNotFoundError, WatchlistNotFoundError, WatchlistOwnershipError) as exc:
        raise _map_error(exc) from exc
    return to_evaluate_response(summary)


@evaluate_router.get(
    "/events",
    response_model=AlertEventListResponse,
    summary="List the authenticated user's alert events (Sprint 19)",
)
async def list_events(
    rule_id: str | None = None,
    limit: int = Query(50, ge=1, le=200),
    user_id: str | None = Query(default=None, description="Demo-mode fallback user id"),
    authorization: str | None = Header(default=None),
    event_repository: AlertEventRepository = Depends(get_alert_event_repository),
    user_platform: UserPlatformService = Depends(get_user_platform_service),
) -> AlertEventListResponse:
    actor = _require_actor(_resolve_actor(authorization, user_platform, fallback_user_id=user_id))
    events = event_repository.list_events(user_id=actor, rule_id=rule_id, limit=limit)
    return AlertEventListResponse(events=[to_event_payload(e) for e in events])


def _rule_status(value: str):
    from app.domain.entities.alerts import AlertRuleStatus

    try:
        return AlertRuleStatus(value)
    except ValueError as exc:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST, detail=f"Invalid status: {value!r}"
        ) from exc


def _repeat_policy(value: str):
    from app.domain.entities.alerts import AlertRepeatPolicy

    try:
        return AlertRepeatPolicy(value)
    except ValueError as exc:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST, detail=f"Invalid repeat_policy: {value!r}"
        ) from exc


def _severity(value: str):
    from app.domain.entities.alerts import AlertSeverity

    try:
        return AlertSeverity(value)
    except ValueError as exc:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST, detail=f"Invalid severity: {value!r}"
        ) from exc


def _channels(values: list[str]):
    from app.domain.entities.watchlist import NotificationChannel

    try:
        return [NotificationChannel(v) for v in values]
    except ValueError as exc:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST, detail=f"Invalid channel in {values!r}"
        ) from exc

"""FastAPI document routes for the Product Foundation consumer experience."""

from __future__ import annotations

from json import JSONDecodeError
from pathlib import Path
from typing import Any

from fastapi import APIRouter, Depends, Query, Request
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.staticfiles import StaticFiles

from app.consumer import mode as consumer_mode
from app.consumer.canonical_presentation import page_view_from_snapshot
from app.consumer.canonical_resolve import resolve_canonical_snapshot
from app.consumer.decision_owner import OWNER_COOKIE, parse_owner_cookie
from app.consumer.fixtures import DEFAULT_CATALOG_ID, get_decision
from app.consumer.location import (
    DELIVERY_COOKIE,
    LocationValidationError,
    context_from_manual,
    parse_delivery_cookie,
    set_delivery_cookie,
    skipped_context,
)
from app.consumer.pages import render_page
from app.consumer.presentation import build_page_view
from app.consumer.uuid import is_canonical_uuid
from app.consumer.view_models import DecisionPageView, PageName
from app.core.dependencies import get_shopping_decision_snapshot_repository
from app.core.logging import get_logger, log_extra
from app.domain.interfaces.decision_snapshot_repository import DecisionSnapshotRepository

router = APIRouter(include_in_schema=False)
logger = get_logger(__name__)
_STATIC_DIR = Path(__file__).resolve().parent.parent / "static" / "consumer"

_ALLOWED_NEXT_PREFIXES = ("/results/", "/compare/", "/why-best-piq/")


def mount_consumer_static(app) -> None:  # noqa: ANN001 — FastAPI app
    app.mount(
        "/static/consumer",
        StaticFiles(directory=str(_STATIC_DIR)),
        name="consumer_static",
    )


def _location_from_request(request: Request):
    return parse_delivery_cookie(request.cookies.get(DELIVERY_COOKIE))


def _owner_from_request(request: Request):
    return parse_owner_cookie(request.cookies.get(OWNER_COOKIE))


def _page_view(
    request: Request,
    *,
    decision_id: str,
    page: PageName,
    location_prompt: bool | None = None,
    recalculating: bool = False,
    location_error: str | None = None,
    snapshots: DecisionSnapshotRepository | None = None,
) -> DecisionPageView:
    location = _location_from_request(request)
    prompt = location.is_absent if location_prompt is None else location_prompt
    if is_canonical_uuid(decision_id):
        snapshot = resolve_canonical_snapshot(decision_id, _owner_from_request(request), snapshots)
        if snapshot is None:
            return build_page_view(
                decision_id=decision_id,
                page=page,
                location=location,
                location_prompt=prompt,
                recalculating=False,
                location_error=location_error,
            )
        return page_view_from_snapshot(
            snapshot,
            page=page,
            session_location=location,
            location_prompt=prompt,
            recalculating=False,
            location_error=location_error,
        )
    return build_page_view(
        decision_id=decision_id,
        page=page,
        location=location,
        location_prompt=prompt,
        recalculating=recalculating,
        location_error=location_error,
    )


def _html(view) -> HTMLResponse:
    return HTMLResponse(render_page(view))


def _safe_next(next_path: str, decision_id: str, fallback: PageName) -> str:
    if any(next_path.startswith(prefix) for prefix in _ALLOWED_NEXT_PREFIXES):
        return next_path
    routes = {
        "results": f"/results/{decision_id}",
        "compare": f"/compare/{decision_id}",
        "why": f"/why-best-piq/{decision_id}",
    }
    return routes[fallback]


def _page_from_next(next_path: str) -> PageName:
    if next_path.startswith("/compare/"):
        return "compare"
    if next_path.startswith("/why-best-piq/"):
        return "why"
    return "results"


@router.get("/search")
async def consumer_search(
    request: Request,
    q: str | None = Query(default=None),
    catalog: str = Query(default=DEFAULT_CATALOG_ID),
) -> RedirectResponse:
    if not consumer_mode.fixture_catalogs_permitted():
        logger.info(
            "consumer_search",
            extra={"structured": log_extra(event="consumer_search", query=q or "")},
        )
        return RedirectResponse(url="/results/unavailable", status_code=303)
    try:
        get_decision(catalog)
        decision_id = catalog
    except KeyError:
        decision_id = DEFAULT_CATALOG_ID
    logger.info(
        "consumer_search",
        extra={"structured": log_extra(event="consumer_search", query=q or "")},
    )
    return RedirectResponse(url=f"/results/{decision_id}", status_code=303)


@router.get("/results/{decision_id}", response_class=HTMLResponse)
async def results_page(
    request: Request,
    decision_id: str,
    prompt: int = Query(default=0),
    recalculating: int = Query(default=0),
    snapshots: DecisionSnapshotRepository = Depends(get_shopping_decision_snapshot_repository),
) -> HTMLResponse:
    location = _location_from_request(request)
    view = _page_view(
        request,
        decision_id=decision_id,
        page="results",
        location_prompt=bool(prompt) or location.is_absent,
        recalculating=bool(recalculating),
        snapshots=snapshots,
    )
    return _html(view)


@router.get("/compare/{decision_id}", response_class=HTMLResponse)
async def compare_page(
    request: Request,
    decision_id: str,
    snapshots: DecisionSnapshotRepository = Depends(get_shopping_decision_snapshot_repository),
) -> HTMLResponse:
    view = _page_view(
        request,
        decision_id=decision_id,
        page="compare",
        snapshots=snapshots,
    )
    return _html(view)


@router.get("/why-best-piq/{decision_id}", response_class=HTMLResponse)
async def why_page(
    request: Request,
    decision_id: str,
    snapshots: DecisionSnapshotRepository = Depends(get_shopping_decision_snapshot_repository),
) -> HTMLResponse:
    view = _page_view(
        request,
        decision_id=decision_id,
        page="why",
        snapshots=snapshots,
    )
    return _html(view)


@router.api_route("/consumer/location", methods=["GET", "POST"], response_model=None)
async def save_location(request: Request) -> HTMLResponse | RedirectResponse:
    payload = await _location_payload(request)
    action = str(payload.get("action") or "save")
    decision_id = str(payload.get("decision_id") or DEFAULT_CATALOG_ID)
    if not consumer_mode.fixture_catalogs_permitted() and decision_id == DEFAULT_CATALOG_ID:
        decision_id = "unavailable"
    destination = _safe_next(str(payload.get("next") or ""), decision_id, "results")
    previous = _location_from_request(request)
    if action == "skip":
        response = RedirectResponse(url=destination, status_code=303)
        set_delivery_cookie(response, skipped_context())
        return response
    try:
        context = context_from_manual(
            str(payload.get("city") or ""),
            str(payload.get("postal_code") or "") or None,
        )
    except LocationValidationError as exc:
        snapshots = get_shopping_decision_snapshot_repository()
        view = _page_view(
            request,
            decision_id=decision_id,
            page=_page_from_next(destination),
            location_prompt=True,
            location_error=str(exc),
            snapshots=snapshots,
        )
        return _html(view)
    changed = previous.is_known and previous.destination_key != context.destination_key
    separator = "&" if "?" in destination else "?"
    target = f"{destination}{separator}recalculating=1" if changed else destination
    response = RedirectResponse(url=target, status_code=303)
    set_delivery_cookie(response, context)
    return response


async def _location_payload(request: Request) -> dict[str, Any]:
    if request.method == "POST":
        try:
            body = await request.json()
        except (JSONDecodeError, ValueError):
            body = {}
        if isinstance(body, dict):
            return body
        return {}
    return {key: value for key, value in request.query_params.items()}

"""Public PiqSavi Early Access landing page (GET /)."""

from __future__ import annotations

from html import escape
from pathlib import Path

from fastapi import APIRouter, Request
from fastapi.responses import HTMLResponse
from fastapi.staticfiles import StaticFiles

from app.consumer.account_pages import public_head_extras
from app.consumer.seo import apply_staging_noindex_if_needed
from app.core.config import get_settings
from app.core.countries import country_options
from app.core.logging import get_logger, log_extra
from app.core.public_brand import PUBLIC_BRAND, PUBLIC_TAGLINE

router = APIRouter(tags=["early-access"], include_in_schema=False)
logger = get_logger(__name__)

_STATIC_DIR = Path(__file__).resolve().parent.parent / "static" / "early_access"
_INDEX_PATH = _STATIC_DIR / "index.html"


def _country_options_html() -> str:
    parts = ['<option value="">Select your country</option>']
    for code, name in country_options():
        parts.append(f'<option value="{escape(code)}">{escape(name)}</option>')
    return "\n".join(parts)


@router.get("/", response_class=HTMLResponse)
async def early_access_landing(request: Request) -> HTMLResponse:
    """Serve the PiqSavi Early Access landing page."""
    html = _INDEX_PATH.read_text(encoding="utf-8")
    html = html.replace("<!--COUNTRY_OPTIONS-->", _country_options_html())
    html = html.replace("{{PUBLIC_BRAND}}", escape(PUBLIC_BRAND))
    html = html.replace("{{PUBLIC_TAGLINE}}", escape(PUBLIC_TAGLINE))
    extras = public_head_extras(staging=get_settings().is_staging)
    html = html.replace("</head>", f"{extras}\n  </head>", 1)
    logger.info(
        "early_access_page_view",
        extra={
            "structured": log_extra(
                event="early_access_page_view",
                request_id=getattr(request.state, "request_id", None),
            )
        },
    )
    return apply_staging_noindex_if_needed(HTMLResponse(content=html))


def mount_early_access_static(app) -> None:  # noqa: ANN001 — FastAPI app
    """Mount CSS/JS/assets for the Early Access page."""
    app.mount(
        "/static/early_access",
        StaticFiles(directory=str(_STATIC_DIR)),
        name="early_access_static",
    )

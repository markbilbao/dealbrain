"""Internal Product Intelligence demo page."""

from pathlib import Path

from fastapi import APIRouter
from fastapi.responses import HTMLResponse, RedirectResponse

from app.consumer.mode import unfinished_html_surfaces_enabled

router = APIRouter(tags=["demo"])

_DEMO_HTML_PATH = Path(__file__).resolve().parent.parent / "static" / "demo.html"


@router.get("/demo", response_class=HTMLResponse, include_in_schema=False, response_model=None)
async def product_intelligence_demo() -> HTMLResponse | RedirectResponse:
    """Serve the internal Product Intelligence demo UI.

    Production Early Access redirects to the public landing page.
    """
    if not unfinished_html_surfaces_enabled():
        return RedirectResponse(url="/", status_code=303)
    html = _DEMO_HTML_PATH.read_text(encoding="utf-8")
    return HTMLResponse(content=html)

"""Internal Product Intelligence demo page."""

from pathlib import Path

from fastapi import APIRouter
from fastapi.responses import HTMLResponse

router = APIRouter(tags=["demo"])

_DEMO_HTML_PATH = Path(__file__).resolve().parent.parent / "static" / "demo.html"


@router.get("/demo", response_class=HTMLResponse, include_in_schema=False)
async def product_intelligence_demo() -> HTMLResponse:
    """Serve the internal Product Intelligence demo UI."""
    html = _DEMO_HTML_PATH.read_text(encoding="utf-8")
    return HTMLResponse(content=html)

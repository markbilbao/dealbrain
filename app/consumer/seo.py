"""Sprint 29 SEO technical foundation for the FastAPI consumer.

Public pages may be indexable in production. Personalized account and
decision pages stay noindex. Staging is never indexable.
"""

from __future__ import annotations

from starlette.responses import Response

from app.consumer.robots import NOINDEX_ROBOTS_TAG
from app.core.config import get_settings
from app.core.public_brand import PUBLIC_BRAND, PUBLIC_TAGLINE

CANONICAL_ORIGIN = "https://piqsavi.com"
STAGING_ROBOTS_TAG = NOINDEX_ROBOTS_TAG

PUBLIC_SITEMAP_PATHS = ("/",)
PRIVATE_ROBOTS_DISALLOWS = (
    "/results/",
    "/compare/",
    "/why-best-piq/",
    "/account",
    "/login",
    "/register",
    "/reset-password",
    "/verify-email",
    "/support",
    "/consumer/",
)


def canonical_origin() -> str:
    settings = get_settings()
    configured = str(getattr(settings, "public_app_base_url", "") or "").rstrip("/")
    if configured.startswith("https://") or configured.startswith("http://"):
        return configured
    return CANONICAL_ORIGIN


def canonical_url(path: str) -> str:
    if not path.startswith("/"):
        path = f"/{path}"
    if path != "/" and path.endswith("/"):
        path = path.rstrip("/")
    origin = canonical_origin()
    return f"{origin}/" if path == "/" else f"{origin}{path}"


def robots_txt() -> str:
    settings = get_settings()
    if settings.is_staging:
        return "User-agent: *\nDisallow: /\n"
    lines = ["User-agent: *"]
    for path in PRIVATE_ROBOTS_DISALLOWS:
        lines.append(f"Disallow: {path}")
    lines.append("Allow: /")
    lines.append(f"Sitemap: {canonical_url('/sitemap.xml')}")
    return "\n".join(lines) + "\n"


def sitemap_xml() -> str:
    urls = "\n".join(
        (
            "  <url>\n"
            f"    <loc>{_xml(canonical_url(path))}</loc>\n"
            "    <changefreq>weekly</changefreq>\n"
            "  </url>"
        )
        for path in PUBLIC_SITEMAP_PATHS
    )
    return (
        '<?xml version="1.0" encoding="UTF-8"?>\n'
        '<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">\n'
        f"{urls}\n"
        "</urlset>\n"
    )


def organization_json_ld() -> str:
    origin = canonical_origin()
    return (
        "{"
        '"@context":"https://schema.org",'
        '"@type":"Organization",'
        f'"name":"{PUBLIC_BRAND}",'
        f'"slogan":"{PUBLIC_TAGLINE}",'
        f'"url":"{origin}/",'
        f'"logo":"{origin}/static/early_access/assets/piqsavi-logo.png"'
        "}"
    )


def website_json_ld() -> str:
    origin = canonical_origin()
    return (
        "{"
        '"@context":"https://schema.org",'
        '"@type":"WebSite",'
        f'"name":"{PUBLIC_BRAND}",'
        f'"alternateName":"{PUBLIC_TAGLINE}",'
        f'"url":"{origin}/"'
        "}"
    )


def apply_noindex(response: Response) -> Response:
    response.headers["X-Robots-Tag"] = NOINDEX_ROBOTS_TAG
    return response


def apply_staging_noindex_if_needed(response: Response) -> Response:
    if get_settings().is_staging:
        return apply_noindex(response)
    return response


def _xml(value: str) -> str:
    return (
        value.replace("&", "&amp;")
        .replace("<", "&lt;")
        .replace(">", "&gt;")
        .replace('"', "&quot;")
    )

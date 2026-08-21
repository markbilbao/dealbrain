"""HTML helpers for Product Foundation pages."""

# ruff: noqa: E501

from __future__ import annotations

from html import escape


def h(value: object) -> str:
    return escape("" if value is None else str(value), quote=False)


def attr(name: str, value: object) -> str:
    return f'{name}="{escape("" if value is None else str(value), quote=True)}"'


def classes(*names: str | None) -> str:
    return " ".join(name for name in names if name)


ICON_PIN = """<svg viewBox="0 0 24 24" width="16" height="16" aria-hidden="true"><path fill="currentColor" d="M12 2a7 7 0 00-7 7c0 5.25 7 13 7 13s7-7.75 7-13a7 7 0 00-7-7zm0 9.5A2.5 2.5 0 119.5 9 2.5 2.5 0 0112 11.5z"/></svg>"""
ICON_SEARCH = """<svg viewBox="0 0 24 24" width="18" height="18" aria-hidden="true"><circle cx="11" cy="11" r="7" fill="none" stroke="currentColor" stroke-width="2"/><path fill="none" stroke="currentColor" stroke-width="2" d="M20 20l-3.5-3.5"/></svg>"""
ICON_LOCK = """<svg viewBox="0 0 24 24" width="14" height="14" aria-hidden="true"><rect x="5" y="11" width="14" height="10" rx="2" fill="none" stroke="currentColor" stroke-width="2"/><path fill="none" stroke="currentColor" stroke-width="2" d="M8 11V8a4 4 0 018 0v3"/></svg>"""
ICON_SHIELD = """<svg viewBox="0 0 24 24" width="18" height="18" aria-hidden="true"><path fill="none" stroke="currentColor" stroke-width="2" d="M12 3l8 3v6c0 5-3.4 8.4-8 9-4.6-.6-8-4-8-9V6z"/></svg>"""
ICON_USER = """<svg viewBox="0 0 24 24" width="18" height="18" aria-hidden="true"><circle cx="12" cy="8" r="3.5" fill="none" stroke="currentColor" stroke-width="2"/><path fill="none" stroke="currentColor" stroke-width="2" d="M5 19a7 7 0 0114 0"/></svg>"""
ICON_CHECK = """<svg viewBox="0 0 24 24" width="16" height="16" aria-hidden="true"><path fill="none" stroke="currentColor" stroke-width="2.4" d="M5 12l5 5 9-10"/></svg>"""
ICON_WARN = """<svg viewBox="0 0 24 24" width="16" height="16" aria-hidden="true"><path fill="none" stroke="currentColor" stroke-width="2" d="M12 3l10 18H2L12 3z"/><path fill="currentColor" d="M11 10h2v5h-2zm0 6h2v2h-2z"/></svg>"""
ICON_BOOKMARK = """<svg viewBox="0 0 24 24" width="18" height="18" aria-hidden="true"><path fill="none" stroke="currentColor" stroke-width="2" d="M7 4h10v16l-5-3-5 3z"/></svg>"""
ICON_CLOSE = """<svg viewBox="0 0 24 24" width="18" height="18" aria-hidden="true"><path fill="none" stroke="currentColor" stroke-width="2" d="M6 6l12 12M18 6L6 18"/></svg>"""
ICON_INFO = """<svg viewBox="0 0 24 24" width="14" height="14" aria-hidden="true"><circle cx="12" cy="12" r="9" fill="none" stroke="currentColor" stroke-width="2"/><path fill="currentColor" d="M11 10h2v7h-2zm0-4h2v2h-2z"/></svg>"""
ICON_ASK = """<svg viewBox="0 0 24 24" width="18" height="18" aria-hidden="true"><path fill="none" stroke="currentColor" stroke-width="2" d="M5 12a7 7 0 0114 0c0 4-3 6-7 9-4-3-7-5-7-9z"/><circle cx="12" cy="12" r="2" fill="currentColor"/></svg>"""
ICON_BUILDING = """<svg viewBox="0 0 24 24" width="16" height="16" aria-hidden="true"><path fill="none" stroke="currentColor" stroke-width="2" d="M4 20V8l8-4 8 4v12H4zM9 20v-6h6v6"/></svg>"""
ICON_CLOCK = """<svg viewBox="0 0 24 24" width="14" height="14" aria-hidden="true"><circle cx="12" cy="12" r="8" fill="none" stroke="currentColor" stroke-width="2"/><path fill="none" stroke="currentColor" stroke-width="2" d="M12 8v5l3 2"/></svg>"""


def logo_markup() -> str:
    return (
        '<img class="brand-logo" src="/static/early_access/assets/piqsavi-logo.png" '
        'alt="PiqSavi" width="120" height="80">'
    )


def product_visual(image_key: str, alt: str) -> str:
    return (
        f'<div class="product-visual product-visual--{h(image_key)}" role="img" '
        f'{attr("aria-label", alt)}></div>'
    )


def piqscore_gauge(value: float, size: str = "lg") -> str:
    clamped = max(0.0, min(100.0, float(value)))
    radius = 42 if size == "lg" else 24
    circumference = 2 * 3.1415926535 * radius
    offset = circumference * (1 - clamped / 100)
    dim = 108 if size == "lg" else 64
    center = dim / 2
    display = str(int(round(clamped)))
    return f"""
    <div class="piqscore-gauge piqscore-gauge--{h(size)}" aria-label="PiqScore {h(display)}">
      <svg viewBox="0 0 {dim} {dim}" width="{dim}" height="{dim}" aria-hidden="true">
        <circle class="gauge-track" cx="{center}" cy="{center}" r="{radius}"></circle>
        <circle class="gauge-value" cx="{center}" cy="{center}" r="{radius}"
          stroke-dasharray="{circumference:.2f}" stroke-dashoffset="{offset:.2f}"></circle>
      </svg>
      <span class="gauge-number">{h(display)}</span>
    </div>
    """

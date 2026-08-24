"""Server-rendered Product Foundation pages."""

# ruff: noqa: E501

from __future__ import annotations

from app.consumer.html import (
    ICON_ASK,
    ICON_BOOKMARK,
    ICON_BUILDING,
    ICON_CHECK,
    ICON_CLOCK,
    ICON_CLOSE,
    ICON_INFO,
    ICON_LOCK,
    ICON_PIN,
    ICON_SEARCH,
    ICON_SHIELD,
    ICON_USER,
    ICON_WARN,
    h,
    logo_markup,
    piqscore_gauge,
    product_visual,
)
from app.consumer.pricing import format_php
from app.consumer.view_models import DecisionPageView, ProductCardView


def _offer_link(url: str, css: str) -> str:
    if not url:
        return ""
    return f'<a class="{css}" href="{h(url)}" rel="nofollow noopener">View offer</a>'


def _card_title(card: ProductCardView) -> str:
    return card.model or card.display_name


def render_page(view: DecisionPageView) -> str:
    body = {
        "results": _results_main,
        "compare": _compare_main,
        "why": _why_main,
    }[view.page](view)
    return _document(view, body)


def _document(view: DecisionPageView, main: str) -> str:
    title = (
        "PiqSavi — Offer details unavailable"
        if view.data_unavailable
        else f"PiqSavi — {view.query_label}"
    )
    qualified = "true" if view.best_piq.is_qualified else "false"
    unavailable = "true" if view.data_unavailable else "false"
    snapshot = "true" if view.destination_snapshot_known else "false"
    return f"""<!DOCTYPE html>
<html lang="en">
  <head>
    <meta charset="utf-8">
    <meta name="viewport" content="width=device-width, initial-scale=1, viewport-fit=cover">
    <meta name="theme-color" content="#0B1B33">
    <title>{h(title)}</title>
    <meta name="description" content="PiqSavi is Your AI Personal Shopper.">
    <link rel="stylesheet" href="/static/consumer/css/piqsavi.css">
  </head>
  <body class="page-{h(view.page)} why-{h(view.why_variant)}"
        data-page="{h(view.page)}"
        data-decision-id="{h(view.decision_id)}"
        data-context-version="{h(view.context_version)}"
        data-presentation-mode="{h(view.presentation_mode)}"
        data-location-state="{h(_location_state(view))}"
        data-best-piq="{h(view.best_piq.product_id)}"
        data-piqscore="{"" if view.data_unavailable else h(view.best_piq.piqscore.value)}"
        data-highest-piqscore-id="{h(view.highest_piqscore_product_id)}"
        data-price-state="{"" if view.data_unavailable else h(view.best_piq.economics.dominant_state)}"
        data-canonical-piqscore-set="{h(view.canonical_piqscore_set_sha256)}"
        data-recommendation-sha="{h(view.recommendation_snapshot_sha256)}"
        data-geocode-available="false"
        data-unavailable="{unavailable}"
        data-classification="{h(view.data_classification)}"
        data-recommendation-qualified="{qualified}"
        data-destination-snapshot="{snapshot}">
    <a class="skip-link" href="#main">Skip to content</a>
    {_site_header(view)}
    <main id="main">
      {_ask_top(view) if view.page != "why" else ""}
      {_location_status(view)}
      {main}
    </main>
    {_ask_dock(view)}
    {_location_modal(view)}
    {_recalculating_modal(view)}
    <div class="ask-overlay" id="ask-overlay" hidden>
      <div class="ask-panel" role="dialog" aria-labelledby="ask-panel-title">
        <div class="ask-panel-head">
          <h2 id="ask-panel-title">Ask PiqSavi</h2>
          <button type="button" class="icon-btn js-close-ask" aria-label="Close">{ICON_CLOSE}</button>
        </div>
        <div class="ask-panel-body" id="ask-panel-body"></div>
      </div>
    </div>
    <script type="module" src="/static/consumer/js/consumer.js"></script>
  </body>
</html>
"""


def _location_state(view: DecisionPageView) -> str:
    if view.location.is_known:
        return "known"
    if view.location.is_skipped:
        return "skipped"
    return "absent"


def _site_header(view: DecisionPageView) -> str:
    return f"""
    <header class="site-header">
      <button type="button" class="nav-toggle" aria-expanded="false" aria-controls="mobile-nav" aria-label="Open menu">
        <span></span>
      </button>
      <a class="brand" href="/">{logo_markup()}</a>
      <nav class="header-nav" aria-label="Primary">
        <a href="/#how-it-works">How it works</a>
        <a href="#piqscore">PiqScore</a>
        <a href="/">Saved</a>
        <a href="/">Watch</a>
      </nav>
      <div class="header-actions">
        <a class="text-link" href="/">Sign in</a>
        <a class="btn btn-primary btn-compact" href="/">Sign up</a>
        <button type="button" class="btn btn-gradient btn-compact js-focus-ask header-ask">Ask PiqSavi</button>
        <a class="profile-btn" href="/" aria-label="Account">{ICON_USER}</a>
      </div>
      <nav id="mobile-nav" class="mobile-nav" hidden>
        <a href="/#how-it-works">How it works</a>
        <a href="#piqscore">PiqScore</a>
        <a href="/">Saved</a>
        <a href="/">Watch</a>
        <a href="/">Sign in</a>
      </nav>
    </header>
    """


def _ask_top(view: DecisionPageView) -> str:
    action = (
        f"/results/{h(view.decision_id)}"
        if view.page == "results"
        else f"/{h(view.page)}/{h(view.decision_id)}"
    )
    if view.page == "compare":
        action = f"/compare/{h(view.decision_id)}"
    return f"""
    <section class="ask-insert ask-insert-top" aria-label="Ask PiqSavi">
      <form class="ask-form js-ask-form" method="post" action="{action}">
        <label class="visually-hidden" for="ask-input-top">Ask about this decision</label>
        <span class="ask-icon">{ICON_SEARCH}</span>
        <input id="ask-input-top" class="ask-input" name="question" maxlength="2000"
               placeholder="{h(view.ask_placeholder)}" autocomplete="off">
        <button type="submit" class="btn btn-gradient">Ask PiqSavi</button>
      </form>
    </section>
    """


def _session_location_note(view: DecisionPageView) -> str:
    if not view.session_location_differs:
        return ""
    current = view.session_location_label or "a different area"
    return (
        f'<p class="location-hint" data-session-location-differs="true">'
        f"This decision was evaluated for {h(view.location.display_place)}. "
        f"Your current session location is {h(current)} and has not changed this decision."
        "</p>"
    )


def _location_status(view: DecisionPageView) -> str:
    if view.location.is_known:
        if view.presentation_mode == "canonical":
            hint = (
                "Costs shown are those evaluated for this decision"
                if view.delivery_costs_verified
                else "Some costs were unknown when this decision was evaluated"
            )
        else:
            hint = (
                "Costs calculated for this delivery area"
                if view.delivery_costs_verified
                else "Shipping to this area is not yet verified and may change this recommendation"
            )
        return f"""
        <div class="location-status location-known">
          <p class="location-label">{ICON_PIN}
            <span>{h(view.location.delivering_to_label)}</span>
            <button type="button" class="text-link js-open-location">Change</button>
          </p>
          <p class="location-hint">{h(hint)}</p>
          {_session_location_note(view)}
        </div>
        """
    if view.location.is_skipped:
        return """
        <div class="location-status location-unknown" role="status">
          <p>No delivery location set • Some costs may be unknown</p>
          <button type="button" class="text-link js-open-location">Add location</button>
        </div>
        """
    return """
    <div class="location-status location-absent" hidden>
      <p>No delivery location set</p>
    </div>
    """


def _results_main(view: DecisionPageView) -> str:
    if view.data_unavailable:
        return _unavailable_main(view)
    changed = ""
    if view.recommendation_changed and view.recommendation_changed_message:
        changed = f"""
        <p class="reco-changed" role="status">{ICON_CHECK}
          {h(view.recommendation_changed_message)}
        </p>
        """
    qualified = ""
    if view.recommendation_qualified_message:
        qualified = f"""
        <p class="reco-qualified" role="status">{ICON_WARN}
          {h(view.recommendation_qualified_message)}
        </p>
        """
    alts = "".join(_alt_card(card, view) for card in view.alternatives[:3])
    return f"""
    {changed}
    {qualified}
    <p class="eval-summary">Compared <span class="count-badge">{h(view.evaluated_count)}</span>
      options across multiple signals {ICON_INFO}</p>
    {_hero_card(view)}
    <section class="alt-section" aria-labelledby="alt-heading">
      <h2 id="alt-heading">Other great Piqs worth considering</h2>
      <div class="alt-grid">{alts}</div>
    </section>
    {_disclosures(view)}
    """


def _hero_card(view: DecisionPageView) -> str:
    best = view.best_piq
    badge = "Best Piq for You — Qualified" if best.is_qualified else "Best Piq for You"
    badge_class = "badge-qualified" if best.is_qualified else "badge-best"
    tags = "".join(f"<li>{h(tag)}</li>" for tag in best.tags)
    reasons = "".join(f"<li>{ICON_CHECK}{h(item)}</li>" for item in best.why_it_won)
    percentile = (
        f'<p class="percentile">{h(best.piqscore.percentile_label)}</p>'
        if best.piqscore.percentile_label
        else ""
    )
    merchant = f"from {h(best.merchant)}"
    fresh = (
        f'<p class="freshness">{ICON_CHECK}{h(best.freshness_label)}</p>'
        if best.freshness_label
        else ""
    )
    shipping_note = ""
    if best.economics.dominant_state == "price_before_shipping":
        dest = view.location.display_place if view.location.is_known else "your area"
        shipping_note = f'<p class="shipping-unknown">Shipping to {h(dest)} not yet verified.</p>'
    return f"""
    <article class="hero-card" aria-labelledby="hero-title">
      <p class="badge {badge_class}">{h(badge)}</p>
      <div class="hero-grid">
        {product_visual(best.image_key, best.identity_name)}
        <div class="hero-copy">
          <p class="brand">{h(best.brand)}</p>
          <h1 id="hero-title">{h(_card_title(best))}</h1>
          <p class="category">{h(best.category)}</p>
          <ul class="tag-list">{tags}</ul>
          <div class="fit-box">{ICON_USER}
            <div>
              <p class="fit-label">Why this fits you</p>
              <p>{h(view.shopper.why_this_fits)}</p>
            </div>
          </div>
          <div class="price-block" data-price-state="{h(best.economics.dominant_state)}">
            <p class="price-label tone-{h(_tone(best))}">{h(best.economics.dominant_label)}</p>
            <p class="price-value">{h(format_php(best.economics.dominant_amount))}</p>
            <p class="merchant">{h(merchant)}</p>
            {fresh}
            {shipping_note}
          </div>
          {_breakdown(best)}
          <div class="hero-actions">
            {_offer_link(best.offer_url, "btn btn-gradient")}
            <button type="button" class="icon-btn" aria-label="Save this Piq">{ICON_BOOKMARK}</button>
          </div>
        </div>
        <div class="hero-score" id="piqscore">
          {piqscore_gauge(best.piqscore.value)}
          <p class="score-name">PiqScore</p>
          <p class="score-desc"><strong>{h(best.piqscore.descriptor)}</strong></p>
          {percentile}
          <h2>Why it won</h2>
          <ul class="win-list">{reasons}</ul>
          <a class="text-link" href="/why-best-piq/{h(view.decision_id)}">See full reasoning →</a>
        </div>
      </div>
    </article>
    """


def _tone(card: ProductCardView) -> str:
    state = card.economics.dominant_state
    if state in {
        "price_before_shipping",
        "before_unverified_import_charges",
        "potential_checkout_price",
    }:
        return "warn"
    return "positive"


def _breakdown(card: ProductCardView) -> str:
    rows = "".join(
        f'<div class="break-row"><span>{h(label)}</span>'
        f'<span class="tone-{h(tone)}">{h(display)}</span></div>'
        for label, display, tone in card.economics.breakdown_lines[:-1]
    )
    last_label, last_display, last_tone = card.economics.breakdown_lines[-1]
    return f"""
    <div class="price-breakdown">
      {rows}
      <div class="break-total tone-{h(last_tone)}">
        <span>{h(last_label)}</span>
        <strong>{h(last_display)}</strong>
      </div>
    </div>
    """


def _alt_card(card: ProductCardView, view: DecisionPageView) -> str:
    badge = (
        f'<p class="mini-badge">{h(card.alternative_badge)}</p>' if card.alternative_badge else ""
    )
    return f"""
    <article class="alt-card">
      {badge}
      {product_visual(card.image_key, card.identity_name)}
      <div class="alt-copy">
        <p class="brand">{h(card.brand)}</p>
        <h3>{h(_card_title(card))}</h3>
        <p class="category">{h(card.category)}</p>
        <div class="alt-score">
          {piqscore_gauge(card.piqscore.value, "sm")}
          <p>{h(int(round(card.piqscore.value)))} · {h(card.piqscore.descriptor)}</p>
        </div>
        <p class="price-label tone-{h(_tone(card))}">{h(card.economics.dominant_label)}</p>
        <p class="price-value">{h(format_php(card.economics.dominant_amount))}</p>
        <p class="compact-break">{h(card.compact_breakdown)}</p>
        <p class="merchant">from {h(card.merchant)}</p>
        <p class="alt-reason">{h(card.alternative_reason)}</p>
        <div class="hero-actions">
          {_offer_link(card.offer_url, "btn btn-primary btn-compact")}
          <button type="button" class="icon-btn" aria-label="Save this Piq">{ICON_BOOKMARK}</button>
        </div>
      </div>
    </article>
    """


def _unavailable_main(view: DecisionPageView) -> str:
    message = view.unavailable_message or ("Offer economics are not available for this request.")
    return f"""
    <section class="data-unavailable" data-unavailable="true" aria-labelledby="unavailable-title">
      <p class="badge badge-unavailable">Unavailable</p>
      <h1 id="unavailable-title">Offer details are not available</h1>
      <p>{h(message)}</p>
      <p class="form-hint">PiqSavi will not invent prices, merchants, shipping, discounts,
         PiqScore, or Recommendation evidence when a canonical snapshot does not include them.</p>
    </section>
    """


def _compare_main(view: DecisionPageView) -> str:
    if view.data_unavailable:
        return _unavailable_main(view)
    qualified = ""
    if view.recommendation_qualified_message:
        qualified = f"""
        <p class="reco-qualified" role="status">{ICON_WARN}
          {h(view.recommendation_qualified_message)}
        </p>
        """
    cards = "".join(_compare_product(card, view) for card in view.compared)
    pay = _compare_table("WHAT YOU'LL PAY", view.compare_pay_rows, view)
    fit = _compare_table("PRODUCT FIT", view.compare_fit_rows, view)
    chips = "".join(
        f'<button type="button" class="chip js-ask-chip">{h(item)}</button>'
        for item in view.ask_suggestions
    )
    return f"""
    {qualified}
    <div class="compare-toolbar">
      <p class="muted">Compare up to 4 options</p>
    </div>
    <section class="compare-cards" aria-label="Compared choices">{cards}</section>
    {pay}
    {fit}
    <aside class="compare-cta">
      <p><strong>Best Piq for You</strong> {h(view.best_piq.identity_name)}</p>
      {_offer_link(view.best_piq.offer_url, "btn btn-gradient")}
      <a class="btn btn-secondary" href="/why-best-piq/{h(view.decision_id)}">See full reasoning →</a>
    </aside>
    <section class="ask-suggestions" aria-label="Suggested questions">
      <h2>Ask PiqSavi</h2>
      <div class="chip-row">{chips}</div>
    </section>
    {_affiliate_only(view)}
    """


def _compare_product(card: ProductCardView, view: DecisionPageView) -> str:
    badge = ""
    if card.is_best_piq:
        label = "Best Piq for You — Qualified" if card.is_qualified else "Best Piq for You"
        badge = f'<p class="badge badge-best">{h(label)}</p>'
    elif card.origin_label:
        badge = f'<p class="origin-label">{h(card.origin_label)}</p>'
    tags = "".join(f"<li>{h(tag)}</li>" for tag in card.tags[:2])
    return f"""
    <article class="compare-card" data-product-id="{h(card.product_id)}">
      {badge}
      {product_visual(card.image_key, card.identity_name)}
      <h2>{h(card.identity_name)}</h2>
      <ul class="tag-list">{tags}</ul>
      {piqscore_gauge(card.piqscore.value, "sm")}
      <p class="score-inline">PiqScore {h(int(round(card.piqscore.value)))}</p>
      <p class="price-value">{h(format_php(card.economics.dominant_amount))}</p>
      <p class="price-label tone-{h(_tone(card))}">{h(card.economics.dominant_label)}</p>
      <p class="merchant">from {h(card.merchant)}</p>
    </article>
    """


def _compare_table(title: str, rows, view: DecisionPageView) -> str:
    head = "".join(f"<th scope='col'>{h(card.identity_name)}</th>" for card in view.compared)
    if not rows:
        return f"""
    <section class="compare-table-wrap">
      <h2>{h(title)}</h2>
      <p class="muted">Not captured for this decision.</p>
    </section>
    """
    body = []
    for row in rows:
        cells = []
        for value in row.values:
            if row.kind == "stars":
                cells.append(f"<td>{_stars(value)}</td>")
            else:
                cells.append(f"<td>{h(value)}</td>")
        body.append(f"<tr><th scope='row'>{h(row.label)}</th>{''.join(cells)}</tr>")
    return f"""
    <section class="compare-table-wrap">
      <h2>{h(title)}</h2>
      <div class="table-scroll">
        <table class="compare-table">
          <thead><tr><th scope="col">{h(title)}</th>{head}</tr></thead>
          <tbody>{"".join(body)}</tbody>
        </table>
      </div>
    </section>
    """


def _stars(value: str) -> str:
    try:
        count = int(value)
    except ValueError:
        return h(value)
    filled = "★" * count
    empty = "☆" * (5 - count)
    return f'<span class="stars" aria-label="{h(count)} out of 5">{filled}{empty}</span>'


def _why_main(view: DecisionPageView) -> str:
    if view.data_unavailable:
        return _unavailable_main(view)
    best = view.best_piq
    badge = "Best Piq for You — Qualified" if best.is_qualified else "Best Piq for You"
    sections = "".join(_why_section(view, section) for section in view.why_sections)
    chips = "".join(
        f'<button type="button" class="chip js-ask-chip">{h(item)}</button>'
        for item in view.ask_suggestions
    )
    return f"""
    <div class="why-toolbar">
      <a class="text-link" href="/results/{h(view.decision_id)}">← Back to results</a>
    </div>
    {f'<p class="reco-qualified" role="status">{ICON_WARN} {h(view.recommendation_qualified_message)}</p>' if view.recommendation_qualified_message else ""}
    <header class="why-hero-head">
      <h1>Why This Is the Best Piq for You</h1>
      <p>PiqSavi evaluated {h(len(view.compared))} offers using available sources and signals,
         then selected the option that best matches your priorities, budget, and delivery needs.</p>
    </header>
    <article class="hero-card why-hero">
      <p class="badge {"badge-qualified" if best.is_qualified else "badge-best"}">{h(badge)}</p>
      <div class="hero-grid">
        {product_visual(best.image_key, best.identity_name)}
        <div class="hero-copy">
          <p class="brand">{h(best.brand)}</p>
          <h2>{h(_card_title(best))}</h2>
          <p class="category">{h(best.category)}</p>
          <p class="merchant">from {h(best.merchant)}</p>
          <p class="price-label tone-{h(_tone(best))}">{h(best.economics.dominant_label)}</p>
          <p class="price-value">{h(format_php(best.economics.dominant_amount))}</p>
          <div class="hero-actions">
            {_offer_link(best.offer_url, "btn btn-gradient")}
            <button type="button" class="icon-btn" aria-label="Save this Piq">{ICON_BOOKMARK}</button>
          </div>
        </div>
        <div class="hero-score" id="piqscore">
          {piqscore_gauge(best.piqscore.value)}
          <p class="score-name">PiqScore</p>
          <p class="score-desc"><strong>{h(best.piqscore.descriptor)}</strong></p>
          {f'<p class="percentile">{h(best.piqscore.percentile_label)}</p>' if best.piqscore.percentile_label else ""}
        </div>
        <aside class="evaluated-price">
          <h2>Price PiqSavi evaluated {ICON_INFO}</h2>
          {_breakdown(best)}
        </aside>
      </div>
    </article>
    <section class="why-grid" aria-label="Recommendation detail">{sections}</section>
    <section class="ask-suggestions">
      <div class="chip-row">{chips}</div>
    </section>
    """


def _why_section(view: DecisionPageView, section) -> str:
    extra = ""
    if section.number == 5:
        cats = "".join(
            f"<li><span>{h(item.label)}</span> "
            f'<strong class="status-{h(item.status)}">{h(item.status_label)}</strong></li>'
            for item in view.evidence_categories
        )
        sources = "".join(f"<li>{h(src.name)}</li>" for src in view.sources if src.proven)
        extra = f"""
        <div class="considered">
          <div>
            <h3>Evidence categories</h3>
            <ul>{cats}</ul>
          </div>
          <div>
            <h3>Sources used for this decision</h3>
            <ul class="source-list">{sources}</ul>
          </div>
        </div>
        """
    bullets = "".join(
        f'<li class="icon-{h(kind)}">{_bullet_icon(kind)}{h(text)}</li>'
        for kind, text in section.bullets
    )
    callout = ""
    if section.callout:
        callout = f'<p class="callout callout-{h(section.callout_tone)}">{h(section.callout)}</p>'
    narrative = f"<p>{h(section.narrative)}</p>" if section.narrative else ""
    return f"""
    <article class="why-section" data-section="{h(section.number)}">
      <button type="button" class="why-toggle" aria-expanded="false">
        <span class="why-num">{h(section.number)}</span>
        <span>{h(section.title)}</span>
      </button>
      <div class="why-body">
        {callout}
        {narrative}
        <ul>{bullets}</ul>
        {extra}
      </div>
    </article>
    """


def _bullet_icon(kind: str) -> str:
    if kind == "warn":
        return ICON_WARN
    if kind == "check":
        return ICON_CHECK
    if kind == "delivery":
        return ICON_PIN
    return ICON_USER


def _disclosures(view: DecisionPageView) -> str:
    return f"""
    {_affiliate_only(view)}
    <section class="save-prompt">
      {ICON_USER}
      <div>
        <h2>Want to save or track this?</h2>
        <p>Create a free account to save this Piq and get price updates.</p>
      </div>
      <a class="btn btn-secondary" href="/">Sign up free</a>
    </section>
    <p class="fine-print">{ICON_CLOCK}{h(view.freshness_disclaimer)}
      <a class="text-link" href="/#how-it-works">Learn how PiqSavi works →</a>
    </p>
    """


def _affiliate_only(view: DecisionPageView) -> str:
    return f"""
    <p class="affiliate-note">{ICON_SHIELD}{h(view.affiliate_disclosure)}</p>
    """


def _ask_dock(view: DecisionPageView) -> str:
    chips = "".join(
        f'<button type="button" class="chip js-ask-chip">{h(item)}</button>'
        for item in view.ask_suggestions
    )
    return f"""
    <section class="ask-dock" aria-label="Ask PiqSavi">
      <form class="ask-form js-ask-form">
        <span class="ask-icon">{ICON_ASK}</span>
        <label class="visually-hidden" for="ask-input-dock">Ask PiqSavi</label>
        <input id="ask-input-dock" class="ask-input" name="question" maxlength="2000"
               placeholder="{h(view.ask_placeholder)}" autocomplete="off">
        <button type="submit" class="btn btn-gradient btn-compact">Ask</button>
      </form>
      <div class="chip-row dock-chips">{chips}</div>
    </section>
    """


def _location_modal(view: DecisionPageView) -> str:
    opened = "open" if view.location_prompt else ""
    hidden = "" if view.location_prompt else "hidden"
    error = (
        f'<p class="form-error" role="alert">{h(view.location_error)}</p>'
        if view.location_error
        else ""
    )
    geo_note = ""
    if view.geolocation_needs_city:
        geo_note = (
            '<p class="form-hint" role="status" data-geo-hint="true">'
            "We cannot convert map coordinates into a city yet. "
            "Enter a city or municipality instead. Precise coordinates are not stored.</p>"
        )
    city_value = h(view.location.city or "")
    postal_value = h(view.location.postal_code or "")
    next_path = {
        "results": f"/results/{view.decision_id}",
        "compare": f"/compare/{view.decision_id}",
        "why": f"/why-best-piq/{view.decision_id}",
    }[view.page]
    return f"""
    <dialog class="location-dialog" id="location-dialog" {opened} {hidden}
            aria-labelledby="location-title">
      <form class="location-form" method="get" action="/consumer/location">
        <input type="hidden" name="next" value="{h(next_path)}">
        <input type="hidden" name="decision_id" value="{h(view.decision_id)}">
        <button type="button" class="icon-btn dialog-close js-close-location" aria-label="Close">
          {ICON_CLOSE}
        </button>
        <div class="pin-orb">{ICON_PIN}</div>
        <h2 id="location-title">Where should we calculate delivery to?</h2>
        <p>PiqSavi uses your delivery area to compare shipping, availability, and total cost more accurately.</p>
        {error}
        {geo_note}
        <button type="button" class="btn btn-gradient btn-block js-use-location"
                name="action" value="use_my_location"
                aria-label="Use my location, then enter a city">
          {ICON_PIN} Use my location
        </button>
        <p class="form-hint" data-geo-capability="unavailable">
          PiqSavi cannot determine your city from a map pin. After you share browser
          location permission, enter a city or municipality. Precise coordinates are not stored.
        </p>
        <p class="or-sep">OR</p>
        <label class="field">
          <span class="field-icon">{ICON_BUILDING}</span>
          <input name="city" maxlength="80" value="{city_value}"
                 autocomplete="address-level2" placeholder="City / municipality" required>
        </label>
        <label class="field">
          <span class="field-icon">{ICON_PIN}</span>
          <input name="postal_code" maxlength="12" value="{postal_value}"
                 autocomplete="postal-code" placeholder="Postal code — optional">
        </label>
        <p class="form-hint">Postal code helps improve shipping accuracy.</p>
        <button type="submit" class="btn btn-primary btn-block" name="action" value="save">
          Use this delivery area
        </button>
        <button type="submit" class="text-link skip-link-btn" name="action" value="skip" formnovalidate>
          Skip for now
        </button>
        <p class="privacy-note">{ICON_LOCK} We don’t need your exact home address.</p>
      </form>
    </dialog>
    """


def _recalculating_modal(view: DecisionPageView) -> str:
    if not view.recalculating:
        return ""
    place = view.location.display_place or "your new delivery area"
    return f"""
    <div class="recalc-overlay" role="status">
      <div class="recalc-card">
        <div class="spinner" aria-hidden="true"></div>
        <h2>Updating costs for {h(place)}...</h2>
        <p>Rechecking shipping, availability, and total cost for your new delivery area.</p>
      </div>
    </div>
    """

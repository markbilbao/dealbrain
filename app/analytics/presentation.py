"""First-party analytics preference markup. Not an external consent banner."""

from __future__ import annotations


def tracking_preference_notice() -> str:
    """Visible prompt when the shopper has not made an explicit choice."""

    return """
    <aside class="tracking-preference" data-tracking-preference>
      <p>Optional product analytics is off until you allow it. PiqSavi works either way.
      Advertising tracking is not used.</p>
      <div class="tracking-preference-actions">
        <button type="button" class="btn btn-secondary btn-compact"
          data-tracking-choice="essential_only">Keep essential only</button>
        <button type="button" class="btn btn-primary btn-compact"
          data-tracking-choice="analytics_allowed">Allow product analytics</button>
      </div>
      <p class="form-status" data-tracking-status role="status"></p>
    </aside>
    """


def account_analytics_controls() -> str:
    """Account control for changing the choice later. Advertising stays unavailable."""

    return """
    <h2 id="analytics-preference">Optional product analytics</h2>
    <p>Essential storage stays on so PiqSavi can remember this shopping session.
    Optional product analytics is separate. Advertising tracking is not available.</p>
    <p class="form-status" data-tracking-current role="status"></p>
    <div class="tracking-preference-actions">
      <button type="button" class="btn btn-secondary" data-tracking-choice="essential_only">
        Use essential only
      </button>
      <button type="button" class="btn btn-primary" data-tracking-choice="analytics_allowed">
        Allow product analytics
      </button>
    </div>
    """

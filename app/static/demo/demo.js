    const titleInput = document.getElementById("title");
    const analyzeBtn = document.getElementById("analyze");
    const statusEl = document.getElementById("status");
    const resultsEl = document.getElementById("results");

    const titleAInput = document.getElementById("title_a");
    const titleBInput = document.getElementById("title_b");
    const compareBtn = document.getElementById("compare");
    const matchStatusEl = document.getElementById("match-status");
    const matchResultsEl = document.getElementById("match-results");

    const marketplaceQueryInput = document.getElementById("marketplace_q");
    const marketplaceSearchBtn = document.getElementById("marketplace_search");
    const marketplaceStatusEl = document.getElementById("marketplace-status");
    const marketplaceResultsEl = document.getElementById("marketplace-results");

    const dealscoreQueryInput = document.getElementById("dealscore_q");
    const dealscoreSearchBtn = document.getElementById("dealscore_search");
    const dealscoreStatusEl = document.getElementById("dealscore-status");
    const dealscoreResultsEl = document.getElementById("dealscore-results");

    const recommendationQueryInput = document.getElementById("recommendation_q");
    const recommendationSearchBtn = document.getElementById("recommendation_search");
    const recommendationStatusEl = document.getElementById("recommendation-status");
    const recommendationResultsEl = document.getElementById("recommendation-results");

    function showEl(el, html) {
      el.innerHTML = html;
      el.classList.add("visible");
    }

    function clearEl(el) {
      el.innerHTML = "";
      el.classList.remove("visible");
    }

    function formatConfidence(value) {
      return Math.round(Number(value) * 100) + "%";
    }

    function escapeHtml(text) {
      return String(text)
        .replaceAll("&", "&amp;")
        .replaceAll("<", "&lt;")
        .replaceAll(">", "&gt;")
        .replaceAll('"', "&quot;")
        .replaceAll("'", "&#39;");
    }

    function detailMessage(payload) {
      const detail = payload.detail;
      if (typeof detail === "string") return detail;
      if (Array.isArray(detail) && detail.length) {
        return detail.map((d) => d.msg || JSON.stringify(d)).join(" ");
      }
      return "Request failed.";
    }

    function renderParseResults(data) {
      const product = data.canonical_product;
      const badgeClass = data.is_new_product ? "" : "existing";
      const badgeText = data.is_new_product ? "New registry identity" : "Existing registry identity";

      const fields = [
        ["Brand", product.brand],
        ["Family", product.family],
        ["Model", product.model],
        ["Storage", product.storage || "—"],
        ["Color", product.color || "—"],
      ];

      const fieldRows = fields
        .map(([k, v]) => `<tr><th>${k}</th><td>${escapeHtml(String(v))}</td></tr>`)
        .join("");

      const evidenceRows = (data.evidence || [])
        .map(
          (item) => `<tr>
            <td>${escapeHtml(item.field)}</td>
            <td><code>${escapeHtml(item.matched_text)}</code></td>
            <td><code>${escapeHtml(item.rule)}</code></td>
          </tr>`
        )
        .join("");

      resultsEl.innerHTML = `
        <div class="meta">
          <div class="stat">
            <div class="label">Confidence</div>
            <div class="value emerald">${formatConfidence(data.confidence)}</div>
          </div>
          <div class="stat">
            <div class="label">Canonical ID</div>
            <div class="value">${escapeHtml(product.id)}</div>
          </div>
          <div class="stat">
            <div class="label">Registry</div>
            <div class="value"><span class="badge ${badgeClass}">${badgeText}</span></div>
          </div>
        </div>
        <h3 class="section-title">Canonical product</h3>
        <table><tbody>${fieldRows}</tbody></table>
        <h3 class="section-title">Parsing evidence</h3>
        <table>
          <thead><tr><th>Field</th><th>Matched text</th><th>Rule</th></tr></thead>
          <tbody>${evidenceRows || '<tr><td colspan="3">No evidence signals</td></tr>'}</tbody>
        </table>
      `;
      resultsEl.classList.add("visible");
    }

    function matchBadgeClass(matchType, isMatch) {
      if (isMatch) return "";
      if (matchType === "insufficient_information") return "neutral";
      return "danger";
    }

    function renderMatchResults(data) {
      const matchedChips = (data.matched_fields || [])
        .map((f) => `<span class="chip">${escapeHtml(f)}</span>`)
        .join("") || "<span class='chip conflict'>none</span>";

      const conflictChips = (data.conflicts || [])
        .map(
          (c) =>
            `<span class="chip conflict">${escapeHtml(c.field)}: ${escapeHtml(c.value_a)} ≠ ${escapeHtml(c.value_b)}</span>`
        )
        .join("") || "<span class='chip'>none</span>";

      const explanation = (data.explanation || [])
        .map((line) => `<li>${escapeHtml(line)}</li>`)
        .join("");

      matchResultsEl.innerHTML = `
        <div class="meta">
          <div class="stat">
            <div class="label">Classification</div>
            <div class="value">
              <span class="badge ${matchBadgeClass(data.match_type, data.is_match)}">${escapeHtml(data.match_type)}</span>
            </div>
          </div>
          <div class="stat">
            <div class="label">Confidence</div>
            <div class="value emerald">${formatConfidence(data.confidence)}</div>
          </div>
          <div class="stat">
            <div class="label">Is match</div>
            <div class="value">${data.is_match ? "Yes" : "No"}</div>
          </div>
        </div>
        <h3 class="section-title">Matched fields</h3>
        <div class="chip-row">${matchedChips}</div>
        <h3 class="section-title">Conflicting fields</h3>
        <div class="chip-row">${conflictChips}</div>
        <h3 class="section-title">Explanation</h3>
        <ul class="explain">${explanation || "<li>No explanation available.</li>"}</ul>
      `;
      matchResultsEl.classList.add("visible");
    }

    function formatPrice(price, currency) {
      const amount = Number(price);
      if (Number.isNaN(amount)) return "—";
      return `${escapeHtml(currency || "")} ${amount.toLocaleString(undefined, {
        minimumFractionDigits: 2,
        maximumFractionDigits: 2,
      })}`.trim();
    }

    function renderMarketplaceResults(data) {
      const results = data.results || [];
      const marketplaces = [...new Set(results.map((r) => r.marketplace))];

      const rows = results
        .map(
          (item) => `<tr>
            <td><span class="badge">${escapeHtml(item.marketplace)}</span></td>
            <td>${escapeHtml(item.title)}</td>
            <td>${formatPrice(item.price, item.currency)}</td>
            <td>${escapeHtml(item.seller || "—")}</td>
            <td>${item.rating != null ? escapeHtml(String(item.rating)) : "—"}</td>
            <td><a href="${escapeHtml(item.url)}" target="_blank" rel="noopener noreferrer">Open</a></td>
          </tr>`
        )
        .join("");

      marketplaceResultsEl.innerHTML = `
        <div class="meta">
          <div class="stat">
            <div class="label">Query</div>
            <div class="value">${escapeHtml(data.query || "")}</div>
          </div>
          <div class="stat">
            <div class="label">Results</div>
            <div class="value emerald">${results.length}</div>
          </div>
          <div class="stat">
            <div class="label">Marketplaces</div>
            <div class="value">${escapeHtml(marketplaces.join(", ") || "—")}</div>
          </div>
        </div>
        <h3 class="section-title">Listings</h3>
        <table>
          <thead>
            <tr>
              <th>Marketplace</th>
              <th>Title</th>
              <th>Price</th>
              <th>Seller</th>
              <th>Rating</th>
              <th>URL</th>
            </tr>
          </thead>
          <tbody>${rows || '<tr><td colspan="6">No mocked listings matched this query.</td></tr>'}</tbody>
        </table>
      `;
      marketplaceResultsEl.classList.add("visible");
    }

    async function analyze() {
      const title = titleInput.value.trim();
      clearEl(resultsEl);

      if (!title) {
        showEl(statusEl, '<div class="error">Please enter a product listing title.</div>');
        return;
      }

      analyzeBtn.disabled = true;
      showEl(statusEl, '<div class="loading"><span class="spinner" aria-hidden="true"></span> Analyzing listing…</div>');

      try {
        const response = await fetch("/api/v1/intelligence/parse", {
          method: "POST",
          headers: { "Content-Type": "application/json", "Accept": "application/json" },
          body: JSON.stringify({ title }),
        });
        const payload = await response.json().catch(() => ({}));
        if (!response.ok) {
          showEl(statusEl, `<div class="error">${escapeHtml(detailMessage(payload))}</div>`);
          return;
        }
        clearEl(statusEl);
        renderParseResults(payload);
      } catch (err) {
        showEl(statusEl, '<div class="error">Network error. Is the PiqSavi API running?</div>');
      } finally {
        analyzeBtn.disabled = false;
      }
    }

    async function compare() {
      const title_a = titleAInput.value.trim();
      const title_b = titleBInput.value.trim();
      clearEl(matchResultsEl);

      if (!title_a || !title_b) {
        showEl(matchStatusEl, '<div class="error">Please enter both listing titles.</div>');
        return;
      }

      compareBtn.disabled = true;
      showEl(matchStatusEl, '<div class="loading"><span class="spinner" aria-hidden="true"></span> Comparing listings…</div>');

      try {
        const response = await fetch("/api/v1/intelligence/match", {
          method: "POST",
          headers: { "Content-Type": "application/json", "Accept": "application/json" },
          body: JSON.stringify({ title_a, title_b }),
        });
        const payload = await response.json().catch(() => ({}));
        if (!response.ok) {
          showEl(matchStatusEl, `<div class="error">${escapeHtml(detailMessage(payload))}</div>`);
          return;
        }
        clearEl(matchStatusEl);
        renderMatchResults(payload);
      } catch (err) {
        showEl(matchStatusEl, '<div class="error">Network error. Is the PiqSavi API running?</div>');
      } finally {
        compareBtn.disabled = false;
      }
    }

    analyzeBtn.addEventListener("click", analyze);
    titleInput.addEventListener("keydown", (event) => {
      if (event.key === "Enter") analyze();
    });
    compareBtn.addEventListener("click", compare);

    async function searchMarketplaces() {
      const q = marketplaceQueryInput.value.trim();
      clearEl(marketplaceResultsEl);

      if (!q) {
        showEl(marketplaceStatusEl, '<div class="error">Please enter a search query.</div>');
        return;
      }

      marketplaceSearchBtn.disabled = true;
      showEl(
        marketplaceStatusEl,
        '<div class="loading"><span class="spinner" aria-hidden="true"></span> Searching marketplaces…</div>'
      );

      try {
        const response = await fetch(
          `/api/v1/marketplace/search?q=${encodeURIComponent(q)}`,
          { headers: { Accept: "application/json" } }
        );
        const payload = await response.json().catch(() => ({}));
        if (!response.ok) {
          showEl(
            marketplaceStatusEl,
            `<div class="error">${escapeHtml(detailMessage(payload))}</div>`
          );
          return;
        }
        clearEl(marketplaceStatusEl);
        renderMarketplaceResults(payload);
      } catch (err) {
        showEl(
          marketplaceStatusEl,
          '<div class="error">Network error. Is the PiqSavi API running?</div>'
        );
      } finally {
        marketplaceSearchBtn.disabled = false;
      }
    }

    marketplaceSearchBtn.addEventListener("click", searchMarketplaces);
    marketplaceQueryInput.addEventListener("keydown", (event) => {
      if (event.key === "Enter") searchMarketplaces();
    });

    function formatComponentLabel(key) {
      return key.replaceAll("_", " ").replace(" score", "");
    }

    function renderDealScoreResults(data) {
      const results = data.results || [];
      if (!results.length) {
        dealscoreResultsEl.innerHTML =
          '<p class="empty-state">No marketplace listings matched this query.</p>';
        dealscoreResultsEl.classList.add("visible");
        return;
      }

      const cards = results
        .map((item) => {
          const listing = item.listing || {};
          const deal = item.deal_score || {};
          const isRecommended = listing.product_id === data.recommended_listing_id;
          const components = deal.components || {};
          const componentHtml = Object.entries(components)
            .map(
              ([key, value]) => `<div class="component-item">
                <div class="label">${escapeHtml(formatComponentLabel(key))}</div>
                <div class="value">${escapeHtml(String(value))}</div>
              </div>`
            )
            .join("");
          const explanation = (deal.explanation || [])
            .map((line) => `<li>${escapeHtml(line)}</li>`)
            .join("");
          const warnings = (deal.warnings || [])
            .map((line) => `<li>${escapeHtml(line)}</li>`)
            .join("");

          return `<article class="deal-card ${isRecommended ? "recommended" : ""}">
            <div class="deal-card-header">
              <h3 class="deal-card-title">${escapeHtml(listing.title || "Untitled listing")}</h3>
              <div class="deal-meta-row">
                <span class="badge">Rank #${escapeHtml(String(item.rank))}</span>
                ${isRecommended ? '<span class="badge recommended">Recommended</span>' : ""}
                <span class="badge neutral">${escapeHtml(deal.rating || "—")}</span>
                <span class="badge">${escapeHtml(listing.marketplace || "")}</span>
              </div>
            </div>
            <div class="meta">
              <div class="stat">
                <div class="label">PiqScore</div>
                <div class="value emerald">${escapeHtml(String(deal.score ?? "—"))}</div>
              </div>
              <div class="stat">
                <div class="label">Total cost</div>
                <div class="value">${formatPrice(listing.total_cost ?? deal.total_cost, listing.currency)}</div>
              </div>
              <div class="stat">
                <div class="label">Listing price</div>
                <div class="value">${formatPrice(listing.price, listing.currency)}</div>
              </div>
              <div class="stat">
                <div class="label">Shipping</div>
                <div class="value">${
                  listing.shipping_cost == null
                    ? "—"
                    : formatPrice(listing.shipping_cost, listing.currency)
                }</div>
              </div>
            </div>
            <h4 class="section-title">Component breakdown</h4>
            <div class="component-grid">${componentHtml || '<p class="empty-state">No components</p>'}</div>
            <h4 class="section-title">Explanation</h4>
            <ul class="explain">${explanation || "<li>No explanation available.</li>"}</ul>
            <h4 class="section-title">Warnings</h4>
            ${
              warnings
                ? `<ul class="warnings">${warnings}</ul>`
                : '<p class="empty-state">No warnings.</p>'
            }
          </article>`;
        })
        .join("");

      dealscoreResultsEl.innerHTML = `
        <div class="meta">
          <div class="stat">
            <div class="label">Query</div>
            <div class="value">${escapeHtml(data.query || "")}</div>
          </div>
          <div class="stat">
            <div class="label">Currency</div>
            <div class="value">${escapeHtml(data.currency || "—")}</div>
          </div>
          <div class="stat">
            <div class="label">Market avg total</div>
            <div class="value">${formatPrice(data.market_average_total_cost, data.currency)}</div>
          </div>
          <div class="stat">
            <div class="label">Recommended</div>
            <div class="value">${escapeHtml(data.recommended_listing_id || "—")}</div>
          </div>
        </div>
        <h3 class="section-title">Ranked listings</h3>
        ${cards}
      `;
      dealscoreResultsEl.classList.add("visible");
    }

    async function searchDealScore() {
      const q = dealscoreQueryInput.value.trim();
      clearEl(dealscoreResultsEl);

      if (!q) {
        showEl(dealscoreStatusEl, '<div class="error">Please enter a search query.</div>');
        return;
      }

      dealscoreSearchBtn.disabled = true;
      showEl(
        dealscoreStatusEl,
        '<div class="loading"><span class="spinner" aria-hidden="true"></span> Ranking deals…</div>'
      );

      try {
        const response = await fetch(
          `/api/v1/dealscore/search?q=${encodeURIComponent(q)}`,
          { headers: { Accept: "application/json" } }
        );
        const payload = await response.json().catch(() => ({}));
        if (!response.ok) {
          showEl(
            dealscoreStatusEl,
            `<div class="error">${escapeHtml(detailMessage(payload))}</div>`
          );
          return;
        }
        clearEl(dealscoreStatusEl);
        renderDealScoreResults(payload);
      } catch (err) {
        showEl(
          dealscoreStatusEl,
          '<div class="error">Network error. Is the PiqSavi API running?</div>'
        );
      } finally {
        dealscoreSearchBtn.disabled = false;
      }
    }

    dealscoreSearchBtn.addEventListener("click", searchDealScore);
    dealscoreQueryInput.addEventListener("keydown", (event) => {
      if (event.key === "Enter") searchDealScore();
    });

    function decisionBadgeClass(decision) {
      const key = String(decision || "").toLowerCase();
      return `badge decision-${key || "neutral"}`;
    }

    function formatDecisionLabel(decision) {
      const raw = String(decision || "unknown");
      return raw
        .split("_")
        .map((part) => part.charAt(0).toUpperCase() + part.slice(1))
        .join(" ");
    }

    function renderRecommendationResults(data) {
      const rec = data.recommendation || {};
      const ranked = data.ranked_results || [];
      const decision = rec.decision || "insufficient_information";

      if (!ranked.length && !rec.recommended_listing_id) {
        recommendationResultsEl.innerHTML = `
          <div class="meta">
            <div class="stat">
              <div class="label">Decision</div>
              <div class="value">
                <span class="${decisionBadgeClass(decision)}">${escapeHtml(formatDecisionLabel(decision))}</span>
              </div>
            </div>
            <div class="stat">
              <div class="label">Confidence</div>
              <div class="value">${formatConfidence(rec.confidence || 0)}</div>
            </div>
          </div>
          <h3 class="section-title">${escapeHtml(rec.headline || "No recommendation")}</h3>
          <p>${escapeHtml(rec.summary || "No marketplace listings matched this query.")}</p>
          ${
            (rec.warnings || []).length
              ? `<h3 class="section-title">Warnings</h3>
                 <ul class="warnings">${(rec.warnings || [])
                   .map((line) => `<li>${escapeHtml(line)}</li>`)
                   .join("")}</ul>`
              : ""
          }
          <p class="empty-state">No ranked listings to compare.</p>
        `;
        recommendationResultsEl.classList.add("visible");
        return;
      }

      const recommendedListing = ranked.find(
        (item) => (item.listing || {}).product_id === rec.recommended_listing_id
      );
      const recommendedTitle =
        (recommendedListing && recommendedListing.listing && recommendedListing.listing.title) ||
        rec.recommended_listing_id ||
        "—";

      const reasons = (rec.reasoning || [])
        .map((line) => `<li>${escapeHtml(line)}</li>`)
        .join("");
      const tradeoffs = (rec.tradeoffs || [])
        .map((line) => `<li>${escapeHtml(line)}</li>`)
        .join("");
      const warnings = (rec.warnings || [])
        .map((line) => `<li>${escapeHtml(line)}</li>`)
        .join("");
      const alternatives = (rec.alternatives || [])
        .map(
          (alt) => `<li>
            <strong>${escapeHtml(alt.label || "Alternative")}</strong>
            · listing <code>${escapeHtml(alt.listing_id || "")}</code><br />
            ${escapeHtml(alt.reason || "")}
          </li>`
        )
        .join("");

      const comparisonRows = ranked
        .map((item) => {
          const listing = item.listing || {};
          const deal = item.deal_score || {};
          const isRec = listing.product_id === rec.recommended_listing_id;
          return `<tr>
            <td>${escapeHtml(String(item.rank ?? ""))}${isRec ? ' <span class="badge recommended">Rec</span>' : ""}</td>
            <td>${escapeHtml(listing.title || listing.product_id || "—")}</td>
            <td>${escapeHtml(String(deal.score ?? "—"))}</td>
            <td>${formatPrice(listing.total_cost ?? deal.total_cost, listing.currency || data.currency)}</td>
            <td>${escapeHtml(listing.marketplace || "")}</td>
          </tr>`;
        })
        .join("");

      recommendationResultsEl.innerHTML = `
        <div class="meta">
          <div class="stat">
            <div class="label">Decision</div>
            <div class="value">
              <span class="${decisionBadgeClass(decision)}">${escapeHtml(formatDecisionLabel(decision))}</span>
            </div>
          </div>
          <div class="stat">
            <div class="label">Confidence</div>
            <div class="value emerald">${formatConfidence(rec.confidence || 0)}</div>
          </div>
          <div class="stat">
            <div class="label">Recommended listing</div>
            <div class="value">${escapeHtml(String(rec.recommended_listing_id || "—"))}</div>
          </div>
          <div class="stat">
            <div class="label">Currency</div>
            <div class="value">${escapeHtml(data.currency || "—")}</div>
          </div>
        </div>
        <h3 class="section-title">${escapeHtml(rec.headline || "Recommendation")}</h3>
        <p><strong>${escapeHtml(recommendedTitle)}</strong></p>
        <p>${escapeHtml(rec.summary || "")}</p>
        <h3 class="section-title">Main reasons</h3>
        <ul class="reason-list">${reasons || "<li>No reasons available.</li>"}</ul>
        <h3 class="section-title">Tradeoffs</h3>
        ${
          tradeoffs
            ? `<ul class="tradeoff-list">${tradeoffs}</ul>`
            : '<p class="empty-state">No tradeoffs noted.</p>'
        }
        <h3 class="section-title">Warnings</h3>
        ${
          warnings
            ? `<ul class="warnings">${warnings}</ul>`
            : '<p class="empty-state">No warnings.</p>'
        }
        <h3 class="section-title">Alternative options</h3>
        ${
          alternatives
            ? `<ul class="alt-list">${alternatives}</ul>`
            : '<p class="empty-state">No alternatives in this result set.</p>'
        }
        <h3 class="section-title">PiqScore and total-cost comparison</h3>
        <table class="comparison-table">
          <thead>
            <tr>
              <th>Rank</th>
              <th>Listing</th>
              <th>PiqScore</th>
              <th>Total cost</th>
              <th>Marketplace</th>
            </tr>
          </thead>
          <tbody>${comparisonRows || '<tr><td colspan="5">No ranked results.</td></tr>'}</tbody>
        </table>
      `;
      recommendationResultsEl.classList.add("visible");
    }

    async function searchRecommendations() {
      const q = recommendationQueryInput.value.trim();
      clearEl(recommendationResultsEl);

      if (!q) {
        showEl(recommendationStatusEl, '<div class="error">Please enter a search query.</div>');
        return;
      }

      recommendationSearchBtn.disabled = true;
      showEl(
        recommendationStatusEl,
        '<div class="loading"><span class="spinner" aria-hidden="true"></span> Building recommendation…</div>'
      );

      try {
        const response = await fetch(
          `/api/v1/recommendations/search?q=${encodeURIComponent(q)}`,
          { headers: { Accept: "application/json" } }
        );
        const payload = await response.json().catch(() => ({}));
        if (!response.ok) {
          showEl(
            recommendationStatusEl,
            `<div class="error">${escapeHtml(detailMessage(payload))}</div>`
          );
          return;
        }
        clearEl(recommendationStatusEl);
        renderRecommendationResults(payload);
      } catch (err) {
        showEl(
          recommendationStatusEl,
          '<div class="error">Network error. Is the PiqSavi API running?</div>'
        );
      } finally {
        recommendationSearchBtn.disabled = false;
      }
    }

    recommendationSearchBtn.addEventListener("click", searchRecommendations);
    recommendationQueryInput.addEventListener("keydown", (event) => {
      if (event.key === "Enter") searchRecommendations();
    });

    const priceHistoryQueryInput = document.getElementById("price_history_q");
    const priceHistorySearchBtn = document.getElementById("price_history_search");
    const priceHistoryStatusEl = document.getElementById("price-history-status");
    const priceHistoryResultsEl = document.getElementById("price-history-results");

    function formatTrend(trend) {
      const value = (trend || "insufficient_data").toLowerCase();
      const cls =
        value === "rising"
          ? "decision-consider"
          : value === "falling"
            ? "decision-buy"
            : value === "stable"
              ? "neutral"
              : "decision-insufficient_information";
      return `<span class="badge ${cls}">${escapeHtml(value)}</span>`;
    }

    function renderPriceHistoryResults(data) {
      const stats = data.statistics;
      if (!stats) {
        priceHistoryResultsEl.innerHTML =
          '<p class="empty-state">No recorded observations for this query yet.</p>';
        priceHistoryResultsEl.classList.add("visible");
        return;
      }

      const currency = data.currency || "PHP";
      const summaries = (data.marketplace_summaries || [])
        .map(
          (row) => `
          <tr>
            <td>${escapeHtml(row.marketplace)}</td>
            <td>${formatPrice(row.latest_total_cost, currency)}</td>
            <td>${formatPrice(row.lowest_recorded_total_cost, currency)}</td>
            <td>${formatPrice(row.average_total_cost, currency)}</td>
            <td>${row.observation_count}</td>
            <td><span class="badge neutral">${escapeHtml(row.latest_availability)}</span></td>
            <td>${escapeHtml(row.last_observed)}</td>
          </tr>`
        )
        .join("");

      const historyRows = (data.history || [])
        .map(
          (row) => `
          <tr>
            <td>${escapeHtml(row.observed_at)}</td>
            <td>${escapeHtml(row.marketplace)}</td>
            <td><code>${escapeHtml(row.listing_id)}</code></td>
            <td>${formatPrice(row.item_price, row.currency)}</td>
            <td>${formatPrice(row.shipping_cost, row.currency)}</td>
            <td>${formatPrice(row.total_cost, row.currency)}</td>
            <td><span class="badge neutral">${escapeHtml(row.availability)}</span></td>
            <td>${escapeHtml(row.seller_name || "—")}</td>
          </tr>`
        )
        .join("");

      priceHistoryResultsEl.innerHTML = `
        <p class="hint csp-inline-288801cdaa">
          Development history uses mocked observations.
        </p>
        <p class="hint">${escapeHtml(data.disclaimer || "Lowest recorded price in the available PiqSavi history.")}</p>
        <div class="meta">
          <div class="stat">
            <div class="label">Current recorded price</div>
            <div class="value emerald">${formatPrice(stats.current_total_cost, currency)}</div>
          </div>
          <div class="stat">
            <div class="label">Lowest recorded price</div>
            <div class="value">${formatPrice(stats.lowest_recorded_total_cost, currency)}</div>
          </div>
          <div class="stat">
            <div class="label">Highest recorded price</div>
            <div class="value">${formatPrice(stats.highest_recorded_total_cost, currency)}</div>
          </div>
          <div class="stat">
            <div class="label">Average price</div>
            <div class="value">${formatPrice(stats.average_total_cost, currency)}</div>
          </div>
          <div class="stat">
            <div class="label">Median price</div>
            <div class="value">${formatPrice(stats.median_total_cost, currency)}</div>
          </div>
          <div class="stat">
            <div class="label">Trend</div>
            <div class="value">${formatTrend(stats.trend)}</div>
          </div>
          <div class="stat">
            <div class="label">Observation count</div>
            <div class="value">${stats.observation_count}</div>
          </div>
          <div class="stat">
            <div class="label">First observed</div>
            <div class="value">${escapeHtml(stats.first_observed)}</div>
          </div>
          <div class="stat">
            <div class="label">Last updated</div>
            <div class="value">${escapeHtml(stats.last_observed)}</div>
          </div>
        </div>

        <h3 class="section-title">Marketplace comparison</h3>
        <table class="comparison-table">
          <thead>
            <tr>
              <th>Marketplace</th>
              <th>Latest</th>
              <th>Lowest recorded</th>
              <th>Average</th>
              <th>Obs.</th>
              <th>Availability</th>
              <th>Last observed</th>
            </tr>
          </thead>
          <tbody>${summaries || '<tr><td colspan="7">No marketplace summaries.</td></tr>'}</tbody>
        </table>

        <h3 class="section-title">Historical observations</h3>
        <table>
          <thead>
            <tr>
              <th>Observed at</th>
              <th>Marketplace</th>
              <th>Listing</th>
              <th>Item</th>
              <th>Shipping</th>
              <th>Total</th>
              <th>Availability</th>
              <th>Seller</th>
            </tr>
          </thead>
          <tbody>${historyRows || '<tr><td colspan="8">No observations.</td></tr>'}</tbody>
        </table>
      `;
      priceHistoryResultsEl.classList.add("visible");
    }

    async function searchPriceHistory() {
      const q = priceHistoryQueryInput.value.trim();
      clearEl(priceHistoryResultsEl);

      if (!q) {
        showEl(priceHistoryStatusEl, '<div class="error">Please enter a search query.</div>');
        return;
      }

      priceHistorySearchBtn.disabled = true;
      showEl(
        priceHistoryStatusEl,
        '<div class="loading"><span class="spinner" aria-hidden="true"></span> Loading price history…</div>'
      );

      try {
        const response = await fetch(
          `/api/v1/price-history/search?q=${encodeURIComponent(q)}`,
          { headers: { Accept: "application/json" } }
        );
        const payload = await response.json().catch(() => ({}));
        if (!response.ok) {
          showEl(
            priceHistoryStatusEl,
            `<div class="error">${escapeHtml(detailMessage(payload))}</div>`
          );
          return;
        }
        clearEl(priceHistoryStatusEl);
        renderPriceHistoryResults(payload);
      } catch (err) {
        showEl(
          priceHistoryStatusEl,
          '<div class="error">Network error. Is the PiqSavi API running?</div>'
        );
      } finally {
        priceHistorySearchBtn.disabled = false;
      }
    }

    priceHistorySearchBtn.addEventListener("click", searchPriceHistory);
    priceHistoryQueryInput.addEventListener("keydown", (event) => {
      if (event.key === "Enter") searchPriceHistory();
    });

    const collectionQueryInput = document.getElementById("collection_q");
    const collectionShopeeInput = document.getElementById("collection_shopee");
    const collectionLazadaInput = document.getElementById("collection_lazada");
    const collectionRunBtn = document.getElementById("collection_run");
    const collectionRunDueBtn = document.getElementById("collection_run_due");
    const collectionRefreshRunsBtn = document.getElementById("collection_refresh_runs");
    const collectionStatusEl = document.getElementById("collection-status");
    const collectionResultsEl = document.getElementById("collection-results");

    function selectedCollectionMarketplaces() {
      const markets = [];
      if (collectionShopeeInput.checked) markets.push("shopee");
      if (collectionLazadaInput.checked) markets.push("lazada");
      return markets;
    }

    function renderCollectionRun(run) {
      const failures = (run.results || [])
        .flatMap((result) => result.errors || [])
        .map(
          (error) =>
            `<li><strong>${escapeHtml(error.marketplace)}</strong>: ${escapeHtml(error.code)} — ${escapeHtml(error.message)}</li>`
        )
        .join("");

      const listingRows = (run.results || [])
        .flatMap((result) =>
          (result.listings || []).map(
            (row) => `
            <tr>
              <td>${escapeHtml(row.marketplace)}</td>
              <td><code>${escapeHtml(row.product_id)}</code></td>
              <td>${escapeHtml(row.title)}</td>
              <td>${formatPrice(row.price, row.currency)}</td>
              <td><span class="badge neutral">${escapeHtml(row.availability)}</span></td>
              <td>${row.is_duplicate ? "yes" : "no"}</td>
            </tr>`
          )
        )
        .join("");

      const warningList = (run.warnings || [])
        .map((w) => `<li>${escapeHtml(w)}</li>`)
        .join("");

      return `
        <p class="hint csp-inline-288801cdaa">
          Development collection uses mocked marketplace data. No live marketplace APIs are called.
        </p>
        <div class="meta">
          <div class="stat">
            <div class="label">Status</div>
            <div class="value"><span class="badge neutral">${escapeHtml(run.status)}</span></div>
          </div>
          <div class="stat">
            <div class="label">Run id</div>
            <div class="value"><code>${escapeHtml(run.run_id)}</code></div>
          </div>
          <div class="stat">
            <div class="label">Collected</div>
            <div class="value">${run.collected_count}</div>
          </div>
          <div class="stat">
            <div class="label">Snapshots recorded</div>
            <div class="value emerald">${run.stored_snapshot_count}</div>
          </div>
          <div class="stat">
            <div class="label">Skipped</div>
            <div class="value">${run.skipped_count}</div>
          </div>
          <div class="stat">
            <div class="label">Failures</div>
            <div class="value">${run.failure_count}</div>
          </div>
          <div class="stat">
            <div class="label">Marketplaces attempted</div>
            <div class="value">${escapeHtml((run.marketplaces_attempted || []).join(", ") || "—")}</div>
          </div>
          <div class="stat">
            <div class="label">Marketplaces completed</div>
            <div class="value">${escapeHtml((run.marketplaces_completed || []).join(", ") || "—")}</div>
          </div>
        </div>
        <h3 class="section-title">Listings collected</h3>
        <table>
          <thead>
            <tr>
              <th>Marketplace</th>
              <th>Listing</th>
              <th>Title</th>
              <th>Price</th>
              <th>Availability</th>
              <th>Duplicate</th>
            </tr>
          </thead>
          <tbody>${listingRows || '<tr><td colspan="6">No listings collected.</td></tr>'}</tbody>
        </table>
        <h3 class="section-title">Failures and warnings</h3>
        ${
          failures
            ? `<ul class="warnings">${failures}</ul>`
            : '<p class="empty-state">No marketplace failures.</p>'
        }
        ${
          warningList
            ? `<ul class="warnings">${warningList}</ul>`
            : '<p class="empty-state">No warnings.</p>'
        }
      `;
    }

    function renderCollectionRuns(runs) {
      if (!runs.length) {
        return '<p class="empty-state">No recent collection runs.</p>';
      }
      const rows = runs
        .map(
          (run) => `
          <tr>
            <td><code>${escapeHtml(run.run_id)}</code></td>
            <td>${escapeHtml(run.query)}</td>
            <td><span class="badge neutral">${escapeHtml(run.status)}</span></td>
            <td>${run.collected_count}</td>
            <td>${run.stored_snapshot_count}</td>
            <td>${run.failure_count}</td>
            <td>${escapeHtml(run.started_at || "—")}</td>
          </tr>`
        )
        .join("");
      return `
        <h3 class="section-title">Recent collection runs</h3>
        <table>
          <thead>
            <tr>
              <th>Run</th>
              <th>Query</th>
              <th>Status</th>
              <th>Collected</th>
              <th>Snapshots</th>
              <th>Failures</th>
              <th>Started</th>
            </tr>
          </thead>
          <tbody>${rows}</tbody>
        </table>
      `;
    }

    async function runCollection() {
      const q = collectionQueryInput.value.trim();
      const marketplaces = selectedCollectionMarketplaces();
      clearEl(collectionResultsEl);

      if (!q) {
        showEl(collectionStatusEl, '<div class="error">Please enter a product query.</div>');
        return;
      }
      if (!marketplaces.length) {
        showEl(collectionStatusEl, '<div class="error">Select at least one marketplace.</div>');
        return;
      }

      collectionRunBtn.disabled = true;
      showEl(
        collectionStatusEl,
        '<div class="loading"><span class="spinner" aria-hidden="true"></span> Running mock collection…</div>'
      );

      try {
        const response = await fetch("/api/v1/collections/run", {
          method: "POST",
          headers: {
            Accept: "application/json",
            "Content-Type": "application/json",
          },
          body: JSON.stringify({ query: q, marketplaces }),
        });
        const payload = await response.json().catch(() => ({}));
        if (!response.ok) {
          showEl(
            collectionStatusEl,
            `<div class="error">${escapeHtml(detailMessage(payload))}</div>`
          );
          return;
        }
        clearEl(collectionStatusEl);
        collectionResultsEl.innerHTML = renderCollectionRun(payload);
        collectionResultsEl.classList.add("visible");
      } catch (err) {
        showEl(
          collectionStatusEl,
          '<div class="error">Network error. Is the PiqSavi API running?</div>'
        );
      } finally {
        collectionRunBtn.disabled = false;
      }
    }

    async function runDueCollectionJobs() {
      collectionRunDueBtn.disabled = true;
      showEl(
        collectionStatusEl,
        '<div class="loading"><span class="spinner" aria-hidden="true"></span> Running due jobs…</div>'
      );
      try {
        const response = await fetch("/api/v1/collections/jobs/run-due", {
          method: "POST",
          headers: { Accept: "application/json" },
        });
        const payload = await response.json().catch(() => ({}));
        if (!response.ok) {
          showEl(
            collectionStatusEl,
            `<div class="error">${escapeHtml(detailMessage(payload))}</div>`
          );
          return;
        }
        clearEl(collectionStatusEl);
        const runsHtml = (payload.runs || []).map(renderCollectionRun).join("<hr />");
        collectionResultsEl.innerHTML = `
          <p class="hint">Jobs executed: ${payload.jobs_executed || 0}</p>
          ${runsHtml || '<p class="empty-state">No due jobs were executed.</p>'}
        `;
        collectionResultsEl.classList.add("visible");
      } catch (err) {
        showEl(
          collectionStatusEl,
          '<div class="error">Network error. Is the PiqSavi API running?</div>'
        );
      } finally {
        collectionRunDueBtn.disabled = false;
      }
    }

    async function refreshCollectionRuns() {
      collectionRefreshRunsBtn.disabled = true;
      showEl(
        collectionStatusEl,
        '<div class="loading"><span class="spinner" aria-hidden="true"></span> Loading recent runs…</div>'
      );
      try {
        const response = await fetch("/api/v1/collections/runs?limit=10", {
          headers: { Accept: "application/json" },
        });
        const payload = await response.json().catch(() => ({}));
        if (!response.ok) {
          showEl(
            collectionStatusEl,
            `<div class="error">${escapeHtml(detailMessage(payload))}</div>`
          );
          return;
        }
        clearEl(collectionStatusEl);
        collectionResultsEl.innerHTML = renderCollectionRuns(payload.runs || []);
        collectionResultsEl.classList.add("visible");
      } catch (err) {
        showEl(
          collectionStatusEl,
          '<div class="error">Network error. Is the PiqSavi API running?</div>'
        );
      } finally {
        collectionRefreshRunsBtn.disabled = false;
      }
    }

    collectionRunBtn.addEventListener("click", runCollection);
    collectionRunDueBtn.addEventListener("click", runDueCollectionJobs);
    collectionRefreshRunsBtn.addEventListener("click", refreshCollectionRuns);
    collectionQueryInput.addEventListener("keydown", (event) => {
      if (event.key === "Enter") runCollection();
    });

    const opsRefreshBtn = document.getElementById("ops_refresh");
    const opsRunDueBtn = document.getElementById("ops_run_due");
    const opsSeedJobBtn = document.getElementById("ops_seed_job");
    const opsHealthEl = document.getElementById("ops-health");
    const opsSummaryEl = document.getElementById("ops-summary");
    const opsStatusEl = document.getElementById("ops-status");
    const opsJobsEl = document.getElementById("ops-jobs");
    const opsRunsEl = document.getElementById("ops-runs");

    function opsStat(label, value, emerald) {
      return `<div class="stat"><div class="label">${label}</div><div class="value${emerald ? " emerald" : ""}">${value}</div></div>`;
    }

    function formatTs(value) {
      if (!value) return "—";
      try {
        return new Date(value).toLocaleString();
      } catch {
        return value;
      }
    }

    function renderOpsJobs(jobs) {
      if (!jobs.length) {
        return '<p class="empty-state">No collection jobs yet. Seed a demo job to begin.</p>';
      }
      const rows = jobs.map((job) => {
        const pauseLabel = job.paused ? "Resume" : "Pause";
        const pauseAction = job.paused ? "resume" : "pause";
        return `<tr>
          <td><code>${job.job_id.slice(0, 14)}…</code><div class="hint csp-inline-183dbd7c5b">${job.name}</div></td>
          <td><span class="badge">${job.status}</span></td>
          <td>${formatTs(job.next_run_at)}</td>
          <td>${formatTs(job.last_run_at)}</td>
          <td>${job.consecutive_failure_count}</td>
          <td>
            <div class="row csp-inline-dd57b80b89">
              <button type="button" data-ops-run="${job.job_id}" class="csp-inline-6b9363fbab">Run</button>
              <button type="button" data-ops-toggle="${job.job_id}" data-ops-action="${pauseAction}" class="csp-inline-b927bf8e66">${pauseLabel}</button>
            </div>
          </td>
        </tr>`;
      }).join("");
      return `<table>
        <thead><tr><th>Job</th><th>Status</th><th>Next run</th><th>Last run</th><th>Failures</th><th>Actions</th></tr></thead>
        <tbody>${rows}</tbody>
      </table>`;
    }

    function renderOpsRuns(runs) {
      if (!runs.length) {
        return '<p class="empty-state">No recent collection runs.</p>';
      }
      const rows = runs.map((run) => `<tr>
        <td><code>${run.run_id.slice(0, 14)}…</code></td>
        <td>${run.trigger}</td>
        <td><span class="badge">${run.status}</span></td>
        <td>${run.collected_count}</td>
        <td>${run.stored_snapshot_count}</td>
        <td>${run.failure_count}</td>
        <td>${run.duration_ms == null ? "—" : run.duration_ms + " ms"}</td>
      </tr>`).join("");
      return `<table>
        <thead><tr><th>Run</th><th>Trigger</th><th>Status</th><th>Collected</th><th>Stored</th><th>Failures</th><th>Duration</th></tr></thead>
        <tbody>${rows}</tbody>
      </table>`;
    }

    async function refreshCollectionOps() {
      opsRefreshBtn.disabled = true;
      showEl(
        opsStatusEl,
        '<div class="loading"><span class="spinner" aria-hidden="true"></span> Loading collection operations…</div>'
      );
      try {
        const [statusRes, healthRes, readyRes, jobsRes, runsRes] = await Promise.all([
          fetch("/api/v1/collection-operations/status"),
          fetch("/api/v1/collection-operations/health"),
          fetch("/api/v1/collection-operations/readiness"),
          fetch("/api/v1/collection-operations/jobs"),
          fetch("/api/v1/collection-operations/runs?limit=10"),
        ]);
        if (![statusRes, healthRes, readyRes, jobsRes, runsRes].every((r) => r.ok)) {
          throw new Error("One or more collection-operations requests failed.");
        }
        const status = await statusRes.json();
        const health = await healthRes.json();
        const readiness = await readyRes.json();
        const jobs = (await jobsRes.json()).jobs || [];
        const runs = (await runsRes.json()).runs || [];

        opsHealthEl.innerHTML = [
          opsStat("Health", health.running ? "UP" : "DOWN", health.running),
          opsStat("Readiness", readiness.ready ? "READY" : "NOT READY", readiness.ready),
          opsStat("Scheduler", status.scheduler_status || "—"),
        ].join("");

        opsSummaryEl.innerHTML = [
          opsStat("Total jobs", status.total_jobs),
          opsStat("Enabled", status.enabled_jobs, true),
          opsStat("Paused", status.paused_jobs),
          opsStat("Due now", status.jobs_currently_due),
          opsStat("Recent failures", status.jobs_with_recent_failures),
          opsStat("Snapshots", status.total_snapshots_collected, true),
        ].join("");

        opsJobsEl.innerHTML = renderOpsJobs(jobs);
        opsRunsEl.innerHTML = renderOpsRuns(runs);
        clearEl(opsStatusEl);
      } catch (error) {
        showEl(opsStatusEl, `<div class="error">${error.message || error}</div>`);
      } finally {
        opsRefreshBtn.disabled = false;
      }
    }

    async function seedOpsJob() {
      opsSeedJobBtn.disabled = true;
      showEl(
        opsStatusEl,
        '<div class="loading"><span class="spinner" aria-hidden="true"></span> Seeding demo job…</div>'
      );
      try {
        const response = await fetch("/api/v1/collection-operations/jobs", {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify({
            name: "Demo iPhone watch",
            query: "iPhone 17 Pro Max",
            marketplaces: ["shopee", "lazada"],
            interval_minutes: 60,
            enabled: true,
          }),
        });
        if (!response.ok) {
          const detail = await response.json().catch(() => ({}));
          throw new Error(detail.detail || "Failed to seed demo job.");
        }
        clearEl(opsStatusEl);
        await refreshCollectionOps();
      } catch (error) {
        showEl(opsStatusEl, `<div class="error">${error.message || error}</div>`);
      } finally {
        opsSeedJobBtn.disabled = false;
      }
    }

    async function runOpsDueJobs() {
      opsRunDueBtn.disabled = true;
      showEl(
        opsStatusEl,
        '<div class="loading"><span class="spinner" aria-hidden="true"></span> Running due jobs…</div>'
      );
      try {
        const response = await fetch("/api/v1/collection-operations/run-due", { method: "POST" });
        if (!response.ok) {
          throw new Error("Failed to run due jobs.");
        }
        const payload = await response.json();
        showEl(
          opsStatusEl,
          `<div class="hint csp-inline-4fde948ccd">Executed ${payload.jobs_executed} due job(s).</div>`
        );
        await refreshCollectionOps();
      } catch (error) {
        showEl(opsStatusEl, `<div class="error">${error.message || error}</div>`);
      } finally {
        opsRunDueBtn.disabled = false;
      }
    }

    document.getElementById("ops-jobs").addEventListener("click", async (event) => {
      const runBtn = event.target.closest("[data-ops-run]");
      const toggleBtn = event.target.closest("[data-ops-toggle]");
      if (runBtn) {
        const jobId = runBtn.getAttribute("data-ops-run");
        runBtn.disabled = true;
        try {
          const response = await fetch(`/api/v1/collection-operations/jobs/${encodeURIComponent(jobId)}/run`, {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify({}),
          });
          if (!response.ok) {
            const detail = await response.json().catch(() => ({}));
            throw new Error(detail.detail || "Manual run failed.");
          }
          await refreshCollectionOps();
        } catch (error) {
          showEl(opsStatusEl, `<div class="error">${error.message || error}</div>`);
        } finally {
          runBtn.disabled = false;
        }
      }
      if (toggleBtn) {
        const jobId = toggleBtn.getAttribute("data-ops-toggle");
        const action = toggleBtn.getAttribute("data-ops-action");
        toggleBtn.disabled = true;
        try {
          const response = await fetch(
            `/api/v1/collection-operations/jobs/${encodeURIComponent(jobId)}/${action}`,
            { method: "POST" }
          );
          if (!response.ok) {
            const detail = await response.json().catch(() => ({}));
            throw new Error(detail.detail || `Failed to ${action} job.`);
          }
          await refreshCollectionOps();
        } catch (error) {
          showEl(opsStatusEl, `<div class="error">${error.message || error}</div>`);
        } finally {
          toggleBtn.disabled = false;
        }
      }
    });

    opsRefreshBtn.addEventListener("click", refreshCollectionOps);
    opsRunDueBtn.addEventListener("click", runOpsDueJobs);
    opsSeedJobBtn.addEventListener("click", seedOpsJob);
    refreshCollectionOps();

    const wlRefreshBtn = document.getElementById("wl_refresh");
    const wlSeedBtn = document.getElementById("wl_seed");
    const wlCheckBtn = document.getElementById("wl_check");
    const wlSummaryEl = document.getElementById("wl-summary");
    const wlStatusEl = document.getElementById("wl-status");
    const wlListsEl = document.getElementById("wl-lists");
    const wlItemsEl = document.getElementById("wl-items");
    const wlAlertsEl = document.getElementById("wl-alerts");
    const wlAuthHintEl = document.getElementById("wl-auth-hint");
    const wlPauseBtn = document.getElementById("wl_pause");
    const wlResumeBtn = document.getElementById("wl_resume");
    const wlArchiveBtn = document.getElementById("wl_archive");
    const wlAddItemBtn = document.getElementById("wl_add_item");
    const wlAddProductIdInput = document.getElementById("wl_add_product_id");
    const wlAddTargetPriceInput = document.getElementById("wl_add_target_price");
    const wlPreferredSellersInput = document.getElementById("wl_preferred_sellers");
    const wlPreferredMarketplacesInput = document.getElementById("wl_preferred_marketplaces");
    const wlSavePreferencesBtn = document.getElementById("wl_save_preferences");
    const WL_DEMO_PRODUCT_ID = "00000000-0000-4000-8000-000000000017";
    let wlActiveId = null;

    function wlAuthHeaders() {
      const headers = { "Content-Type": "application/json" };
      if (typeof upAccessToken !== "undefined" && upAccessToken) {
        headers["Authorization"] = `Bearer ${upAccessToken}`;
      }
      return headers;
    }

    function wlUpdateAuthHint() {
      if (typeof upAccessToken !== "undefined" && upAccessToken) {
        wlAuthHintEl.innerHTML = `<span class="csp-inline-4fde948ccd">Authenticated as ${escapeHtml(upUserId || "")} — watchlists persist for this account.</span>`;
      } else {
        wlAuthHintEl.innerHTML = `Not logged in — <strong>log in via the User Platform panel below</strong> for persistent, owner-scoped watchlists. Sprint 19 requires a Bearer token by default (<code>WATCHLISTS_REQUIRE_AUTH</code>); anonymous requests will be rejected with 401 until you log in.`;
      }
    }

    function wlStat(label, value, emerald) {
      return `<div class="stat"><div class="label">${label}</div><div class="value${emerald ? " emerald" : ""}">${value}</div></div>`;
    }

    function formatMoney(value, currency) {
      if (value == null) return "—";
      const cur = currency || "PHP";
      return `${cur} ${Number(value).toLocaleString(undefined, { minimumFractionDigits: 2, maximumFractionDigits: 2 })}`;
    }

    function renderWatchlists(lists) {
      if (!lists.length) {
        return '<p class="empty-state">No watchlists yet. Seed a demo watchlist to begin.</p>';
      }
      const rows = lists.map((wl) => {
        const active = wl.watchlist_id === wlActiveId ? " class=\"csp-inline-c79496a04a\"" : "";
        return `<tr${active}>
          <td><button type="button" data-wl-select="${wl.watchlist_id}" class="csp-inline-a48ad02acf">${escapeHtml(wl.name)}</button>
            <div class="hint csp-inline-183dbd7c5b"><code>${wl.watchlist_id.slice(0, 12)}…</code></div></td>
          <td><span class="badge">${wl.enabled ? "enabled" : "disabled"}</span></td>
          <td>${wl.item_count}</td>
          <td>${formatTs(wl.updated_at)}</td>
        </tr>`;
      }).join("");
      return `<table>
        <thead><tr><th>Watchlist</th><th>Status</th><th>Items</th><th>Updated</th></tr></thead>
        <tbody>${rows}</tbody>
      </table>`;
    }

    function renderWatchlistItems(items) {
      if (!items.length) {
        return '<p class="empty-state">No tracked products on this watchlist.</p>';
      }
      const rows = items.map((item) => `<tr>
        <td>${escapeHtml(item.product_label || item.canonical_product_id.slice(0, 12) + "…")}
          <div class="hint csp-inline-183dbd7c5b">Target ${formatMoney(item.target_price, item.currency)}</div></td>
        <td>${formatMoney(item.current_price, item.observed_currency || item.currency)}</td>
        <td>${formatMoney(item.historical_low, item.observed_currency || item.currency)}</td>
        <td>${item.dealscore == null ? "—" : Number(item.dealscore).toFixed(1)}</td>
        <td>${item.observation_count || 0}</td>
      </tr>`).join("");
      return `<table>
        <thead><tr><th>Product</th><th>Current</th><th>Hist. low</th><th>PiqScore</th><th>Obs.</th></tr></thead>
        <tbody>${rows}</tbody>
      </table>`;
    }

    function renderWatchlistAlerts(alerts) {
      if (!alerts.length) {
        return '<p class="empty-state">No alerts yet. Click Check Alerts after seeding price history.</p>';
      }
      const rows = alerts.map((alert) => `<tr>
        <td><span class="badge">${escapeHtml(alert.alert_type)}</span></td>
        <td>${escapeHtml(alert.message)}</td>
        <td><span class="badge">${escapeHtml(alert.status)}</span></td>
        <td>${formatTs(alert.created_at)}</td>
      </tr>`).join("");
      return `<table>
        <thead><tr><th>Type</th><th>Message</th><th>Status</th><th>Created</th></tr></thead>
        <tbody>${rows}</tbody>
      </table>`;
    }

    async function ensureDemoPriceHistory() {
      await fetch("/api/v1/price-history/search?q=" + encodeURIComponent("iPhone 17 Pro Max"), {
        headers: { Accept: "application/json" },
      });
    }

    async function refreshWatchlists() {
      wlUpdateAuthHint();
      wlRefreshBtn.disabled = true;
      showEl(
        wlStatusEl,
        '<div class="loading"><span class="spinner" aria-hidden="true"></span> Loading watchlists…</div>'
      );
      try {
        const [listsRes, alertsRes] = await Promise.all([
          fetch("/api/v1/watchlists", { headers: wlAuthHeaders() }),
          fetch("/api/v1/alerts?limit=20"),
        ]);
        if (listsRes.status === 401) {
          wlListsEl.innerHTML = "";
          wlItemsEl.innerHTML = "";
          wlAlertsEl.innerHTML = "";
          wlSummaryEl.innerHTML = "";
          showEl(
            wlStatusEl,
            '<div class="error">Authentication required — log in via the User Platform panel below, then click Refresh again.</div>'
          );
          return;
        }
        if (!listsRes.ok || !alertsRes.ok) {
          throw new Error("Failed to load watchlists or alerts.");
        }
        const lists = (await listsRes.json()).watchlists || [];
        const alerts = (await alertsRes.json()).alerts || [];
        if (!wlActiveId && lists.length) {
          wlActiveId = lists[0].watchlist_id;
        }
        let items = [];
        let activeWatchlist = null;
        if (wlActiveId) {
          const itemsRes = await fetch(`/api/v1/watchlists/${encodeURIComponent(wlActiveId)}/items`, {
            headers: wlAuthHeaders(),
          });
          if (itemsRes.ok) {
            items = (await itemsRes.json()).items || [];
          }
          activeWatchlist = lists.find((wl) => wl.watchlist_id === wlActiveId) || null;
        }
        wlSummaryEl.innerHTML = [
          wlStat("Watchlists", lists.length, true),
          wlStat("Tracked", items.length),
          wlStat("Alerts", alerts.length, alerts.length > 0),
          wlStat("Active status", activeWatchlist ? activeWatchlist.status : "—"),
        ].join("");
        wlListsEl.innerHTML = renderWatchlists(lists);
        wlItemsEl.innerHTML = renderWatchlistItems(items);
        wlAlertsEl.innerHTML = renderWatchlistAlerts(alerts);
        if (activeWatchlist) {
          wlPreferredSellersInput.value = (activeWatchlist.preferred_sellers || []).join(", ");
          wlPreferredMarketplacesInput.value = (activeWatchlist.preferred_marketplaces || []).join(", ");
        }
        clearEl(wlStatusEl);
      } catch (error) {
        showEl(wlStatusEl, `<div class="error">${error.message || error}</div>`);
      } finally {
        wlRefreshBtn.disabled = false;
      }
    }

    async function seedWatchlist() {
      wlSeedBtn.disabled = true;
      showEl(
        wlStatusEl,
        '<div class="loading"><span class="spinner" aria-hidden="true"></span> Seeding demo watchlist…</div>'
      );
      try {
        await ensureDemoPriceHistory();
        const created = await fetch("/api/v1/watchlists", {
          method: "POST",
          headers: wlAuthHeaders(),
          body: JSON.stringify({
            name: "Demo phone watchlist",
            owner_id: "demo-user",
            description: "iPhone 17 Pro Max price alerts",
            enabled: true,
          }),
        });
        if (!created.ok) {
          const detail = await created.json().catch(() => ({}));
          throw new Error(
            created.status === 401
              ? "Authentication required — log in via the User Platform panel below."
              : detail.detail || "Failed to create watchlist."
          );
        }
        const watchlist = await created.json();
        wlActiveId = watchlist.watchlist_id;
        const itemRes = await fetch(
          `/api/v1/watchlists/${encodeURIComponent(watchlist.watchlist_id)}/items`,
          {
            method: "POST",
            headers: wlAuthHeaders(),
            body: JSON.stringify({
              canonical_product_id: WL_DEMO_PRODUCT_ID,
              product_label: "iPhone 17 Pro Max 256GB",
              target_price: 74000,
              currency: "PHP",
              search_query: "iPhone 17 Pro Max",
              last_known_price: 76000,
              last_known_dealscore: 70,
              last_historical_low: 73990,
            }),
          }
        );
        if (!itemRes.ok) {
          const detail = await itemRes.json().catch(() => ({}));
          throw new Error(detail.detail || "Failed to add watchlist item.");
        }
        clearEl(wlStatusEl);
        await refreshWatchlists();
      } catch (error) {
        showEl(wlStatusEl, `<div class="error">${error.message || error}</div>`);
      } finally {
        wlSeedBtn.disabled = false;
      }
    }

    async function checkWatchlistAlerts() {
      wlCheckBtn.disabled = true;
      showEl(
        wlStatusEl,
        '<div class="loading"><span class="spinner" aria-hidden="true"></span> Checking alerts…</div>'
      );
      try {
        await ensureDemoPriceHistory();
        const url = wlActiveId
          ? `/api/v1/watchlists/${encodeURIComponent(wlActiveId)}/check-alerts`
          : "/api/v1/watchlists/check-alerts";
        const response = await fetch(url, { method: "POST", headers: wlAuthHeaders() });
        if (!response.ok) {
          const detail = await response.json().catch(() => ({}));
          throw new Error(
            response.status === 401
              ? "Authentication required — log in via the User Platform panel below."
              : detail.detail || "Alert check failed."
          );
        }
        const payload = await response.json();
        showEl(
          wlStatusEl,
          `<div class="hint csp-inline-4fde948ccd">
            Checked ${payload.items_checked} item(s) · created ${payload.alerts_count} alert(s)
            (notifications queued, not sent).
          </div>`
        );
        await refreshWatchlists();
      } catch (error) {
        showEl(wlStatusEl, `<div class="error">${error.message || error}</div>`);
      } finally {
        wlCheckBtn.disabled = false;
      }
    }

    async function wlLifecycleAction(action) {
      if (!wlActiveId) {
        showEl(wlStatusEl, '<div class="error">Select or seed a watchlist first.</div>');
        return;
      }
      showEl(
        wlStatusEl,
        `<div class="loading"><span class="spinner" aria-hidden="true"></span> ${action[0].toUpperCase()}${action.slice(1)}ing watchlist…</div>`
      );
      try {
        const response = await fetch(
          `/api/v1/watchlists/${encodeURIComponent(wlActiveId)}/${action}`,
          { method: "POST", headers: wlAuthHeaders() }
        );
        const body = await response.json().catch(() => ({}));
        if (!response.ok) {
          throw new Error(
            response.status === 401
              ? "Authentication required — log in via the User Platform panel below."
              : body.detail || `Failed to ${action} watchlist.`
          );
        }
        showEl(
          wlStatusEl,
          `<div class="hint csp-inline-4fde948ccd">Watchlist now ${escapeHtml(body.status)}.</div>`
        );
        await refreshWatchlists();
      } catch (error) {
        showEl(wlStatusEl, `<div class="error">${error.message || error}</div>`);
      }
    }

    async function wlAddItemToActive() {
      if (!wlActiveId) {
        showEl(wlStatusEl, '<div class="error">Select or seed a watchlist first.</div>');
        return;
      }
      wlAddItemBtn.disabled = true;
      showEl(
        wlStatusEl,
        '<div class="loading"><span class="spinner" aria-hidden="true"></span> Adding item…</div>'
      );
      try {
        const productId = wlAddProductIdInput.value.trim();
        const targetPriceRaw = wlAddTargetPriceInput.value.trim();
        const targetPrice = targetPriceRaw === "" ? null : Number(targetPriceRaw);
        if (!productId) throw new Error("Product ID is required.");
        const response = await fetch(
          `/api/v1/watchlists/${encodeURIComponent(wlActiveId)}/items`,
          {
            method: "POST",
            headers: wlAuthHeaders(),
            body: JSON.stringify({
              canonical_product_id: productId,
              target_price: targetPrice != null && Number.isFinite(targetPrice) ? targetPrice : null,
              currency: "PHP",
            }),
          }
        );
        const body = await response.json().catch(() => ({}));
        if (!response.ok) {
          throw new Error(
            response.status === 401
              ? "Authentication required — log in via the User Platform panel below."
              : body.detail || "Failed to add item."
          );
        }
        clearEl(wlStatusEl);
        await refreshWatchlists();
      } catch (error) {
        showEl(wlStatusEl, `<div class="error">${error.message || error}</div>`);
      } finally {
        wlAddItemBtn.disabled = false;
      }
    }

    async function wlSavePreferredSellersAndMarketplaces() {
      if (!wlActiveId) {
        showEl(wlStatusEl, '<div class="error">Select or seed a watchlist first.</div>');
        return;
      }
      wlSavePreferencesBtn.disabled = true;
      showEl(
        wlStatusEl,
        '<div class="loading"><span class="spinner" aria-hidden="true"></span> Saving preferences…</div>'
      );
      try {
        const sellers = wlPreferredSellersInput.value
          .split(",").map((s) => s.trim()).filter(Boolean);
        const marketplaces = wlPreferredMarketplacesInput.value
          .split(",").map((s) => s.trim()).filter(Boolean);
        const [sellersRes, marketplacesRes] = await Promise.all([
          fetch(`/api/v1/watchlists/${encodeURIComponent(wlActiveId)}/preferred-sellers`, {
            method: "PUT",
            headers: wlAuthHeaders(),
            body: JSON.stringify({ sellers }),
          }),
          fetch(`/api/v1/watchlists/${encodeURIComponent(wlActiveId)}/preferred-marketplaces`, {
            method: "PUT",
            headers: wlAuthHeaders(),
            body: JSON.stringify({ marketplaces }),
          }),
        ]);
        if (!sellersRes.ok || !marketplacesRes.ok) {
          const detail = await (sellersRes.ok ? marketplacesRes : sellersRes).json().catch(() => ({}));
          throw new Error(
            sellersRes.status === 401 || marketplacesRes.status === 401
              ? "Authentication required — log in via the User Platform panel below."
              : detail.detail || "Failed to save preferences."
          );
        }
        showEl(
          wlStatusEl,
          '<div class="hint csp-inline-4fde948ccd">Preferred sellers/marketplaces saved.</div>'
        );
        await refreshWatchlists();
      } catch (error) {
        showEl(wlStatusEl, `<div class="error">${error.message || error}</div>`);
      } finally {
        wlSavePreferencesBtn.disabled = false;
      }
    }

    document.getElementById("wl-lists").addEventListener("click", async (event) => {
      const btn = event.target.closest("[data-wl-select]");
      if (!btn) return;
      wlActiveId = btn.getAttribute("data-wl-select");
      await refreshWatchlists();
    });

    wlRefreshBtn.addEventListener("click", refreshWatchlists);
    wlSeedBtn.addEventListener("click", seedWatchlist);
    wlCheckBtn.addEventListener("click", checkWatchlistAlerts);
    wlPauseBtn.addEventListener("click", () => wlLifecycleAction("pause"));
    wlResumeBtn.addEventListener("click", () => wlLifecycleAction("resume"));
    wlArchiveBtn.addEventListener("click", () => wlLifecycleAction("archive"));
    wlAddItemBtn.addEventListener("click", wlAddItemToActive);
    wlSavePreferencesBtn.addEventListener("click", wlSavePreferredSellersAndMarketplaces);
    wlUpdateAuthHint();
    refreshWatchlists();

    // ================================================================
    // Sprint 19 — Alert Rules & Evaluation
    // ================================================================
    const arAuthHintEl = document.getElementById("ar-auth-hint");
    const arRefreshBtn = document.getElementById("ar_refresh");
    const arEvaluateAllBtn = document.getElementById("ar_evaluate_all");
    const arEventsBtn = document.getElementById("ar_events");
    const arNameInput = document.getElementById("ar_name");
    const arConditionTypeSelect = document.getElementById("ar_condition_type");
    const arThresholdValueInput = document.getElementById("ar_threshold_value");
    const arThresholdPercentInput = document.getElementById("ar_threshold_percent");
    const arComparisonSelect = document.getElementById("ar_comparison");
    const arWatchlistIdInput = document.getElementById("ar_watchlist_id");
    const arItemIdInput = document.getElementById("ar_item_id");
    const arCreateBtn = document.getElementById("ar_create");
    const arStatusEl = document.getElementById("ar-status");
    const arRulesEl = document.getElementById("ar-rules");
    const arEvaluationEl = document.getElementById("ar-evaluation");
    const arEventsEl = document.getElementById("ar-events");
    const arScenarioStatusEl = document.getElementById("ar-scenario-status");
    const arScenarioResultEl = document.getElementById("ar-scenario-result");

    function arAuthHeaders() {
      const headers = { "Content-Type": "application/json" };
      if (typeof upAccessToken !== "undefined" && upAccessToken) {
        headers["Authorization"] = `Bearer ${upAccessToken}`;
      }
      return headers;
    }

    function arUpdateAuthHint() {
      if (typeof upAccessToken !== "undefined" && upAccessToken) {
        arAuthHintEl.innerHTML = `<span class="csp-inline-4fde948ccd">Authenticated as ${escapeHtml(upUserId || "")}.</span>`;
      } else {
        arAuthHintEl.innerHTML = `Not logged in — <strong>log in via the User Platform panel below</strong> first. Alert rules always require a Bearer token.`;
      }
    }

    function arRenderRules(rules) {
      if (!rules.length) {
        return '<p class="empty-state">No alert rules yet. Create one above or run a demo scenario.</p>';
      }
      const rows = rules.map((rule) => `<tr>
        <td>${escapeHtml(rule.name)}<div class="hint csp-inline-183dbd7c5b"><code>${rule.rule_id.slice(0, 12)}…</code></div></td>
        <td>${rule.conditions.map((c) => `<span class="badge">${escapeHtml(c.condition_type)}</span>`).join(" ")}</td>
        <td><span class="badge">${escapeHtml(rule.status)}</span> ${rule.enabled ? "" : "<span class=\"badge danger\">disabled</span>"}</td>
        <td>${rule.watchlist_id ? "watchlist" : rule.item_id ? "item" : "account-wide"}</td>
        <td>${formatTs(rule.last_triggered_at)}</td>
        <td><button type="button" data-ar-evaluate="${rule.rule_id}" class="csp-inline-a48ad02acf">Evaluate</button></td>
      </tr>`).join("");
      return `<table>
        <thead><tr><th>Rule</th><th>Conditions</th><th>Status</th><th>Scope</th><th>Last triggered</th><th></th></tr></thead>
        <tbody>${rows}</tbody>
      </table>`;
    }

    function arRenderEvents(events) {
      if (!events.length) {
        return '<p class="empty-state">No alert events yet. Evaluate a rule or run a demo scenario.</p>';
      }
      const rows = events.map((event) => `<tr>
        <td><span class="badge">${escapeHtml(event.event_type)}</span></td>
        <td><span class="badge">${escapeHtml(event.severity)}</span></td>
        <td><pre class="csp-inline-ba01be5f04">${escapeHtml(JSON.stringify(event.payload))}</pre></td>
        <td>${formatTs(event.created_at)}</td>
      </tr>`).join("");
      return `<table>
        <thead><tr><th>Type</th><th>Severity</th><th>Payload</th><th>Created</th></tr></thead>
        <tbody>${rows}</tbody>
      </table>`;
    }

    async function arRefreshRules() {
      arUpdateAuthHint();
      arRefreshBtn.disabled = true;
      showEl(arStatusEl, '<div class="loading"><span class="spinner" aria-hidden="true"></span> Loading rules…</div>');
      try {
        const response = await fetch("/api/v1/alerts/rules", { headers: arAuthHeaders() });
        if (response.status === 401) {
          arRulesEl.innerHTML = "";
          showEl(arStatusEl, '<div class="error">Authentication required — log in via the User Platform panel below.</div>');
          return;
        }
        const body = await response.json();
        if (!response.ok) throw new Error(body.detail || "Failed to load rules.");
        arRulesEl.innerHTML = arRenderRules(body.rules || []);
        clearEl(arStatusEl);
      } catch (error) {
        showEl(arStatusEl, `<div class="error">${escapeHtml(error.message || String(error))}</div>`);
      } finally {
        arRefreshBtn.disabled = false;
      }
    }

    async function arRefreshEvents() {
      try {
        const response = await fetch("/api/v1/alerts/events?limit=30", { headers: arAuthHeaders() });
        if (response.status === 401) {
          arEventsEl.innerHTML = "";
          return;
        }
        const body = await response.json();
        if (!response.ok) throw new Error(body.detail || "Failed to load events.");
        arEventsEl.innerHTML = arRenderEvents(body.events || []);
      } catch (error) {
        showEl(arStatusEl, `<div class="error">${escapeHtml(error.message || String(error))}</div>`);
      }
    }

    function arBuildConditionPayload() {
      const conditionType = arConditionTypeSelect.value;
      const thresholdValue = arThresholdValueInput.value.trim();
      const thresholdPercent = arThresholdPercentInput.value.trim();
      const comparison = arComparisonSelect.value;
      return {
        condition_type: conditionType,
        threshold_value: thresholdValue === "" ? null : Number(thresholdValue),
        threshold_percent: thresholdPercent === "" ? null : Number(thresholdPercent),
        comparison: comparison === "" ? null : comparison,
      };
    }

    async function arCreateRule() {
      arCreateBtn.disabled = true;
      showEl(arStatusEl, '<div class="loading"><span class="spinner" aria-hidden="true"></span> Creating rule…</div>');
      try {
        const response = await fetch("/api/v1/alerts/rules", {
          method: "POST",
          headers: arAuthHeaders(),
          body: JSON.stringify({
            name: arNameInput.value.trim() || "Demo rule",
            conditions: [arBuildConditionPayload()],
            watchlist_id: arWatchlistIdInput.value.trim() || null,
            item_id: arItemIdInput.value.trim() || null,
          }),
        });
        const body = await response.json().catch(() => ({}));
        if (!response.ok) {
          throw new Error(
            response.status === 401
              ? "Authentication required — log in via the User Platform panel below."
              : body.detail || "Failed to create rule."
          );
        }
        showEl(arStatusEl, `<div class="hint csp-inline-4fde948ccd">Rule "${escapeHtml(body.name)}" created.</div>`);
        await arRefreshRules();
      } catch (error) {
        showEl(arStatusEl, `<div class="error">${escapeHtml(error.message || String(error))}</div>`);
      } finally {
        arCreateBtn.disabled = false;
      }
    }

    async function arEvaluate(scope) {
      showEl(arStatusEl, '<div class="loading"><span class="spinner" aria-hidden="true"></span> Evaluating…</div>');
      try {
        const response = await fetch("/api/v1/alerts/evaluate", {
          method: "POST",
          headers: arAuthHeaders(),
          body: JSON.stringify(scope || {}),
        });
        const body = await response.json().catch(() => ({}));
        if (!response.ok) {
          throw new Error(
            response.status === 401
              ? "Authentication required — log in via the User Platform panel below."
              : body.detail || "Evaluation failed."
          );
        }
        arEvaluationEl.innerHTML = `
          <div class="meta">
            ${wlStat("Rules evaluated", body.rules_evaluated)}
            ${wlStat("Triggered", body.triggered_count, body.triggered_count > 0)}
            ${wlStat("Events created", (body.events_created || []).length)}
          </div>
          <div class="hint">${escapeHtml(body.disclaimer || "")}</div>
          ${(body.failures || []).length ? `<div class="error">${(body.failures || []).map(escapeHtml).join("<br/>")}</div>` : ""}
        `;
        clearEl(arStatusEl);
        await arRefreshRules();
        await arRefreshEvents();
        return body;
      } catch (error) {
        showEl(arStatusEl, `<div class="error">${escapeHtml(error.message || String(error))}</div>`);
        return null;
      }
    }

    arRefreshBtn.addEventListener("click", arRefreshRules);
    arEventsBtn.addEventListener("click", arRefreshEvents);
    arEvaluateAllBtn.addEventListener("click", () => arEvaluate({}));
    arCreateBtn.addEventListener("click", arCreateRule);
    arRulesEl.addEventListener("click", (event) => {
      const btn = event.target.closest("[data-ar-evaluate]");
      if (!btn) return;
      arEvaluate({ rule_id: btn.getAttribute("data-ar-evaluate") });
    });
    arRefreshRules();
    arRefreshEvents();

    // ---------------------------------------------------------------
    // Deterministic demo scenarios.
    //
    // Each scenario creates/reuses a dedicated demo watchlist item and a
    // scoped alert rule, then calls the real POST /api/v1/alerts/evaluate
    // endpoint. Where the real AlertEvaluationService can genuinely be
    // driven to trigger (price_drop, restock/out-of-stock via a real
    // marketplace-offer re-point, low_inventory, preferred_seller_available,
    // stale_data via a demo-only 0h threshold, dealscore_threshold), the
    // scenario produces a real triggered event. Two conditions
    // (better_offer, freshness_restored) have documented backend gaps —
    // see the inline notes below and the result panel's "Simulated" text.
    // ---------------------------------------------------------------
    let arScenarioWatchlistId = null;

    async function arEnsureScenarioWatchlist() {
      if (arScenarioWatchlistId) return arScenarioWatchlistId;
      const listRes = await fetch("/api/v1/watchlists", { headers: arAuthHeaders() });
      if (listRes.status === 401) throw new Error("Authentication required — log in via the User Platform panel below.");
      const listBody = await listRes.json().catch(() => ({}));
      const existing = (listBody.watchlists || []).find((wl) => wl.name === "Alert Rules Demo");
      if (existing) {
        arScenarioWatchlistId = existing.watchlist_id;
        return arScenarioWatchlistId;
      }
      const created = await fetch("/api/v1/watchlists", {
        method: "POST",
        headers: arAuthHeaders(),
        body: JSON.stringify({ name: "Alert Rules Demo", description: "Sprint 19 scenario fixtures", enabled: true }),
      });
      const body = await created.json().catch(() => ({}));
      if (!created.ok) throw new Error(body.detail || "Failed to create scenario watchlist.");
      arScenarioWatchlistId = body.watchlist_id;
      return arScenarioWatchlistId;
    }

    async function arImportOffer(row) {
      const header = "marketplace_product_id,title,brand,model,category,sku,upc,currency,regular_price,sale_price,shipping_cost,availability,inventory_quantity,seller_name,seller_rating,marketplace_url";
      const csv = `${header}\n${row}`;
      const response = await fetch("/api/v1/marketplaces/imports", {
        method: "POST",
        headers: arAuthHeaders(),
        body: JSON.stringify({ filename: "ar-scenario.csv", content: csv, content_type: "text/csv" }),
      });
      const body = await response.json().catch(() => ({}));
      if (!response.ok) throw new Error(body.detail || "Scenario offer import failed.");
      const mpid = row.split(",")[0];
      const offersRes = await fetch("/api/v1/marketplaces/offers?marketplace=imported&limit=200");
      const offersBody = await offersRes.json().catch(() => ({}));
      const matches = (offersBody.offers || []).filter((o) => o.marketplace_product_id === mpid);
      const match = matches[matches.length - 1];
      if (!match) throw new Error("Could not locate imported scenario offer.");
      return match;
    }

    async function arAttachOffer(watchlistId, offerId, canonicalProductId, label) {
      const response = await fetch(`/api/v1/watchlists/${encodeURIComponent(watchlistId)}/offers`, {
        method: "POST",
        headers: arAuthHeaders(),
        body: JSON.stringify({
          marketplace_offer_id: offerId,
          canonical_product_id: canonicalProductId,
          product_label: label,
          currency: "PHP",
        }),
      });
      const body = await response.json().catch(() => ({}));
      if (!response.ok) throw new Error(body.detail || "Failed to attach scenario offer.");
      return body;
    }

    async function arEnsurePriceItem(canonicalProductId, label, lastKnownPrice, lastKnownDealscore) {
      const watchlistId = await arEnsureScenarioWatchlist();
      const itemsRes = await fetch(`/api/v1/watchlists/${encodeURIComponent(watchlistId)}/items?enrich=false`, {
        headers: arAuthHeaders(),
      });
      const itemsBody = await itemsRes.json().catch(() => ({}));
      const existing = (itemsBody.items || []).find((i) => i.canonical_product_id === canonicalProductId);
      if (existing) {
        return { watchlistId, itemId: existing.item_id };
      }
      const created = await fetch(`/api/v1/watchlists/${encodeURIComponent(watchlistId)}/items`, {
        method: "POST",
        headers: arAuthHeaders(),
        body: JSON.stringify({
          canonical_product_id: canonicalProductId,
          product_label: label,
          currency: "PHP",
          last_known_price: lastKnownPrice,
          last_known_dealscore: lastKnownDealscore,
        }),
      });
      const body = await created.json().catch(() => ({}));
      if (!created.ok) throw new Error(body.detail || "Failed to create scenario item.");
      return { watchlistId, itemId: body.item_id };
    }

    async function arEnsureRule(name, itemId, condition) {
      const response = await fetch("/api/v1/alerts/rules", {
        method: "POST",
        headers: arAuthHeaders(),
        body: JSON.stringify({ name, conditions: [condition], item_id: itemId, cooldown_seconds: 0 }),
      });
      const body = await response.json().catch(() => ({}));
      if (!response.ok) throw new Error(body.detail || "Failed to create scenario rule.");
      return body.rule_id;
    }

    function arRenderScenario(title, note, evalResult) {
      const triggered = evalResult && evalResult.triggered_count > 0;
      const outcomeReasons = ((evalResult && evalResult.events_created) || [])
        .map((e) => `${e.event_type}: ${JSON.stringify(e.payload)}`);
      arScenarioResultEl.classList.add("visible");
      arScenarioResultEl.innerHTML = `
        <h3 class="section-title">${escapeHtml(title)}</h3>
        <div class="meta">
          ${wlStat("Triggered", triggered ? "yes" : "no", triggered)}
          ${wlStat("Events", (evalResult && evalResult.events_created || []).length)}
        </div>
        ${outcomeReasons.length ? `<p class="hint">${outcomeReasons.map(escapeHtml).join("<br/>")}</p>` : ""}
        <p class="hint csp-inline-4fde948ccd">${escapeHtml(note)}</p>
      `;
    }

    async function arRunScenario(fn, btn) {
      btn.disabled = true;
      showEl(arScenarioStatusEl, '<div class="loading"><span class="spinner" aria-hidden="true"></span> Running scenario…</div>');
      try {
        await fn();
        clearEl(arScenarioStatusEl);
      } catch (error) {
        showEl(arScenarioStatusEl, `<div class="error">${escapeHtml(error.message || String(error))}</div>`);
      } finally {
        btn.disabled = false;
      }
    }

    async function arScenarioPriceDrop() {
      // REAL trigger: the iPhone 17 Pro Max demo product has genuine seeded
      // price-history fixture data; setting last_known_price above the real
      // recorded price makes price_drop fire for real, no fabrication.
      await ensureDemoPriceHistory();
      const productId = "00000000-0000-4000-8000-000000000017";
      const { itemId } = await arEnsurePriceItem(productId, "iPhone 17 Pro Max 256GB (price drop demo)", 82000, null);
      const ruleId = await arEnsureRule("Demo: price drop", itemId, { condition_type: "price_drop" });
      const result = await arEvaluate({ rule_id: ruleId });
      if (!result) return;
      arRenderScenario(
        "Price drop",
        "REAL: uses genuine iPhone 17 Pro Max price-history fixture data (last_known_price set above the actual recorded price).",
        result
      );
    }

    async function arScenarioDealscore() {
      // REAL trigger: dealscore_threshold compares an absolute value, no
      // delta needed — item.last_known_dealscore is used as-is when no
      // search_query is set, so this is fully controllable and genuine.
      const productId = "00000000-0000-4000-8000-0000000000a6";
      const { itemId } = await arEnsurePriceItem(productId, "PiqScore improvement demo item", 50000, 88);
      const ruleId = await arEnsureRule("Demo: PiqScore improvement", itemId, {
        condition_type: "dealscore_threshold",
        threshold_value: 75,
        comparison: "gte",
      });
      const result = await arEvaluate({ rule_id: ruleId });
      if (!result) return;
      arRenderScenario(
        "PiqScore improvement",
        "REAL: dealscore_threshold triggers on item.last_known_dealscore (88) vs. threshold (75, gte) — a genuine engine result.",
        result
      );
    }

    async function arScenarioStaleData() {
      // REAL trigger with a documented demo-only threshold: a freshly
      // imported offer's age_hours is always >= 0, so threshold_value=0
      // reliably triggers stale_data without waiting for real staleness
      // (production rules would use a meaningful threshold, e.g. 72h).
      const watchlistId = await arEnsureScenarioWatchlist();
      const offer = await arImportOffer(
        "ar-demo-stale,Stale Data Demo Item,Generic,Demo,Accessories,SKU-STALE,000000000001,PHP,1999,1899,50,in_stock,10,Demo Seller,4.2,https://demo.dealbrain.local/stale"
      );
      const productId = "00000000-0000-4000-8000-0000000000a4";
      await arAttachOffer(watchlistId, offer.offer_id, productId, "Stale data demo item");
      const itemsRes = await fetch(`/api/v1/watchlists/${encodeURIComponent(watchlistId)}/items?enrich=false`, { headers: arAuthHeaders() });
      const itemsBody = await itemsRes.json().catch(() => ({}));
      const item = (itemsBody.items || []).find((i) => i.canonical_product_id === productId);
      const ruleId = await arEnsureRule("Demo: stale data", item.item_id, {
        condition_type: "stale_data",
        threshold_value: 0,
      });
      const result = await arEvaluate({ rule_id: ruleId });
      if (!result) return;
      arRenderScenario(
        "Stale data",
        "REAL call with a demo-only threshold_value=0h (any real data age triggers immediately) — production rules would use a meaningful threshold such as 72h.",
        result
      );
    }

    async function arScenarioFreshnessRestored() {
      // SIMULATED / documented limitation: freshness_restored needs a real
      // stale -> fresh transition (freshness is computed from real elapsed
      // wall-clock time since import, thresholded at 72h by default). The
      // demo API surface cannot fast-forward server time or backdate
      // ingested_at, so a genuine trigger cannot be forced here. We still
      // create the rule and call the real evaluate endpoint to show the
      // exact request/response contract.
      const watchlistId = await arEnsureScenarioWatchlist();
      const offer = await arImportOffer(
        "ar-demo-fresh,Freshness Restored Demo Item,Generic,Demo,Accessories,SKU-FRESH,000000000002,PHP,1999,1899,50,in_stock,10,Demo Seller,4.2,https://demo.dealbrain.local/fresh"
      );
      const productId = "00000000-0000-4000-8000-0000000000a5";
      await arAttachOffer(watchlistId, offer.offer_id, productId, "Freshness restored demo item");
      const itemsRes = await fetch(`/api/v1/watchlists/${encodeURIComponent(watchlistId)}/items?enrich=false`, { headers: arAuthHeaders() });
      const itemsBody = await itemsRes.json().catch(() => ({}));
      const item = (itemsBody.items || []).find((i) => i.canonical_product_id === productId);
      const ruleId = await arEnsureRule("Demo: freshness restored", item.item_id, { condition_type: "freshness_restored" });
      const result = await arEvaluate({ rule_id: ruleId });
      if (!result) return;
      arRenderScenario(
        "Freshness restored",
        "SIMULATED (documented backend limitation): freshness_restored requires a genuine stale→fresh transition based on real elapsed time (72h+ by default). The demo cannot fast-forward server time, so this call is expected to report \"no condition matched\" — the rule + real evaluate call above show the exact contract a live sync would exercise.",
        result
      );
    }

    async function arScenarioBetterOffer() {
      // SIMULATED / documented backend limitation: AlertEvaluationService
      // currently hardcodes observation["better_offer_price"] = None (see
      // app/services/alert_evaluation_service.py::_apply_marketplace_offer),
      // i.e. no competing-offer detection is wired up yet. This scenario
      // still creates a real rule and calls the real evaluate endpoint to
      // demonstrate the contract, but a trigger is not currently possible.
      const watchlistId = await arEnsureScenarioWatchlist();
      const offer = await arImportOffer(
        "ar-demo-better,Better Offer Demo Item,Generic,Demo,Accessories,SKU-BETTER,000000000003,PHP,1999,1899,50,in_stock,10,Demo Seller,4.2,https://demo.dealbrain.local/better"
      );
      const productId = "00000000-0000-4000-8000-0000000000a3";
      await arAttachOffer(watchlistId, offer.offer_id, productId, "Better offer demo item");
      const itemsRes = await fetch(`/api/v1/watchlists/${encodeURIComponent(watchlistId)}/items?enrich=false`, { headers: arAuthHeaders() });
      const itemsBody = await itemsRes.json().catch(() => ({}));
      const item = (itemsBody.items || []).find((i) => i.canonical_product_id === productId);
      const ruleId = await arEnsureRule("Demo: better offer", item.item_id, { condition_type: "better_offer" });
      const result = await arEvaluate({ rule_id: ruleId });
      if (!result) return;
      arRenderScenario(
        "Better offer",
        "SIMULATED (documented backend limitation): AlertEvaluationService always sets better_offer_price=None (no competing-offer detection wired up yet), so this condition cannot trigger via the current backend. This call still exercises the real rule + evaluate contract.",
        result
      );
    }

    async function arScenarioRestock() {
      // REAL trigger: import an out_of_stock offer, attach + evaluate once
      // (baseline observation), then import an in_stock offer with a new
      // marketplace_product_id and re-attach via POST /offers — add_offer
      // re-points the SAME item's marketplace_offer_id — then evaluate
      // again. The engine's own previous-observation cache genuinely
      // reports a real out_of_stock -> in_stock transition.
      const watchlistId = await arEnsureScenarioWatchlist();
      const productId = "00000000-0000-4000-8000-0000000000a1";
      const outOffer = await arImportOffer(
        "ar-demo-restock-out,Restock Demo Item,Generic,Demo,Accessories,SKU-RESTOCK,000000000004,PHP,1999,1899,50,out_of_stock,0,Demo Seller,4.2,https://demo.dealbrain.local/restock"
      );
      await arAttachOffer(watchlistId, outOffer.offer_id, productId, "Restock demo item");
      const itemsRes1 = await fetch(`/api/v1/watchlists/${encodeURIComponent(watchlistId)}/items?enrich=false`, { headers: arAuthHeaders() });
      const itemsBody1 = await itemsRes1.json().catch(() => ({}));
      const item = (itemsBody1.items || []).find((i) => i.canonical_product_id === productId);
      const ruleId = await arEnsureRule("Demo: restocked", item.item_id, { condition_type: "restocked" });
      await arEvaluate({ rule_id: ruleId }); // baseline pass — caches out_of_stock, will not trigger yet
      const inOffer = await arImportOffer(
        "ar-demo-restock-in,Restock Demo Item,Generic,Demo,Accessories,SKU-RESTOCK,000000000004,PHP,1999,1899,50,in_stock,8,Demo Seller,4.2,https://demo.dealbrain.local/restock"
      );
      await arAttachOffer(watchlistId, inOffer.offer_id, productId, "Restock demo item");
      const result = await arEvaluate({ rule_id: ruleId }); // second pass — real out_of_stock -> in_stock transition
      if (!result) return;
      arRenderScenario(
        "Restock",
        "REAL: two genuine evaluate passes — an out_of_stock offer is attached and observed first, then re-pointed to a real in_stock offer. The engine's own previous-observation cache reports the real transition.",
        result
      );
    }

    async function arScenarioOutOfStock() {
      // REAL trigger — mirror of Restock: start in_stock, then re-point to
      // a real out_of_stock offer.
      const watchlistId = await arEnsureScenarioWatchlist();
      const productId = "00000000-0000-4000-8000-0000000000a2";
      const inOffer = await arImportOffer(
        "ar-demo-oos-in,Out of Stock Demo Item,Generic,Demo,Accessories,SKU-OOS,000000000005,PHP,1999,1899,50,in_stock,8,Demo Seller,4.2,https://demo.dealbrain.local/oos"
      );
      await arAttachOffer(watchlistId, inOffer.offer_id, productId, "Out of stock demo item");
      const itemsRes1 = await fetch(`/api/v1/watchlists/${encodeURIComponent(watchlistId)}/items?enrich=false`, { headers: arAuthHeaders() });
      const itemsBody1 = await itemsRes1.json().catch(() => ({}));
      const item = (itemsBody1.items || []).find((i) => i.canonical_product_id === productId);
      const ruleId = await arEnsureRule("Demo: unavailable", item.item_id, { condition_type: "unavailable" });
      await arEvaluate({ rule_id: ruleId }); // baseline pass — caches in_stock
      const outOffer = await arImportOffer(
        "ar-demo-oos-out,Out of Stock Demo Item,Generic,Demo,Accessories,SKU-OOS,000000000005,PHP,1999,1899,50,out_of_stock,0,Demo Seller,4.2,https://demo.dealbrain.local/oos"
      );
      await arAttachOffer(watchlistId, outOffer.offer_id, productId, "Out of stock demo item");
      const result = await arEvaluate({ rule_id: ruleId }); // second pass — real in_stock -> out_of_stock transition
      if (!result) return;
      arRenderScenario(
        "Out of stock",
        "REAL: two genuine evaluate passes — an in_stock offer is observed first, then re-pointed to a real out_of_stock offer, producing a genuine unavailable trigger.",
        result
      );
    }

    document.getElementById("ar_scenario_price_drop").addEventListener("click", (e) => arRunScenario(arScenarioPriceDrop, e.currentTarget));
    document.getElementById("ar_scenario_restock").addEventListener("click", (e) => arRunScenario(arScenarioRestock, e.currentTarget));
    document.getElementById("ar_scenario_out_of_stock").addEventListener("click", (e) => arRunScenario(arScenarioOutOfStock, e.currentTarget));
    document.getElementById("ar_scenario_better_offer").addEventListener("click", (e) => arRunScenario(arScenarioBetterOffer, e.currentTarget));
    document.getElementById("ar_scenario_stale_data").addEventListener("click", (e) => arRunScenario(arScenarioStaleData, e.currentTarget));
    document.getElementById("ar_scenario_freshness_restored").addEventListener("click", (e) => arRunScenario(arScenarioFreshnessRestored, e.currentTarget));
    document.getElementById("ar_scenario_dealscore").addEventListener("click", (e) => arRunScenario(arScenarioDealscore, e.currentTarget));

    // ================================================================
    // Sprint 19 — Notification Center
    // ================================================================
    const ncAuthHintEl = document.getElementById("nc-auth-hint");
    const ncUnreadBadgeEl = document.getElementById("nc-unread-badge");
    const ncTypeFilterSelect = document.getElementById("nc_type_filter");
    const ncRefreshBtn = document.getElementById("nc_refresh");
    const ncMarkAllReadBtn = document.getElementById("nc_mark_all_read");
    const ncStatusEl = document.getElementById("nc-status");
    const ncListEl = document.getElementById("nc-list");

    function ncAuthHeaders() {
      const headers = { "Content-Type": "application/json" };
      if (typeof upAccessToken !== "undefined" && upAccessToken) {
        headers["Authorization"] = `Bearer ${upAccessToken}`;
      }
      return headers;
    }

    function ncUpdateAuthHint() {
      if (typeof upAccessToken !== "undefined" && upAccessToken) {
        ncAuthHintEl.innerHTML = `<span class="csp-inline-4fde948ccd">Authenticated as ${escapeHtml(upUserId || "")}.</span>`;
      } else {
        ncAuthHintEl.innerHTML = `Not logged in — <strong>log in via the User Platform panel below</strong> first. The Notification Center always requires a Bearer token.`;
      }
    }

    function ncRenderNotification(n) {
      const isEmail = n.channel === "email";
      const readBadge = n.is_read ? '<span class="badge">read</span>' : '<span class="badge recommended">unread</span>';
      const archivedBadge = n.is_archived ? '<span class="badge danger">archived</span>' : "";
      return `<div class="csp-inline-740c092ad0">
        <div><strong>${escapeHtml(n.title)}</strong> <span class="badge">${escapeHtml(n.type)}</span> <span class="badge">${escapeHtml(n.severity)}</span> ${readBadge} ${archivedBadge}</div>
        <div class="hint csp-inline-d2b48491a0">${escapeHtml(n.body)}</div>
        ${isEmail ? '<div class="hint csp-inline-6c237daad4">SIMULATED EMAIL — NO REAL MESSAGE SENT</div>' : ""}
        <div class="hint">${formatTs(n.created_at)}</div>
        <div class="row csp-inline-249160d0ab">
          ${!n.is_read ? `<button type="button" data-nc-read="${n.notification_id}" class="csp-inline-d4f9d29f15">Mark read</button>` : ""}
          ${!n.is_archived ? `<button type="button" data-nc-archive="${n.notification_id}" class="csp-inline-28d52a09bd">Archive</button>` : ""}
        </div>
      </div>`;
    }

    async function ncRefreshUnreadCount() {
      try {
        const response = await fetch("/api/v1/notifications/unread-count", { headers: ncAuthHeaders() });
        if (!response.ok) {
          ncUnreadBadgeEl.style.display = "none";
          return;
        }
        const body = await response.json();
        if (body.unread_count > 0) {
          ncUnreadBadgeEl.textContent = String(body.unread_count);
          ncUnreadBadgeEl.style.display = "inline-block";
        } else {
          ncUnreadBadgeEl.style.display = "none";
        }
      } catch (_err) {
        ncUnreadBadgeEl.style.display = "none";
      }
    }

    async function ncRefreshList() {
      ncUpdateAuthHint();
      ncRefreshBtn.disabled = true;
      showEl(ncStatusEl, '<div class="loading"><span class="spinner" aria-hidden="true"></span> Loading notifications…</div>');
      try {
        const typeParam = ncTypeFilterSelect.value ? `&type=${encodeURIComponent(ncTypeFilterSelect.value)}` : "";
        const response = await fetch(`/api/v1/notifications?limit=50${typeParam}`, { headers: ncAuthHeaders() });
        if (response.status === 401) {
          ncListEl.innerHTML = "";
          showEl(ncStatusEl, '<div class="error">Authentication required — log in via the User Platform panel below.</div>');
          return;
        }
        const body = await response.json();
        if (!response.ok) throw new Error(body.detail || "Failed to load notifications.");
        const notifications = body.notifications || [];
        ncListEl.innerHTML = notifications.length
          ? notifications.map(ncRenderNotification).join("")
          : '<p class="empty-state">No notifications yet. Trigger an alert scenario above to generate some.</p>';
        clearEl(ncStatusEl);
        await ncRefreshUnreadCount();
      } catch (error) {
        showEl(ncStatusEl, `<div class="error">${escapeHtml(error.message || String(error))}</div>`);
      } finally {
        ncRefreshBtn.disabled = false;
      }
    }

    async function ncMarkAllRead() {
      try {
        const response = await fetch("/api/v1/notifications/read-all", { method: "POST", headers: ncAuthHeaders() });
        const body = await response.json().catch(() => ({}));
        if (!response.ok) throw new Error(body.detail || "Failed to mark all read.");
        showEl(ncStatusEl, `<div class="hint csp-inline-4fde948ccd">Marked ${body.marked_read} notification(s) read.</div>`);
        await ncRefreshList();
      } catch (error) {
        showEl(ncStatusEl, `<div class="error">${escapeHtml(error.message || String(error))}</div>`);
      }
    }

    ncRefreshBtn.addEventListener("click", ncRefreshList);
    ncMarkAllReadBtn.addEventListener("click", ncMarkAllRead);
    ncTypeFilterSelect.addEventListener("change", ncRefreshList);
    ncListEl.addEventListener("click", async (event) => {
      const readBtn = event.target.closest("[data-nc-read]");
      const archiveBtn = event.target.closest("[data-nc-archive]");
      try {
        if (readBtn) {
          await fetch(`/api/v1/notifications/${encodeURIComponent(readBtn.getAttribute("data-nc-read"))}/read`, {
            method: "POST", headers: ncAuthHeaders(),
          });
          await ncRefreshList();
        } else if (archiveBtn) {
          await fetch(`/api/v1/notifications/${encodeURIComponent(archiveBtn.getAttribute("data-nc-archive"))}/archive`, {
            method: "POST", headers: ncAuthHeaders(),
          });
          await ncRefreshList();
        }
      } catch (error) {
        showEl(ncStatusEl, `<div class="error">${escapeHtml(error.message || String(error))}</div>`);
      }
    });
    ncRefreshList();

    // ================================================================
    // Sprint 19 — Notification Preferences
    // ================================================================
    const npAuthHintEl = document.getElementById("np-auth-hint");
    const npRefreshBtn = document.getElementById("np_refresh");
    const npSaveBtn = document.getElementById("np_save");
    const npStatusEl = document.getElementById("np-status");
    const npCurrentEl = document.getElementById("np-current");
    const npInAppEnabled = document.getElementById("np_in_app_enabled");
    const npEmailEnabled = document.getElementById("np_email_enabled");
    const npImmediateAlerts = document.getElementById("np_immediate_alerts");
    const npDailyDigest = document.getElementById("np_daily_digest");
    const npWeeklyDigest = document.getElementById("np_weekly_digest");
    const npPriceAlerts = document.getElementById("np_price_alerts");
    const npStockAlerts = document.getElementById("np_stock_alerts");
    const npFreshnessWarnings = document.getElementById("np_freshness_warnings");
    const npMarketingEnabled = document.getElementById("np_marketing_enabled");
    const npQuietHoursStart = document.getElementById("np_quiet_hours_start");
    const npQuietHoursEnd = document.getElementById("np_quiet_hours_end");
    const npTimezone = document.getElementById("np_timezone");

    function npAuthHeaders() {
      const headers = { "Content-Type": "application/json" };
      if (typeof upAccessToken !== "undefined" && upAccessToken) {
        headers["Authorization"] = `Bearer ${upAccessToken}`;
      }
      return headers;
    }

    function npUpdateAuthHint() {
      if (typeof upAccessToken !== "undefined" && upAccessToken) {
        npAuthHintEl.innerHTML = `<span class="csp-inline-4fde948ccd">Authenticated as ${escapeHtml(upUserId || "")}.</span>`;
      } else {
        npAuthHintEl.innerHTML = `Not logged in — <strong>log in via the User Platform panel below</strong> first. Notification Preferences always require a Bearer token.`;
      }
    }

    function npApplyToForm(prefs) {
      npInAppEnabled.checked = !!prefs.in_app_enabled;
      npEmailEnabled.checked = !!prefs.email_enabled;
      npImmediateAlerts.checked = !!prefs.immediate_alerts;
      npDailyDigest.checked = !!prefs.daily_digest;
      npWeeklyDigest.checked = !!prefs.weekly_digest;
      npPriceAlerts.checked = !!prefs.price_alerts;
      npStockAlerts.checked = !!prefs.stock_alerts;
      npFreshnessWarnings.checked = !!prefs.freshness_warnings;
      npMarketingEnabled.checked = !!prefs.marketing_enabled;
      npQuietHoursStart.value = prefs.quiet_hours_start || "";
      npQuietHoursEnd.value = prefs.quiet_hours_end || "";
      npTimezone.value = prefs.timezone || "UTC";
    }

    async function npRefresh() {
      npUpdateAuthHint();
      npRefreshBtn.disabled = true;
      showEl(npStatusEl, '<div class="loading"><span class="spinner" aria-hidden="true"></span> Loading preferences…</div>');
      try {
        const response = await fetch("/api/v1/notification-preferences", { headers: npAuthHeaders() });
        if (response.status === 401) {
          npCurrentEl.innerHTML = "";
          showEl(npStatusEl, '<div class="error">Authentication required — log in via the User Platform panel below.</div>');
          return;
        }
        const body = await response.json();
        if (!response.ok) throw new Error(body.detail || "Failed to load preferences.");
        npApplyToForm(body);
        npCurrentEl.innerHTML = `<pre class="csp-inline-834fd7b300">${escapeHtml(JSON.stringify(body, null, 2))}</pre>`;
        clearEl(npStatusEl);
      } catch (error) {
        showEl(npStatusEl, `<div class="error">${escapeHtml(error.message || String(error))}</div>`);
      } finally {
        npRefreshBtn.disabled = false;
      }
    }

    async function npSave() {
      npSaveBtn.disabled = true;
      showEl(npStatusEl, '<div class="loading"><span class="spinner" aria-hidden="true"></span> Saving preferences…</div>');
      try {
        const response = await fetch("/api/v1/notification-preferences", {
          method: "PUT",
          headers: npAuthHeaders(),
          body: JSON.stringify({
            in_app_enabled: npInAppEnabled.checked,
            email_enabled: npEmailEnabled.checked,
            immediate_alerts: npImmediateAlerts.checked,
            daily_digest: npDailyDigest.checked,
            weekly_digest: npWeeklyDigest.checked,
            price_alerts: npPriceAlerts.checked,
            stock_alerts: npStockAlerts.checked,
            freshness_warnings: npFreshnessWarnings.checked,
            marketing_enabled: false,
            quiet_hours_start: npQuietHoursStart.value.trim() || null,
            clear_quiet_hours_start: npQuietHoursStart.value.trim() === "",
            quiet_hours_end: npQuietHoursEnd.value.trim() || null,
            clear_quiet_hours_end: npQuietHoursEnd.value.trim() === "",
            timezone: npTimezone.value.trim() || "UTC",
          }),
        });
        const body = await response.json().catch(() => ({}));
        if (!response.ok) {
          throw new Error(
            response.status === 401
              ? "Authentication required — log in via the User Platform panel below."
              : body.detail || "Failed to save preferences."
          );
        }
        npApplyToForm(body);
        npCurrentEl.innerHTML = `<pre class="csp-inline-834fd7b300">${escapeHtml(JSON.stringify(body, null, 2))}</pre>`;
        showEl(npStatusEl, '<div class="hint csp-inline-4fde948ccd">Preferences saved. Marketing remains disabled by default.</div>');
      } catch (error) {
        showEl(npStatusEl, `<div class="error">${escapeHtml(error.message || String(error))}</div>`);
      } finally {
        npSaveBtn.disabled = false;
      }
    }

    npRefreshBtn.addEventListener("click", npRefresh);
    npSaveBtn.addEventListener("click", npSave);
    npRefresh();

    // ================================================================
    // Sprint 19 — Personalized Dashboard
    // ================================================================
    const dbAuthHintEl = document.getElementById("db-auth-hint");
    const dbRefreshBtn = document.getElementById("db_refresh");
    const dbStatusEl = document.getElementById("db-status");
    const dbSummaryEl = document.getElementById("db-summary");
    const dbFreshnessEl = document.getElementById("db-freshness");
    const dbCardsEl = document.getElementById("db-cards");
    const dbActivityEl = document.getElementById("db-activity");

    function dbAuthHeaders() {
      const headers = { "Content-Type": "application/json" };
      if (typeof upAccessToken !== "undefined" && upAccessToken) {
        headers["Authorization"] = `Bearer ${upAccessToken}`;
      }
      return headers;
    }

    function dbUpdateAuthHint() {
      if (typeof upAccessToken !== "undefined" && upAccessToken) {
        dbAuthHintEl.innerHTML = `<span class="csp-inline-4fde948ccd">Authenticated as ${escapeHtml(upUserId || "")}.</span>`;
      } else {
        dbAuthHintEl.innerHTML = `Not logged in — <strong>log in via the User Platform panel below</strong> first. The dashboard always requires a Bearer token.`;
      }
    }

    function dbRenderCard(card) {
      const items = card.items || [];
      return `<div class="csp-inline-740c092ad0">
        <div><strong>${escapeHtml(card.title)}</strong> <span class="badge">${escapeHtml(card.card_type)}</span>
          ${card.source_mode_label ? `<span class="badge neutral">${escapeHtml(card.source_mode_label)}</span>` : ""}
        </div>
        ${card.summary ? `<div class="hint csp-inline-d2b48491a0">${escapeHtml(card.summary)}</div>` : ""}
        ${card.freshness_label ? `<div class="hint csp-inline-e28e3e8b87">${escapeHtml(card.freshness_label)}</div>` : ""}
        <div class="hint">${items.length} item(s)</div>
        ${items.length ? `<pre class="csp-inline-4b7ad6fb66">${escapeHtml(JSON.stringify(items.slice(0, 5), null, 2))}</pre>` : ""}
      </div>`;
    }

    async function dbRefresh() {
      dbUpdateAuthHint();
      dbRefreshBtn.disabled = true;
      showEl(dbStatusEl, '<div class="loading"><span class="spinner" aria-hidden="true"></span> Loading dashboard…</div>');
      try {
        const response = await fetch("/api/v1/dashboard?currency=PHP", { headers: dbAuthHeaders() });
        if (response.status === 401) {
          dbSummaryEl.innerHTML = "";
          dbFreshnessEl.innerHTML = "";
          dbCardsEl.innerHTML = "";
          dbActivityEl.innerHTML = "";
          showEl(dbStatusEl, '<div class="error">Authentication required — log in via the User Platform panel below.</div>');
          return;
        }
        const body = await response.json();
        if (!response.ok) throw new Error(body.detail || "Failed to load dashboard.");
        const s = body.summary || {};
        dbSummaryEl.innerHTML = [
          wlStat("Watched products", s.watched_products || 0, true),
          wlStat("Active rules", s.active_alert_rules || 0),
          wlStat("Price drops", s.recent_price_drops || 0),
          wlStat("Restocks", s.restocked_items || 0),
          wlStat("Better offers", s.better_offers || 0),
          wlStat("Unread", s.unread_notifications || 0, (s.unread_notifications || 0) > 0),
          wlStat("Stale data", s.stale_data_count || 0),
          wlStat("Potential savings", `${s.potential_savings_currency || "PHP"} ${Number(s.potential_savings || 0).toLocaleString()}`, true),
        ].join("");
        dbFreshnessEl.innerHTML = `
          <p class="hint">${escapeHtml(s.savings_freshness_note || body.limitations || "")}</p>
          <p class="hint">Personalization: <code>${escapeHtml(JSON.stringify(body.personalization || {}))}</code></p>
        `;
        const cards = body.cards || [];
        dbCardsEl.innerHTML = cards.length ? cards.map(dbRenderCard).join("") : '<p class="empty-state">No cards yet.</p>';
        const activity = body.recent_activity || [];
        dbActivityEl.innerHTML = activity.length
          ? `<ul>${activity.map((a) => `<li>${formatTs(a.created_at)} — ${escapeHtml(a.message)}</li>`).join("")}</ul>`
          : '<p class="empty-state">No recent activity.</p>';
        clearEl(dbStatusEl);
      } catch (error) {
        showEl(dbStatusEl, `<div class="error">${escapeHtml(error.message || String(error))}</div>`);
      } finally {
        dbRefreshBtn.disabled = false;
      }
    }

    dbRefreshBtn.addEventListener("click", dbRefresh);
    dbRefresh();

    const rvCollectBtn = document.getElementById("rv_collect");
    const rvRefreshBtn = document.getElementById("rv_refresh");
    const rvCompareBtn = document.getElementById("rv_compare");
    const rvProductIdInput = document.getElementById("rv_product_id");
    const rvProductLabelInput = document.getElementById("rv_product_label");
    const rvSummaryEl = document.getElementById("rv-summary");
    const rvStatusEl = document.getElementById("rv-status");
    const rvCompareEl = document.getElementById("rv-compare");
    const rvRatingsEl = document.getElementById("rv-ratings");
    const rvHistoryEl = document.getElementById("rv-history");

    function rvStat(label, value, emerald) {
      return `<div class="stat"><div class="label">${label}</div><div class="value${emerald ? " emerald" : ""}">${value}</div></div>`;
    }

    function renderReviewMarketplaces(marketplaces) {
      if (!marketplaces.length) {
        return '<p class="empty-state">No marketplace reviews yet. Collect reviews to begin.</p>';
      }
      const rows = marketplaces.map((m) => `
        <tr>
          <td>${escapeHtml(m.marketplace)}</td>
          <td><strong>${Number(m.rating).toFixed(1)}</strong></td>
          <td>${Number(m.reviews).toLocaleString()}</td>
          <td>${m.seller_rating != null ? Number(m.seller_rating).toFixed(1) : "—"}</td>
          <td>${m.seller_followers != null ? Number(m.seller_followers).toLocaleString() : "—"}</td>
        </tr>`).join("");
      return `<table>
        <thead><tr><th>Marketplace</th><th>Rating</th><th>Reviews</th><th>Seller</th><th>Followers</th></tr></thead>
        <tbody>${rows}</tbody>
      </table>`;
    }

    function renderReviewStars(marketplaces) {
      if (!marketplaces.length) {
        return '<p class="empty-state">No star distributions available.</p>';
      }
      return marketplaces.map((m) => `
        <div class="csp-inline-f9bcedfd33">
          <div class="hint csp-inline-9b13d04fb8"><strong>${escapeHtml(m.marketplace)}</strong>
            · ${Number(m.rating).toFixed(1)} · ${Number(m.reviews).toLocaleString()} reviews</div>
          <div class="meta">
            ${rvStat("★★★★★", (m.five_star_count || 0).toLocaleString())}
            ${rvStat("★★★★", (m.four_star_count || 0).toLocaleString())}
            ${rvStat("★★★", (m.three_star_count || 0).toLocaleString())}
            ${rvStat("★★", (m.two_star_count || 0).toLocaleString())}
            ${rvStat("★", (m.one_star_count || 0).toLocaleString())}
          </div>
        </div>`).join("");
    }

    function renderReviewHistory(snapshots) {
      if (!snapshots.length) {
        return '<p class="empty-state">No review history yet.</p>';
      }
      const rows = snapshots.slice(0, 24).map((s) => `
        <tr>
          <td>${escapeHtml(s.marketplace)}</td>
          <td>${Number(s.average_rating).toFixed(2)}</td>
          <td>${Number(s.review_count).toLocaleString()}</td>
          <td>${s.seller_rating != null ? Number(s.seller_rating).toFixed(1) : "—"}</td>
          <td><code>${escapeHtml((s.collected_at || "").replace("T", " ").slice(0, 19))}</code></td>
        </tr>`).join("");
      return `<table>
        <thead><tr><th>Marketplace</th><th>Rating</th><th>Reviews</th><th>Seller</th><th>Collected</th></tr></thead>
        <tbody>${rows}</tbody>
      </table>`;
    }

    async function refreshReviews() {
      const productId = (rvProductIdInput.value || "").trim();
      if (!productId) {
        showEl(rvStatusEl, '<div class="error">Product ID is required.</div>');
        return;
      }
      showEl(
        rvStatusEl,
        '<div class="loading"><span class="spinner" aria-hidden="true"></span> Loading reviews…</div>'
      );
      try {
        const [latestRes, historyRes] = await Promise.all([
          fetch(`/api/v1/reviews/${encodeURIComponent(productId)}`),
          fetch(`/api/v1/reviews/history/${encodeURIComponent(productId)}`),
        ]);
        if (latestRes.status === 404) {
          rvSummaryEl.innerHTML = rvStat("Overall Rating", "—") + rvStat("Total Reviews", "0");
          rvCompareEl.innerHTML = '<p class="empty-state">No reviews yet. Click Collect Reviews.</p>';
          rvRatingsEl.innerHTML = "";
          rvHistoryEl.innerHTML = "";
          showEl(rvStatusEl, '<div class="hint">No snapshots stored for this product.</div>');
          return;
        }
        if (!latestRes.ok) {
          const detail = await latestRes.json().catch(() => ({}));
          throw new Error(detail.detail || "Failed to load reviews.");
        }
        const latest = await latestRes.json();
        const history = historyRes.ok ? await historyRes.json() : { snapshots: [] };
        rvSummaryEl.innerHTML = [
          rvStat("Overall Rating", latest.overall_rating != null ? Number(latest.overall_rating).toFixed(2) : "—", true),
          rvStat("Total Reviews", Number(latest.total_review_count || 0).toLocaleString(), true),
          rvStat("Product", escapeHtml(latest.product || productId)),
          rvStat("Marketplaces", (latest.marketplaces || []).length),
        ].join("");
        rvCompareEl.innerHTML = renderReviewMarketplaces(latest.marketplaces || []);
        rvRatingsEl.innerHTML = renderReviewStars(latest.marketplaces || []);
        rvHistoryEl.innerHTML = renderReviewHistory(history.snapshots || []);
        showEl(rvStatusEl, "");
      } catch (error) {
        showEl(rvStatusEl, `<div class="error">${error.message || error}</div>`);
      }
    }

    async function collectReviews() {
      const productId = (rvProductIdInput.value || "").trim();
      const productLabel = (rvProductLabelInput.value || "").trim() || null;
      if (!productId) {
        showEl(rvStatusEl, '<div class="error">Product ID is required.</div>');
        return;
      }
      rvCollectBtn.disabled = true;
      showEl(
        rvStatusEl,
        '<div class="loading"><span class="spinner" aria-hidden="true"></span> Collecting mock reviews…</div>'
      );
      try {
        const response = await fetch("/api/v1/reviews/collect", {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify({
            product_id: productId,
            product_label: productLabel,
          }),
        });
        if (!response.ok) {
          const detail = await response.json().catch(() => ({}));
          throw new Error(detail.detail || "Failed to collect reviews.");
        }
        const body = await response.json();
        showEl(
          rvStatusEl,
          `<div class="hint">Collected ${body.collected_count} marketplace snapshots · overall ${body.overall_rating}</div>`
        );
        await refreshReviews();
      } catch (error) {
        showEl(rvStatusEl, `<div class="error">${error.message || error}</div>`);
      } finally {
        rvCollectBtn.disabled = false;
      }
    }

    async function compareReviews() {
      const productId = (rvProductIdInput.value || "").trim();
      if (!productId) {
        showEl(rvStatusEl, '<div class="error">Product ID is required.</div>');
        return;
      }
      rvCompareBtn.disabled = true;
      showEl(
        rvStatusEl,
        '<div class="loading"><span class="spinner" aria-hidden="true"></span> Comparing marketplaces…</div>'
      );
      try {
        const response = await fetch(`/api/v1/reviews/compare/${encodeURIComponent(productId)}`);
        if (!response.ok) {
          const detail = await response.json().catch(() => ({}));
          throw new Error(detail.detail || "Failed to compare marketplaces.");
        }
        const body = await response.json();
        rvSummaryEl.innerHTML = [
          rvStat("Overall Rating", body.overall_rating != null ? Number(body.overall_rating).toFixed(2) : "—", true),
          rvStat("Total Reviews", Number(body.total_review_count || 0).toLocaleString(), true),
          rvStat("Product", escapeHtml(body.product || productId)),
        ].join("");
        rvCompareEl.innerHTML = renderReviewMarketplaces(body.marketplaces || []);
        rvRatingsEl.innerHTML = renderReviewStars(body.marketplaces || []);
        showEl(rvStatusEl, '<div class="hint">Marketplace comparison updated.</div>');
      } catch (error) {
        showEl(rvStatusEl, `<div class="error">${error.message || error}</div>`);
      } finally {
        rvCompareBtn.disabled = false;
      }
    }

    rvCollectBtn.addEventListener("click", collectReviews);
    rvRefreshBtn.addEventListener("click", refreshReviews);
    rvCompareBtn.addEventListener("click", compareReviews);
    refreshReviews();

    const rsLoadBtn = document.getElementById("rs_load");
    const rsDemoBtn = document.getElementById("rs_demo");
    const rsProductIdInput = document.getElementById("rs_product_id");
    const rsModeInput = document.getElementById("rs_mode");
    const rsSentimentEl = document.getElementById("rs-sentiment");
    const rsMetaEl = document.getElementById("rs-meta");
    const rsStatusEl = document.getElementById("rs-status");
    const rsSummaryTextEl = document.getElementById("rs-summary-text");
    const rsProsEl = document.getElementById("rs-pros");
    const rsConsEl = document.getElementById("rs-cons");
    const rsWarningsEl = document.getElementById("rs-warnings");
    const rsRecommendationEl = document.getElementById("rs-recommendation");
    const rsDisagreementsEl = document.getElementById("rs-disagreements");

    function sentimentStars(sentiment) {
      const map = {
        "Very Positive": "★★★★★",
        "Positive": "★★★★☆",
        "Mixed": "★★★☆☆",
        "Negative": "★★☆☆☆",
      };
      return map[sentiment] || "★★★☆☆";
    }

    function renderBulletList(items, emptyLabel) {
      if (!items || !items.length) {
        return `<p class="empty-state">${emptyLabel}</p>`;
      }
      return `<ul class="csp-inline-b20f3b6fe5">${items.map((item) =>
        `<li>${escapeHtml(item)}</li>`
      ).join("")}</ul>`;
    }

    function rsModeQuery() {
      const mode = (rsModeInput.value || "").trim();
      return mode ? `?mode=${encodeURIComponent(mode)}` : "";
    }

    function renderReviewSummary(body) {
      rsSentimentEl.innerHTML = [
        rvStat("Overall Sentiment", escapeHtml(body.overall_sentiment || "—"), true),
        rvStat("Stars", sentimentStars(body.overall_sentiment || ""), true),
        rvStat("Rating", body.average_rating != null ? Number(body.average_rating).toFixed(2) : "—"),
        rvStat("Recommendation", escapeHtml(body.recommendation || "—"), true),
      ].join("");
      const providers = (body.providers_used || []).join(", ") || body.provider || "—";
      const confidence = body.consensus_confidence != null
        ? Number(body.consensus_confidence).toFixed(2)
        : "—";
      const agreement = body.agreement_score != null
        ? Number(body.agreement_score).toFixed(2)
        : "—";
      rsMetaEl.innerHTML = [
        rvStat("Analysis mode", escapeHtml(body.mode || "economy"), true),
        rvStat("Providers used", escapeHtml(providers)),
        rvStat("Confidence", confidence, true),
        rvStat("Agreement", agreement),
        rvStat("Fallback", body.fallback_used ? "Yes" : "No"),
      ].join("");
      rsSummaryTextEl.innerHTML = body.summary
        ? `<p class="csp-inline-ce31057250">${escapeHtml(body.summary)}</p>`
        : '<p class="empty-state">No summary paragraph.</p>';
      rsProsEl.innerHTML = renderBulletList(body.pros || [], "No pros detected.");
      rsConsEl.innerHTML = renderBulletList(body.cons || [], "No cons detected.");
      rsWarningsEl.innerHTML = renderBulletList(body.warnings || [], "No warnings.");
      rsRecommendationEl.innerHTML = body.recommendation
        ? `<p class="csp-inline-97f859c4da">${escapeHtml(body.recommendation)}</p>`
        : '<p class="empty-state">No recommendation.</p>';
      const disagreements = body.disagreements || [];
      if (!disagreements.length) {
        rsDisagreementsEl.innerHTML = '<p class="empty-state">No model disagreements reported.</p>';
      } else {
        rsDisagreementsEl.innerHTML = `<ul class="csp-inline-b20f3b6fe5">${
          disagreements.map((d) =>
            `<li><strong>${escapeHtml(d.field || "claim")}</strong>: ${escapeHtml(d.detail || "")}</li>`
          ).join("")
        }</ul>`;
      }
    }

    async function loadReviewSummary(url) {
      showEl(
        rsStatusEl,
        '<div class="loading"><span class="spinner" aria-hidden="true"></span> Generating review summary…</div>'
      );
      try {
        const response = await fetch(url);
        if (!response.ok) {
          const detail = await response.json().catch(() => ({}));
          throw new Error(detail.detail || "Failed to load review summary.");
        }
        const body = await response.json();
        renderReviewSummary(body);
        const fallbackNote = body.fallback_used
          ? ` · fallback${body.fallback_reason ? ` (${escapeHtml(body.fallback_reason)})` : ""}`
          : "";
        showEl(
          rsStatusEl,
          `<div class="hint">Mode: ${escapeHtml(body.mode || "economy")} · providers: ${escapeHtml((body.providers_used || []).join(", ") || body.provider || "—")}${fallbackNote}</div>`
        );
      } catch (error) {
        showEl(rsStatusEl, `<div class="error">${error.message || error}</div>`);
      }
    }

    async function summarizeReviews() {
      const productId = (rsProductIdInput.value || "").trim();
      if (!productId) {
        showEl(rsStatusEl, '<div class="error">Product ID is required.</div>');
        return;
      }
      rsLoadBtn.disabled = true;
      try {
        await loadReviewSummary(`/api/v1/review-summary/${encodeURIComponent(productId)}${rsModeQuery()}`);
      } finally {
        rsLoadBtn.disabled = false;
      }
    }

    async function loadDemoSummary() {
      rsDemoBtn.disabled = true;
      try {
        await loadReviewSummary(`/api/v1/review-summary/demo${rsModeQuery()}`);
      } finally {
        rsDemoBtn.disabled = false;
      }
    }

    rsLoadBtn.addEventListener("click", summarizeReviews);
    rsDemoBtn.addEventListener("click", loadDemoSummary);
    loadDemoSummary();

    // --- Personal AI Shopping Agent panel ---
    const paProfileSelect = document.getElementById("pa_profile");
    const paSwitchBtn = document.getElementById("pa_switch");
    const paDemoBtn = document.getElementById("pa_demo");
    const paDealsBtn = document.getElementById("pa_deals");
    const paMetaEl = document.getElementById("pa-meta");
    const paProfileCardEl = document.getElementById("pa-profile-card");
    const paStatusEl = document.getElementById("pa-status");
    const paDealsListEl = document.getElementById("pa-deals-list");
    const paAdviceEl = document.getElementById("pa-advice");
    const paLimitationsEl = document.getElementById("pa-limitations");
    let activePersonalProfileId = null;

    function renderPersonalProfileCard(profile) {
      if (!profile) {
        paProfileCardEl.innerHTML = '<p class="empty-state">No profile loaded.</p>';
        return;
      }
      paProfileCardEl.innerHTML = [
        rvStat("Profile", escapeHtml(profile.display_name), true),
        rvStat("Persona", escapeHtml(profile.persona), true),
        rvStat("Budget", profile.budget != null ? `${Number(profile.budget).toLocaleString()} ${escapeHtml(profile.currency || "")}` : "—", true),
        rvStat("Brands", escapeHtml((profile.favorite_brands || []).join(", ") || "—")),
        rvStat("Use cases", escapeHtml((profile.use_cases || []).join(", ") || "—")),
        `<p class="csp-inline-5884433a5f">${escapeHtml(profile.description || "")}</p>`,
      ].join("");
    }

    function renderPersonalDeals(deals) {
      const recs = (deals && deals.recommendations) || [];
      if (!recs.length) {
        paDealsListEl.innerHTML = '<p class="empty-state">No personalized deals.</p>';
        paAdviceEl.innerHTML = '<p class="empty-state">No advice.</p>';
        return;
      }
      paDealsListEl.innerHTML = `<ul class="csp-inline-b20f3b6fe5">${recs.map((item) =>
        `<li class="csp-inline-2f5ae6861a">
          <strong>${escapeHtml(item.product_name)}</strong>
          · Personalized PiqScore ${Number(item.personal_deal_score).toFixed(1)}
          · pref ${Number(item.preference_score).toFixed(2)}
          · ${item.known_price != null ? Number(item.known_price).toLocaleString() + " " + escapeHtml(item.currency || "") : "—"}
          <div class="hint csp-inline-b23a8be8db">${escapeHtml(item.reason || "")}</div>
        </li>`
      ).join("")}</ul>`;
      const advice = recs[0].advice;
      if (!advice) {
        paAdviceEl.innerHTML = '<p class="empty-state">No buying advice.</p>';
      } else {
        paAdviceEl.innerHTML = [
          rvStat("Verdict", escapeHtml(advice.label), true),
          rvStat("Personalized PiqScore", advice.personal_deal_score != null ? Number(advice.personal_deal_score).toFixed(1) : "—", true),
          `<p class="csp-inline-c6e72cd9d3"><strong>${escapeHtml(advice.summary || "")}</strong></p>`,
          `<p class="csp-inline-0c65958f14">${escapeHtml(advice.explanation || "")}</p>`,
        ].join("");
      }
    }

    function fillPersonalProfileSelect(profiles, activeId) {
      const options = (profiles || []).map((p) =>
        `<option value="${escapeHtml(p.profile_id)}" ${p.profile_id === activeId ? "selected" : ""}>${escapeHtml(p.display_name)}</option>`
      ).join("");
      paProfileSelect.innerHTML = options || '<option value="">No profiles</option>';
      activePersonalProfileId = activeId || (profiles[0] && profiles[0].profile_id) || null;
    }

    async function loadPersonalDemo(profileId) {
      showEl(
        paStatusEl,
        '<div class="loading"><span class="spinner" aria-hidden="true"></span> Loading personal demo…</div>'
      );
      try {
        const qs = profileId ? `?profile_id=${encodeURIComponent(profileId)}` : "";
        const response = await fetch(`/api/v1/personal/demo${qs}`);
        if (!response.ok) {
          const detail = await response.json().catch(() => ({}));
          throw new Error(detail.detail || "Failed to load personal demo.");
        }
        const body = await response.json();
        fillPersonalProfileSelect(body.profiles || [], body.active_profile && body.active_profile.profile_id);
        renderPersonalProfileCard(body.active_profile);
        renderPersonalDeals(body.deals);
        paLimitationsEl.innerHTML = renderBulletList(body.limitations || [], "No limitations listed.");
        paMetaEl.innerHTML = [
          rvStat("Active profile", escapeHtml(body.active_profile.display_name), true),
          rvStat("Profiles", String((body.profiles || []).length), true),
          rvStat("Auth", "None"),
          rvStat("Data", escapeHtml((body.deals && body.deals.data_status) || "mock")),
        ].join("");
        showEl(
          paStatusEl,
          `<div class="hint">Personal demo ready · ${escapeHtml(body.active_profile.display_name)} · recommendations update instantly on profile switch</div>`
        );
      } catch (error) {
        showEl(paStatusEl, `<div class="error">${error.message || error}</div>`);
      }
    }

    async function switchPersonalProfile() {
      const profileId = paProfileSelect.value;
      if (!profileId) return;
      paSwitchBtn.disabled = true;
      try {
        const response = await fetch("/api/v1/personal/profile/switch", {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify({ profile_id: profileId }),
        });
        if (!response.ok) {
          const detail = await response.json().catch(() => ({}));
          throw new Error(detail.detail || "Failed to switch profile.");
        }
        await loadPersonalDemo(profileId);
        // Instantly refresh shopping assistant with the new profile when enabled
        const saUseProfile = document.getElementById("sa_use_profile");
        if (saUseProfile && saUseProfile.value === "1") {
          const query = (document.getElementById("sa_query").value || "").trim();
          if (query) {
            await askShoppingAssistant({
              query,
              mode: document.getElementById("sa_mode").value || "economy",
              conversation_id: (document.getElementById("sa_conversation_id").value || "").trim() || null,
              profile_id: profileId,
            });
          }
        }
      } catch (error) {
        showEl(paStatusEl, `<div class="error">${error.message || error}</div>`);
      } finally {
        paSwitchBtn.disabled = false;
      }
    }

    async function refreshPersonalDeals() {
      const profileId = paProfileSelect.value || activePersonalProfileId;
      paDealsBtn.disabled = true;
      try {
        const qs = profileId ? `?profile_id=${encodeURIComponent(profileId)}&limit=5` : "?limit=5";
        const response = await fetch(`/api/v1/personal/deals${qs}`);
        if (!response.ok) {
          const detail = await response.json().catch(() => ({}));
          throw new Error(detail.detail || "Failed to load deals.");
        }
        const body = await response.json();
        renderPersonalDeals(body);
        showEl(paStatusEl, `<div class="hint">Deals refreshed for ${escapeHtml(profileId || "active profile")}</div>`);
      } catch (error) {
        showEl(paStatusEl, `<div class="error">${error.message || error}</div>`);
      } finally {
        paDealsBtn.disabled = false;
      }
    }

    paSwitchBtn.addEventListener("click", switchPersonalProfile);
    paDemoBtn.addEventListener("click", () => loadPersonalDemo(paProfileSelect.value || null));
    paDealsBtn.addEventListener("click", refreshPersonalDeals);
    paProfileSelect.addEventListener("change", () => {
      // Instant preview on select change
      loadPersonalDemo(paProfileSelect.value || null);
    });
    loadPersonalDemo();

    // ---------------------------------------------------------- Sprint 20: Affiliate Revenue Engine
    const affRefreshBtn = document.getElementById("aff_refresh");
    const affGenLinkBtn = document.getElementById("aff_gen_link");
    const affTrackClickBtn = document.getElementById("aff_track_click");
    const affSummaryEl = document.getElementById("aff-summary");
    const affStatusEl = document.getElementById("aff-status");
    const affReportEl = document.getElementById("aff-report");
    const affMerchantsEl = document.getElementById("aff-merchants");
    const affTopProductsEl = document.getElementById("aff-top-products");
    const affLinksEl = document.getElementById("aff-links");
    const affClicksEl = document.getElementById("aff-clicks");
    const affDisclosureEl = document.getElementById("aff-disclosure");

    function affPct(value) {
      return `${((Number(value) || 0) * 100).toFixed(2)}%`;
    }

    function affMoney(value, currency) {
      const n = Number(value);
      if (!Number.isFinite(n)) return "—";
      return `${n.toFixed(2)} ${escapeHtml(currency || "USD")}`;
    }

    function renderAffBuckets(buckets) {
      if (!buckets || !buckets.length) return '<p class="empty-state">No data.</p>';
      return buckets.map((b) =>
        `<div class="card-line"><strong>${escapeHtml(b.label || b.key)}</strong> · ` +
        `${b.clicks} clicks · ${b.conversions} conv · CTR/CVR ${affPct(b.conversion_rate)} · ` +
        `est. ${affMoney(b.estimated_commission, b.currency)}</div>`
      ).join("");
    }

    async function affRefresh() {
      affStatusEl.textContent = "Loading affiliate dashboard…";
      try {
        const [reportRes, merchantsRes, linksRes, clicksRes, disclosureRes] = await Promise.all([
          fetch("/api/v1/affiliate/report"),
          fetch("/api/v1/affiliate/merchant"),
          fetch("/api/v1/affiliate/link?limit=20"),
          fetch("/api/v1/affiliate/click?limit=20"),
          fetch("/api/v1/affiliate/disclosure/resolve?region=US"),
        ]);
        const report = await reportRes.json();
        const merchantsBody = await merchantsRes.json();
        const linksBody = await linksRes.json();
        const clicksBody = await clicksRes.json();
        const disclosure = await disclosureRes.json();
        if (!reportRes.ok) throw new Error(report.detail || "Report failed");
        if (!merchantsRes.ok) throw new Error(merchantsBody.detail || "Merchants failed");

        affSummaryEl.innerHTML =
          `<div><strong>Clicks</strong> ${report.total_clicks} · <strong>CTR</strong> ${affPct(report.ctr)} · ` +
          `<strong>Conv rate</strong> ${affPct(report.conversion_rate)}</div>` +
          `<div><strong>Est. commission</strong> ${affMoney(report.estimated_commission, report.currency)} · ` +
          `<strong>Revenue</strong> ${affMoney(report.total_revenue, report.currency)} · ` +
          `<strong>Impressions</strong> ${report.impressions}</div>` +
          `<div class="hint">${escapeHtml(report.disclaimer || "")}</div>`;

        affReportEl.innerHTML =
          `<div class="card-line"><strong>By merchant</strong></div>${renderAffBuckets(report.by_merchant)}` +
          `<div class="card-line csp-inline-d3639b4955"><strong>By category</strong></div>${renderAffBuckets(report.by_category)}` +
          `<div class="card-line csp-inline-d3639b4955"><strong>Top converting merchants</strong></div>${renderAffBuckets(report.top_converting_merchants)}`;

        const merchants = merchantsBody.merchants || [];
        affMerchantsEl.innerHTML = merchants.length
          ? `<table class="csp-inline-8792cea7d2">
              <thead><tr>
                <th align="left">Merchant</th><th align="left">Marketplace</th>
                <th align="left">Commission</th><th align="left">Status</th>
                <th align="left">Health</th><th align="right">Priority</th>
              </tr></thead>
              <tbody>${merchants.map((m) =>
                `<tr>
                  <td>${escapeHtml(m.merchant_name)}</td>
                  <td>${escapeHtml(m.marketplace)}</td>
                  <td>${escapeHtml(String(m.commission_value))}${m.commission_type === "percent" ? "%" : " fixed"} / ${m.cookie_days}d</td>
                  <td>${escapeHtml(m.status)}</td>
                  <td>${escapeHtml(m.health_status)}</td>
                  <td align="right">${m.priority}</td>
                </tr>`
              ).join("")}</tbody></table>`
          : '<p class="empty-state">No merchants.</p>';

        affTopProductsEl.innerHTML = renderAffBuckets(report.top_converting_products);

        const links = linksBody.links || [];
        affLinksEl.innerHTML = links.length
          ? links.map((l) =>
              `<div class="card-line"><strong>${escapeHtml(l.product_name)}</strong> · ${escapeHtml(l.marketplace)}` +
              `<div class="csp-inline-3eeaa5ef1d">${escapeHtml(l.affiliate_url)}</div></div>`
            ).join("")
          : '<p class="empty-state">No generated links yet.</p>';

        const clicks = clicksBody.clicks || [];
        affClicksEl.innerHTML = clicks.length
          ? clicks.map((c) =>
              `<div class="card-line"><strong>${escapeHtml(c.click_id)}</strong> · ${escapeHtml(c.product_name || c.product_id)}` +
              ` · ${escapeHtml(c.source)} · ${escapeHtml(c.conversion_status)} · est. ${affMoney(c.estimated_commission, c.currency)}</div>`
            ).join("")
          : '<p class="empty-state">No clicks yet.</p>';

        affDisclosureEl.innerHTML =
          `<div class="card-line">${escapeHtml(disclosure.combined_text || "")}</div>` +
          `<div class="hint">${escapeHtml(disclosure.disclaimer || "")}</div>`;

        affStatusEl.innerHTML = '<div class="hint">Affiliate dashboard loaded (demo data only).</div>';
      } catch (err) {
        affStatusEl.innerHTML = `<div class="error">${escapeHtml(err.message || String(err))}</div>`;
      }
    }

    async function affGenerateLink() {
      affStatusEl.textContent = "Generating demo affiliate link…";
      try {
        const response = await fetch("/api/v1/affiliate/link", {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify({
            product_id: "prod-iphone-17-pro",
            product_name: "iPhone 17 Pro",
            marketplace: "shopee",
            country: "PH",
            category: "smartphones",
            campaign_id: "demo-ui",
            sub_id: "dashboard",
            order_value: 899,
          }),
        });
        const body = await response.json();
        if (!response.ok) throw new Error(body.detail || "Link generation failed");
        affStatusEl.innerHTML = `<div class="hint">Generated link <code>${escapeHtml(body.link_id)}</code></div>`;
        await affRefresh();
      } catch (err) {
        affStatusEl.innerHTML = `<div class="error">${escapeHtml(err.message || String(err))}</div>`;
      }
    }

    async function affTrackClick() {
      affStatusEl.textContent = "Tracking demo click…";
      try {
        const linksRes = await fetch("/api/v1/affiliate/link?limit=1");
        const linksBody = await linksRes.json();
        const link = (linksBody.links || [])[0];
        const payload = link
          ? { link_id: link.link_id, source: "affiliate_dashboard", device: "desktop", country: "PH" }
          : {
              merchant_id: "merchant-shopee-ph",
              product_id: "prod-iphone-17-pro",
              product_name: "iPhone 17 Pro",
              category: "smartphones",
              source: "affiliate_dashboard",
              device: "desktop",
              country: "PH",
              estimated_commission: 49.45,
            };
        const response = await fetch("/api/v1/affiliate/click", {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify(payload),
        });
        const body = await response.json();
        if (!response.ok) throw new Error(body.detail || "Click tracking failed");
        affStatusEl.innerHTML = `<div class="hint">Tracked click <code>${escapeHtml(body.click_id)}</code></div>`;
        await affRefresh();
      } catch (err) {
        affStatusEl.innerHTML = `<div class="error">${escapeHtml(err.message || String(err))}</div>`;
      }
    }

    if (affRefreshBtn) affRefreshBtn.addEventListener("click", affRefresh);
    if (affGenLinkBtn) affGenLinkBtn.addEventListener("click", affGenerateLink);
    if (affTrackClickBtn) affTrackClickBtn.addEventListener("click", affTrackClick);

    const saAskBtn = document.getElementById("sa_ask");
    const saDemoBtn = document.getElementById("sa_demo");
    const saQueryInput = document.getElementById("sa_query");
    const saModeInput = document.getElementById("sa_mode");
    const saConversationInput = document.getElementById("sa_conversation_id");
    const saUseProfileInput = document.getElementById("sa_use_profile");
    const saExamplesEl = document.getElementById("sa-examples");
    const saSentimentEl = document.getElementById("sa-sentiment");
    const saMetaEl = document.getElementById("sa-meta");
    const saStatusEl = document.getElementById("sa-status");
    const saAnswerEl = document.getElementById("sa-answer");
    const saPersonalEl = document.getElementById("sa-personal");
    const saTopEl = document.getElementById("sa-top");
    const saAltsEl = document.getElementById("sa-alts");
    const saComparisonEl = document.getElementById("sa-comparison");
    const saEvidenceEl = document.getElementById("sa-evidence");
    const saWarningsEl = document.getElementById("sa-warnings");
    const saDisagreementsEl = document.getElementById("sa-disagreements");

    function renderShoppingAssistant(body) {
      const top = body.top_recommendation;
      saSentimentEl.innerHTML = [
        rvStat("Intent", escapeHtml(body.intent || "—"), true),
        rvStat("Confidence", body.confidence ? `${escapeHtml(body.confidence.band)} (${Number(body.confidence.score).toFixed(2)})` : "—", true),
        rvStat("Data status", escapeHtml(body.data_status || "mock"), true),
        rvStat("Fallback", body.fallback_used ? "Yes" : "No"),
      ].join("");
      const providers = (body.providers_used || []).join(", ") || "—";
      const personalMode = (body.processing && body.processing.personalization_mode) || "generic";
      saMetaEl.innerHTML = [
        rvStat("Mode", escapeHtml(body.mode || "economy"), true),
        rvStat("Personalization", escapeHtml(personalMode), true),
        rvStat("Profile", escapeHtml(body.profile_id || "—")),
        rvStat("Providers used", escapeHtml(providers)),
        rvStat("Conversation", escapeHtml(body.conversation_id || "—")),
        rvStat("Allowed modes", escapeHtml((body.allowed_modes || []).join(", ") || "economy")),
      ].join("");
      saAnswerEl.innerHTML = body.answer
        ? `<p class="csp-inline-ce31057250">${escapeHtml(body.answer)}</p>`
        : '<p class="empty-state">No answer.</p>';
      const personal = body.personal_recommendation;
      if (personal && personal.recommendation) {
        const rec = personal.recommendation;
        const advice = personal.advice || rec.advice;
        saPersonalEl.innerHTML = [
          rvStat("Profile", escapeHtml(personal.profile_name || personal.profile_id || "—"), true),
          rvStat("Product", escapeHtml(rec.product_name || "—"), true),
          rvStat("Personalized PiqScore", rec.personal_deal_score != null ? Number(rec.personal_deal_score).toFixed(1) : "—", true),
          rvStat("Advisor", escapeHtml((advice && advice.label) || "—")),
          `<p class="csp-inline-5884433a5f">${escapeHtml(rec.explanation || rec.reason || "")}</p>`,
        ].join("");
      } else {
        saPersonalEl.innerHTML = '<p class="empty-state">Generic mode — no personal profile applied.</p>';
      }
      if (top) {
        saTopEl.innerHTML = [
          rvStat("Product", escapeHtml(top.product_name), true),
          rvStat("Price", top.known_price != null ? `${Number(top.known_price).toLocaleString()} ${escapeHtml(top.currency || "")}` : "—"),
          rvStat("Marketplace", escapeHtml(top.marketplace || "—")),
          rvStat("PiqScore", top.deal_score != null ? Number(top.deal_score).toFixed(1) : "—", true),
          `<p class="csp-inline-5884433a5f">${escapeHtml(top.reason || "")}</p>`,
        ].join("");
      } else {
        saTopEl.innerHTML = '<p class="empty-state">No top recommendation.</p>';
      }
      const alts = body.alternatives || [];
      saAltsEl.innerHTML = alts.length
        ? `<ul class="csp-inline-b20f3b6fe5">${alts.map((item) =>
          `<li><strong>${escapeHtml(item.product_name)}</strong> · PiqScore ${item.deal_score != null ? Number(item.deal_score).toFixed(1) : "—"} · ${item.known_price != null ? Number(item.known_price).toLocaleString() + " " + escapeHtml(item.currency || "") : "—"}</li>`
        ).join("")}</ul>`
        : '<p class="empty-state">No alternatives.</p>';
      const comparison = body.comparison;
      if (!comparison) {
        saComparisonEl.innerHTML = '<p class="empty-state">No comparison for this query.</p>';
      } else {
        const winners = (comparison.category_winners || []).map((w) =>
          `<tr><td>${escapeHtml(w.category)}</td><td>${escapeHtml(w.product_name)}</td><td>${escapeHtml(w.reason)}</td></tr>`
        ).join("");
        saComparisonEl.innerHTML = `
          <p class="csp-inline-cfd9149bca">${escapeHtml(comparison.overall_recommendation || "")}</p>
          <table class="csp-inline-8792cea7d2">
            <thead><tr><th align="left">Category</th><th align="left">Winner</th><th align="left">Reason</th></tr></thead>
            <tbody>${winners || '<tr><td colspan="3">No category winners.</td></tr>'}</tbody>
          </table>
          <p class="hint csp-inline-1e59f5bb72">${escapeHtml((comparison.unresolved_uncertainty || [])[0] || "")}</p>
        `;
      }
      const evidence = body.evidence || [];
      saEvidenceEl.innerHTML = evidence.length
        ? `<ul class="csp-inline-b20f3b6fe5">${evidence.slice(0, 12).map((item) =>
          `<li><strong>${escapeHtml(item.type)}</strong>: ${escapeHtml(item.description)}</li>`
        ).join("")}</ul>`
        : '<p class="empty-state">No evidence items.</p>';
      const warnings = (body.warnings || []).map((w) => w.message || w);
      saWarningsEl.innerHTML = renderBulletList(warnings, "No warnings.");
      const disagreements = body.disagreements || [];
      saDisagreementsEl.innerHTML = disagreements.length
        ? `<ul class="csp-inline-b20f3b6fe5">${disagreements.map((d) =>
          `<li><strong>${escapeHtml(d.field || "claim")}</strong>: ${escapeHtml(d.detail || "")}</li>`
        ).join("")}</ul>`
        : '<p class="empty-state">No model disagreements reported.</p>';
      if (body.conversation_id) {
        saConversationInput.value = body.conversation_id;
      }
    }

    async function askShoppingAssistant(payload) {
      showEl(
        saStatusEl,
        '<div class="loading"><span class="spinner" aria-hidden="true"></span> Asking shopping assistant…</div>'
      );
      try {
        const response = await fetch("/api/v1/shopping-assistant/query", {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify(payload),
        });
        if (!response.ok) {
          const detail = await response.json().catch(() => ({}));
          throw new Error(detail.detail || "Shopping assistant request failed.");
        }
        const body = await response.json();
        renderShoppingAssistant(body);
        const fallbackNote = body.fallback_used
          ? ` · fallback${body.fallback_reason ? ` (${escapeHtml(body.fallback_reason)})` : ""}`
          : "";
        showEl(
          saStatusEl,
          `<div class="hint">Mock/demo results · mode: ${escapeHtml(body.mode || "economy")} · providers: ${escapeHtml((body.providers_used || []).join(", ") || "—")}${fallbackNote}</div>`
        );
      } catch (error) {
        showEl(saStatusEl, `<div class="error">${error.message || error}</div>`);
      }
    }

    async function askFromForm() {
      const query = (saQueryInput.value || "").trim();
      if (!query) {
        showEl(saStatusEl, '<div class="error">Query is required.</div>');
        return;
      }
      saAskBtn.disabled = true;
      try {
        const payload = {
          query,
          mode: saModeInput.value || "economy",
          conversation_id: (saConversationInput.value || "").trim() || null,
        };
        if (saUseProfileInput && saUseProfileInput.value === "1") {
          payload.profile_id = paProfileSelect.value || activePersonalProfileId || null;
        }
        await askShoppingAssistant(payload);
      } finally {
        saAskBtn.disabled = false;
      }
    }

    async function loadShoppingDemo() {
      saDemoBtn.disabled = true;
      showEl(
        saStatusEl,
        '<div class="loading"><span class="spinner" aria-hidden="true"></span> Loading demo…</div>'
      );
      try {
        const mode = saModeInput.value || "economy";
        const response = await fetch(`/api/v1/shopping-assistant/demo?mode=${encodeURIComponent(mode)}`);
        if (!response.ok) {
          const detail = await response.json().catch(() => ({}));
          throw new Error(detail.detail || "Failed to load shopping demo.");
        }
        const body = await response.json();
        saQueryInput.value = body.query || saQueryInput.value;
        renderShoppingAssistant(body);
        showEl(
          saStatusEl,
          `<div class="hint">Demo loaded · mock/imported data · mode: ${escapeHtml(body.mode || "economy")}</div>`
        );
      } catch (error) {
        showEl(saStatusEl, `<div class="error">${error.message || error}</div>`);
      } finally {
        saDemoBtn.disabled = false;
      }
    }

    async function loadShoppingMeta() {
      try {
        const response = await fetch("/api/v1/shopping-assistant/meta");
        if (!response.ok) return;
        const body = await response.json();
        const examples = body.example_queries || [];
        saExamplesEl.innerHTML = examples.length
          ? `<div class="csp-inline-263981b302">${examples.slice(0, 6).map((q) =>
            `<button type="button" class="sa-example csp-inline-f4b94616ed">${escapeHtml(q)}</button>`
          ).join("")}</div>`
          : "";
        saExamplesEl.querySelectorAll(".sa-example").forEach((btn) => {
          btn.addEventListener("click", () => {
            saQueryInput.value = btn.textContent || "";
          });
        });
        const allowed = new Set(body.allowed_modes || ["economy"]);
        Array.from(saModeInput.options).forEach((opt) => {
          opt.disabled = !allowed.has(opt.value);
        });
      } catch (_error) {
        // Meta is optional for the demo panel.
      }
    }

    saAskBtn.addEventListener("click", askFromForm);
    saDemoBtn.addEventListener("click", loadShoppingDemo);
    loadShoppingMeta();
    loadShoppingDemo();

    const ciLoadBtn = document.getElementById("ci_load");
    const ciDemoBtn = document.getElementById("ci_demo");
    const ciProductInput = document.getElementById("ci_product_id");
    const ciModeInput = document.getElementById("ci_mode");
    const ciTrustEl = document.getElementById("ci-trust");
    const ciMetaEl = document.getElementById("ci-meta");
    const ciStatusEl = document.getElementById("ci-status");
    const ciSourcesEl = document.getElementById("ci-sources");
    const ciTopicsEl = document.getElementById("ci-topics");
    const ciPositiveEl = document.getElementById("ci-positive");
    const ciNegativeEl = document.getElementById("ci-negative");
    const ciTimelineEl = document.getElementById("ci-timeline");
    const ciConnectorsEl = document.getElementById("ci-connectors");
    const ciRecentEl = document.getElementById("ci-recent");
    const ciExplorerEl = document.getElementById("ci-explorer");
    const ciSummaryEl = document.getElementById("ci-summary");
    const ciWarningsEl = document.getElementById("ci-warnings");

    function renderCommunityDashboard(body) {
      const trust = body.trust || {};
      ciTrustEl.innerHTML = [
        rvStat("Community Trust", trust.score != null ? String(trust.score) : "—", true),
        rvStat("Band", escapeHtml(trust.band || "—"), true),
        rvStat("Evidence count", body.evidence_count != null ? String(body.evidence_count) : "—", true),
        rvStat("Data status", escapeHtml(body.data_status || "mock")),
      ].join("");
      ciMetaEl.innerHTML = [
        rvStat("Product", escapeHtml(body.product_name || "—"), true),
        rvStat("Product ID", escapeHtml(body.product_id || "—")),
        rvStat("Positive topics", escapeHtml((body.positive_topics || []).slice(0, 3).join(", ") || "—")),
        rvStat("Negative topics", escapeHtml((body.negative_topics || []).slice(0, 3).join(", ") || "—")),
      ].join("");
      const sources = body.source_breakdown || body.connector_status || [];
      ciSourcesEl.innerHTML = sources.length
        ? `<ul class="csp-inline-b20f3b6fe5">${sources.map((s) =>
          `<li><strong>${escapeHtml(s.source)}</strong> · ${escapeHtml(s.status)} · ${s.evidence_count || 0} evidence · eng ${Number(s.average_engagement || 0).toFixed(1)}</li>`
        ).join("")}</ul>`
        : '<p class="empty-state">No source metrics.</p>';
      const topics = body.topics || [];
      ciTopicsEl.innerHTML = topics.length
        ? `<table class="csp-inline-8792cea7d2">
            <thead><tr><th align="left">Topic</th><th align="left">Mentions</th><th align="left">Sentiment</th><th align="left">Confidence</th></tr></thead>
            <tbody>${topics.slice(0, 12).map((t) =>
              `<tr><td>${escapeHtml(t.name)}</td><td>${t.mention_count}</td><td>${escapeHtml((t.sentiment && t.sentiment.label) || "—")}</td><td>${escapeHtml(t.confidence || "—")}</td></tr>`
            ).join("")}</tbody></table>`
        : '<p class="empty-state">No topics.</p>';
      ciPositiveEl.innerHTML = renderBulletList(body.positive_topics || [], "No positive topics.");
      ciNegativeEl.innerHTML = renderBulletList(body.negative_topics || [], "No negative topics.");
      const timeline = body.timeline || [];
      ciTimelineEl.innerHTML = timeline.length
        ? `<ul class="csp-inline-b20f3b6fe5">${timeline.map((e) =>
          `<li>${escapeHtml((e.timestamp || "").slice(0, 10))} · ${e.evidence_count} evidence · +${e.positive_count}/-${e.negative_count}</li>`
        ).join("")}</ul>`
        : '<p class="empty-state">No timeline events.</p>';
      ciConnectorsEl.innerHTML = sources.length
        ? `<ul class="csp-inline-b20f3b6fe5">${sources.map((s) =>
          `<li><strong>${escapeHtml(s.source)}</strong>: ${escapeHtml(s.status)}${s.enabled ? " (enabled)" : " (disabled)"} · ${escapeHtml(s.transport || "mock")}</li>`
        ).join("")}</ul>`
        : '<p class="empty-state">No connectors.</p>';
      const recent = body.recent_discussions || [];
      ciRecentEl.innerHTML = recent.length
        ? `<ul class="csp-inline-b20f3b6fe5">${recent.map((d) =>
          `<li><strong>${escapeHtml(d.source)}</strong> · ${escapeHtml(d.topic || "")}: ${escapeHtml(d.title || d.body || "")}</li>`
        ).join("")}</ul>`
        : '<p class="empty-state">No recent discussions.</p>';
      ciExplorerEl.innerHTML = topics.length
        ? topics.slice(0, 6).map((t) => {
          const label = (t.sentiment && t.sentiment.label === "positive") ? "Excellent" : ((t.sentiment && t.sentiment.label) || "Mixed");
          const ids = (t.evidence_ids || []).slice(0, 4);
          return `<div class="csp-inline-f9bcedfd33">
            <strong>${escapeHtml(t.name)} ${escapeHtml(label)}</strong>
            <div class="hint">Confidence ${escapeHtml(t.confidence || "—")}</div>
            <div>Supported by:</div>
            <ul class="csp-inline-0795f14a67">${ids.map((id) => `<li>${escapeHtml(id)}</li>`).join("") || "<li>No evidence IDs</li>"}</ul>
          </div>`;
        }).join("")
        : '<p class="empty-state">No explorer insights.</p>';
      const summary = body.summary || {};
      const praised = (summary.most_praised || []).map((i) => i.statement);
      const complaints = (summary.most_complaints || []).map((i) => i.statement);
      const advice = (summary.buying_advice || []).map((i) => i.statement);
      ciSummaryEl.innerHTML = `
        <p class="hint csp-inline-1727ad60a8">Provider: ${escapeHtml(summary.provider || "deterministic")} · mode: ${escapeHtml(summary.mode || "economy")}</p>
        <div><strong>Most praised</strong>${renderBulletList(praised, "None")}</div>
        <div class="csp-inline-1e59f5bb72"><strong>Most complaints</strong>${renderBulletList(complaints, "None")}</div>
        <div class="csp-inline-1e59f5bb72"><strong>Buying advice</strong>${renderBulletList(advice, "None")}</div>
      `;
      const warnings = (body.warnings || []).map((w) => w.message || w);
      ciWarningsEl.innerHTML = renderBulletList(warnings, "No warnings.");
      if (body.product_id) ciProductInput.value = body.product_id;
    }

    async function loadCommunityDemo() {
      ciDemoBtn.disabled = true;
      showEl(ciStatusEl, '<div class="loading"><span class="spinner" aria-hidden="true"></span> Loading community dashboard…</div>');
      try {
        const mode = ciModeInput.value || "economy";
        const response = await fetch(`/api/v1/community/demo?mode=${encodeURIComponent(mode)}`);
        if (!response.ok) {
          const detail = await response.json().catch(() => ({}));
          throw new Error(detail.detail || "Failed to load community demo.");
        }
        const body = await response.json();
        renderCommunityDashboard(body);
        showEl(ciStatusEl, `<div class="hint">Dashboard loaded · trust ${body.trust ? body.trust.score : "—"} · ${body.evidence_count || 0} evidence</div>`);
      } catch (error) {
        showEl(ciStatusEl, `<div class="error">${error.message || error}</div>`);
      } finally {
        ciDemoBtn.disabled = false;
      }
    }

    async function loadCommunityProduct() {
      const productId = (ciProductInput.value || "").trim();
      if (!productId) {
        showEl(ciStatusEl, '<div class="error">Product ID is required.</div>');
        return;
      }
      ciLoadBtn.disabled = true;
      showEl(ciStatusEl, '<div class="loading"><span class="spinner" aria-hidden="true"></span> Loading product community intel…</div>');
      try {
        const mode = ciModeInput.value || "economy";
        const response = await fetch(`/api/v1/community/product/${encodeURIComponent(productId)}?mode=${encodeURIComponent(mode)}`);
        if (!response.ok) {
          const detail = await response.json().catch(() => ({}));
          throw new Error(detail.detail || "Failed to load community product.");
        }
        const body = await response.json();
        renderCommunityDashboard({
          ...body,
          source_breakdown: body.source_metrics || [],
          connector_status: body.source_metrics || [],
          recent_discussions: (body.evidence || []).slice(0, 8),
          positive_topics: (body.topics || []).filter((t) => t.sentiment && t.sentiment.label === "positive").map((t) => t.name),
          negative_topics: (body.topics || []).filter((t) => t.negative_count > t.positive_count).map((t) => t.name),
        });
        showEl(ciStatusEl, `<div class="hint">Product loaded · trust ${body.trust ? body.trust.score : "—"} · ${body.evidence_count || 0} evidence</div>`);
      } catch (error) {
        showEl(ciStatusEl, `<div class="error">${error.message || error}</div>`);
      } finally {
        ciLoadBtn.disabled = false;
      }
    }

    ciLoadBtn.addEventListener("click", loadCommunityProduct);
    ciDemoBtn.addEventListener("click", loadCommunityDemo);
    loadCommunityDemo();

    // --- Knowledge Graph panel ---
    const kgProductInput = document.getElementById("kg_product_id");
    const kgLoadBtn = document.getElementById("kg_load");
    const kgDemoBtn = document.getElementById("kg_demo");
    const kgMetaEl = document.getElementById("kg-meta");
    const kgStatusEl = document.getElementById("kg-status");
    const kgSummaryEl = document.getElementById("kg-summary");
    const kgNodeCountsEl = document.getElementById("kg-node-counts");
    const kgEdgeCountsEl = document.getElementById("kg-edge-counts");
    const kgSellersEl = document.getElementById("kg-sellers");
    const kgEvidenceEl = document.getElementById("kg-evidence");
    const kgTopicsEl = document.getElementById("kg-topics");
    const kgSimilarEl = document.getElementById("kg-similar");
    const kgContradictionsEl = document.getElementById("kg-contradictions");
    const kgVizEl = document.getElementById("kg-viz");
    const kgWarningsEl = document.getElementById("kg-warnings");

    function renderCountMap(map) {
      const entries = Object.entries(map || {});
      if (!entries.length) return '<p class="empty-state">None.</p>';
      return `<ul class="csp-inline-b20f3b6fe5">${entries.map(([k, v]) =>
        `<li><strong>${escapeHtml(k)}</strong>: ${escapeHtml(String(v))}</li>`
      ).join("")}</ul>`;
    }

    function renderKgViz(body) {
      const root = body.root_node;
      const nodes = (body.nodes || []).slice(0, 18);
      if (!root || !nodes.length) {
        kgVizEl.innerHTML = '<p class="empty-state">No graph nodes to visualize.</p>';
        return;
      }
      const width = 640;
      const height = 320;
      const cx = width / 2;
      const cy = height / 2;
      const radius = 120;
      const others = nodes.filter((n) => n.node_id !== root.node_id);
      const points = others.map((node, index) => {
        const angle = (Math.PI * 2 * index) / Math.max(others.length, 1) - Math.PI / 2;
        return {
          ...node,
          x: cx + radius * Math.cos(angle),
          y: cy + radius * Math.sin(angle),
        };
      });
      const lines = points.map((p) =>
        `<line x1="${cx}" y1="${cy}" x2="${p.x}" y2="${p.y}" stroke="#94a3b8" stroke-width="1.5" />`
      ).join("");
      const circles = points.map((p) =>
        `<g>
          <circle cx="${p.x}" cy="${p.y}" r="10" fill="#0d9488" />
          <title>${escapeHtml(p.label)} (${escapeHtml(p.node_type)})</title>
        </g>`
      ).join("");
      kgVizEl.innerHTML = `
        <svg viewBox="0 0 ${width} ${height}" width="100%" height="${height}" role="img" aria-label="Knowledge graph explorer">
          ${lines}
          <circle cx="${cx}" cy="${cy}" r="16" fill="#0f172a" />
          <text x="${cx}" y="${cy + 36}" text-anchor="middle" font-size="12" fill="#0f172a">${escapeHtml(root.label.slice(0, 42))}</text>
          ${circles}
        </svg>
        <p class="hint">Lightweight SVG explorer · fixture data · truncated to ${nodes.length} nodes</p>
      `;
    }

    function renderKnowledgeGraph(body) {
      const summary = body.summary || {};
      const root = body.root_node || {};
      kgMetaEl.innerHTML = `
        <span class="pill">data_status: ${escapeHtml(body.data_status || "mock")}</span>
        <span class="pill">truncated: ${body.truncated ? "yes" : "no"}</span>
        <span class="pill">nodes: ${(body.nodes || []).length}</span>
        <span class="pill">edges: ${(body.edges || []).length}</span>
        <span class="pill">confidence method: min edge</span>
      `;
      kgSummaryEl.innerHTML = `
        <p class="csp-inline-9ef7edc7a9"><strong>${escapeHtml(root.label || "Product")}</strong>
        · type ${escapeHtml(root.node_type || "product")}
        · confidence ${escapeHtml(String(root.confidence ?? "—"))}</p>
      `;
      kgNodeCountsEl.innerHTML = renderCountMap(summary.node_counts || {});
      kgEdgeCountsEl.innerHTML = renderCountMap(summary.edge_counts || {});
      kgSellersEl.innerHTML = renderBulletList(
        [
          ...((summary.sellers || []).map((s) => `Seller: ${s}`)),
          ...((summary.marketplaces || []).map((m) => `Marketplace: ${m}`)),
          ...((summary.price_history || []).map((p) => `Price history: ${p}`)),
        ],
        "No sellers/marketplaces linked."
      );
      kgEvidenceEl.innerHTML = renderBulletList(
        [
          ...((summary.reviews || []).map((r) => `Review: ${r}`)),
          ...((summary.community_evidence || []).map((c) => `Community: ${c}`)),
          ...((summary.ai_summaries || []).map((a) => `AI summary: ${a}`)),
        ],
        "No review/community evidence."
      );
      kgTopicsEl.innerHTML = renderBulletList(
        [
          ...((summary.topics || []).map((t) => `Topic: ${t}`)),
          ...((summary.brands || []).map((b) => `Brand: ${b}`)),
          ...((summary.categories || []).map((c) => `Category: ${c}`)),
        ],
        "No topics/brands/categories."
      );
      kgSimilarEl.innerHTML = renderBulletList(summary.similar_products || [], "No similar products.");
      const contradictions = body.contradictions || [];
      kgContradictionsEl.innerHTML = contradictions.length
        ? `<ul class="csp-inline-b20f3b6fe5">${contradictions.map((c) =>
          `<li>${escapeHtml(c.other_label || c.edge_id || "contradiction")} · confidence ${escapeHtml(String(c.confidence ?? "—"))}</li>`
        ).join("")}</ul>`
        : '<p class="empty-state">No contradictions detected.</p>';
      renderKgViz(body);
      kgWarningsEl.innerHTML = renderBulletList(body.warnings || [], "No warnings.");
    }

    async function loadKnowledgeGraph(url, label) {
      showEl(kgStatusEl, `<div class="loading"><span class="spinner" aria-hidden="true"></span> Loading ${escapeHtml(label)}…</div>`);
      try {
        const response = await fetch(url);
        if (!response.ok) {
          const detail = await response.json().catch(() => ({}));
          throw new Error(detail.detail || `Failed to load ${label}.`);
        }
        const body = await response.json();
        renderKnowledgeGraph(body);
        showEl(
          kgStatusEl,
          `<div class="hint">Fixture/mock graph · data_status: ${escapeHtml(body.data_status || "mock")} · ${(body.nodes || []).length} nodes</div>`
        );
      } catch (error) {
        showEl(kgStatusEl, `<div class="error">${error.message || error}</div>`);
      }
    }

    async function loadKgDemo() {
      kgDemoBtn.disabled = true;
      try {
        await loadKnowledgeGraph("/api/v1/graph/demo", "knowledge graph demo");
      } finally {
        kgDemoBtn.disabled = false;
      }
    }

    async function loadKgProduct() {
      const productId = (kgProductInput.value || "").trim();
      if (!productId) {
        showEl(kgStatusEl, '<div class="error">Product ID is required.</div>');
        return;
      }
      kgLoadBtn.disabled = true;
      try {
        await loadKnowledgeGraph(`/api/v1/graph/product/${encodeURIComponent(productId)}`, "product graph");
      } finally {
        kgLoadBtn.disabled = false;
      }
    }

    kgLoadBtn.addEventListener("click", loadKgProduct);
    kgDemoBtn.addEventListener("click", loadKgDemo);
    loadKgDemo();

    // Shared auth token for User Platform + Marketplace Data ops
    let upAccessToken = null;
    let upUserId = null;

    // --- Marketplace Data panel ---
    const mdStatusEl = document.getElementById("md-status");
    const mdSourcesEl = document.getElementById("md-sources");
    const mdOpsEl = document.getElementById("md-ops");
    const mdOffersEl = document.getElementById("md-offers");
    const mdHistoryEl = document.getElementById("md-history");
    const mdConnector = document.getElementById("md_connector");
    const mdImport = document.getElementById("md_import");
    const mdProductId = document.getElementById("md_product_id");
    const MD_SAMPLE_CSV = "marketplace_product_id,title,brand,model,category,sku,upc,currency,regular_price,sale_price,shipping_cost,availability,inventory_quantity,seller_name,seller_rating,marketplace_url\\nimp-demo-1,Apple iPhone 15 Pro 256GB Import,Apple,iPhone 15 Pro,Smartphones,IP15PRO-256,194253431413,PHP,71000,69500,50,in_stock,5,Import Seller PH,4.5,https://imported.dealbrain.local/iphone";

    function mdAuthHeaders() {
      const headers = { "Content-Type": "application/json" };
      if (typeof upAccessToken !== "undefined" && upAccessToken) {
        headers["Authorization"] = `Bearer ${upAccessToken}`;
      }
      return headers;
    }

    function mdRenderOffer(o) {
      const freshness = o.freshness ? `${o.freshness.status}` : "unknown";
      const match = o.match_confidence != null ? Number(o.match_confidence).toFixed(2) : "n/a";
      return `<div class="csp-inline-8d25ea81e1">
        <strong>${escapeHtml(o.title)}</strong><br/>
        mode=<code>${escapeHtml(o.source_mode)}</code>
        · freshness=<code>${escapeHtml(freshness)}</code>
        · match=${escapeHtml(match)} (${escapeHtml(o.match_ambiguity || "")})
        · ${escapeHtml(String(o.total_price))} ${escapeHtml(o.currency)}
        <div class="hint">${escapeHtml(o.label || "")}</div>
        <div class="hint">${escapeHtml((o.freshness && o.freshness.warning) || "")}</div>
        <div class="hint">reasons: ${escapeHtml((o.match_reasons || []).join("; "))}</div>
      </div>`;
    }

    async function mdLoadSources() {
      mdStatusEl.innerHTML = '<div class="loading"><span class="spinner" aria-hidden="true"></span> Loading sources…</div>';
      try {
        const [sourcesRes, connectorsRes] = await Promise.all([
          fetch("/api/v1/marketplaces/sources"),
          fetch("/api/v1/marketplaces/connectors?include_stubs=true"),
        ]);
        const sources = await sourcesRes.json();
        const connectors = await connectorsRes.json();
        mdSourcesEl.innerHTML = `
          <div><strong>Sources</strong><ul>${(sources.sources || []).map((s) =>
            `<li>${escapeHtml(s.name)} · <code>${escapeHtml(s.source_mode)}</code> · ${escapeHtml(s.label || "")}</li>`
          ).join("")}</ul></div>
          <div><strong>Connectors</strong><ul>${(connectors.connectors || []).map((c) =>
            `<li>${escapeHtml(c.name)} · caps=${escapeHtml((c.capabilities || []).slice(0,4).join(", "))}
            ${c.simulated ? " · <strong>SIMULATED LIVE</strong>" : ""} · enabled=${c.enabled}</li>`
          ).join("")}</ul></div>`;
        mdStatusEl.innerHTML = `<div class="hint">${sources.count || 0} sources · ${connectors.count || 0} connectors</div>`;
      } catch (err) {
        mdStatusEl.innerHTML = `<div class="error">${escapeHtml(err.message || String(err))}</div>`;
      }
    }

    async function mdSeed() {
      mdStatusEl.innerHTML = '<div class="loading"><span class="spinner" aria-hidden="true"></span> Seeding demo sync…</div>';
      try {
        const response = await fetch("/api/v1/marketplaces/demo/seed", {
          method: "POST",
          headers: mdAuthHeaders(),
        });
        const body = await response.json();
        if (!response.ok) throw new Error(body.detail || "Seed failed — login via User Platform first");
        mdOpsEl.innerHTML = `<pre>${escapeHtml(JSON.stringify(body, null, 2))}</pre>
          <div class="hint"><strong>${escapeHtml(body.label || "")}</strong></div>`;
        mdStatusEl.innerHTML = `<div class="hint">Seeded · offers=${body.offers}</div>`;
        await mdLoadOffers();
      } catch (err) {
        mdStatusEl.innerHTML = `<div class="error">${escapeHtml(err.message || String(err))}</div>`;
      }
    }

    async function mdLoadOffers() {
      try {
        const response = await fetch("/api/v1/marketplaces/offers?limit=20");
        const body = await response.json();
        mdOffersEl.innerHTML = (body.offers || []).map(mdRenderOffer).join("") || "<div class='hint'>No offers yet — seed or import.</div>";
      } catch (err) {
        mdOffersEl.innerHTML = `<div class="error">${escapeHtml(err.message || String(err))}</div>`;
      }
    }

    async function mdTest() {
      try {
        const response = await fetch(`/api/v1/marketplaces/connectors/${encodeURIComponent(mdConnector.value)}/test`, {
          method: "POST",
          headers: mdAuthHeaders(),
        });
        const body = await response.json();
        if (!response.ok) throw new Error(body.detail || "Test failed");
        mdOpsEl.innerHTML = `<pre>${escapeHtml(JSON.stringify(body, null, 2))}</pre>`;
        mdStatusEl.innerHTML = `<div class="hint">${body.ok ? "OK" : "Failed"} · ${escapeHtml(body.label || body.message || "")}</div>`;
      } catch (err) {
        mdStatusEl.innerHTML = `<div class="error">${escapeHtml(err.message || String(err))}</div>`;
      }
    }

    async function mdHealth() {
      try {
        const response = await fetch(`/api/v1/marketplaces/connectors/${encodeURIComponent(mdConnector.value)}/health`);
        const body = await response.json();
        if (!response.ok) throw new Error(body.detail || "Health failed");
        mdOpsEl.innerHTML = `<pre>${escapeHtml(JSON.stringify(body, null, 2))}</pre>`;
        mdStatusEl.innerHTML = `<div class="hint">Health: ${escapeHtml(body.status)}</div>`;
      } catch (err) {
        mdStatusEl.innerHTML = `<div class="error">${escapeHtml(err.message || String(err))}</div>`;
      }
    }

    async function mdSync() {
      try {
        const response = await fetch("/api/v1/marketplaces/sync", {
          method: "POST",
          headers: mdAuthHeaders(),
          body: JSON.stringify({ connector_id: mdConnector.value, mode: "full" }),
        });
        const body = await response.json();
        if (!response.ok) throw new Error(body.detail || "Sync failed");
        mdOpsEl.innerHTML = `<pre>${escapeHtml(JSON.stringify(body, null, 2))}</pre>`;
        mdStatusEl.innerHTML = `<div class="hint">Sync ${escapeHtml(body.status)} · ${escapeHtml(body.summary || "")}</div>`;
        await mdLoadOffers();
      } catch (err) {
        mdStatusEl.innerHTML = `<div class="error">${escapeHtml(err.message || String(err))}</div>`;
      }
    }

    async function mdDoImport(filename, contentType) {
      try {
        const response = await fetch("/api/v1/marketplaces/imports", {
          method: "POST",
          headers: mdAuthHeaders(),
          body: JSON.stringify({
            filename,
            content: mdImport.value,
            content_type: contentType,
          }),
        });
        const body = await response.json();
        if (!response.ok) throw new Error(body.detail || "Import failed");
        mdOpsEl.innerHTML = `<pre>${escapeHtml(JSON.stringify(body, null, 2))}</pre>`;
        mdStatusEl.innerHTML = `<div class="hint">${escapeHtml(body.summary || body.status)}</div>`;
        await mdLoadOffers();
      } catch (err) {
        mdStatusEl.innerHTML = `<div class="error">${escapeHtml(err.message || String(err))}</div>`;
      }
    }

    async function mdHistory(kind) {
      try {
        const pid = mdProductId.value.trim();
        const response = await fetch(`/api/v1/products/${encodeURIComponent(pid)}/${kind}`);
        const body = await response.json();
        if (!response.ok) throw new Error(body.detail || "History failed");
        mdHistoryEl.innerHTML = `<pre>${escapeHtml(JSON.stringify(body, null, 2))}</pre>`;
        mdStatusEl.innerHTML = `<div class="hint">${kind}: ${body.count || 0} snapshots</div>`;
      } catch (err) {
        mdStatusEl.innerHTML = `<div class="error">${escapeHtml(err.message || String(err))}</div>`;
      }
    }

    document.getElementById("md_sources").addEventListener("click", mdLoadSources);
    document.getElementById("md_connectors").addEventListener("click", mdLoadSources);
    document.getElementById("md_seed").addEventListener("click", mdSeed);
    document.getElementById("md_offers").addEventListener("click", mdLoadOffers);
    document.getElementById("md_test").addEventListener("click", mdTest);
    document.getElementById("md_health").addEventListener("click", mdHealth);
    document.getElementById("md_sync").addEventListener("click", mdSync);
    document.getElementById("md_import_csv").addEventListener("click", () => mdDoImport("import.csv", "text/csv"));
    document.getElementById("md_import_json").addEventListener("click", () => mdDoImport("import.json", "application/json"));
    document.getElementById("md_load_sample").addEventListener("click", () => { mdImport.value = MD_SAMPLE_CSV.replace(/\\\\n/g, "\\n"); });
    document.getElementById("md_price_hist").addEventListener("click", () => mdHistory("price-history"));
    document.getElementById("md_inv_hist").addEventListener("click", () => mdHistory("inventory-history"));
    mdLoadSources();

    // --- User Platform panel ---
    const upEmail = document.getElementById("up_email");
    const upPassword = document.getElementById("up_password");
    const upLoginBtn = document.getElementById("up_login");
    const upLogoutBtn = document.getElementById("up_logout");
    const upMeBtn = document.getElementById("up_me");
    const upSavedBtn = document.getElementById("up_saved");
    const upHistoryBtn = document.getElementById("up_history");
    const upStatusEl = document.getElementById("up-status");
    const upSessionEl = document.getElementById("up-session");
    const upProfileEl = document.getElementById("up-profile");
    const upSavedListEl = document.getElementById("up-saved-list");
    const upMetaEl = document.getElementById("up-meta");
    const upLimitationsEl = document.getElementById("up-limitations");

    function upAuthHeaders() {
      const headers = { "Content-Type": "application/json" };
      if (upAccessToken) headers["Authorization"] = `Bearer ${upAccessToken}`;
      return headers;
    }

    async function loadUserPlatformMeta() {
      try {
        const response = await fetch("/api/v1/auth/demo");
        if (!response.ok) return;
        const body = await response.json();
        upMetaEl.innerHTML = `Demo users: ${(body.demo_users || []).map((u) => escapeHtml(u.email)).join(", ")} · persistence=${escapeHtml(body.persistence || "memory")}`;
        upLimitationsEl.innerHTML = `<ul>${(body.limitations || []).map((l) => `<li>${escapeHtml(l)}</li>`).join("")}</ul>`;
      } catch (_err) {
        /* ignore */
      }
    }

    async function upLogin() {
      upStatusEl.innerHTML = '<div class="loading"><span class="spinner" aria-hidden="true"></span> Logging in…</div>';
      try {
        const response = await fetch("/api/v1/auth/login", {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify({
            email: upEmail.value,
            password: upPassword.value,
            remember_me: true,
          }),
        });
        const body = await response.json();
        if (!response.ok) throw new Error(body.detail || "Login failed");
        upAccessToken = body.access_token;
        upUserId = body.user && body.user.user_id;
        upSessionEl.innerHTML = `${escapeHtml(body.user.display_name)} · ${escapeHtml(body.user.email)} · expires ${escapeHtml(body.expires_at || "")}`;
        upStatusEl.innerHTML = `<div class="hint">Logged in as ${escapeHtml(body.user.email)}</div>`;
        await upLoadProfile();
        await upLoadSaved();
        sprint19RefreshAfterAuthChange();
      } catch (err) {
        upStatusEl.innerHTML = `<div class="error">${escapeHtml(err.message || String(err))}</div>`;
      }
    }

    async function upLogout() {
      try {
        await fetch("/api/v1/auth/logout", { method: "POST", headers: upAuthHeaders() });
      } catch (_err) {
        /* ignore */
      }
      upAccessToken = null;
      upUserId = null;
      upSessionEl.innerHTML = "";
      upProfileEl.innerHTML = "";
      upSavedListEl.innerHTML = "";
      upStatusEl.innerHTML = '<div class="hint">Logged out.</div>';
      sprint19RefreshAfterAuthChange();
    }

    // Re-fetch every Sprint 19 panel that depends on upAccessToken after a
    // login/logout transition, so auth hints and data flip immediately.
    function sprint19RefreshAfterAuthChange() {
      refreshWatchlists();
      arRefreshRules();
      arRefreshEvents();
      ncRefreshList();
      npRefresh();
      dbRefresh();
    }

    async function upLoadProfile() {
      const response = await fetch("/api/v1/profile", { headers: upAuthHeaders() });
      const body = await response.json();
      if (!response.ok) throw new Error(body.detail || "Profile failed");
      upProfileEl.innerHTML = `
        <div><strong>${escapeHtml(body.display_name || "")}</strong></div>
        <div>Budget ${body.budget != null ? body.budget : "—"} ${escapeHtml(body.currency || "")} · ${escapeHtml(body.country || "")}</div>
        <div>Modes: student=${body.student_mode} creator=${body.creator_mode} gaming=${body.gaming_mode} business=${body.business_mode}</div>
        <div>Linked personal profile: ${escapeHtml(body.personal_profile_id || "—")}</div>
      `;
    }

    async function upLoadSaved() {
      const response = await fetch("/api/v1/user/saved-products", { headers: upAuthHeaders() });
      const body = await response.json();
      if (!response.ok) throw new Error(body.detail || "Saved products failed");
      const items = Array.isArray(body) ? body : (body.items || body.saved_products || []);
      if (!items.length) {
        upSavedListEl.innerHTML = '<p class="empty-state">No saved products.</p>';
        return;
      }
      upSavedListEl.innerHTML = items.map((item) =>
        `<div class="card-line"><strong>${escapeHtml(item.product_name)}</strong> · ${escapeHtml(item.product_id)} · ${item.price != null ? item.price : "—"} ${escapeHtml(item.currency || "")}</div>`
      ).join("");
    }

    async function upLoadHistory() {
      const response = await fetch("/api/v1/user/history", { headers: upAuthHeaders() });
      const body = await response.json();
      if (!response.ok) throw new Error(body.detail || "History failed");
      const items = Array.isArray(body) ? body : (body.items || body.history || []);
      upSavedListEl.innerHTML = items.length
        ? items.map((item) =>
            `<div class="card-line"><strong>${escapeHtml(item.query)}</strong><div>${escapeHtml(item.recommendation_summary || "")}</div></div>`
          ).join("")
        : '<p class="empty-state">No recommendation history.</p>';
    }

    upLoginBtn.addEventListener("click", upLogin);
    upLogoutBtn.addEventListener("click", upLogout);
    upMeBtn.addEventListener("click", async () => {
      try {
        await upLoadProfile();
        upStatusEl.innerHTML = '<div class="hint">Profile refreshed.</div>';
      } catch (err) {
        upStatusEl.innerHTML = `<div class="error">${escapeHtml(err.message || String(err))}</div>`;
      }
    });
    upSavedBtn.addEventListener("click", async () => {
      try {
        await upLoadSaved();
        upStatusEl.innerHTML = '<div class="hint">Saved products loaded.</div>';
      } catch (err) {
        upStatusEl.innerHTML = `<div class="error">${escapeHtml(err.message || String(err))}</div>`;
      }
    });
    upHistoryBtn.addEventListener("click", async () => {
      try {
        await upLoadHistory();
        upStatusEl.innerHTML = '<div class="hint">History loaded.</div>';
      } catch (err) {
        upStatusEl.innerHTML = `<div class="error">${escapeHtml(err.message || String(err))}</div>`;
      }
    });
    loadUserPlatformMeta();

    // ---------------------------------------------------------- Sprint 21: Merchant Platform
    const mpOrgEl = document.getElementById("mp_org");
    const mpTokenEl = document.getElementById("mp_token");
    const mpRefreshBtn = document.getElementById("mp_refresh");
    const mpSubmitBtn = document.getElementById("mp_submit_product");
    const mpAdminBtn = document.getElementById("mp_admin_review");
    const mpSummaryEl = document.getElementById("mp-summary");
    const mpStatusEl = document.getElementById("mp-status");

    function mpHeaders() {
      return { "Authorization": "Bearer " + mpTokenEl.value, "Content-Type": "application/json" };
    }
    function mpOrg() { return mpOrgEl.value; }
    function mpSet(id, html) {
      const el = document.getElementById(id);
      if (el) el.innerHTML = html;
    }
    function mpJsonTable(rows) {
      if (!rows || !rows.length) return '<div class="hint">No items.</div>';
      return '<pre class="csp-inline-40d06a384d">' + escapeHtml(JSON.stringify(rows, null, 2)) + '</pre>';
    }

    async function mpLoadDashboard() {
      mpStatusEl.innerHTML = '<div class="hint">Loading merchant dashboard…</div>';
      const org = mpOrg();
      const headers = mpHeaders();
      try {
        const [meta, profile, members, products, offers, promotions, campaigns, analytics, audit] = await Promise.all([
          fetch("/api/v1/merchants/meta/demo").then(r => r.json()),
          fetch(`/api/v1/merchants/${org}`, { headers }).then(r => r.json()),
          fetch(`/api/v1/merchants/${org}/members`, { headers }).then(r => r.json()),
          fetch(`/api/v1/merchants/${org}/products`, { headers }).then(r => r.json()),
          fetch(`/api/v1/merchants/${org}/offers`, { headers }).then(r => r.json()),
          fetch(`/api/v1/merchants/${org}/promotions`, { headers }).then(r => r.json()),
          fetch(`/api/v1/merchants/${org}/campaigns`, { headers }).then(r => r.json()),
          fetch(`/api/v1/merchants/${org}/analytics`, { headers }).then(r => r.json()),
          fetch(`/api/v1/merchants/${org}/audit-log`, { headers }).then(r => r.json()),
        ]);

        mpSummaryEl.innerHTML = `<div class="hint"><strong>${escapeHtml(profile.profile?.display_name || org)}</strong> · status ${escapeHtml(profile.status || "?")} · verification ${escapeHtml(profile.profile?.verification_status || "?")} · affiliate link ${escapeHtml(profile.affiliate_merchant_id || "none")}</div>`;
        mpSet("mp-profile", mpJsonTable([profile]));
        mpSet("mp-members", mpJsonTable(members.items || []));
        mpSet("mp-products", mpJsonTable((products.items || []).map(p => ({
          submission_id: p.submission_id, title: p.title, status: p.status,
          source_mode: p.source_mode, source_label: p.source_label,
          match: p.match_result, matched_product_id: p.matched_product_id,
          validation_errors: p.validation_errors
        }))));
        mpSet("mp-offers", mpJsonTable(offers.items || []));
        mpSet("mp-promotions", mpJsonTable((promotions.items || []).map(p => ({
          ...p, note: p.note || "Promotions do not automatically increase PiqScore."
        }))));
        mpSet("mp-campaigns", mpJsonTable((campaigns.items || []).map(c => ({
          campaign_id: c.campaign_id, name: c.name, status: c.status,
          sponsored_label: c.sponsored_label,
          organic_ranking_independent: c.organic_ranking_independent,
          billing: c.billing, placements: c.placements
        }))));
        mpSet("mp-analytics", `<div class="hint csp-inline-4fde948ccd">${escapeHtml(analytics.label || "Demo analytics")}</div>` + mpJsonTable([analytics]));
        mpSet("mp-affiliate", mpJsonTable([analytics.affiliate || { read_only: true, simulated: true }]));

        const productId = (products.items || []).find(p => p.matched_product_id)?.matched_product_id || "prod-laptop-x1";
        try {
          const ranking = await fetch(`/api/v1/merchants/${org}/products/${productId}/ranking-explanation`, { headers }).then(r => r.json());
          mpSet("mp-ranking", mpJsonTable([ranking]));
        } catch (e) {
          mpSet("mp-ranking", `<div class="hint">${escapeHtml(String(e))}</div>`);
        }

        const matchRows = (products.items || []).map(p => ({
          submission_id: p.submission_id,
          title: p.title,
          match_result: p.match_result,
          matched_product_id: p.matched_product_id,
          note: "Low-confidence matches are never silently merged."
        }));
        mpSet("mp-matching", mpJsonTable(matchRows));
        mpSet("mp-audit", mpJsonTable(audit.items || []));
        mpSet("mp-limitations", '<ul>' + (meta.limitations || []).map(l => `<li>${escapeHtml(l)}</li>`).join("") + '</ul>');
        mpSet("mp-admin", '<div class="hint">Use Internal Admin token + “Admin review panel” to load pending submissions.</div>');
        mpStatusEl.innerHTML = '<div class="hint">Merchant dashboard loaded. Labels: demo analytics · simulated conversions · draft sponsored campaigns · merchant-submitted / unverified data.</div>';
      } catch (err) {
        mpStatusEl.innerHTML = `<div class="error">${escapeHtml(err.message || String(err))}</div>`;
      }
    }

    mpRefreshBtn.addEventListener("click", () => mpLoadDashboard());
    mpSubmitBtn.addEventListener("click", async () => {
      const org = mpOrg();
      const headers = mpHeaders();
      try {
        const created = await fetch(`/api/v1/merchants/${org}/products`, {
          method: "POST", headers,
          body: JSON.stringify({
            title: "NovaTech X1 Pro 14-inch Laptop — Merchant Demo",
            brand: "NovaTech", model: "X1 Pro", sku: "NT-X1PRO-14",
            upc: "012345678901", merchant_product_id: "mp-x1-001",
            image_urls: ["https://cdn.techhaven.demo/products/x1-demo.png"],
            description: "Demo merchant product submission for matching.",
            warranty: "1 year limited"
          })
        }).then(async r => { const j = await r.json(); if (!r.ok) throw new Error(j.detail || r.statusText); return j; });
        const submitted = await fetch(`/api/v1/merchants/${org}/products/${created.submission_id}/submit`, {
          method: "POST", headers
        }).then(async r => { const j = await r.json(); if (!r.ok) throw new Error(j.detail || r.statusText); return j; });
        mpStatusEl.innerHTML = `<div class="hint">Submitted ${escapeHtml(submitted.submission_id)} · match ${escapeHtml(JSON.stringify(submitted.match_result))} · source ${escapeHtml(submitted.source_mode)}</div>`;
        await mpLoadDashboard();
      } catch (err) {
        mpStatusEl.innerHTML = `<div class="error">${escapeHtml(err.message || String(err))}</div>`;
      }
    });
    mpAdminBtn.addEventListener("click", async () => {
      const headers = { "Authorization": "Bearer demo-token-internal-admin", "Content-Type": "application/json" };
      try {
        const subs = await fetch("/api/v1/admin/merchant-submissions", { headers }).then(r => r.json());
        mpSet("mp-admin", '<div class="hint">INTERNAL_ADMIN review — approve/reject only; never changes organic ranking.</div>' + mpJsonTable(subs.items || []));
        mpStatusEl.innerHTML = '<div class="hint">Admin review panel loaded.</div>';
      } catch (err) {
        mpStatusEl.innerHTML = `<div class="error">${escapeHtml(err.message || String(err))}</div>`;
      }
    });

    // ---------------------------------------------------------- Sprint 22: Launch Readiness
    const ADMIN_H = { "Authorization": "Bearer demo-token-internal-admin", "Content-Type": "application/json" };
    function launchTable(rows) {
      if (!rows || !rows.length) return '<div class="hint">No rows.</div>';
      return mpJsonTable(rows);
    }
    function showLaunch(elId, html) {
      const el = document.getElementById(elId);
      if (el) el.innerHTML = html;
    }

    async function dlRefresh() {
      const st = document.getElementById("dl-status");
      st.style.display = "block";
      try {
        const data = await fetch("/api/v1/launch/demo").then(r => r.json());
        showLaunch("dl-active", launchTable([{
          persona: data.active_persona, label: data.label,
          auth_header: data.auth_header, organization_id: data.organization_id,
          user_email: data.user_email
        }]));
        showLaunch("dl-hints", '<ul>' + (data.seeded_hints || []).map(h => `<li>${escapeHtml(h)}</li>`).join("") +
          '</ul><div class="hint">Capabilities: ' + escapeHtml((data.capabilities || []).join(", ")) + '</div>');
        st.innerHTML = '<div class="hint">Demo launcher ready · seeded data from prior sprints.</div>';
        if (data.active_persona) document.getElementById("dl_persona").value = data.active_persona;
      } catch (err) {
        st.innerHTML = `<div class="error">${escapeHtml(err.message || String(err))}</div>`;
      }
    }
    document.getElementById("dl_refresh").addEventListener("click", dlRefresh);
    document.getElementById("dl_switch").addEventListener("click", async () => {
      const st = document.getElementById("dl-status");
      st.style.display = "block";
      try {
        const persona = document.getElementById("dl_persona").value;
        await fetch("/api/v1/launch/demo/switch", {
          method: "POST", headers: { "Content-Type": "application/json" },
          body: JSON.stringify({ persona })
        }).then(async r => { const j = await r.json(); if (!r.ok) throw new Error(j.detail || j.message || r.statusText); return j; });
        await dlRefresh();
        st.innerHTML = `<div class="hint">Switched to ${escapeHtml(persona)}.</div>`;
      } catch (err) {
        st.innerHTML = `<div class="error">${escapeHtml(err.message || String(err))}</div>`;
      }
    });

    document.getElementById("ss_probes").addEventListener("click", async () => {
      const st = document.getElementById("ss-status");
      st.style.display = "block";
      try {
        const [live, ready, health] = await Promise.all([
          fetch("/live").then(r => r.json()),
          fetch("/ready").then(r => r.json()),
          fetch("/health").then(r => r.json())
        ]);
        showLaunch("ss-probes", launchTable([
          { probe: "live", ...live },
          { probe: "ready", ...ready },
          { probe: "health", status: health.status, database: health.database, cache: health.cache, version: health.version, uptime_seconds: health.uptime_seconds }
        ]));
        st.innerHTML = '<div class="hint">Probes loaded from /live · /ready · /health.</div>';
      } catch (err) {
        st.innerHTML = `<div class="error">${escapeHtml(err.message || String(err))}</div>`;
      }
    });
    document.getElementById("ss_flags").addEventListener("click", async () => {
      const st = document.getElementById("ss-status");
      st.style.display = "block";
      try {
        const data = await fetch("/api/v1/launch/feature-flags").then(r => r.json());
        showLaunch("ss-flags", launchTable(data.flags || []));
        st.innerHTML = '<div class="hint">Feature flags loaded.</div>';
      } catch (err) {
        st.innerHTML = `<div class="error">${escapeHtml(err.message || String(err))}</div>`;
      }
    });
    document.getElementById("ss_settings").addEventListener("click", async () => {
      const st = document.getElementById("ss-status");
      st.style.display = "block";
      try {
        const data = await fetch("/api/v1/launch/system-status").then(r => r.json());
        showLaunch("ss-settings", launchTable([data]));
        st.innerHTML = '<div class="hint">Production settings snapshot (secrets excluded).</div>';
      } catch (err) {
        st.innerHTML = `<div class="error">${escapeHtml(err.message || String(err))}</div>`;
      }
    });

    async function lcLoad() {
      const st = document.getElementById("lc-status");
      st.style.display = "block";
      try {
        const data = await fetch("/api/v1/launch/checklist").then(r => r.json());
        showLaunch("lc-summary", launchTable([{
          total: data.total, completed: data.completed, remaining: data.remaining, percent_complete: data.percent_complete
        }]));
        showLaunch("lc-items", launchTable(data.items || []));
        st.innerHTML = '<div class="hint">Launch checklist loaded.</div>';
        return data;
      } catch (err) {
        st.innerHTML = `<div class="error">${escapeHtml(err.message || String(err))}</div>`;
        return null;
      }
    }
    document.getElementById("lc_load").addEventListener("click", () => lcLoad());
    document.getElementById("lc_toggle").addEventListener("click", async () => {
      const st = document.getElementById("lc-status");
      st.style.display = "block";
      try {
        const data = await lcLoad();
        const item = (data?.items || []).find(i => !i.completed);
        if (!item) { st.innerHTML = '<div class="hint">All checklist items already complete.</div>'; return; }
        await fetch(`/api/v1/launch/checklist/${item.item_id}`, {
          method: "PATCH", headers: ADMIN_H,
          body: JSON.stringify({ completed: true, notes: "Marked from demo UI" })
        }).then(async r => { const j = await r.json(); if (!r.ok) throw new Error(j.detail || j.message || r.statusText); return j; });
        await lcLoad();
        st.innerHTML = `<div class="hint">Completed ${escapeHtml(item.item_id)}.</div>`;
      } catch (err) {
        st.innerHTML = `<div class="error">${escapeHtml(err.message || String(err))}</div>`;
      }
    });

    document.getElementById("am_dashboard").addEventListener("click", async () => {
      const st = document.getElementById("am-status");
      st.style.display = "block";
      try {
        const data = await fetch("/api/v1/launch/dashboard", { headers: ADMIN_H }).then(async r => {
          const j = await r.json(); if (!r.ok) throw new Error(j.detail || j.message || r.statusText); return j;
        });
        showLaunch("am-metrics", launchTable([data.metrics || {}]));
        showLaunch("am-health", launchTable([{
          ...(data.api_health || {}),
          ...(data.system_status || {}),
          environment: data.environment,
          uptime_seconds: data.uptime_seconds
        }]));
        st.innerHTML = '<div class="hint">Launch dashboard loaded · demo metrics only · ranking unchanged.</div>';
      } catch (err) {
        st.innerHTML = `<div class="error">${escapeHtml(err.message || String(err))}</div>`;
      }
    });
    document.getElementById("am_perf").addEventListener("click", async () => {
      const st = document.getElementById("am-status");
      st.style.display = "block";
      try {
        const data = await fetch("/api/v1/launch/performance").then(r => r.json());
        showLaunch("am-perf", launchTable([data]));
        st.innerHTML = '<div class="hint">Performance cache stats · memoizes identical reads only.</div>';
      } catch (err) {
        st.innerHTML = `<div class="error">${escapeHtml(err.message || String(err))}</div>`;
      }
    });
    document.getElementById("am_export").addEventListener("click", async () => {
      const st = document.getElementById("am-status");
      st.style.display = "block";
      try {
        const data = await fetch("/api/v1/launch/config/export", { method: "POST", headers: ADMIN_H }).then(async r => {
          const j = await r.json(); if (!r.ok) throw new Error(j.detail || j.message || r.statusText); return j;
        });
        showLaunch("am-export", launchTable([{
          snapshot_id: data.snapshot_id, environment: data.environment, label: data.label,
          note: data.note, keys: Object.keys(data.payload || {}).length
        }]));
        st.innerHTML = '<div class="hint">Config exported · secrets redacted.</div>';
      } catch (err) {
        st.innerHTML = `<div class="error">${escapeHtml(err.message || String(err))}</div>`;
      }
    });
  

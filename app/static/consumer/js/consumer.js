const ASK_ENDPOINT = "/api/v1/shopping-assistant/query";

function qs(id) {
  return document.getElementById(id);
}

function initNav() {
  const toggle = document.querySelector(".nav-toggle");
  const menu = qs("mobile-nav");
  if (!toggle || !menu) return;
  toggle.addEventListener("click", () => {
    const open = toggle.getAttribute("aria-expanded") === "true";
    toggle.setAttribute("aria-expanded", String(!open));
    menu.hidden = open;
  });
}

function initLocation() {
  const dialog = qs("location-dialog");
  if (!dialog) return;
  const openers = document.querySelectorAll(".js-open-location");
  const closers = document.querySelectorAll(".js-close-location");
  const useMine = document.querySelector(".js-use-location");
  const city = dialog.querySelector('input[name="city"]');

  openers.forEach((el) =>
    el.addEventListener("click", () => {
      dialog.hidden = false;
      if (typeof dialog.showModal === "function") dialog.showModal();
      else dialog.setAttribute("open", "");
    }),
  );
  closers.forEach((el) =>
    el.addEventListener("click", () => {
      if (typeof dialog.close === "function") dialog.close();
      else dialog.removeAttribute("open");
    }),
  );

  if (dialog.hasAttribute("open") && typeof dialog.showModal === "function" && !dialog.open) {
    dialog.showModal();
  }

  if (!useMine) return;
  useMine.addEventListener("click", () => {
    const hint = dialog.querySelector("[data-geo-hint]") || document.createElement("p");
    hint.className = "form-hint";
    hint.setAttribute("role", "status");
    hint.setAttribute("data-geo-hint", "true");
    if (!navigator.geolocation) {
      hint.textContent =
        "This browser cannot share location. Enter a city or municipality instead.";
      city?.after(hint);
      city?.focus();
      return;
    }
    navigator.geolocation.getCurrentPosition(
      () => {
        hint.textContent =
          "We cannot convert map coordinates into a city yet. Enter a city or municipality. Precise coordinates are not stored.";
        city?.before(hint);
        city?.focus();
      },
      (err) => {
        if (err && err.code === 1) {
          hint.textContent =
            "Location permission denied. Enter a city or municipality instead.";
        } else {
          hint.textContent =
            "Location is unavailable right now. Enter a city or municipality instead.";
        }
        city?.before(hint);
        city?.focus();
      },
      { enableHighAccuracy: false, timeout: 8000, maximumAge: 0 },
    );
  });
}

function initAccordion() {
  if (window.matchMedia("(min-width: 981px)").matches) {
    document.querySelectorAll(".why-section").forEach((section) => {
      section.classList.add("is-open");
      const btn = section.querySelector(".why-toggle");
      if (btn) btn.setAttribute("aria-expanded", "true");
    });
    return;
  }
  document.querySelectorAll(".why-toggle").forEach((btn) => {
    btn.addEventListener("click", () => {
      const section = btn.closest(".why-section");
      const open = section.classList.toggle("is-open");
      btn.setAttribute("aria-expanded", String(open));
    });
  });
}

function showAsk(text) {
  const overlay = qs("ask-overlay");
  const body = qs("ask-panel-body");
  if (!overlay || !body) return;
  body.innerHTML = text;
  overlay.hidden = false;
}

function initAsk() {
  const overlay = qs("ask-overlay");
  document.querySelectorAll(".js-close-ask").forEach((btn) => {
    btn.addEventListener("click", () => {
      if (overlay) overlay.hidden = true;
    });
  });
  document.querySelectorAll(".js-focus-ask").forEach((btn) => {
    btn.addEventListener("click", () => qs("ask-input-dock")?.focus());
  });
  document.querySelectorAll(".js-ask-chip").forEach((chip) => {
    chip.addEventListener("click", () => {
      const input = qs("ask-input-dock") || qs("ask-input-top");
      if (input) input.value = chip.textContent.trim();
      input?.focus();
    });
  });
  document.querySelectorAll(".js-ask-form").forEach((form) => {
    form.addEventListener("submit", async (event) => {
      event.preventDefault();
      const input = form.querySelector(".ask-input");
      const question = (input?.value || "").trim();
      if (!question) return;
      showAsk("<p>Looking at the current decision…</p>");
      const payload = { query: question };
      const decisionId = document.body?.dataset?.decisionId;
      const surface = document.body?.dataset?.page;
      if (decisionId) payload.decision_id = decisionId;
      if (surface) payload.surface = surface;
      const contextVersion = document.body?.dataset?.contextVersion;
      if (contextVersion) payload.context_version = Number(contextVersion);
      try {
        const conversationId = window.sessionStorage.getItem("piqsavi_ask_conversation");
        if (conversationId) payload.conversation_id = conversationId;
      } catch {
        /* sessionStorage may be unavailable */
      }
      try {
        const response = await fetch(ASK_ENDPOINT, {
          method: "POST",
          headers: { "Content-Type": "application/json", Accept: "application/json" },
          body: JSON.stringify(payload),
        });
        const payloadJson = await response.json();
        if (payloadJson.conversation_id) {
          try {
            window.sessionStorage.setItem("piqsavi_ask_conversation", payloadJson.conversation_id);
          } catch {
            /* ignore */
          }
        }
        const answer =
          payloadJson.answer ||
          payloadJson.summary ||
          payloadJson.message ||
          "PiqSavi can discuss this decision, but a detailed evidence answer is not available yet.";
        const warnings = Array.isArray(payloadJson.warnings)
          ? payloadJson.warnings.map((item) => item.message || item).join(" ")
          : "";
        showAsk(`<p>${escapeHtml(String(answer))}</p>${warnings ? `<p class="form-hint">${escapeHtml(warnings)}</p>` : ""}`);
        const processing = payloadJson.processing || {};
        const sessionBest = processing.session_best_piq_product_id;
        const currentBest = document.body?.dataset?.bestPiq;
        if (
          sessionBest &&
          currentBest &&
          sessionBest !== currentBest &&
          processing.recommendation_changed
        ) {
          window.setTimeout(() => window.location.reload(), 1200);
        }
      } catch {
        showAsk("<p>Ask PiqSavi is unavailable right now. Try again in a moment.</p>");
      }
    });
  });
}

function escapeHtml(value) {
  return value
    .replaceAll("&", "&amp;")
    .replaceAll("<", "&lt;")
    .replaceAll(">", "&gt;")
    .replaceAll('"', "&quot;");
}

function initRecalc() {
  const overlay = document.querySelector(".recalc-overlay");
  if (!overlay) return;
  window.setTimeout(() => {
    const url = new URL(window.location.href);
    url.searchParams.delete("recalculating");
    window.location.replace(url.toString());
  }, 900);
}

initNav();
initLocation();
initAccordion();
initAsk();
initRecalc();

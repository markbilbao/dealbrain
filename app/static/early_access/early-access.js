(() => {
  const BREAKPOINT = 767;
  const EMAIL_RE = /^[^\s@]+@[^\s@]+\.[^\s@]+$/;
  const layer = document.getElementById("signup-layer");
  const sheet = document.getElementById("signup-sheet");
  const form = document.getElementById("early-access-form");
  const submitBtn = document.getElementById("ea-submit");
  const tryAgain = document.getElementById("ea-try-again");
  const landing = document.getElementById("landing-root");
  const how = document.getElementById("how-it-works");

  const state = {
    view: "landing",
    form: "default",
    result: null,
    lastCta: null,
    formStarted: false,
  };

  const panels = {
    form: sheet.querySelector('[data-panel="form"]'),
    success: sheet.querySelector('[data-panel="success"]'),
    duplicate: sheet.querySelector('[data-panel="duplicate"]'),
    technical_error: sheet.querySelector('[data-panel="technical_error"]'),
  };

  const mobileQuery = window.matchMedia(`(max-width: ${BREAKPOINT}px)`);

  function isMobile() {
    return mobileQuery.matches;
  }

  function syncSignupAriaModal() {
    sheet.setAttribute("aria-modal", isMobile() ? "false" : "true");
  }

  function onMobileBreakpointChange() {
    if (!layer.hidden) {
      document.body.classList.toggle("is-signup-open", isMobile());
    }
    syncSignupAriaModal();
  }

  if (typeof mobileQuery.addEventListener === "function") {
    mobileQuery.addEventListener("change", onMobileBreakpointChange);
  } else if (typeof mobileQuery.addListener === "function") {
    mobileQuery.addListener(onMobileBreakpointChange);
  }
  syncSignupAriaModal();

  function focusables() {
    return [...sheet.querySelectorAll("a, button, input, select, textarea")]
      .filter((el) => !el.hasAttribute("disabled") && el.offsetParent !== null);
  }

  function showPanel(name) {
    Object.entries(panels).forEach(([key, node]) => {
      node.hidden = key !== name;
    });
  }

  function setFormErrors(errors) {
    const map = {
      full_name: "err-full-name",
      email: "err-email",
      country: "err-country",
    };
    Object.keys(map).forEach((field) => {
      const wrap = form.querySelector(`[data-field="${field}"]`);
      const err = document.getElementById(map[field]);
      const invalid = Boolean(errors[field]);
      wrap.classList.toggle("is-invalid", invalid);
      err.hidden = !invalid;
      const input = wrap.querySelector("input, select");
      input.setAttribute("aria-invalid", invalid ? "true" : "false");
    });
  }

  function validate() {
    const values = readForm();
    const errors = {};
    if (!values.full_name) errors.full_name = true;
    if (!values.email || !EMAIL_RE.test(values.email)) errors.email = true;
    if (!values.country) errors.country = true;
    return errors;
  }

  function readForm() {
    const data = new FormData(form);
    return {
      full_name: String(data.get("full_name") || "").trim(),
      email: String(data.get("email") || "").trim(),
      country: String(data.get("country") || "").trim(),
      shopping_interest: String(data.get("shopping_interest") || "").trim() || null,
    };
  }

  function attribution() {
    const params = new URLSearchParams(window.location.search);
    return {
      source: "early_access_landing",
      utm_source: params.get("utm_source"),
      utm_medium: params.get("utm_medium"),
      utm_campaign: params.get("utm_campaign"),
      utm_content: params.get("utm_content"),
      utm_term: params.get("utm_term"),
      referrer: document.referrer || null,
    };
  }

  function track(event, source) {
    const body = { event };
    if (source === "header" || source === "hero") {
      body.source = source;
    }
    fetch("/api/v1/early-access/events", {
      method: "POST",
      headers: { "Content-Type": "application/json", Accept: "application/json" },
      body: JSON.stringify(body),
    }).catch(() => {});
  }

  function openSignup(cta) {
    state.view = "form";
    state.form = "default";
    state.result = null;
    state.lastCta = cta;
    setFormErrors({});
    submitBtn.disabled = false;
    submitBtn.classList.remove("is-loading");
    submitBtn.querySelector(".btn-label").textContent = "Join Early Access — Free";
    showPanel("form");
    layer.hidden = false;
    document.body.classList.toggle("is-signup-open", isMobile());
    track("early_access_cta_clicked", cta?.dataset.ctaSource);
    window.requestAnimationFrame(() => {
      document.getElementById("ea-full-name").focus();
    });
  }

  function closeSignup() {
    layer.hidden = true;
    document.body.classList.remove("is-signup-open");
    state.view = "landing";
    state.result = null;
    const restore = state.lastCta;
    state.lastCta = null;
    if (restore) restore.focus();
  }

  function showResult(kind) {
    state.view = "result";
    state.result = kind;
    showPanel(kind);
    const action = sheet.querySelector(`[data-panel="${kind}"] .btn`);
    if (action) action.focus();
  }

  function setLoading(loading) {
    state.form = loading ? "loading" : "default";
    form.setAttribute("aria-busy", loading ? "true" : "false");
    submitBtn.disabled = loading;
    submitBtn.classList.toggle("is-loading", loading);
    submitBtn.querySelector(".btn-label").textContent = loading
      ? "Joining Early Access..."
      : "Join Early Access — Free";
  }

  form.addEventListener("focusin", () => {
    if (!state.formStarted) {
      state.formStarted = true;
      track("early_access_form_started");
    }
  });

  form.addEventListener("submit", async (event) => {
    event.preventDefault();
    const errors = validate();
    if (Object.keys(errors).length) {
      state.form = "validation";
      setFormErrors(errors);
      const first = form.querySelector(".field.is-invalid input, .field.is-invalid select");
      if (first) first.focus();
      return;
    }
    setFormErrors({});
    setLoading(true);
    track("early_access_form_submitted");
    try {
      const response = await fetch("/api/v1/early-access", {
        method: "POST",
        headers: { "Content-Type": "application/json", Accept: "application/json" },
        body: JSON.stringify({ ...readForm(), ...attribution() }),
      });
      if (response.status === 429) {
        setLoading(false);
        showResult("technical_error");
        return;
      }
      if (!response.ok) {
        const payload = await response.json().catch(() => ({}));
        if (response.status === 400 || response.status === 422) {
          setLoading(false);
          state.form = "validation";
          const next = { full_name: false, email: false, country: false };
          const details = payload.details;
          const blob = JSON.stringify(payload).toLowerCase();
          if (blob.includes("full_name") || blob.includes("full name")) next.full_name = true;
          if (blob.includes("email")) next.email = true;
          if (blob.includes("country")) next.country = true;
          if (!next.full_name && !next.email && !next.country) {
            next.full_name = !readForm().full_name;
            next.email = true;
            next.country = !readForm().country;
          }
          setFormErrors(next);
          return;
        }
        setLoading(false);
        showResult("technical_error");
        return;
      }
      const body = await response.json();
      setLoading(false);
      if (body.outcome === "already_registered") {
        showResult("duplicate");
        return;
      }
      showResult("success");
    } catch (_err) {
      setLoading(false);
      showResult("technical_error");
    }
  });

  document.querySelectorAll(".js-open-signup").forEach((btn) => {
    btn.addEventListener("click", () => openSignup(btn));
  });

  document.querySelectorAll("[data-close-signup]").forEach((el) => {
    el.addEventListener("click", (event) => {
      if (el.classList.contains("signup-backdrop") && isMobile()) return;
      event.preventDefault();
      closeSignup();
    });
  });

  tryAgain.addEventListener("click", () => {
    state.view = "form";
    state.form = "default";
    state.result = null;
    setLoading(false);
    showPanel("form");
    document.getElementById("ea-full-name").focus();
  });

  document.querySelectorAll("[data-legal-gated]").forEach((link) => {
    link.addEventListener("click", (event) => {
      event.preventDefault();
    });
  });

  document.addEventListener("keydown", (event) => {
    if (layer.hidden) return;
    if (event.key === "Escape") {
      event.preventDefault();
      closeSignup();
      return;
    }
    if (event.key !== "Tab" || isMobile()) return;
    const nodes = focusables();
    if (!nodes.length) return;
    const first = nodes[0];
    const last = nodes[nodes.length - 1];
    if (event.shiftKey && document.activeElement === first) {
      event.preventDefault();
      last.focus();
    } else if (!event.shiftKey && document.activeElement === last) {
      event.preventDefault();
      first.focus();
    }
  });

  if (window.visualViewport) {
    const onViewport = () => {
      const inset = Math.max(0, window.innerHeight - window.visualViewport.height - window.visualViewport.offsetTop);
      document.documentElement.style.setProperty("--kb-inset", `${inset}px`);
      const active = document.activeElement;
      if (active && sheet.contains(active) && typeof active.scrollIntoView === "function") {
        active.scrollIntoView({ block: "center" });
      }
    };
    window.visualViewport.addEventListener("resize", onViewport);
    window.visualViewport.addEventListener("scroll", onViewport);
  }

  if (how && "IntersectionObserver" in window) {
    const observer = new IntersectionObserver(
      (entries) => {
        if (entries.some((entry) => entry.isIntersecting)) {
          track("how_it_works_viewed");
          observer.disconnect();
        }
      },
      { threshold: 0.4 },
    );
    observer.observe(how);
  }
})();

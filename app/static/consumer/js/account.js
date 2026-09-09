const TOKEN_KEY = "piqsavi_access_token";
const REMEMBER_KEY = "piqsavi_remember_me";
const CONVERSATION_KEY = "piqsavi_ask_conversation";

let pendingIdentityToken = "";

function qs(selector, root = document) {
  return root.querySelector(selector);
}

function statusNode(name = "account") {
  return qs(`[data-${name}-status]`) || qs("[data-account-status]");
}

function setStatus(message, name = "account") {
  const node = name === "account" ? qs("[data-account-status]") : qs(`[data-${name}-status]`);
  if (node) node.textContent = message;
}

function storageForRemember(remember) {
  return remember ? window.localStorage : window.sessionStorage;
}

function readToken() {
  try {
    return window.sessionStorage.getItem(TOKEN_KEY) || window.localStorage.getItem(TOKEN_KEY) || "";
  } catch {
    return "";
  }
}

function storeToken(token, remember) {
  try {
    window.sessionStorage.removeItem(TOKEN_KEY);
    window.localStorage.removeItem(TOKEN_KEY);
    storageForRemember(remember).setItem(TOKEN_KEY, token);
    window.localStorage.setItem(REMEMBER_KEY, remember ? "1" : "0");
  } catch {
    /* storage may be unavailable */
  }
}

function clearToken() {
  try {
    window.sessionStorage.removeItem(TOKEN_KEY);
    window.localStorage.removeItem(TOKEN_KEY);
    window.sessionStorage.removeItem(CONVERSATION_KEY);
  } catch {
    /* ignore */
  }
}

async function clearLocalAuth() {
  clearToken();
  try {
    await fetch("/account/clear-device", { method: "POST", headers: { Accept: "application/json" } });
  } catch {
    /* ignore */
  }
}

function consumeUrlToken() {
  const params = new URLSearchParams(window.location.search);
  const token = String(params.get("token") || "");
  if (window.history?.replaceState) {
    const url = new URL(window.location.href);
    url.searchParams.delete("token");
    window.history.replaceState({}, "", `${url.pathname}${url.search}${url.hash}`);
  }
  return token;
}

function redactToken(message, token) {
  let text = String(message || "");
  if (token) text = text.split(token).join("");
  return text;
}

function revealIdentityOutcome(kind) {
  const pending = qs("[data-identity-pending]");
  const sent = qs("[data-identity-sent]");
  const success = qs("[data-identity-success]");
  const failure = qs("[data-identity-failure]");
  if (pending) pending.hidden = true;
  if (sent) sent.hidden = kind !== "sent";
  if (success) success.hidden = kind !== "success";
  if (failure) failure.hidden = kind !== "failure";
}

function acceptedIdentityMessage(payload, deliveredCopy, pendingCopy) {
  if (payload && payload.email_delivery === true) return deliveredCopy;
  return pendingCopy;
}

function apiError(payload, fallback) {
  if (!payload || typeof payload !== "object") return fallback;
  const detail = payload.detail;
  if (typeof detail === "string") return detail;
  if (Array.isArray(detail) && detail[0]?.msg) return detail[0].msg;
  return fallback;
}

async function api(path, options = {}) {
  const headers = { Accept: "application/json", ...(options.headers || {}) };
  if (options.body && !headers["Content-Type"]) {
    headers["Content-Type"] = "application/json";
  }
  const token = readToken();
  if (token) headers.Authorization = `Bearer ${token}`;
  const response = await fetch(path, { ...options, headers });
  let payload = {};
  if (response.status !== 204) {
    try {
      payload = await response.json();
    } catch {
      payload = {};
    }
  }
  return { response, payload };
}

function safeNext(value) {
  const next = value || document.body?.dataset?.next || "/account";
  if (
    next.startsWith("/results/") ||
    next.startsWith("/compare/") ||
    next.startsWith("/why-best-piq/") ||
    next === "/account" ||
    next.startsWith("/account") ||
    next === "/search" ||
    next.startsWith("/search?")
  ) {
    return next;
  }
  return "/account";
}

async function claimDecision(nextPath) {
  let conversationId = "";
  try {
    conversationId = window.sessionStorage.getItem(CONVERSATION_KEY) || "";
  } catch {
    conversationId = "";
  }
  const decisionMatch = nextPath.match(/^\/(?:results|compare|why-best-piq)\/([^/?#]+)/);
  const body = {
    conversation_id: conversationId,
    decision_id: decisionMatch ? decisionMatch[1] : "",
  };
  await fetch("/consumer/claim-decision", {
    method: "POST",
    headers: {
      "Content-Type": "application/json",
      Accept: "application/json",
      Authorization: `Bearer ${readToken()}`,
    },
    body: JSON.stringify(body),
  });
}

async function afterAuth(payload, nextPath, remember) {
  if (!payload.access_token) {
    setStatus("Sign-in succeeded without a session token. Try again.");
    return;
  }
  storeToken(payload.access_token, remember);
  await claimDecision(nextPath);
  window.location.assign(nextPath);
}

function bindIdentityToken() {
  const page = document.body?.dataset?.page || "";
  if (page === "confirm-email-change") {
    pendingIdentityToken = consumeUrlToken();
    if (!pendingIdentityToken) {
      revealIdentityOutcome("failure");
    }
    return;
  }
  if (page === "verify-email" || page === "reset-password") {
    consumeUrlToken();
  }
}

async function handleIdentityForm(form, kind, data) {
  if (kind === "reset-request") {
    setStatus("Sending reset instructions…");
    const { response, payload } = await api("/api/v1/auth/password-reset", {
      method: "POST",
      body: JSON.stringify({ email: String(data.get("email") || "") }),
    });
    if (!response.ok) {
      setStatus(apiError(payload, "Reset request failed."));
      return;
    }
    setStatus("");
    revealIdentityOutcome("sent");
    return;
  }
  if (kind === "reset-confirm") {
    setStatus("Updating password…");
    const token = String(data.get("token") || "");
    const { response, payload } = await api("/api/v1/auth/password-reset/confirm", {
      method: "POST",
      body: JSON.stringify({
        token,
        new_password: String(data.get("new_password") || ""),
      }),
    });
    if (!response.ok) {
      const message = redactToken(apiError(payload, "Password reset confirmation failed."), token);
      if (response.status === 401) {
        setStatus("");
        revealIdentityOutcome("failure");
        return;
      }
      setStatus(message);
      return;
    }
    await clearLocalAuth();
    setStatus("");
    revealIdentityOutcome("success");
    return;
  }
  if (kind === "verify-request") {
    setStatus("Sending a verification link…");
    const { response, payload } = await api("/api/v1/auth/verify-email", {
      method: "POST",
      body: JSON.stringify({ email: String(data.get("email") || "") }),
    });
    if (!response.ok) {
      setStatus(apiError(payload, "Verification request failed."));
      return;
    }
    setStatus("");
    revealIdentityOutcome("sent");
    return;
  }
  if (kind === "verify-confirm") {
    setStatus("Confirming email…");
    const token = String(data.get("token") || "");
    const { response, payload } = await api("/api/v1/auth/verify-email/confirm", {
      method: "POST",
      body: JSON.stringify({ token }),
    });
    if (!response.ok) {
      const message = redactToken(apiError(payload, "Email confirmation failed."), token);
      if (response.status === 401) {
        setStatus("");
        revealIdentityOutcome("failure");
        return;
      }
      setStatus(message);
      return;
    }
    setStatus("");
    revealIdentityOutcome("success");
    return;
  }
  if (kind === "email-change") {
    setStatus("Sending confirmation…", "email-change");
    const { response, payload } = await api("/api/v1/auth/email-change", {
      method: "POST",
      body: JSON.stringify({
        new_email: String(data.get("new_email") || ""),
        password: String(data.get("password") || ""),
      }),
    });
    if (!response.ok) {
      setStatus(apiError(payload, "We could not start the email change."), "email-change");
      return;
    }
    setStatus(
      acceptedIdentityMessage(
        payload,
        "Check your new email for a confirmation link.",
        "Check your new email. If this address can be used, we've sent a confirmation link to complete the change.",
      ),
      "email-change",
    );
    form.reset();
    return;
  }
  if (kind === "email-change-confirm") {
    setStatus("Confirming email change…");
    const token = pendingIdentityToken;
    const { response, payload } = await api("/api/v1/auth/email-change/confirm", {
      method: "POST",
      body: JSON.stringify({ token }),
    });
    if (!response.ok) {
      setStatus("");
      revealIdentityOutcome("failure");
      return;
    }
    await clearLocalAuth();
    setStatus("");
    revealIdentityOutcome("success");
    return;
  }
  return false;
}

function bindForms() {
  document.querySelectorAll("[data-account-form]").forEach((form) => {
    form.addEventListener("submit", async (event) => {
      event.preventDefault();
      const kind = form.getAttribute("data-account-form");
      const data = new FormData(form);
      try {
        if (kind === "login") {
          setStatus("Signing in…");
          const remember = data.get("remember_me") === "on";
          const { response, payload } = await api("/api/v1/auth/login", {
            method: "POST",
            body: JSON.stringify({
              email: String(data.get("email") || ""),
              password: String(data.get("password") || ""),
              remember_me: remember,
            }),
          });
          if (!response.ok) {
            setStatus(apiError(payload, "Sign in failed."));
            return;
          }
          await afterAuth(payload, safeNext(String(data.get("next") || "")), remember);
          return;
        }
        if (kind === "register") {
          setStatus("Creating account…");
          const remember = data.get("remember_me") === "on";
          const { response, payload } = await api("/api/v1/auth/register", {
            method: "POST",
            body: JSON.stringify({
              email: String(data.get("email") || ""),
              password: String(data.get("password") || ""),
              display_name: String(data.get("display_name") || ""),
              remember_me: remember,
              terms_accepted: Boolean(form.querySelector("[name=terms_accepted]")?.checked),
              privacy_acknowledged: Boolean(form.querySelector("[name=privacy_acknowledged]")?.checked),
            }),
          });
          if (!response.ok) {
            setStatus(apiError(payload, "Registration failed."));
            return;
          }
          await afterAuth(payload, safeNext(String(data.get("next") || "")), remember);
          return;
        }
        if (await handleIdentityForm(form, kind, data) !== false) {
          return;
        }
        if (kind === "delete") {
          setStatus("Deleting account…", "delete");
          const { response, payload } = await api("/api/v1/auth/account/delete", {
            method: "POST",
            body: JSON.stringify({
              confirmation: String(data.get("confirmation") || ""),
              password: String(data.get("password") || ""),
            }),
          });
          if (!response.ok) {
            setStatus(apiError(payload, "Account deletion failed."), "delete");
            return;
          }
          await clearLocalAuth();
          setStatus(
            `Account deleted. Sessions revoked: ${payload.sessions_revoked ?? 0}. This does not certify backup, log, or vendor erasure.`,
            "delete",
          );
          window.setTimeout(() => window.location.assign("/login"), 1200);
        }
      } catch {
        setStatus("PiqSavi could not reach the account service. Try again.");
      }
    });
  });
}

function setHeaderAuthState(signedIn) {
  document.querySelectorAll("[data-header-auth]").forEach((node) => {
    const state = node.getAttribute("data-header-auth");
    node.hidden = signedIn ? state !== "signed-in" : state !== "signed-out";
  });
}

async function resolveAuthSession() {
  const token = readToken();
  if (!token) {
    setHeaderAuthState(false);
    return { ok: false, payload: null, reason: "missing" };
  }
  try {
    const { response, payload } = await api("/api/v1/auth/me");
    if (!response.ok) {
      await clearLocalAuth();
      setHeaderAuthState(false);
      return { ok: false, payload: null, reason: "invalid" };
    }
    setHeaderAuthState(true);
    return { ok: true, payload, reason: "valid" };
  } catch {
    setHeaderAuthState(false);
    return { ok: false, payload: null, reason: "error" };
  }
}

function applyAccountPageSession(session) {
  const signedIn = qs("[data-account-signed-in]");
  const signedOut = qs("[data-account-signed-out]");
  if (!signedIn || !signedOut) return;
  if (!session.ok) {
    signedOut.hidden = false;
    signedIn.hidden = true;
    if (session.reason === "invalid") {
      setStatus("This session is no longer valid. Sign in again.");
    } else if (session.reason === "error") {
      setStatus("PiqSavi could not reach the account service. Try again.");
    } else {
      setStatus("You are signed out on this device.");
    }
    return;
  }
  const payload = session.payload || {};
  signedOut.hidden = true;
  signedIn.hidden = false;
  qs("[data-account-name]").textContent = payload.display_name || "";
  qs("[data-account-email]").textContent = payload.email || "";
  qs("[data-account-id]").textContent = payload.user_id || "";
  const verified = qs("[data-account-verified]");
  const verifyNeeded = qs("[data-account-verify-needed]");
  if (payload.email_verified) {
    verified.textContent = "Verified";
    verified.classList.add("status-verified");
    if (verifyNeeded) verifyNeeded.hidden = true;
  } else {
    verified.textContent = "Not verified";
    verified.classList.remove("status-verified");
    if (verifyNeeded) verifyNeeded.hidden = false;
  }
  setStatus("Signed in.");
}

async function loadAccount() {
  const session = await resolveAuthSession();
  applyAccountPageSession(session);
  const consentList = qs("[data-consent-records]");
  if (session.ok && consentList) {
    await loadConsentAudit(consentList);
  }
}

async function signOutCurrentDevice(redirectTo) {
  setStatus("Signing out…");
  try {
    await api("/api/v1/auth/logout", { method: "POST" });
  } catch {
    /* Logout is best-effort. Local/device auth still clears. */
  }
  await clearLocalAuth();
  window.location.assign(redirectTo);
}

function bindActions() {
  document.querySelectorAll('[data-account-action="sign-out"]').forEach((button) => {
    button.addEventListener("click", async () => {
      const redirectTo = button.getAttribute("data-sign-out-redirect") || "/login";
      await signOutCurrentDevice(redirectTo);
    });
  });
  qs('[data-account-action="export"]')?.addEventListener("click", async () => {
    setStatus("Preparing export…", "export");
    const { response, payload } = await api("/api/v1/auth/account/export");
    if (!response.ok) {
      setStatus(apiError(payload, "Export failed."), "export");
      return;
    }
    const blob = new Blob([JSON.stringify(payload, null, 2)], { type: "application/json" });
    const url = URL.createObjectURL(blob);
    const link = document.createElement("a");
    link.href = url;
    link.download = "piqsavi-account-export.json";
    link.click();
    URL.revokeObjectURL(url);
    setStatus(
      `Export downloaded (${payload.export_schema || "unknown schema"}). This is an engineering export, not a complete legal DSAR.`,
      "export",
    );
  });
}

async function loadConsentAudit(listNode) {
  const unpublished = qs("[data-consent-unpublished]");
  setStatus("Loading consent records…", "consent");
  const { response, payload } = await api("/api/v1/auth/account/consents");
  if (!response.ok) {
    setStatus(apiError(payload, "Could not load consent records."), "consent");
    return;
  }
  const records = Array.isArray(payload.records) ? payload.records : [];
  listNode.replaceChildren();
  if (unpublished) unpublished.hidden = !payload.unpublished;
  if (!records.length) {
    setStatus(
      payload.unpublished
        ? "No published policy version exists, so no acceptance records were stored."
        : "No policy-acceptance records for this account.",
      "consent",
    );
    return;
  }
  records.forEach((record) => {
    const item = document.createElement("li");
    const policy = String(record.policy_type || "policy");
    const version = String(record.version_id || "unknown");
    const accepted = String(record.accepted_at || "");
    item.textContent = `${policy} ${version}${accepted ? ` accepted ${accepted}` : ""}`;
    listNode.appendChild(item);
  });
  setStatus(`${records.length} policy-acceptance record(s) for this account.`, "consent");
}

bindIdentityToken();
bindForms();
bindActions();
loadAccount();

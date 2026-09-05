const TOKEN_KEY = "piqsavi_access_token";
const REMEMBER_KEY = "piqsavi_remember_me";
const CONVERSATION_KEY = "piqsavi_ask_conversation";

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
              terms_accepted: data.get("terms_accepted") === "on",
              privacy_acknowledged: data.get("privacy_acknowledged") === "on",
            }),
          });
          if (!response.ok) {
            setStatus(apiError(payload, "Registration failed."));
            return;
          }
          await afterAuth(payload, safeNext(String(data.get("next") || "")), remember);
          return;
        }
        if (kind === "reset-request") {
          setStatus("Submitting reset request…");
          const { response, payload } = await api("/api/v1/auth/password-reset", {
            method: "POST",
            body: JSON.stringify({ email: String(data.get("email") || "") }),
          });
          if (!response.ok) {
            setStatus(apiError(payload, "Reset request failed."));
            return;
          }
          const delivery = payload.email_delivery ? "A reset email can be delivered." : "Email delivery is not available on this host.";
          setStatus(`If an account exists, the request was accepted. ${delivery} Demo tokens are not shown.`);
          return;
        }
        if (kind === "reset-confirm") {
          setStatus("Updating password…");
          const { response, payload } = await api("/api/v1/auth/password-reset/confirm", {
            method: "POST",
            body: JSON.stringify({
              token: String(data.get("token") || ""),
              new_password: String(data.get("new_password") || ""),
            }),
          });
          if (!response.ok) {
            setStatus(apiError(payload, "Password reset confirmation failed."));
            return;
          }
          setStatus("Password updated. You can sign in with the new password.");
          return;
        }
        if (kind === "verify-request") {
          setStatus("Submitting verification request…");
          const { response, payload } = await api("/api/v1/auth/verify-email", {
            method: "POST",
            body: JSON.stringify({ email: String(data.get("email") || "") }),
          });
          if (!response.ok) {
            setStatus(apiError(payload, "Verification request failed."));
            return;
          }
          const delivery = payload.email_delivery ? "A verification email can be delivered." : "Email delivery is not available on this host.";
          setStatus(`If an account exists, the request was accepted. ${delivery} Demo tokens are not shown.`);
          return;
        }
        if (kind === "verify-confirm") {
          setStatus("Confirming email…");
          const { response, payload } = await api("/api/v1/auth/verify-email/confirm", {
            method: "POST",
            body: JSON.stringify({ token: String(data.get("token") || "") }),
          });
          if (!response.ok) {
            setStatus(apiError(payload, "Email confirmation failed."));
            return;
          }
          setStatus("Email verified.");
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
          clearToken();
          await fetch("/account/clear-device", { method: "POST", headers: { Accept: "application/json" } });
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

async function loadAccount() {
  const signedIn = qs("[data-account-signed-in]");
  const signedOut = qs("[data-account-signed-out]");
  if (!signedIn || !signedOut) return;
  const token = readToken();
  if (!token) {
    signedOut.hidden = false;
    signedIn.hidden = true;
    setStatus("You are signed out on this device.");
    return;
  }
  const { response, payload } = await api("/api/v1/auth/me");
  if (!response.ok) {
    clearToken();
    signedOut.hidden = false;
    signedIn.hidden = true;
    setStatus("This session is no longer valid. Sign in again.");
    return;
  }
  signedOut.hidden = true;
  signedIn.hidden = false;
  qs("[data-account-name]").textContent = payload.display_name || "";
  qs("[data-account-email]").textContent = payload.email || "";
  qs("[data-account-id]").textContent = payload.user_id || "";
  qs("[data-account-verified]").textContent = payload.email_verified
    ? "Verified"
    : "Not verified";
  setStatus("Signed in.");
}

function bindActions() {
  qs('[data-account-action="sign-out"]')?.addEventListener("click", async () => {
    setStatus("Signing out…");
    await api("/api/v1/auth/logout", { method: "POST" });
    clearToken();
    await fetch("/account/clear-device", { method: "POST", headers: { Accept: "application/json" } });
    window.location.assign("/login");
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

bindForms();
bindActions();
loadAccount();

const REPORTS_URL = "/api/v1/feedback/reports";
const UUID_RE =
  /^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$/i;

function newId() {
  if (window.crypto && typeof window.crypto.randomUUID === "function") {
    return window.crypto.randomUUID();
  }
  return "";
}

function statusNode(root) {
  return root.querySelector("[data-feedback-status]") || document.querySelector("[data-feedback-status]");
}

async function submitReport(body, status) {
  try {
    const response = await fetch(REPORTS_URL, {
      method: "POST",
      headers: { Accept: "application/json", "Content-Type": "application/json" },
      body: JSON.stringify(body),
    });
    const payload = await response.json();
    if (!response.ok) {
      if (status) status.textContent = "The report was not saved. You can email support@piqsavi.com.";
      return;
    }
    const reference = String(payload.report_id || "");
    if (status) {
      status.textContent = reference
        ? `Received. Reference ${reference}. This does not promise a correction or a response time.`
        : "Received. This does not promise a correction or a response time.";
    }
  } catch {
    if (status) status.textContent = "The report was not saved. Shopping and support email still work.";
  }
}

export function initProductFeedback() {
  document.querySelectorAll("[data-feedback-form]").forEach((form) => {
    if (!(form instanceof HTMLFormElement)) return;
    let submissionId = newId();
    form.addEventListener("submit", (event) => {
      event.preventDefault();
      const data = new FormData(form);
      const body = {
        category: String(data.get("category") || ""),
        message: String(data.get("message") || ""),
        surface: String(data.get("surface") || "support"),
      };
      const decisionId = String(data.get("decision_id") || "");
      if (UUID_RE.test(decisionId)) body.decision_id = decisionId;
      const version = String(data.get("context_version") || "");
      if (version) body.context_version = Number(version);
      if (!submissionId) submissionId = newId();
      if (submissionId) body.client_submission_id = submissionId;
      const status = statusNode(form.parentElement || document);
      void submitReport(body, status).then(() => {
        submissionId = newId();
      });
    });
  });

  document.querySelectorAll("[data-feedback-category]").forEach((button) => {
    if (button.closest("[data-feedback-form]")) return;
    button.addEventListener("click", () => {
      const category = button.getAttribute("data-feedback-category");
      if (!category) return;
      const body = { category, message: "", surface: document.body?.dataset?.page || "results" };
      const decisionId = document.body?.dataset?.decisionId || "";
      if (UUID_RE.test(decisionId)) body.decision_id = decisionId;
      const version = document.body?.dataset?.contextVersion || "";
      if (version) body.context_version = Number(version);
      const submissionId = newId();
      if (submissionId) body.client_submission_id = submissionId;
      const root = button.closest("[data-feedback-controls]") || document;
      void submitReport(body, statusNode(root));
    });
  });
}

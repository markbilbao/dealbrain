import { analyticsAllowed } from "./tracking_preference.js";

const EVENTS_URL = "/api/v1/analytics/events";
const PAGE_EVENTS = {
  results: "results_viewed",
  compare: "compare_opened",
  why: "why_opened",
};
const UUID_RE =
  /^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$/i;

function eventId() {
  if (window.crypto && typeof window.crypto.randomUUID === "function") {
    return window.crypto.randomUUID();
  }
  return "";
}

export async function emitProductEvent(eventName, properties) {
  try {
    if (!(await analyticsAllowed())) return;
    const body = { event_name: eventName };
    const id = eventId();
    if (id) body.event_id = id;
    const source = properties || {};
    ["surface", "action_type", "outcome", "evidence_count", "turn_number"].forEach((key) => {
      if (source[key] !== undefined && source[key] !== null && source[key] !== "") {
        body[key] = source[key];
      }
    });
    if (source.decision_id && UUID_RE.test(String(source.decision_id))) {
      body.decision_id = String(source.decision_id);
    }
    await fetch(EVENTS_URL, {
      method: "POST",
      headers: { Accept: "application/json", "Content-Type": "application/json" },
      body: JSON.stringify(body),
    });
  } catch {
    /* Analytics must not break shopping or navigation. */
  }
}

export function initProductAnalytics() {
  const page = document.body?.dataset?.page || "";
  const eventName = PAGE_EVENTS[page];
  if (eventName) {
    const decisionId = document.body?.dataset?.decisionId || "";
    void emitProductEvent(eventName, {
      surface: page,
      action_type: page === "results" ? "view" : "open",
      outcome: page === "results" ? "viewed" : "opened",
      decision_id: decisionId,
    });
  }
  document.addEventListener("click", (event) => {
    const target = event.target;
    if (!(target instanceof Element)) return;
    const link = target.closest("[data-analytics-event]");
    if (!link) return;
    const name = link.getAttribute("data-analytics-event");
    if (!name) return;
    void emitProductEvent(name, {
      surface: document.body?.dataset?.page || "results",
      action_type: "click",
      outcome: "clicked",
      decision_id: document.body?.dataset?.decisionId || "",
    });
  });
}

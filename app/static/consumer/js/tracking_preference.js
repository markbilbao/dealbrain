const PREFERENCE_URL = "/api/v1/privacy/tracking-preference";

async function readPreference() {
  const response = await fetch(PREFERENCE_URL, { headers: { Accept: "application/json" } });
  if (!response.ok) return null;
  return response.json();
}

function choiceLabel(choice) {
  if (choice === "analytics_allowed") return "Optional product analytics is allowed on this device.";
  return "Essential only. Optional product analytics is off.";
}

export async function analyticsAllowed() {
  try {
    const preference = await readPreference();
    return Boolean(preference && preference.analytics_allowed);
  } catch {
    return false;
  }
}

export function initTrackingPreference() {
  const buttons = document.querySelectorAll("[data-tracking-choice]");
  if (!buttons.length) return;
  const status = document.querySelector("[data-tracking-status]");
  const current = document.querySelector("[data-tracking-current]");
  buttons.forEach((button) => {
    button.addEventListener("click", async () => {
      const choice = button.getAttribute("data-tracking-choice");
      try {
        const response = await fetch(PREFERENCE_URL, {
          method: "POST",
          headers: { Accept: "application/json", "Content-Type": "application/json" },
          body: JSON.stringify({ choice }),
        });
        const payload = await response.json();
        if (!response.ok) {
          const message = "Could not save that choice. Essential-only remains the default.";
          if (status) status.textContent = message;
          if (current) current.textContent = message;
          return;
        }
        const text = choiceLabel(payload.choice);
        if (status) status.textContent = text;
        if (current) current.textContent = text;
        const notice = document.querySelector("[data-tracking-preference]");
        if (notice) notice.hidden = true;
      } catch {
        const message = "Could not save that choice. Shopping still works.";
        if (status) status.textContent = message;
        if (current) current.textContent = message;
      }
    });
  });
  if (current) {
    readPreference()
      .then((preference) => {
        if (preference) current.textContent = choiceLabel(preference.choice);
      })
      .catch(() => {
        current.textContent = choiceLabel("essential_only");
      });
  }
}

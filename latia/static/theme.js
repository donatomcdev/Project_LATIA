"use strict";

try {
  if (localStorage.getItem("latia-theme") === "dark") {
    document.documentElement.dataset.theme = "dark";
  }
} catch {
  // The theme still works for the current page if storage is unavailable.
}

document.addEventListener("DOMContentLoaded", () => {
  const settings = document.querySelector("#settings");
  if (!settings) return;

  const summary = settings.querySelector("summary");
  const theme = document.documentElement.dataset.theme || "light";
  settings.querySelector(`input[value="${theme}"]`).checked = true;
  settings.addEventListener("change", event => {
    const theme = event.target.value;
    document.documentElement.dataset.theme = theme;
    try {
      localStorage.setItem("latia-theme", theme);
    } catch {
      // Leave the current theme applied.
    }
    document.dispatchEvent(new Event("latia-theme-change"));
  });
  document.addEventListener("click", event => {
    if (!settings.contains(event.target)) settings.open = false;
  });
  settings.addEventListener("keydown", event => {
    if (event.key === "Escape" && settings.open) {
      settings.open = false;
      summary.focus();
    }
  });
});

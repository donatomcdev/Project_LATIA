"use strict";

(() => {
  if (!matchMedia("(prefers-reduced-motion: no-preference)").matches) return;

  try {
    if (sessionStorage.getItem("latia-splash-seen")) return;
    sessionStorage.setItem("latia-splash-seen", "1");
  } catch {
    // Skip the intro when its frequency cannot be tracked.
    return;
  }

  document.querySelector(".splash").classList.add("splash-active");
})();

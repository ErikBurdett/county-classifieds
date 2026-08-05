(() => {
  "use strict";

  const center = document.querySelector("[data-notification-center]");
  if (!center) return;

  center.classList.add("notification-center--enhanced");
  const summary = center.querySelector("summary");

  document.addEventListener("click", (event) => {
    if (center.open && !center.contains(event.target)) center.open = false;
  });

  document.addEventListener("keydown", (event) => {
    if (event.key === "Escape" && center.open) {
      event.preventDefault();
      center.open = false;
      summary.focus();
    }
  });
})();

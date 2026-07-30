(() => {
  "use strict";

  const header = document.querySelector("[data-site-header]");
  const toggle = document.querySelector("[data-nav-toggle]");
  const navigation = document.querySelector("[data-primary-navigation]");

  if (!header || !toggle || !navigation) return;

  header.classList.add("nav-enhanced");

  function closeNavigation({ returnFocus = false } = {}) {
    header.classList.remove("is-nav-open");
    toggle.setAttribute("aria-expanded", "false");
    if (returnFocus) toggle.focus();
  }

  function openNavigation() {
    header.classList.add("is-nav-open");
    toggle.setAttribute("aria-expanded", "true");
  }

  toggle.addEventListener("click", () => {
    if (header.classList.contains("is-nav-open")) {
      closeNavigation();
    } else {
      openNavigation();
    }
  });

  document.addEventListener("keydown", (event) => {
    if (event.key === "Escape" && header.classList.contains("is-nav-open")) {
      event.preventDefault();
      closeNavigation({ returnFocus: true });
    }
  });

  navigation.addEventListener("click", (event) => {
    if (event.target.closest("a, button")) closeNavigation();
  });
})();

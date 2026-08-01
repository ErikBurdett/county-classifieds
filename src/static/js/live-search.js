(() => {
  "use strict";

  const FRAGMENT_ACCEPT = "text/vnd.countypost.fragment+html";
  const DEBOUNCE_MS = 250;

  function setLoading(form, isLoading) {
    const status = form.querySelector(".live-search-status");
    form.setAttribute("aria-busy", String(isLoading));
    if (status) {
      status.textContent = isLoading ? "Loading results…" : "";
    }
  }

  function formUrl(form, resetPage) {
    const url = new URL(form.action || window.location.href, window.location.origin);
    const values = new FormData(form);
    for (const [key, value] of values.entries()) {
      if (key === "nearby_radius" && value === "50") continue;
      if (key === "scope" && value === "state") continue;
      if (key === "intent" && value === "offer") continue;
      if (typeof value === "string" && value) {
        url.searchParams.set(key, value);
      }
    }
    if (resetPage) {
      url.searchParams.delete("page");
    }
    return url;
  }

  function enableLiveSearch(form) {
    const kind = form.dataset.liveSearch;
    const resultId = kind === "market" ? "market-finder-results" : "listing-results";
    if (!document.getElementById(resultId)) return;

    let requestController;
    let timer;
    let lastUrl = "";

    async function update(resetPage) {
      const url = formUrl(form, resetPage);
      if (kind === "market" && !url.searchParams.get("q")?.trim()) return;
      if (url.href === lastUrl) return;
      requestController?.abort();
      const controller = new AbortController();
      requestController = controller;
      setLoading(form, true);

      try {
        const response = await fetch(url, {
          headers: { Accept: FRAGMENT_ACCEPT },
          signal: controller.signal,
        });
        if (!response.ok) throw new Error("Search request failed");
        const replacement = await response.text();
        const results = document.getElementById(resultId);
        if (!results || controller.signal.aborted) return;
        results.outerHTML = replacement;
        lastUrl = url.href;
        window.history.replaceState({}, "", `${url.pathname}${url.search}`);
      } catch (error) {
        if (error.name !== "AbortError") {
          const status = form.querySelector(".live-search-status");
          if (status) status.textContent = "Results could not be updated. Use Apply filters to try again.";
        }
      } finally {
        if (requestController === controller && !controller.signal.aborted) {
          setLoading(form, false);
        }
      }
    }

    form.addEventListener("submit", (event) => {
      event.preventDefault();
      void update(kind === "browse");
    });

    form.querySelectorAll("input").forEach((input) => {
      if (input.dataset.nearbyRadius !== undefined) {
        const output = form.querySelector("#nearby-radius-output");
        input.addEventListener("input", () => {
          if (output) output.value = `${input.value} miles`;
        });
        input.addEventListener("change", () => {
          window.location.assign(formUrl(form, true));
        });
      }
      input.addEventListener("input", () => {
        if (input.dataset.nearbyRadius !== undefined) return;
        window.clearTimeout(timer);
        timer = window.setTimeout(() => void update(kind === "browse"), DEBOUNCE_MS);
      });
    });
    form.querySelectorAll("select").forEach((select) => {
      select.addEventListener("change", () => void update(kind === "browse"));
    });
  }

  document.querySelectorAll("form[data-live-search]").forEach(enableLiveSearch);

  function enableFilterDisclosure(panel) {
    const toggle = panel.querySelector("[data-filter-toggle]");
    const controls = panel.querySelector(".filter-disclosure-content");
    if (!toggle || !controls) return;

    const mobileQuery = window.matchMedia("(max-width: 45rem)");
    const startsOpen = panel.dataset.filterOpen === "true";
    const hasErrors = panel.dataset.filterHasErrors === "true";

    function setOpen(isOpen) {
      panel.classList.toggle("is-filter-open", isOpen);
      toggle.setAttribute("aria-expanded", String(isOpen));
      toggle.textContent = isOpen ? "Hide filters" : "Show filters";
    }

    function applyViewportState() {
      if (mobileQuery.matches) {
        panel.classList.add("filter-enhanced");
        setOpen(startsOpen);
      } else {
        panel.classList.remove("filter-enhanced");
        setOpen(true);
      }
    }

    toggle.addEventListener("click", () => {
      setOpen(toggle.getAttribute("aria-expanded") !== "true");
    });
    document.addEventListener("keydown", (event) => {
      if (
        event.key === "Escape" &&
        mobileQuery.matches &&
        panel.classList.contains("is-filter-open")
      ) {
        event.preventDefault();
        setOpen(false);
        toggle.focus();
      }
    });
    mobileQuery.addEventListener("change", applyViewportState);
    applyViewportState();

    if (hasErrors) {
      panel.querySelector("[data-filter-error-summary]")?.focus();
    }
  }

  document.querySelectorAll("[data-filter-disclosure]").forEach(enableFilterDisclosure);
})();

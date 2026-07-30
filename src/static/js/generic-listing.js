(() => {
  const form = document.querySelector("[data-generic-listing-form]");
  if (!form) return;
  const vertical = form.querySelector("#id_vertical");
  const category = form.querySelector("#id_category");
  const categoryField = form.querySelector("[data-category-field]");
  const state = form.querySelector("#id_state");
  const zip = form.querySelector("#id_postal_code");
  const county = form.querySelector("#id_county");
  const additional = form.querySelector("#id_additional_counties");
  const status = form.querySelector("[data-county-status]");
  const countyEnhancement = form.querySelector("[data-county-enhancement]");
  const countyFallback = form.querySelector("[data-county-fallback]");
  const countyInput = form.querySelector("[data-county-input]");
  const countyResults = form.querySelector("[data-county-results]");
  const additionalEnhancement = form.querySelector("[data-additional-county-enhancement]");
  const additionalFallback = form.querySelector("[data-additional-county-fallback]");
  const additionalInput = form.querySelector("[data-additional-county-input]");
  const additionalResults = form.querySelector("[data-additional-county-results]");
  const additionalTags = form.querySelector("[data-additional-county-tags]");
  const quote = form.querySelector("[data-placement-quote]");
  const categoryUrl = form.dataset.categoryUrl;
  const countyUrl = form.dataset.countyUrl;
  let countyRequest;
  let countySearchTimer;
  let activeResultIndex = -1;
  let countyResultsData = [];
  let countyLoadRequest;
  let allCountiesData = [];
  let latestCountyStatus = "state_counties";
  let latestCrosswalkLoaded = false;

  const selectedValues = (element) => Array.from(element.selectedOptions, ({ value }) => value);
  const replaceOptions = (element, items, selected, { showVerification = false } = {}) => {
    const selectedSet = new Set(selected);
    const options = element === category
      ? [new Option("Choose a category", "")]
      : element === county
        ? [new Option("Choose a county", "")]
        : [];
    items.forEach(({ id, name, verified }) => {
      const verification = showVerification
        ? verified ? " — verified for this ZIP" : " — not verified for this ZIP"
        : "";
      options.push(new Option(`${name}${verification}`, id, selectedSet.has(String(id)), selectedSet.has(String(id))));
    });
    element.replaceChildren(...options);
  };
  const selectedCounty = () => county.selectedOptions[0];
  const zipIsValid = () => /^\d{5}$/.test(zip.value);
  const countyForId = (id) => allCountiesData.find((item) => String(item.id) === String(id));
  const updateQuote = () => {
    const count = additional.selectedOptions.length;
    quote.textContent = `Local demo quote: $10 primary placement + $5 × ${count} nearby ${count === 1 ? "county" : "counties"} = $${10 + (count * 5)}. This is a local-demo display, not a payment claim or production checkout; the server quote and snapshot remain authoritative.`;
  };
  const verificationText = (item) => {
    if (!zipIsValid()) return "ZIP not yet verified";
    return item.verified ? "Verified for this ZIP" : "Not verified for this ZIP";
  };
  const renderAdditionalTags = () => {
    const selected = selectedValues(additional).map(countyForId).filter(Boolean);
    additionalTags.replaceChildren(...selected.map((item) => {
      const tag = document.createElement("li");
      tag.className = "county-tag";
      const label = document.createElement("span");
      label.textContent = `${item.name} — ${verificationText(item)}`;
      const remove = document.createElement("button");
      remove.type = "button";
      remove.className = "county-tag__remove";
      remove.textContent = `Remove ${item.name}`;
      remove.setAttribute("aria-label", `Remove ${item.name} from nearby counties`);
      remove.addEventListener("click", () => {
        const option = Array.from(additional.options).find((candidate) => candidate.value === String(item.id));
        if (option) option.selected = false;
        additional.dispatchEvent(new Event("change", { bubbles: true }));
      });
      tag.append(label, remove);
      return tag;
    }));
  };
  const updateAllCountyStatus = () => {
    if (!state.value) {
      status.textContent = "Choose a state to see its active counties. Enter a five-digit ZIP to verify your choices before saving.";
    } else if (zipIsValid() && !latestCrosswalkLoaded) {
      status.textContent = "The offline HUD ZIP–county reference data has not been loaded. Your county choices are preserved, but a ZIP cannot be verified until it is imported.";
    } else if (latestCountyStatus === "zip_no_candidates") {
      status.textContent = "No offline HUD ZIP–county candidates were found for this ZIP and state. Your county choices are preserved, but choose a ZIP with loaded candidates before saving.";
    } else if (zipIsValid()) {
      const selected = [countyForId(county.value), ...selectedValues(additional).map(countyForId)].filter(Boolean);
      status.textContent = selected.length
        ? selected.map((item) => `${item.name}: ${verificationText(item)}.`).join(" ")
        : "Choose a primary county and any additional counties. Only counties verified for this ZIP can be saved.";
    } else {
      status.textContent = "Choose a primary county and any additional counties. Enter a five-digit ZIP to verify your choices before saving.";
    }
  };
  const closeCountyResults = () => {
    countyResults.hidden = true;
    countyInput.setAttribute("aria-expanded", "false");
    countyInput.removeAttribute("aria-activedescendant");
    activeResultIndex = -1;
  };
  const updateActiveResult = (index) => {
    const options = Array.from(countyResults.querySelectorAll('[role="option"]'));
    if (!options.length) return;
    activeResultIndex = (index + options.length) % options.length;
    options.forEach((option, optionIndex) => {
      const isActive = optionIndex === activeResultIndex;
      option.setAttribute("aria-selected", String(isActive));
      option.classList.toggle("is-active", isActive);
    });
    countyInput.setAttribute("aria-activedescendant", options[activeResultIndex].id);
  };
  const updateCountyStatus = (countyStatus, crosswalkLoaded, counties) => {
    latestCountyStatus = countyStatus;
    latestCrosswalkLoaded = crosswalkLoaded;
    allCountiesData = counties;
    if (!counties.length && countyStatus === "state_counties") {
      status.textContent = "This state has no active counties available. Contact support before saving a listing.";
    } else {
      updateAllCountyStatus();
    }
  };
  const selectCounty = (item) => {
    county.value = String(item.id);
    countyInput.value = item.name;
    const matchingAdditional = Array.from(additional.options).find(
      (option) => option.value === String(item.id)
    );
    if (matchingAdditional) matchingAdditional.selected = false;
    closeCountyResults();
    renderAdditionalTags();
    updateQuote();
    updateAllCountyStatus();
    county.dispatchEvent(new Event("change", { bubbles: true }));
  };
  const renderCountyResults = (items) => {
    countyResultsData = items;
    countyResults.replaceChildren(...items.map((item, index) => {
      const option = document.createElement("li");
      option.id = `county-search-option-${index}`;
      option.setAttribute("role", "option");
      option.setAttribute("aria-selected", "false");
      option.dataset.countyId = String(item.id);
      option.textContent = item.name;
      option.addEventListener("mousedown", (event) => {
        event.preventDefault();
        selectCounty(item);
      });
      return option;
    }));
    countyResults.hidden = !items.length;
    countyInput.setAttribute("aria-expanded", String(items.length > 0));
    activeResultIndex = -1;
  };
  const loadCategories = async () => {
    if (!vertical.value) return replaceOptions(category, [], []);
    const response = await fetch(`${categoryUrl}?vertical=${encodeURIComponent(vertical.value)}`, { headers: { Accept: "application/json" } });
    if (!response.ok) return;
    const payload = await response.json();
    replaceOptions(category, payload.categories, [category.value]);
    if (payload.automatic_category_id) {
      category.value = String(payload.automatic_category_id);
      categoryField.hidden = true;
      if (form.dataset.unifiedCreate) showFields();
    } else {
      categoryField.hidden = false;
    }
  };
  const loadCounties = async ({ stateChanged = false } = {}) => {
    if (!state.value) {
      county.value = "";
      additional.replaceChildren();
      countyInput.value = "";
      countyInput.disabled = true;
      countyInput.placeholder = "Choose a state first";
      additionalInput.value = "";
      additionalInput.disabled = true;
      additionalInput.placeholder = "Choose a state first";
      allCountiesData = [];
      renderAdditionalTags();
      updateQuote();
      closeCountyResults();
      updateAllCountyStatus();
      return;
    }
    if (stateChanged) {
      countyRequest?.abort();
      additionalRequest?.abort();
      county.value = "";
      additional.replaceChildren();
      countyInput.value = "";
      additionalInput.value = "";
      closeCountyResults();
      closeAdditionalResults();
      renderAdditionalTags();
      updateQuote();
    }
    status.textContent = "Loading active counties…";
    status.setAttribute("aria-busy", "true");
    countyLoadRequest?.abort();
    countyLoadRequest = new AbortController();
    let response;
    try {
      response = await fetch(
        `${countyUrl}?state=${encodeURIComponent(state.value)}&postal_code=${encodeURIComponent(zip.value)}`,
        { headers: { Accept: "application/json" }, signal: countyLoadRequest.signal }
      );
    } catch (error) {
      if (error.name === "AbortError") return;
      status.textContent = "Active counties could not be loaded. You can still submit the form for server-side validation.";
      status.setAttribute("aria-busy", "false");
      return;
    }
    if (!response.ok) {
      status.textContent = "Active counties could not be loaded. You can still submit the form for server-side validation.";
      status.setAttribute("aria-busy", "false");
      return;
    }
    const previousCounty = [county.value];
    const previousAdditional = selectedValues(additional);
    const { counties, status: countyStatus, crosswalk_loaded: crosswalkLoaded } = await response.json();
    const showVerification = /^\d{5}$/.test(zip.value);
    replaceOptions(county, counties, previousCounty, { showVerification });
    replaceOptions(additional, counties, previousAdditional, { showVerification });
    const chosen = selectedCounty();
    countyInput.value = chosen && chosen.value ? chosen.textContent.replace(/ — (verified|not verified) for this ZIP$/, "") : "";
    countyInput.disabled = false;
    countyInput.placeholder = "Type a county name";
    additionalInput.disabled = false;
    additionalInput.placeholder = "Type a county name";
    updateCountyStatus(countyStatus, crosswalkLoaded, counties);
    renderAdditionalTags();
    updateQuote();
    status.setAttribute("aria-busy", "false");
  };
  const searchCounties = async () => {
    const query = countyInput.value.trim();
    if (!state.value) return;
    if (!query) return closeCountyResults();
    countyRequest?.abort();
    countyRequest = new AbortController();
    status.textContent = "Searching active counties…";
    status.setAttribute("aria-busy", "true");
    try {
      const response = await fetch(
        `${countyUrl}?state=${encodeURIComponent(state.value)}&postal_code=${encodeURIComponent(zip.value)}&q=${encodeURIComponent(query)}`,
        { headers: { Accept: "application/json" }, signal: countyRequest.signal }
      );
      if (!response.ok) throw new Error("County search failed");
      const { counties } = await response.json();
      renderCountyResults(counties);
      status.textContent = counties.length
        ? `${counties.length} matching active ${counties.length === 1 ? "county" : "counties"}. Use Arrow keys and Enter to select.`
        : "No active counties match that name.";
    } catch (error) {
      if (error.name !== "AbortError") {
        closeCountyResults();
        status.textContent = "County search is unavailable. Use the county select or try again.";
      }
    } finally {
      status.setAttribute("aria-busy", "false");
    }
  };
  let additionalRequest;
  let additionalSearchTimer;
  let additionalActiveResultIndex = -1;
  let additionalResultsData = [];
  const closeAdditionalResults = () => {
    additionalResults.hidden = true;
    additionalInput.setAttribute("aria-expanded", "false");
    additionalInput.removeAttribute("aria-activedescendant");
    additionalActiveResultIndex = -1;
  };
  const selectAdditionalCounty = (item) => {
    if (String(item.id) === county.value || selectedValues(additional).includes(String(item.id))) {
      status.textContent = `${item.name} is already selected or is the primary county.`;
      closeAdditionalResults();
      return;
    }
    const option = Array.from(additional.options).find((candidate) => candidate.value === String(item.id));
    if (option) option.selected = true;
    additionalInput.value = "";
    closeAdditionalResults();
    renderAdditionalTags();
    updateQuote();
    updateAllCountyStatus();
    additional.dispatchEvent(new Event("change", { bubbles: true }));
  };
  const renderAdditionalResults = (items) => {
    additionalResultsData = items;
    additionalResults.replaceChildren(...items.map((item, index) => {
      const option = document.createElement("li");
      option.id = `additional-county-search-option-${index}`;
      option.setAttribute("role", "option");
      option.setAttribute("aria-selected", "false");
      option.dataset.countyId = String(item.id);
      option.textContent = `${item.name}${zipIsValid() ? ` — ${verificationText(item)}` : ""}`;
      option.addEventListener("mousedown", (event) => {
        event.preventDefault();
        selectAdditionalCounty(item);
      });
      return option;
    }));
    additionalResults.hidden = !items.length;
    additionalInput.setAttribute("aria-expanded", String(items.length > 0));
    additionalActiveResultIndex = -1;
  };
  const searchAdditionalCounties = async () => {
    const query = additionalInput.value.trim();
    if (!state.value || !query) return closeAdditionalResults();
    additionalRequest?.abort();
    additionalRequest = new AbortController();
    status.textContent = "Searching active counties…";
    status.setAttribute("aria-busy", "true");
    try {
      const response = await fetch(
        `${countyUrl}?state=${encodeURIComponent(state.value)}&postal_code=${encodeURIComponent(zip.value)}&q=${encodeURIComponent(query)}`,
        { headers: { Accept: "application/json" }, signal: additionalRequest.signal }
      );
      if (!response.ok) throw new Error("County search failed");
      const { counties } = await response.json();
      renderAdditionalResults(counties);
      status.textContent = counties.length
        ? `${counties.length} matching active ${counties.length === 1 ? "county" : "counties"}. Use Arrow keys and Enter to add one.`
        : "No active counties match that name.";
    } catch (error) {
      if (error.name !== "AbortError") {
        closeAdditionalResults();
        status.textContent = "County search is unavailable. Use the county select or try again.";
      }
    } finally {
      status.setAttribute("aria-busy", "false");
    }
  };
  vertical.addEventListener("change", () => { void loadCategories(); });
  const showFields = () => {
    let intent = form.querySelector('input[name="show_fields"]');
    if (!intent) {
      intent = document.createElement("input");
      intent.type = "hidden";
      intent.name = "show_fields";
      intent.value = "1";
      form.append(intent);
    }
    form.requestSubmit();
  };
  category.addEventListener("change", () => {
    if (!form.dataset.unifiedCreate || !category.value) return;
    showFields();
  });
  state.addEventListener("change", () => { void loadCounties({ stateChanged: true }); });
  zip.addEventListener("change", () => { void loadCounties(); });
  county.addEventListener("change", () => {
    const matchingAdditional = Array.from(additional.options).find(
      (option) => option.value === county.value
    );
    if (matchingAdditional) matchingAdditional.selected = false;
    renderAdditionalTags();
    updateQuote();
    updateAllCountyStatus();
  });
  additional.addEventListener("change", () => {
    renderAdditionalTags();
    updateQuote();
    updateAllCountyStatus();
  });
  countyInput.addEventListener("input", () => {
    if (countyInput.value !== selectedCounty()?.textContent.replace(/ — (verified|not verified) for this ZIP$/, "")) county.value = "";
    window.clearTimeout(countySearchTimer);
    countySearchTimer = window.setTimeout(() => { void searchCounties(); }, 250);
  });
  countyInput.addEventListener("keydown", (event) => {
    if (event.key === "ArrowDown" || event.key === "ArrowUp") {
      event.preventDefault();
      updateActiveResult(activeResultIndex + (event.key === "ArrowDown" ? 1 : -1));
    } else if (event.key === "Enter" && countyResultsData.length) {
      event.preventDefault();
      selectCounty(countyResultsData[Math.max(activeResultIndex, 0)]);
    } else if (event.key === "Escape") {
      closeCountyResults();
    } else if (event.key === "Tab") {
      closeCountyResults();
    }
  });
  countyInput.addEventListener("keypress", (event) => {
    if (event.key === "Enter" && countyResultsData.length) event.preventDefault();
  });
  additionalInput.addEventListener("input", () => {
    window.clearTimeout(additionalSearchTimer);
    additionalSearchTimer = window.setTimeout(() => { void searchAdditionalCounties(); }, 250);
  });
  additionalInput.addEventListener("keydown", (event) => {
    const options = Array.from(additionalResults.querySelectorAll('[role="option"]'));
    if (event.key === "ArrowDown" || event.key === "ArrowUp") {
      event.preventDefault();
      if (!options.length) return;
      additionalActiveResultIndex = (
        additionalActiveResultIndex + (event.key === "ArrowDown" ? 1 : -1) + options.length
      ) % options.length;
      options.forEach((option, index) => {
        const isActive = index === additionalActiveResultIndex;
        option.setAttribute("aria-selected", String(isActive));
        option.classList.toggle("is-active", isActive);
      });
      additionalInput.setAttribute("aria-activedescendant", options[additionalActiveResultIndex].id);
    } else if (event.key === "Enter" && additionalResultsData.length) {
      event.preventDefault();
      selectAdditionalCounty(additionalResultsData[Math.max(additionalActiveResultIndex, 0)]);
    } else if (event.key === "Escape" || event.key === "Tab") {
      closeAdditionalResults();
    }
  });
  form.addEventListener("submit", (event) => {
    if (document.activeElement === countyInput && !countyResults.hidden && countyResultsData.length) {
      event.preventDefault();
      selectCounty(countyResultsData[Math.max(activeResultIndex, 0)]);
    } else if (
      document.activeElement === additionalInput
      && !additionalResults.hidden
      && additionalResultsData.length
    ) {
      event.preventDefault();
      selectAdditionalCounty(additionalResultsData[Math.max(additionalActiveResultIndex, 0)]);
    }
  });
  countyInput.addEventListener("blur", () => { window.setTimeout(closeCountyResults, 100); });
  additionalInput.addEventListener("blur", () => { window.setTimeout(closeAdditionalResults, 100); });
  countyEnhancement.hidden = false;
  countyFallback.hidden = true;
  additionalEnhancement.hidden = false;
  additionalFallback.hidden = true;
  updateQuote();
  void loadCounties();
})();

(() => {
  const form = document.querySelector("[data-generic-listing-form]");
  const state = form?.querySelector("#id_state");
  const input = form?.querySelector("[data-state-input]");
  const results = form?.querySelector("[data-state-results]");
  const enhancement = form?.querySelector("[data-state-enhancement]");
  const fallback = form?.querySelector("[data-state-fallback]");
  const endpoint = form?.dataset.stateUrl;
  if (!form || !state || !input || !results || !enhancement || !fallback || !endpoint) return;
  let matches = [];
  let active = -1;
  let timer;
  const close = () => {
    results.hidden = true;
    input.setAttribute("aria-expanded", "false");
    input.removeAttribute("aria-activedescendant");
  };
  const select = (item) => {
    const hasPlacement = state.value && state.value !== String(item.id)
      && (form.querySelector("#id_county")?.value || form.querySelector("#id_additional_counties")?.selectedOptions.length);
    if (hasPlacement && !window.confirm("Changing state clears selected counties. Continue?")) return;
    state.value = String(item.id);
    input.value = `${item.name} (${item.code})`;
    close();
    state.dispatchEvent(new Event("change", { bubbles: true }));
  };
  const render = () => {
    results.replaceChildren(...matches.map((item, index) => {
      const option = document.createElement("li");
      option.id = `state-search-option-${index}`;
      option.setAttribute("role", "option");
      option.setAttribute("aria-selected", "false");
      option.textContent = `${item.name} (${item.code})`;
      option.addEventListener("mousedown", (event) => {
        event.preventDefault();
        select(item);
      });
      return option;
    }));
    results.hidden = !matches.length;
    input.setAttribute("aria-expanded", String(matches.length > 0));
  };
  input.addEventListener("input", () => {
    window.clearTimeout(timer);
    timer = window.setTimeout(async () => {
      if (!input.value.trim()) return close();
      try {
        const response = await fetch(`${endpoint}?q=${encodeURIComponent(input.value.trim())}`, { headers: { Accept: "application/json" } });
        if (!response.ok) throw new Error("State search failed");
        matches = (await response.json()).states;
        active = -1;
        render();
      } catch {
        close();
      }
    }, 200);
  });
  input.addEventListener("keydown", (event) => {
    if (event.key === "Escape") return close();
    if ((event.key === "ArrowDown" || event.key === "ArrowUp") && matches.length) {
      event.preventDefault();
      active = (active + (event.key === "ArrowDown" ? 1 : -1) + matches.length) % matches.length;
      const options = [...results.querySelectorAll('[role="option"]')];
      options.forEach((option, index) => option.setAttribute("aria-selected", String(index === active)));
      input.setAttribute("aria-activedescendant", options[active].id);
    }
    if (event.key === "Enter" && matches.length) {
      event.preventDefault();
      select(matches[Math.max(active, 0)]);
    }
  });
  input.addEventListener("blur", () => window.setTimeout(close, 100));
  if (state.selectedOptions[0]?.value) input.value = state.selectedOptions[0].textContent;
  enhancement.hidden = false;
  fallback.hidden = true;
})();

(() => {
  const form = document.querySelector("[data-unified-listing-form]");
  const vertical = form?.querySelector("#id_vertical");
  const category = form?.querySelector("#id_category");
  const categoryField = form?.querySelector("[data-category-field]");
  const categoryUrl = form?.dataset.categoryUrl;
  if (!form || !vertical || !category || !categoryUrl) return;

  const replaceCategories = (categories) => {
    const selected = category.value;
    const options = [new Option("Choose a category", "")];
    categories.forEach(({ id, name }) => {
      options.push(new Option(name, id, String(id) === selected, String(id) === selected));
    });
    category.replaceChildren(...options);
  };

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
  const loadCategories = async () => {
    if (!vertical.value) {
      replaceCategories([]);
      return;
    }
    try {
      const response = await fetch(
        `${categoryUrl}?vertical=${encodeURIComponent(vertical.value)}`,
        { headers: { Accept: "application/json" } }
      );
      if (!response.ok) throw new Error("Category request failed");
      const payload = await response.json();
      replaceCategories(payload.categories);
      if (payload.automatic_category_id) {
        category.value = String(payload.automatic_category_id);
        categoryField.hidden = true;
        showFields();
      } else {
        categoryField.hidden = false;
      }
    } catch {
      // The ordinary form submission remains the accessible fallback.
      replaceCategories([]);
    }
  };

  vertical.addEventListener("change", () => {
    void loadCategories();
  });

  category.addEventListener("change", () => {
    if (!category.value) return;
    showFields();
  });

  const state = form.querySelector("#id_state");
  const county = form.querySelector("#id_county");
  const stateInput = form.querySelector("[data-state-input]");
  const stateResults = form.querySelector("[data-state-results]");
  const stateEnhancement = form.querySelector("[data-state-enhancement]");
  const stateFallback = form.querySelector("[data-state-fallback]");
  const countyInput = form.querySelector("[data-county-input]");
  const countyResults = form.querySelector("[data-county-results]");
  const countyEnhancement = form.querySelector("[data-county-enhancement]");
  const countyFallback = form.querySelector("[data-county-fallback]");
  const stateUrl = form.dataset.stateUrl;
  const countyUrl = form.dataset.countyUrl;

  const close = (input, results) => {
    results.hidden = true;
    input.setAttribute("aria-expanded", "false");
    input.removeAttribute("aria-activedescendant");
  };
  const render = (input, results, items, select, label) => {
    results.replaceChildren(...items.map((item, index) => {
      const option = document.createElement("li");
      option.id = `${results.id}-option-${index}`;
      option.setAttribute("role", "option");
      option.setAttribute("aria-selected", "false");
      option.textContent = label(item);
      option.addEventListener("mousedown", (event) => {
        event.preventDefault();
        select(item);
      });
      return option;
    }));
    results.hidden = !items.length;
    input.setAttribute("aria-expanded", String(items.length > 0));
  };
  const searchable = (input, results, fetchItems, select, label) => {
    let items = [];
    let active = -1;
    let timer;
    input.addEventListener("input", () => {
      window.clearTimeout(timer);
      timer = window.setTimeout(async () => {
        const query = input.value.trim();
        if (!query) return close(input, results);
        try {
          items = await fetchItems(query);
          active = -1;
          render(input, results, items, select, label);
        } catch {
          close(input, results);
        }
      }, 200);
    });
    input.addEventListener("keydown", (event) => {
      if (event.key === "Escape") return close(input, results);
      if (event.key === "ArrowDown" || event.key === "ArrowUp") {
        event.preventDefault();
        if (!items.length) return;
        active = (active + (event.key === "ArrowDown" ? 1 : -1) + items.length) % items.length;
        const options = [...results.querySelectorAll('[role="option"]')];
        options.forEach((option, index) => option.setAttribute("aria-selected", String(index === active)));
        input.setAttribute("aria-activedescendant", options[active].id);
      }
      if (event.key === "Enter" && items.length) {
        event.preventDefault();
        select(items[Math.max(active, 0)]);
      }
    });
    input.addEventListener("blur", () => window.setTimeout(() => close(input, results), 100));
  };
  if (state && county && stateInput && stateResults && countyInput && countyResults && stateUrl && countyUrl) {
    const selectState = async (item) => {
      const changed = state.value && state.value !== String(item.id);
      if (changed && county.value && !window.confirm("Changing state clears the selected county. Continue?")) return;
      state.value = String(item.id);
      stateInput.value = `${item.name} (${item.code})`;
      close(stateInput, stateResults);
      county.value = "";
      countyInput.value = "";
      countyInput.disabled = false;
      countyInput.placeholder = "Type a county name";
      state.dispatchEvent(new Event("change", { bubbles: true }));
    };
    const selectCounty = (item) => {
      county.value = String(item.id);
      countyInput.value = item.name;
      close(countyInput, countyResults);
      county.dispatchEvent(new Event("change", { bubbles: true }));
    };
    const selectedState = state.selectedOptions[0];
    if (selectedState?.value) {
      stateInput.value = selectedState.textContent;
      countyInput.disabled = false;
      countyInput.placeholder = "Type a county name";
    }
    searchable(stateInput, stateResults, async (query) => {
      const response = await fetch(`${stateUrl}?q=${encodeURIComponent(query)}`, { headers: { Accept: "application/json" } });
      if (!response.ok) throw new Error("State search failed");
      return (await response.json()).states;
    }, selectState, (item) => `${item.name} (${item.code})`);
    searchable(countyInput, countyResults, async (query) => {
      if (!state.value) return [];
      const response = await fetch(`${countyUrl}?state=${encodeURIComponent(state.value)}&q=${encodeURIComponent(query)}`, { headers: { Accept: "application/json" } });
      if (!response.ok) throw new Error("County search failed");
      return (await response.json()).counties;
    }, selectCounty, (item) => item.name);
    stateEnhancement.hidden = false;
    stateFallback.hidden = true;
    countyEnhancement.hidden = false;
    countyFallback.hidden = true;
  }

  const revealNext = (selector, buttonSelector) => {
    const button = form.querySelector(buttonSelector);
    if (!button) return;
    button.addEventListener("click", () => {
      const next = form.querySelector(`${selector}[hidden]`);
      if (!next) {
        button.hidden = true;
        return;
      }
      next.hidden = false;
      const input = next.querySelector("input");
      if (input) input.focus();
      if (!form.querySelector(`${selector}[hidden]`)) button.hidden = true;
    });
  };
  revealNext("[data-seller-tag-extra]", "[data-add-seller-tag]");
  revealNext("[data-custom-field-extra]", "[data-add-custom-field]");
  const errorSummary = form.querySelector("[data-error-summary]");
  if (errorSummary) errorSummary.focus();
})();

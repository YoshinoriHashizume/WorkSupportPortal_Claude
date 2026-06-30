(function () {
  const Core = window.PortalListCore;
  if (!Core) {
    return;
  }

  const DEFAULT_DEBOUNCE_MS = 600;

  function createPrefixColumnFilter(config) {
    const { getValue, normalizeValue, debounceMs = DEFAULT_DEBOUNCE_MS } = config;
    if (typeof getValue !== "function") {
      throw new Error("createPrefixColumnFilter requires getValue(row)");
    }

    return {
      debounceMs,
      normalizeValue,
      matchesRow(row, filterValue) {
        return Core.matchesPrefixFilter(getValue(row), filterValue, normalizeValue);
      },
      bind(input, datalistElement, options, onValueChange) {
        return Core.bindPrefixFilterInput(input, {
          datalistElement,
          options,
          debounceMs,
          normalizeValue,
          onValueChange,
        });
      },
      filterRows(rows, filterValue) {
        const query = String(filterValue || "").trim();
        if (!query) {
          return rows;
        }
        return rows.filter((row) => this.matchesRow(row, filterValue));
      },
    };
  }

  window.PortalListPrefixFilter = {
    DEFAULT_DEBOUNCE_MS,
    createPrefixColumnFilter,
  };
})();

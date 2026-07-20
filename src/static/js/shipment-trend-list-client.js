(function () {
  const Core = window.PortalListCore;
  const PrefixFilter = window.PortalListPrefixFilter;
  const CustFilter = window.PortalListDependentCustFilter;
  if (!Core || !PrefixFilter || !CustFilter) {
    return;
  }

  const itemCdColumnFilter = PrefixFilter.createPrefixColumnFilter({
    getValue: (row) => row.item_cd,
  });

  function defaultDirectionForColumn(column) {
    if (column === "change_rate_pct" || column === "change_qty") {
      return "asc";
    }
    return "asc";
  }

  function readStateFromUrl(defaults, allRows) {
    const params = new URLSearchParams(window.location.search);
    const allCustOptions = defaults.filterOptions.custOptions || [];
    const custChrgCustIndex = CustFilter.buildCustChrgCustIndex(allRows);
    const custChrgPsnCdRaw = params.get("cust_chrg_psn_cd") || "";
    const validChrg = new Set((defaults.filterOptions.custChrgPsnOptions || []).map((option) => option.value));
    const custChrgPsnCd = custChrgPsnCdRaw && validChrg.has(custChrgPsnCdRaw) ? custChrgPsnCdRaw : "";
    const visibleCustOptions = CustFilter.custOptionsForChrg(allCustOptions, custChrgCustIndex, custChrgPsnCd);
    const validCust = new Set(visibleCustOptions.map((option) => option.value));
    const custCodeRaw = params.get("cust_code") || "";
    return {
      custCode: custCodeRaw && validCust.has(custCodeRaw) ? custCodeRaw : "",
      custChrgPsnCd,
      itemCd: params.get("item_cd") || "",
      ...Core.readBaseStateFromUrl(defaults, defaultDirectionForColumn),
    };
  }

  function numericCodeSortKey(code) {
    const stripped = String(code || "").trim();
    if (/^\d+$/.test(stripped)) {
      return [0, Number(stripped)];
    }
    return [1, stripped.toLowerCase()];
  }

  function sortValue(row, column) {
    if (column === "change_rate_pct") {
      const value = row.change_rate_pct;
      if (value === "" || value === null || value === undefined) {
        return [1, 0];
      }
      return [0, Number(value)];
    }
    if (column === "change_qty") {
      return [0, Number(row.change_qty || 0)];
    }
    if (column === "first_fiscal_year") {
      const value = row.first_fiscal_year;
      if (value === "" || value === null || value === undefined) {
        return [1, 0];
      }
      return [0, Number(value)];
    }
    if (
      column === "first_fy_total" ||
      column === "prev_fy_total" ||
      column === "current_fy_with_forecast_total"
    ) {
      return [0, Number(row[column] || 0)];
    }
    if (column === "cust_code" || column === "cust_chrg_psn_cd") {
      const parts = numericCodeSortKey(row[column]);
      return parts;
    }
    return String(row[column] || "").trim().toLowerCase();
  }

  function applyListFilters(rows, state) {
    return rows.filter((row) => {
      if (state.custCode && String(row.cust_code || "").trim() !== state.custCode) {
        return false;
      }
      if (state.custChrgPsnCd && String(row.cust_chrg_psn_cd || "").trim() !== state.custChrgPsnCd) {
        return false;
      }
      if (!itemCdColumnFilter.matchesRow(row, state.itemCd)) {
        return false;
      }
      return true;
    });
  }

  function initListClient() {
    const dataElement = document.getElementById("st-list-data");
    const pageRoot = document.querySelector(".shipment-trend-page");
    if (!dataElement || !pageRoot) {
      return null;
    }
    let defaults;
    try {
      defaults = JSON.parse(dataElement.textContent || "{}");
    } catch (_error) {
      return null;
    }
    const allRows = defaults.rows || [];
    const allCustOptions = defaults.filterOptions?.custOptions || [];
    const custChrgCustIndex = CustFilter.buildCustChrgCustIndex(allRows);
    let state = readStateFromUrl(defaults, allRows);
    const sortableColumns = defaults.sortableColumns || [];
    const filterPanel = pageRoot.querySelector(".st-filter-panel");
    const tableBody = pageRoot.querySelector("#st-table-body");
    const tableHead = pageRoot.querySelector(".st-table thead tr");
    const countsEl = pageRoot.querySelector(".st-table-counts-left");
    const custChrgSelect = filterPanel?.querySelector('select[name="cust_chrg_psn_cd"]');
    const custCodeSelect = filterPanel?.querySelector('select[name="cust_code"]');
    const itemCdInput = filterPanel?.querySelector(".st-filter-item-cd");
    const itemCdDatalist = document.getElementById("st-item-cd-options");
    const exportLink = pageRoot.querySelector(".st-export-csv-link");
    const exportCsvPath = exportLink?.getAttribute("href")?.split("?")[0] || "/app/sales/shipment-trend/export.csv";
    const itemCdOptions = Array.isArray(defaults.itemCdOptions) ? defaults.itemCdOptions : [];
    const paginationElements = {
      footer: pageRoot.querySelector(".st-table-footer"),
      pageSizeSelect: pageRoot.querySelector("#st-page-size"),
      prevButton: pageRoot.querySelector(".st-pagination-prev"),
      nextButton: pageRoot.querySelector(".st-pagination-next"),
      rangeElement: pageRoot.querySelector(".st-table-range"),
    };
    const itemCdAutocomplete = itemCdColumnFilter.bind(
      itemCdInput,
      itemCdDatalist,
      itemCdOptions,
      (value) => setState({ itemCd: value, page: 1 }),
    );

    function updateUrl() {
      const params = new URLSearchParams();
      if (state.custCode) {
        params.set("cust_code", state.custCode);
      }
      if (state.custChrgPsnCd) {
        params.set("cust_chrg_psn_cd", state.custChrgPsnCd);
      }
      if (state.itemCd.trim()) {
        params.set("item_cd", state.itemCd.trim());
      }
      Core.appendSortQueryParams(params, state.sortSpecs, state.page, state.pageSize);
      const query = params.toString();
      Core.replaceUrl(window.location.pathname, query);
      if (exportLink) {
        exportLink.href = query ? `${exportCsvPath}?${query}` : exportCsvPath;
      }
    }

    function renderTableBody(pageRows) {
      if (!pageRows.length) {
        tableBody.innerHTML = `<tr><td colspan="${sortableColumns.length}" class="st-table-empty">表示する行がありません。</td></tr>`;
        return;
      }
      tableBody.innerHTML = pageRows
        .map((row) => {
          const display = row.display && typeof row.display === "object" ? row.display : {};
          const cells = sortableColumns
            .map((column) => `<td>${Core.escapeHtml(display[column.key] ?? row[column.key] ?? "")}</td>`)
            .join("");
          return `<tr class="st-data-row ${Core.escapeHtml(row.alertRowClass || "st-row-neutral")}"
            data-cust-code="${Core.escapeHtml(row.cust_code || "")}"
            data-cust-name="${Core.escapeHtml(row.cust_name || "")}"
            data-item-cd="${Core.escapeHtml(row.item_cd || "")}">${cells}</tr>`;
        })
        .join("");
    }

    function render() {
      const filtered = applyListFilters(allRows, state);
      if (countsEl) {
        countsEl.textContent = `全 ${allRows.length} 件 / 表示対象 ${filtered.length} 件`;
      }
      const sorted = Core.sortRows(filtered, state.sortSpecs, sortValue, [
        { column: "cust_code", direction: "asc" },
        { column: "item_cd", direction: "asc" },
      ]);
      const pagination = Core.paginateRows(sorted, state.page, state.pageSize);
      if (state.page !== pagination.page) {
        state.page = pagination.page;
      }
      Core.renderTableHeaders(tableHead, {
        sortableColumns,
        sortSpecs: state.sortSpecs,
        sortColumnDataAttr: "data-st-sort-column",
        sortPriorityClass: "st-sort-priority",
        headerMode: "link",
        onColumnClick: (column) => {
          state.sortSpecs = [
            { column, direction: Core.toggleSortDirection(state.sortSpecs, column, defaultDirectionForColumn) },
          ];
          state.page = 1;
          render();
        },
      });
      renderTableBody(pagination.rows);
      Core.renderPagination(paginationElements, pagination);
      updateUrl();
      itemCdAutocomplete.sync(state.itemCd);
    }

    function setState(patch) {
      state = { ...state, ...patch };
      render();
    }

    custChrgSelect?.addEventListener("change", () => {
      const custCode = CustFilter.renderCustCodeSelect(
        custCodeSelect,
        allCustOptions,
        custChrgCustIndex,
        custChrgSelect.value,
        "",
      );
      setState({
        custChrgPsnCd: custChrgSelect.value,
        custCode,
        itemCd: "",
        page: 1,
      });
    });
    custCodeSelect?.addEventListener("change", () => {
      setState({ custCode: custCodeSelect.value, itemCd: "", page: 1 });
    });
    Core.bindPaginationControls(
      paginationElements,
      () => state.page,
      (patch) => setState({ ...patch, pageSize: patch.pageSize || state.pageSize }),
    );

    if (custChrgSelect) {
      custChrgSelect.value = state.custChrgPsnCd;
    }
    CustFilter.renderCustCodeSelect(
      custCodeSelect,
      allCustOptions,
      custChrgCustIndex,
      state.custChrgPsnCd,
      state.custCode,
    );
    if (itemCdInput) {
      itemCdInput.value = state.itemCd;
    }
    render();

    return {
      applySortSpecs(sortSpecs) {
        state.sortSpecs = sortSpecs.map((spec) => ({ ...spec }));
        state.page = 1;
        render();
      },
      getSortSpecs() {
        return state.sortSpecs.map((spec) => ({ ...spec }));
      },
      getSortableColumns() {
        return sortableColumns.map((column) => ({ ...column }));
      },
      updateThresholds(decreaseThresholdPct, increaseThresholdPct) {
        defaults.decreaseThresholdPct = decreaseThresholdPct;
        defaults.increaseThresholdPct = increaseThresholdPct;
        allRows.forEach((row) => {
          const rate = row.change_rate_pct === "" ? null : Number(row.change_rate_pct);
          row.alertRowClass = classifyRow(rate, decreaseThresholdPct, increaseThresholdPct);
        });
        render();
      },
    };
  }

  function classifyRow(rate, decreaseThreshold, increaseThreshold) {
    if (rate === null || Number.isNaN(rate)) {
      return "st-row-neutral";
    }
    if (rate < 0) {
      return rate <= -decreaseThreshold ? "st-row-decrease-strong" : "st-row-decrease-mild";
    }
    if (rate > 0) {
      return rate >= increaseThreshold ? "st-row-increase-strong" : "st-row-neutral";
    }
    return "st-row-neutral";
  }

  window.ShipmentTrendListClient = { init: initListClient, classifyRow };
})();

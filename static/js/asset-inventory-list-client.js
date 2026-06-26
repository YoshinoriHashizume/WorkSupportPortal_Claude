(function () {
  const Core = window.PortalListCore;
  if (!Core) {
    return;
  }

  const STATUS_SORT_ORDER = { matched: 0, asset_only: 1, inventory_only: 2 };
  const TONE_SORT_ORDER = { MATCH_CLEAN: 0, MATCH_FACTORY: 1, MATCH_DIFF: 2, NONE: 3 };
  const ASSET_NUMBER_DEBOUNCE_MS = 600;

  function normalizeAssetNumber(value) {
    let text = String(value || "").trim();
    if (text && (text[0] === "L" || text[0] === "l")) {
      text = text.slice(1).trim();
    }
    return text;
  }

  function parseAcquisitionDate(value) {
    const text = String(value || "").trim();
    if (!text) {
      return null;
    }
    const datePart = text.split(/[T ]/)[0].replace(/\//g, "-");
    const match = datePart.match(/^(\d{4})-(\d{1,2})-(\d{1,2})$/);
    if (!match) {
      return null;
    }
    const year = Number(match[1]);
    const month = Number(match[2]);
    const day = Number(match[3]);
    const parsed = new Date(year, month - 1, day);
    if (
      parsed.getFullYear() !== year ||
      parsed.getMonth() !== month - 1 ||
      parsed.getDate() !== day
    ) {
      return null;
    }
    return parsed;
  }

  function defaultDirectionForColumn(column) {
    return column === "inventory_datetime" ? "desc" : "asc";
  }

  function readStateFromUrl(defaults) {
    const params = new URLSearchParams(window.location.search);
    return {
      status: params.get("status") || "all",
      plate: params.get("plate") || "all",
      site: params.get("site") || "all",
      assetNumber: params.get("assetNumber") || "",
      ...Core.readBaseStateFromUrl(defaults, defaultDirectionForColumn),
    };
  }

  function matchesAssetNumberFilter(assetNumber, filterValue) {
    const query = String(filterValue || "").trim();
    if (!query) {
      return true;
    }
    const rowDisplay = String(assetNumber || "").trim();
    if (!rowDisplay) {
      return false;
    }
    const queryNorm = normalizeAssetNumber(query);
    const rowNorm = normalizeAssetNumber(rowDisplay);
    if (!queryNorm) {
      return true;
    }
    return rowNorm.startsWith(queryNorm);
  }

  function applyFilters(rows, state) {
    return rows.filter((row) => {
      if (state.status !== "all" && row.match_status !== state.status) {
        return false;
      }
      if (state.plate !== "all" && row.plate_created_code !== state.plate) {
        return false;
      }
      if (state.site !== "all" && String(row.site_name || "").trim() !== state.site) {
        return false;
      }
      if (!matchesAssetNumberFilter(row.asset_number, state.assetNumber)) {
        return false;
      }
      return true;
    });
  }

  function countRows(rows) {
    return rows.reduce(
      (counts, row) => {
        if (row.match_status === "matched") {
          counts.matched += 1;
        } else if (row.match_status === "asset_only") {
          counts.asset_only += 1;
        } else if (row.match_status === "inventory_only") {
          counts.inventory_only += 1;
        }
        return counts;
      },
      { matched: 0, asset_only: 0, inventory_only: 0 },
    );
  }

  function sortValue(row, column) {
    if (column === "status_label") {
      return [STATUS_SORT_ORDER[row.match_status] ?? 99, String(row.status_label || "").toLowerCase()];
    }
    if (column === "tone_label") {
      return [TONE_SORT_ORDER[row.row_tone] ?? 99, String(row.tone_label || "").toLowerCase()];
    }
    const value = row[column] ?? "";
    return [value === "" || value === null, String(value).toLowerCase()];
  }

  function sortRows(rows, sortSpecs) {
    const sorted = rows.slice();
    for (let specIndex = sortSpecs.length - 1; specIndex >= 0; specIndex -= 1) {
      const spec = sortSpecs[specIndex];
      const reverse = spec.direction === "desc";
      if (spec.column === "asset_acquisition_date") {
        const dated = sorted.filter((row) => parseAcquisitionDate(row.asset_acquisition_date));
        const empty = sorted.filter((row) => !parseAcquisitionDate(row.asset_acquisition_date));
        dated.sort((left, right) => {
          const leftDate = parseAcquisitionDate(left.asset_acquisition_date);
          const rightDate = parseAcquisitionDate(right.asset_acquisition_date);
          return leftDate - rightDate;
        });
        if (reverse) {
          dated.reverse();
        }
        sorted.splice(0, sorted.length, ...dated, ...empty);
        continue;
      }
      sorted.sort((left, right) => {
        const comparison = Core.compareSortValues(sortValue(left, spec.column), sortValue(right, spec.column));
        return reverse ? -comparison : comparison;
      });
    }
    return sorted;
  }

  function buildQueryString(state, managementId) {
    const params = new URLSearchParams();
    params.set("managementId", managementId);
    params.set("status", state.status);
    params.set("plate", state.plate);
    if (state.site && state.site !== "all") {
      params.set("site", state.site);
    }
    if (state.assetNumber.trim()) {
      params.set("assetNumber", state.assetNumber.trim());
    }
    Core.appendSortQueryParams(params, state.sortSpecs, state.page, state.pageSize);
    return params.toString();
  }

  function initListClient() {
    const dataElement = document.getElementById("aiv-list-data");
    const pageRoot = document.querySelector(".asset-inventory-page");
    if (!dataElement || !pageRoot) {
      return null;
    }

    let payload;
    try {
      payload = JSON.parse(dataElement.textContent || "{}");
    } catch (_error) {
      return null;
    }

    const defaults = {
      defaultSortSpecs: payload.defaultSortSpecs || [],
      defaultPageSize: payload.defaultPageSize || 50,
      pageSizeOptions: payload.pageSizeOptions || [20, 50, 100, 200],
    };
    const allRows = Array.isArray(payload.rows) ? payload.rows : [];
    const rowDetails = payload.rowDetails && typeof payload.rowDetails === "object" ? payload.rowDetails : {};
    const managementId = String(payload.managementId || "");
    const exportCsvPath = String(payload.exportCsvPath || "");
    const sortableColumns = Array.isArray(payload.sortableColumns) ? payload.sortableColumns : [];

    const filterPanel = pageRoot.querySelector(".aiv-filter-panel");
    const statusSelect = filterPanel?.querySelector('select[name="status"]');
    const plateSelect = filterPanel?.querySelector('select[name="plate"]');
    const siteSelect = filterPanel?.querySelector('select[name="site"]');
    const assetNumberInput = filterPanel?.querySelector(".aiv-filter-asset-number");
    const datalist = document.getElementById("aiv-asset-number-options");
    const tableBody = pageRoot.querySelector(".aiv-table tbody");
    const tableHead = pageRoot.querySelector(".aiv-table thead");
    const countsElement = pageRoot.querySelector(".aiv-table-counts");
    const paginationElements = {
      footer: pageRoot.querySelector(".aiv-table-footer"),
      pageSizeSelect: pageRoot.querySelector(".aiv-page-size-select"),
      rangeElement: pageRoot.querySelector(".aiv-table-range"),
      prevButton: pageRoot.querySelector(".aiv-pagination-prev"),
      nextButton: pageRoot.querySelector(".aiv-pagination-next"),
    };
    const exportLink = pageRoot.querySelector(".aiv-export-csv-link");
    const assetNumberOptions = Array.isArray(payload.assetNumberOptions) ? payload.assetNumberOptions : [];

    if (!filterPanel || !tableBody || !countsElement) {
      return null;
    }

    let state = readStateFromUrl(defaults);
    let assetNumberDebounceTimer = null;
    let isComposing = false;

    function syncControlsFromState() {
      if (statusSelect) {
        statusSelect.value = state.status;
      }
      if (plateSelect) {
        plateSelect.value = state.plate;
      }
      if (siteSelect) {
        siteSelect.value = state.site;
      }
      if (assetNumberInput) {
        assetNumberInput.value = state.assetNumber;
      }
      if (paginationElements.pageSizeSelect) {
        paginationElements.pageSizeSelect.value = String(state.pageSize);
      }
    }

    function filterAssetNumberOptions(query) {
      const queryNorm = normalizeAssetNumber(query);
      if (!queryNorm) {
        return assetNumberOptions;
      }
      return assetNumberOptions.filter((option) => normalizeAssetNumber(option).startsWith(queryNorm));
    }

    function updateDatalistOptions(query) {
      if (!datalist) {
        return;
      }
      const matches = filterAssetNumberOptions(query);
      datalist.replaceChildren();
      matches.forEach((value) => {
        const option = document.createElement("option");
        option.value = value;
        datalist.appendChild(option);
      });
    }

    function updateUrl() {
      const query = buildQueryString(state, managementId);
      Core.replaceUrl(window.location.pathname, query);
      if (exportLink) {
        exportLink.href = `${exportCsvPath}?${query}`;
      }
    }

    function renderTableBody(pageRows) {
      if (!pageRows.length) {
        tableBody.innerHTML = '<tr><td colspan="15">表示するデータがありません。</td></tr>';
        return;
      }
      tableBody.innerHTML = pageRows
        .map((row) => {
          const rowKey = `${row.asset_number}|${row.branch_number}`;
          const cssClass = [row.css_class, "aiv-table-row--clickable"].filter(Boolean).join(" ");
          return `<tr class="${Core.escapeHtml(cssClass)}" tabindex="0" role="button" data-aiv-row-key="${Core.escapeHtml(rowKey)}" aria-label="詳細を表示">
            <td>${Core.escapeHtml(row.status_label)}</td>
            <td>${Core.escapeHtml(row.tone_label)}</td>
            <td>${Core.escapeHtml(row.asset_number)}</td>
            <td>${Core.escapeHtml(row.branch_number)}</td>
            <td>${Core.escapeHtml(row.site_name)}</td>
            <td>${Core.escapeHtml(row.manufacturer)}</td>
            <td>${Core.escapeHtml(row.model_name)}</td>
            <td>${Core.escapeHtml(row.serial_number)}</td>
            <td>${Core.escapeHtml(row.asset_acquisition_date)}</td>
            <td>${Core.escapeHtml(row.old_asset_number)}</td>
            <td>${Core.escapeHtml(row.usage_category)}</td>
            <td>${Core.escapeHtml(row.summary)}</td>
            <td>${Core.escapeHtml(row.plate_created)}</td>
            <td>${Core.escapeHtml(row.inventory_operator)}</td>
            <td>${Core.escapeHtml(row.inventory_datetime)}</td>
          </tr>`;
        })
        .join("");
    }

    function render() {
      const filtered = applyFilters(allRows, state);
      const filteredCounts = countRows(filtered);
      const sorted = sortRows(filtered, state.sortSpecs);
      const pagination = Core.paginateRows(sorted, state.page, state.pageSize);
      if (state.page !== pagination.page) {
        state.page = pagination.page;
      }

      countsElement.textContent = `棚卸済み ${filteredCounts.matched} 件 / 未棚卸 ${filteredCounts.asset_only} 件 / 台帳外 ${filteredCounts.inventory_only} 件`;
      Core.renderTableHeaders(tableHead, {
        sortableColumns,
        sortSpecs: state.sortSpecs,
        sortColumnDataAttr: "data-aiv-sort-column",
        sortPriorityClass: "aiv-sort-priority",
        headerMode: "button",
        headerButtonClass: "aiv-sort-header",
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
      updateDatalistOptions(state.assetNumber);
    }

    function setState(patch) {
      state = { ...state, ...patch };
      render();
    }

    function scheduleAssetNumberRender() {
      if (assetNumberDebounceTimer !== null) {
        window.clearTimeout(assetNumberDebounceTimer);
      }
      assetNumberDebounceTimer = window.setTimeout(() => {
        assetNumberDebounceTimer = null;
        if (!isComposing) {
          setState({ assetNumber: assetNumberInput?.value || "", page: 1 });
        }
      }, ASSET_NUMBER_DEBOUNCE_MS);
    }

    statusSelect?.addEventListener("change", () => {
      setState({ status: statusSelect.value, page: 1 });
    });
    plateSelect?.addEventListener("change", () => {
      setState({ plate: plateSelect.value, page: 1 });
    });
    siteSelect?.addEventListener("change", () => {
      setState({ site: siteSelect.value, page: 1 });
    });
    Core.bindPaginationControls(
      paginationElements,
      () => state.page,
      (patch) => setState({ ...patch, pageSize: patch.pageSize || state.pageSize }),
    );

    assetNumberInput?.addEventListener("compositionstart", () => {
      isComposing = true;
    });
    assetNumberInput?.addEventListener("compositionend", () => {
      isComposing = false;
      scheduleAssetNumberRender();
    });
    assetNumberInput?.addEventListener("input", () => {
      updateDatalistOptions(assetNumberInput.value);
      if (isComposing) {
        return;
      }
      scheduleAssetNumberRender();
    });
    assetNumberInput?.addEventListener("keydown", (event) => {
      if (event.key !== "Enter") {
        return;
      }
      event.preventDefault();
      if (assetNumberDebounceTimer !== null) {
        window.clearTimeout(assetNumberDebounceTimer);
        assetNumberDebounceTimer = null;
      }
      setState({ assetNumber: assetNumberInput.value, page: 1 });
    });

    syncControlsFromState();
    render();

    return {
      getRowDetails() {
        return rowDetails;
      },
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
    };
  }

  window.AivListClient = { init: initListClient };
})();

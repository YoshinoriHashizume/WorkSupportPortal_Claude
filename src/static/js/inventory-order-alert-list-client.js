(function () {
  const Core = window.PortalListCore;
  const CustFilter = window.PortalListDependentCustFilter;
  if (!Core || !CustFilter) {
    return;
  }

  const createPrefixColumnFilter =
    window.PortalListPrefixFilter?.createPrefixColumnFilter ||
    function createPrefixColumnFilterFallback(config) {
      const { getValue, normalizeValue } = config;
      return {
        matchesRow(row, filterValue) {
          return Core.matchesPrefixFilter(getValue(row), filterValue, normalizeValue);
        },
        bind(input, datalistElement, options, onValueChange) {
          return Core.bindPrefixFilterInput(input, {
            datalistElement,
            options,
            normalizeValue,
            onValueChange,
          });
        },
      };
    };

  const itemCdColumnFilter = createPrefixColumnFilter({
    getValue: (row) => row.item_cd,
  });
  const level1ItemCdColumnFilter = createPrefixColumnFilter({
    getValue: (row) => row.level1_item_cd,
  });

  function parseRowKey(value) {
    const text = String(value || "").trim();
    const separatorIndex = text.indexOf("|");
    if (separatorIndex <= 0 || separatorIndex >= text.length - 1) {
      return { custCode: "", itemCd: "" };
    }
    return {
      custCode: text.slice(0, separatorIndex).trim(),
      itemCd: text.slice(separatorIndex + 1).trim(),
    };
  }

  function readRowKeysFromDomElement(element) {
    if (!element) {
      return { custCode: "", itemCd: "" };
    }
    const fromRowKey = parseRowKey(element.getAttribute("data-row-key") || element.dataset?.rowKey || "");
    if (fromRowKey.custCode && fromRowKey.itemCd) {
      return fromRowKey;
    }
    const custCode = String(element.getAttribute("data-cust-code") || element.dataset?.custCode || "").trim();
    const itemCd = String(element.getAttribute("data-item-cd") || element.dataset?.itemCd || "").trim();
    if (custCode && itemCd) {
      return { custCode, itemCd };
    }
    return { custCode: "", itemCd: "" };
  }

  const ALERT_NONE = "アラート無し";
  const ALERT_RANK = {
    重点: 0,
    "警告（出荷あり）": 1,
    "警告（出荷なし）": 2,
    [ALERT_NONE]: 3,
  };
  const CONFIRMATION_STATUS_RANK = {
    unconfirmed: 0,
    in_progress: 1,
    confirmed: 2,
  };

  function normalizeAlertLevel(level) {
    const text = String(level || "").trim();
    if (text === "" || text === "なし" || text === "アラートなし" || text === "問題なし") {
      return ALERT_NONE;
    }
    if (text === "警告（出荷）") {
      return "警告（出荷あり）";
    }
    if (text === "警告（入荷）") {
      return "警告（出荷なし）";
    }
    return text;
  }

  function alertSortRank(level) {
    return ALERT_RANK[normalizeAlertLevel(level)] ?? 99;
  }

  function confirmationStatusSortRank(row) {
    const key = String(row.confirmationStatusKey || "");
    if (Object.prototype.hasOwnProperty.call(CONFIRMATION_STATUS_RANK, key)) {
      return CONFIRMATION_STATUS_RANK[key];
    }
    const label = String(row.confirmation_status || "未確認");
    if (label === "確認中") {
      return CONFIRMATION_STATUS_RANK.in_progress;
    }
    if (label === "確認済み") {
      return CONFIRMATION_STATUS_RANK.confirmed;
    }
    return CONFIRMATION_STATUS_RANK.unconfirmed;
  }

  function defaultDirectionForColumn(column) {
    if (column === "alert_level") {
      return "asc";
    }
    if (column === "post_shipment_count" || column === "post_shipment_total_qty" || column === "stock_qty") {
      return "desc";
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
      level1ItemCd: params.get("level1_item_cd") || "",
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

  function parseOptionalYmd(value) {
    const text = String(value || "").trim();
    if (!text) {
      return null;
    }
    const normalized = text.replace(/-/g, "/");
    const match = normalized.match(/^(\d{4})\/(\d{1,2})\/(\d{1,2})$/);
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

  function dateSortKey(value) {
    const text = String(value || "").trim();
    if (!text) {
      return [0, ""];
    }
    const parsed = parseOptionalYmd(text);
    if (!parsed) {
      return [1, text];
    }
    const iso = [
      parsed.getFullYear(),
      String(parsed.getMonth() + 1).padStart(2, "0"),
      String(parsed.getDate()).padStart(2, "0"),
    ].join("-");
    return [1, iso];
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
      if (!level1ItemCdColumnFilter.matchesRow(row, state.level1ItemCd)) {
        return false;
      }
      return true;
    });
  }

  function countRows(rows) {
    return rows.reduce(
      (counts, row) => {
        const level = normalizeAlertLevel(row.alert_level);
        if (level === "重点") {
          counts.critical += 1;
        } else if (level === "警告（出荷あり）") {
          counts.warningShip += 1;
        } else if (level === "警告（出荷なし）") {
          counts.warningIncoming += 1;
        } else {
          counts.alertNone += 1;
        }
        const status = String(row.confirmation_status || "未確認");
        if (status === "確認済み") {
          counts.confirmed += 1;
        } else if (status === "確認中") {
          counts.inProgress += 1;
        } else {
          counts.unconfirmed += 1;
        }
        return counts;
      },
      {
        critical: 0,
        warningShip: 0,
        warningIncoming: 0,
        alertNone: 0,
        confirmed: 0,
        inProgress: 0,
        unconfirmed: 0,
      },
    );
  }

  function sortValue(row, column) {
    const value = row[column] ?? "";
    if (column === "alert_level") {
      return alertSortRank(value);
    }
    if (column === "post_shipment_count" || column === "post_shipment_total_qty") {
      const number = Number.parseInt(String(value || "0"), 10);
      return Number.isFinite(number) ? number : 0;
    }
    if (column === "stock_qty") {
      const text = String(value || "").replace(/,/g, "").trim();
      if (!text) {
        return -1;
      }
      const number = Number(text);
      return Number.isFinite(number) ? number : -1;
    }
    if (column === "last_incoming_date" || column === "last_ship_date") {
      return dateSortKey(value);
    }
    if (column === "cust_chrg_psn_cd") {
      return numericCodeSortKey(String(value || ""));
    }
    if (column === "confirmation_status") {
      return confirmationStatusSortRank(row);
    }
    return String(value || "").toLowerCase();
  }

  function initListClient() {
    const dataElement = document.getElementById("ioa-list-data");
    const pageRoot = document.querySelector(".inventory-order-alert-page");
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
      filterOptions: payload.filterOptions || { custOptions: [], custChrgPsnOptions: [] },
    };
    const allRows = Array.isArray(payload.rows) ? payload.rows : [];
    const allCustOptions = defaults.filterOptions?.custOptions || [];
    const custChrgCustIndex = CustFilter.buildCustChrgCustIndex(allRows);
    const sortableColumns = Array.isArray(payload.sortableColumns) ? payload.sortableColumns : [];
    const confirmationStatusChoices = Array.isArray(payload.confirmationStatusChoices)
      ? payload.confirmationStatusChoices
      : [];

    const filterPanel = pageRoot.querySelector(".ioa-filter-panel");
    const custChrgSelect = filterPanel?.querySelector('select[name="cust_chrg_psn_cd"]');
    const custCodeSelect = filterPanel?.querySelector('select[name="cust_code"]');
    const itemCdInput = filterPanel?.querySelector(".ioa-filter-item-cd");
    const level1ItemCdInput = filterPanel?.querySelector(".ioa-filter-level1-item-cd");
    const itemCdDatalist = document.getElementById("ioa-item-cd-options");
    const level1ItemCdDatalist = document.getElementById("ioa-level1-item-cd-options");
    const itemCdOptions = Array.isArray(payload.itemCdOptions) ? payload.itemCdOptions : [];
    const level1ItemCdOptions = Array.isArray(payload.level1ItemCdOptions) ? payload.level1ItemCdOptions : [];
    const tableBody = pageRoot.querySelector(".ioa-table tbody");
    const tableHead = pageRoot.querySelector(".ioa-table thead");
    const countsLeft = pageRoot.querySelector(".ioa-table-counts-left");
    const countsRight = pageRoot.querySelector(".ioa-table-counts-right");
    const paginationElements = {
      footer: pageRoot.querySelector(".ioa-table-footer"),
      pageSizeSelect: pageRoot.querySelector(".ioa-page-size-select"),
      rangeElement: pageRoot.querySelector(".ioa-table-range"),
      prevButton: pageRoot.querySelector(".ioa-pagination-prev"),
      nextButton: pageRoot.querySelector(".ioa-pagination-next"),
    };

    if (!filterPanel || !tableBody || !countsLeft || !countsRight) {
      return null;
    }

    let state = readStateFromUrl(defaults, allRows);
    let visiblePageRows = [];
    const rowIdentityByTr = new WeakMap();

    function formatRowIdentity(row) {
      const fromKey = parseRowKey(row?.rowKey);
      if (fromKey.custCode && fromKey.itemCd) {
        return fromKey;
      }
      return {
        custCode: String(row?.cust_code ?? row?.custCode ?? "").trim(),
        itemCd: String(row?.item_cd ?? row?.itemCd ?? "").trim(),
      };
    }

    function buildRowKeyAttribute(identity) {
      if (!identity.custCode || !identity.itemCd) {
        return "";
      }
      return `${identity.custCode}|${identity.itemCd}`;
    }

    function readIdentityFromElement(element) {
      return readRowKeysFromDomElement(element);
    }

    function readIdentityFromTableCells(rowElement) {
      const cells = rowElement?.querySelectorAll("td");
      if (!cells?.length) {
        return { custCode: "", itemCd: "" };
      }
      let custCode = "";
      let itemCd = "";
      sortableColumns.forEach((column, index) => {
        if (column.key === "cust_code") {
          custCode = String(cells[index]?.textContent || "").trim();
        } else if (column.key === "item_cd") {
          itemCd = String(cells[index]?.textContent || "").trim();
        }
      });
      return { custCode, itemCd };
    }

    function cacheRenderedRowIdentities(pageRows) {
      const renderedRows = tableBody.querySelectorAll("tr.ioa-data-row");
      renderedRows.forEach((tr, index) => {
        const identity = formatRowIdentity(pageRows[index]);
        if (!identity.custCode || !identity.itemCd) {
          return;
        }
        rowIdentityByTr.set(tr, identity);
        tr.setAttribute("data-row-key", buildRowKeyAttribute(identity));
        tr.setAttribute("data-cust-code", identity.custCode);
        tr.setAttribute("data-item-cd", identity.itemCd);
        const select = tr.querySelector(".ioa-confirmation-status");
        if (select) {
          select.setAttribute("data-row-key", buildRowKeyAttribute(identity));
          select.setAttribute("data-cust-code", identity.custCode);
          select.setAttribute("data-item-cd", identity.itemCd);
        }
      });
    }

    const itemCdAutocomplete = itemCdColumnFilter.bind(
      itemCdInput,
      itemCdDatalist,
      itemCdOptions,
      (value) => setState({ itemCd: value, page: 1 }),
    );
    const level1ItemCdAutocomplete = level1ItemCdColumnFilter.bind(
      level1ItemCdInput,
      level1ItemCdDatalist,
      level1ItemCdOptions,
      (value) => setState({ level1ItemCd: value, page: 1 }),
    );

    function findRow(custCode, itemCd) {
      return allRows.find(
        (row) => String(row.cust_code || "") === custCode && String(row.item_cd || "") === itemCd,
      );
    }

    function syncControlsFromState() {
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
        itemCdInput.value = state.itemCd || "";
      }
      if (level1ItemCdInput) {
        level1ItemCdInput.value = state.level1ItemCd || "";
      }
      if (paginationElements.pageSizeSelect) {
        paginationElements.pageSizeSelect.value = String(state.pageSize);
      }
    }

    function updateUrl() {
      const params = new URLSearchParams();
      if (state.custCode) {
        params.set("cust_code", state.custCode);
      }
      if (state.custChrgPsnCd) {
        params.set("cust_chrg_psn_cd", state.custChrgPsnCd);
      }
      if (state.itemCd && String(state.itemCd).trim()) {
        params.set("item_cd", String(state.itemCd).trim());
      }
      if (state.level1ItemCd && String(state.level1ItemCd).trim()) {
        params.set("level1_item_cd", String(state.level1ItemCd).trim());
      }
      Core.appendSortQueryParams(params, state.sortSpecs, state.page, state.pageSize);
      Core.replaceUrl(window.location.pathname, params.toString());
    }

    function renderConfirmationSelect(selectedValue, identity) {
      const rowKey = buildRowKeyAttribute(identity);
      return `<select class="ioa-confirmation-status" aria-label="確認状態"
        data-row-key="${Core.escapeHtml(rowKey)}"
        data-cust-code="${Core.escapeHtml(identity.custCode)}"
        data-item-cd="${Core.escapeHtml(identity.itemCd)}">${confirmationStatusChoices
        .map(
          (choice) =>
            `<option value="${Core.escapeHtml(choice.value)}"${
              choice.value === selectedValue ? " selected" : ""
            }>${Core.escapeHtml(choice.label)}</option>`,
        )
        .join("")}</select>`;
    }

    function renderTableBody(pageRows) {
      visiblePageRows = pageRows;
      if (!pageRows.length) {
        tableBody.innerHTML = `<tr><td colspan="${sortableColumns.length}" class="ioa-table-empty">表示する行がありません。</td></tr>`;
        return;
      }
      tableBody.innerHTML = pageRows
        .map((row) => {
          const display = row.display && typeof row.display === "object" ? row.display : {};
          const identity = formatRowIdentity(row);
          const rowKey = row.rowKey || buildRowKeyAttribute(identity);
          const cells = sortableColumns
            .map((column) => {
              if (column.key === "confirmation_status") {
                return `<td>${renderConfirmationSelect(
                  row.confirmationStatusKey || "unconfirmed",
                  identity,
                )}</td>`;
              }
              return `<td>${Core.escapeHtml(display[column.key] ?? "")}</td>`;
            })
            .join("");
          return `<tr class="alert-row alert-row--${Core.escapeHtml(row.alertRowClass || "")} ioa-data-row"
            data-row-key="${Core.escapeHtml(String(rowKey || ""))}"
            data-cust-code="${Core.escapeHtml(identity.custCode)}"
            data-cust-name="${Core.escapeHtml(row.cust_name || "")}"
            data-item-cd="${Core.escapeHtml(identity.itemCd)}"
            data-stock-qty="${Core.escapeHtml(row.stock_qty || "")}"
            data-stock-location-detail="${Core.escapeHtml(row.stock_location_detail || "")}"
            data-stock-as-of-label="${Core.escapeHtml(row.stock_as_of_label || "")}"
            data-confirmation-status="${Core.escapeHtml(row.confirmationStatusKey || "unconfirmed")}">${cells}</tr>`;
        })
        .join("");
      cacheRenderedRowIdentities(pageRows);
    }

    function renderCounts(counts) {
      countsLeft.textContent =
        `重点 ${counts.critical} 件 / 警告（出荷あり） ${counts.warningShip} 件 / 警告（出荷なし） ${counts.warningIncoming} 件 / アラート無し ${counts.alertNone} 件`;
      countsRight.textContent =
        `確認済み ${counts.confirmed} 件 / 確認中 ${counts.inProgress} 件 / 未確認 ${counts.unconfirmed} 件`;
    }

    function render() {
      const filtered = applyListFilters(allRows, state);
      const counts = countRows(filtered);
      const sorted = Core.sortRows(filtered, state.sortSpecs, sortValue, [
        { column: "cust_code", direction: "asc" },
        { column: "item_cd", direction: "asc" },
      ]);
      const pagination = Core.paginateRows(sorted, state.page, state.pageSize);
      if (state.page !== pagination.page) {
        state.page = pagination.page;
      }
      renderCounts(counts);
      Core.renderTableHeaders(tableHead, {
        sortableColumns,
        sortSpecs: state.sortSpecs,
        sortColumnDataAttr: "data-ioa-sort-column",
        sortPriorityClass: "ioa-sort-priority",
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
      level1ItemCdAutocomplete.sync(state.level1ItemCd);
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
        level1ItemCd: "",
        page: 1,
      });
    });
    custCodeSelect?.addEventListener("change", () => {
      setState({ custCode: custCodeSelect.value, itemCd: "", level1ItemCd: "", page: 1 });
    });
    Core.bindPaginationControls(
      paginationElements,
      () => state.page,
      (patch) => setState({ ...patch, pageSize: patch.pageSize || state.pageSize }),
    );

    syncControlsFromState();
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
      getListFilterParams() {
        return {
          custCodeFilter: state.custCode,
          custChrgPsnCdFilter: state.custChrgPsnCd,
          itemCdFilter: String(state.itemCd || "").trim(),
          level1ItemCdFilter: String(state.level1ItemCd || "").trim(),
        };
      },
      resolveRowKeysFromElement(rowElement, selectElement) {
        if (!rowElement) {
          return { custCode: "", itemCd: "" };
        }
        const sources = [selectElement, rowElement].filter(Boolean);
        for (const element of sources) {
          const keys = readRowKeysFromDomElement(element);
          if (keys.custCode && keys.itemCd) {
            return keys;
          }
        }
        const cached = rowIdentityByTr.get(rowElement);
        if (cached?.custCode && cached?.itemCd) {
          return cached;
        }
        const fromCells = readIdentityFromTableCells(rowElement);
        if (fromCells.custCode && fromCells.itemCd) {
          return fromCells;
        }
        const dataRows = [...tableBody.querySelectorAll("tr.ioa-data-row")];
        const index = dataRows.indexOf(rowElement);
        if (index >= 0 && index < visiblePageRows.length) {
          return formatRowIdentity(visiblePageRows[index]);
        }
        return fromCells;
      },
      updateRowFromConfirmation(custCode, itemCd, payload) {
        const row = findRow(custCode, itemCd);
        if (!row) {
          return;
        }
        if (payload.confirmationStatusKey) {
          row.confirmationStatusKey = payload.confirmationStatusKey;
          const labelMap = Object.fromEntries(
            confirmationStatusChoices.map((choice) => [choice.value, choice.label]),
          );
          row.confirmation_status = labelMap[payload.confirmationStatusKey] || "未確認";
        }
        if (payload.alertRowClass) {
          row.alertRowClass = payload.alertRowClass;
        }
        render();
      },
    };
  }

  window.IoaListClient = { init: initListClient, parseRowKey, readRowKeysFromDomElement };
})();

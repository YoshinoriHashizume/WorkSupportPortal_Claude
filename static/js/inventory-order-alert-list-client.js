(function () {
  const Core = window.PortalListCore;
  if (!Core) {
    return;
  }

  const ALERT_NONE = "アラート無し";
  const ALERT_RANK = {
    重点: 0,
    "警告（出荷あり）": 1,
    "警告（出荷なし）": 2,
    [ALERT_NONE]: 3,
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

  function defaultDirectionForColumn(column) {
    if (column === "alert_level") {
      return "asc";
    }
    if (column === "post_shipment_count" || column === "post_shipment_total_qty" || column === "stock_qty") {
      return "desc";
    }
    return "asc";
  }

  function readStateFromUrl(defaults) {
    const params = new URLSearchParams(window.location.search);
    const custCode = params.get("cust_code") || "";
    const custChrgPsnCd = params.get("cust_chrg_psn_cd") || "";
    const validCust = new Set((defaults.filterOptions.custOptions || []).map((option) => option.value));
    const validChrg = new Set((defaults.filterOptions.custChrgPsnOptions || []).map((option) => option.value));
    return {
      custCode: custCode && validCust.has(custCode) ? custCode : "",
      custChrgPsnCd: custChrgPsnCd && validChrg.has(custChrgPsnCd) ? custChrgPsnCd : "",
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
    const sortableColumns = Array.isArray(payload.sortableColumns) ? payload.sortableColumns : [];
    const confirmationStatusChoices = Array.isArray(payload.confirmationStatusChoices)
      ? payload.confirmationStatusChoices
      : [];

    const filterPanel = pageRoot.querySelector(".ioa-filter-panel");
    const custChrgSelect = filterPanel?.querySelector('select[name="cust_chrg_psn_cd"]');
    const custCodeSelect = filterPanel?.querySelector('select[name="cust_code"]');
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

    let state = readStateFromUrl(defaults);

    function findRow(custCode, itemCd) {
      return allRows.find(
        (row) => String(row.cust_code || "") === custCode && String(row.item_cd || "") === itemCd,
      );
    }

    function syncControlsFromState() {
      if (custChrgSelect) {
        custChrgSelect.value = state.custChrgPsnCd;
      }
      if (custCodeSelect) {
        custCodeSelect.value = state.custCode;
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
      Core.appendSortQueryParams(params, state.sortSpecs, state.page, state.pageSize);
      Core.replaceUrl(window.location.pathname, params.toString());
    }

    function renderConfirmationSelect(selectedValue) {
      return `<select class="ioa-confirmation-status" aria-label="確認状態">${confirmationStatusChoices
        .map(
          (choice) =>
            `<option value="${Core.escapeHtml(choice.value)}"${
              choice.value === selectedValue ? " selected" : ""
            }>${Core.escapeHtml(choice.label)}</option>`,
        )
        .join("")}</select>`;
    }

    function renderTableBody(pageRows) {
      if (!pageRows.length) {
        tableBody.innerHTML = `<tr><td colspan="${sortableColumns.length}" class="ioa-table-empty">表示する行がありません。</td></tr>`;
        return;
      }
      tableBody.innerHTML = pageRows
        .map((row) => {
          const display = row.display && typeof row.display === "object" ? row.display : {};
          const cells = sortableColumns
            .map((column) => {
              if (column.key === "confirmation_status") {
                return `<td>${renderConfirmationSelect(row.confirmationStatusKey || "unconfirmed")}</td>`;
              }
              return `<td>${Core.escapeHtml(display[column.key] ?? "")}</td>`;
            })
            .join("");
          return `<tr class="alert-row alert-row--${Core.escapeHtml(row.alertRowClass || "")} ioa-data-row"
            data-cust-code="${Core.escapeHtml(row.cust_code || "")}"
            data-cust-name="${Core.escapeHtml(row.cust_name || "")}"
            data-item-cd="${Core.escapeHtml(row.item_cd || "")}"
            data-stock-qty="${Core.escapeHtml(row.stock_qty || "")}"
            data-stock-location-detail="${Core.escapeHtml(row.stock_location_detail || "")}"
            data-stock-as-of-label="${Core.escapeHtml(row.stock_as_of_label || "")}"
            data-confirmation-status="${Core.escapeHtml(row.confirmationStatusKey || "unconfirmed")}">${cells}</tr>`;
        })
        .join("");
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
    }

    function setState(patch) {
      state = { ...state, ...patch };
      render();
    }

    custChrgSelect?.addEventListener("change", () => {
      setState({ custChrgPsnCd: custChrgSelect.value, page: 1 });
    });
    custCodeSelect?.addEventListener("change", () => {
      setState({ custCode: custCodeSelect.value, page: 1 });
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
        };
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

  window.IoaListClient = { init: initListClient };
})();

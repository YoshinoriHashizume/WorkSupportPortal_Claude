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

  // 流動区分の判定ロジックはサーバ側にのみ置く。ここは row.flowQuadrants から引くだけにする
  // （design.md §3.2 案B）。暦月計算を JS に持ち込まない。
  const QUADRANT_NORMAL_FLOW_KEY = "normal-flow";
  const FLOW_QUADRANT_RANK = {
    "supply-risk": 0,
    "dormant-stock": 1,
    "excess-stock-risk": 2,
    [QUADRANT_NORMAL_FLOW_KEY]: 3,
  };
  const CONFIRMATION_STATUS_RANK = {
    unconfirmed: 0,
    in_progress: 1,
    confirmed: 2,
  };

  function flowSelectionKey(state) {
    const axis = String(state.flowAxis || "low_flow");
    const prefix = axis === "dormant" ? "D" : "L";
    return `${prefix}${Number(state.flowPeriod) || 3}`;
  }

  function rowFlowQuadrantKey(row, state) {
    const matrix = row.flowQuadrants || {};
    const key = matrix[flowSelectionKey(state)];
    return key && Object.prototype.hasOwnProperty.call(FLOW_QUADRANT_RANK, key)
      ? key
      : QUADRANT_NORMAL_FLOW_KEY;
  }

  function flowQuadrantSortRank(key) {
    return FLOW_QUADRANT_RANK[key] ?? 99;
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
    if (column === "flow_quadrant") {
      return "asc";
    }
    if (
      column === "post_shipment_count" ||
      column === "post_shipment_total_qty" ||
      column === "stock_qty" ||
      column === "mari_stock_qty"
    ) {
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
    const defaultSelection = defaults.defaultFlowSelection || { axis: "low_flow", period: 3 };
    const flowPeriods = defaults.flowPeriods || {};
    const axisRaw = params.get("axis") || "";
    const flowAxis = Object.prototype.hasOwnProperty.call(flowPeriods, axisRaw)
      ? axisRaw
      : defaultSelection.axis;
    const flowPeriod = resolveFlowPeriod(flowPeriods, flowAxis, params.get("period"), defaultSelection);
    const quadrantRaw = params.get("flow_quadrant") || "";
    return {
      custCode: custCodeRaw && validCust.has(custCodeRaw) ? custCodeRaw : "",
      custChrgPsnCd,
      itemCd: params.get("item_cd") || "",
      level1ItemCd: params.get("level1_item_cd") || "",
      flowAxis,
      flowPeriod,
      flowQuadrant: Object.prototype.hasOwnProperty.call(FLOW_QUADRANT_RANK, quadrantRaw) ? quadrantRaw : "",
      attentionOnly: (params.get("attentionOnly") || "").toLowerCase() === "true",
      ...Core.readBaseStateFromUrl(defaults, defaultDirectionForColumn),
    };
  }

  function resolveFlowPeriod(flowPeriods, axis, rawPeriod, defaultSelection) {
    const options = flowPeriods[axis] || [];
    const parsed = Number(rawPeriod);
    if (options.some((option) => Number(option.value) === parsed)) {
      return parsed;
    }
    // 軸に対応しない値・未指定は当該軸の既定値へ倒す（design.md §6.1）。
    if (axis === defaultSelection.axis) {
      return Number(defaultSelection.period);
    }
    return options.length ? Number(options[0].value) : Number(defaultSelection.period);
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
      const quadrantKey = rowFlowQuadrantKey(row, state);
      if (state.flowQuadrant && quadrantKey !== state.flowQuadrant) {
        return false;
      }
      if (state.attentionOnly && quadrantKey === QUADRANT_NORMAL_FLOW_KEY) {
        return false;
      }
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

  function countRows(rows, state) {
    return rows.reduce(
      (counts, row) => {
        const quadrantKey = rowFlowQuadrantKey(row, state);
        if (quadrantKey === "supply-risk") {
          counts.supplyRisk += 1;
        } else if (quadrantKey === "dormant-stock") {
          counts.dormantStock += 1;
        } else if (quadrantKey === "excess-stock-risk") {
          counts.excessStockRisk += 1;
        } else {
          counts.normalFlow += 1;
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
        supplyRisk: 0,
        dormantStock: 0,
        excessStockRisk: 0,
        normalFlow: 0,
        confirmed: 0,
        inProgress: 0,
        unconfirmed: 0,
      },
    );
  }

  function sortValue(row, column, state) {
    const value = row[column] ?? "";
    if (column === "flow_quadrant") {
      return flowQuadrantSortRank(rowFlowQuadrantKey(row, state));
    }
    if (column === "post_shipment_count" || column === "post_shipment_total_qty") {
      const number = Number.parseInt(String(value || "0"), 10);
      return Number.isFinite(number) ? number : 0;
    }
    if (column === "stock_qty" || column === "mari_stock_qty") {
      // 空（該当なし）も未取得の「－」も末尾へ落とす（design.md §6.1）。
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
    const flowAxisSelect = pageRoot.querySelector("#ioa-flow-axis");
    const flowPeriodSelect = pageRoot.querySelector("#ioa-flow-period");
    const flowQuadrantSelect = pageRoot.querySelector("#ioa-flow-quadrant");
    const flowQuadrantLabels = payload.flowQuadrantLabels || {};
    const flowQuadrantDepartments = payload.flowQuadrantDepartments || {};
    const flowAxes = Array.isArray(payload.flowAxes) ? payload.flowAxes : [];
    const flowPeriods = payload.flowPeriods || {};
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
      // 判定条件は常に URL へ書き戻し、再読み込み後も選択が復元されるようにする（design.md §6.1）。
      params.set("axis", state.flowAxis);
      params.set("period", String(state.flowPeriod));
      if (state.flowQuadrant) {
        params.set("flow_quadrant", state.flowQuadrant);
      }
      if (state.attentionOnly) {
        params.set("attentionOnly", "true");
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
          const quadrantKey = rowFlowQuadrantKey(row, state);
          const statusKey = String(row.confirmationStatusKey || "unconfirmed");
          // 確認状態は流動区分より優先する（design.md §6.6.7）。
          const rowClass =
            statusKey === "confirmed" ? "確認済" : statusKey === "in_progress" ? "確認中" : quadrantKey;
          const cells = sortableColumns
            .map((column) => {
              if (column.key === "confirmation_status") {
                return `<td>${renderConfirmationSelect(
                  row.confirmationStatusKey || "unconfirmed",
                  identity,
                )}</td>`;
              }
              // 判定条件を切り替えたら流動区分は引き直す（design.md §3.2 案B）。
              if (column.key === "flow_quadrant") {
                return `<td>${Core.escapeHtml(flowQuadrantLabels[quadrantKey] || "")}</td>`;
              }
              return `<td>${Core.escapeHtml(display[column.key] ?? "")}</td>`;
            })
            .join("");
          return `<tr class="alert-row alert-row--${Core.escapeHtml(rowClass)} ioa-data-row"
            data-row-key="${Core.escapeHtml(String(rowKey || ""))}"
            data-cust-code="${Core.escapeHtml(identity.custCode)}"
            data-cust-name="${Core.escapeHtml(row.cust_name || "")}"
            data-item-cd="${Core.escapeHtml(identity.itemCd)}"
            data-level1-vend-cd="${Core.escapeHtml(row.level1_vend_cd || "")}"
            data-level1-vend-name="${Core.escapeHtml(row.level1_vend_name || "")}"
            data-level1-item-cd="${Core.escapeHtml(row.level1_item_cd || "")}"
            data-last-incoming-date="${Core.escapeHtml(display.last_incoming_date ?? "")}"
            data-last-ship-date="${Core.escapeHtml(display.last_ship_date ?? "")}"
            data-flow-quadrant="${Core.escapeHtml(quadrantKey)}"
            data-no-incoming-record="${row.noIncomingRecord ? "1" : ""}"
            data-stock-qty="${Core.escapeHtml(display.stock_qty ?? "")}"
            data-mari-stock-qty="${Core.escapeHtml(display.mari_stock_qty ?? "")}"
            data-stock-location-detail="${Core.escapeHtml(row.stock_location_detail || "")}"
            data-stock-as-of-label="${Core.escapeHtml(row.stock_as_of_label || "")}"
            data-confirmation-status="${Core.escapeHtml(row.confirmationStatusKey || "unconfirmed")}">${cells}</tr>`;
        })
        .join("");
      cacheRenderedRowIdentities(pageRows);
    }

    function renderCounts(counts) {
      countsLeft.textContent =
        `供給リスク品 ${counts.supplyRisk} 件 / 在庫死蔵品 ${counts.dormantStock} 件 / 在庫過剰リスク品 ${counts.excessStockRisk} 件 / 通常流動品 ${counts.normalFlow} 件`;
      countsRight.textContent =
        `確認済み ${counts.confirmed} 件 / 確認中 ${counts.inProgress} 件 / 未確認 ${counts.unconfirmed} 件`;
    }

    function render() {
      const filtered = applyListFilters(allRows, state);
      const counts = countRows(filtered, state);
      const sorted = Core.sortRows(filtered, state.sortSpecs, (row, column) => sortValue(row, column, state), [
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
      syncFlowSelector();
      itemCdAutocomplete.sync(state.itemCd);
      level1ItemCdAutocomplete.sync(state.level1ItemCd);
    }

    function setState(patch) {
      state = { ...state, ...patch };
      render();
    }

    function syncFlowSelector() {
      if (flowAxisSelect) {
        flowAxisSelect.value = state.flowAxis;
      }
      if (flowPeriodSelect) {
        // 選択中の判定軸に属する選択肢だけを見せる（design.md §6.6.1）。
        // 判定期間の value は軸をまたいで重複する（例: 低流動1か月と死蔵1年がともに "1"）ため、
        // <select>.value = "1" の代入は DOM 順で最初に一致した option（隠れていても）を選んでしまう。
        // 軸と value の両方が一致する option を明示的に選択する。
        let matchedOption = null;
        Array.from(flowPeriodSelect.options).forEach((option) => {
          const isCurrentAxis = option.dataset.axis === state.flowAxis;
          option.hidden = !isCurrentAxis;
          if (isCurrentAxis && Number(option.value) === Number(state.flowPeriod)) {
            matchedOption = option;
          }
        });
        if (matchedOption) {
          matchedOption.selected = true;
        }
      }
      if (flowQuadrantSelect) {
        flowQuadrantSelect.value = state.flowQuadrant || "";
      }
    }

    flowAxisSelect?.addEventListener("change", () => {
      const nextAxis = flowAxisSelect.value;
      const options = flowPeriods[nextAxis] || [];
      // 軸を切り替えたら判定期間は当該軸の既定値へ戻す（REQ-LFV-F-003）。ページも1へ。
      const defaultPeriod = nextAxis === (payload.defaultFlowSelection || {}).axis
        ? Number((payload.defaultFlowSelection || {}).period)
        : Number(options.length ? options[0].value : 3);
      setState({ flowAxis: nextAxis, flowPeriod: defaultPeriod, page: 1 });
    });

    flowPeriodSelect?.addEventListener("change", () => {
      setState({ flowPeriod: Number(flowPeriodSelect.value), page: 1 });
    });

    flowQuadrantSelect?.addEventListener("change", () => {
      setState({ flowQuadrant: flowQuadrantSelect.value, page: 1 });
    });

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
      // 詳細ダイアログ用（design.md §6.3.1）。責任部署は流動区分からの導出値であり、
      // 判定軸の切替に追随させるため属性ではなく対応表から引く。
      getFlowQuadrantLabel(quadrantKey) {
        return flowQuadrantLabels[quadrantKey] || "";
      },
      getResponsibleDepartment(quadrantKey) {
        return flowQuadrantDepartments[quadrantKey] || "";
      },
      getFlowConditionLabel() {
        const axis = flowAxes.find((option) => option.value === state.flowAxis);
        const period = (flowPeriods[state.flowAxis] || []).find(
          (option) => Number(option.value) === Number(state.flowPeriod),
        );
        return axis && period ? `${axis.label}・${period.label}で判定` : "";
      },
      // 出荷推移(V-216)は24件の配列のため data-* 属性にせず、findRow() 経由で行データから直接返す(design.md §6.3)。
      getShipmentTrend(custCode, itemCd) {
        const row = findRow(custCode, itemCd);
        return Array.isArray(row?.shipment_trend) ? row.shipment_trend : [];
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

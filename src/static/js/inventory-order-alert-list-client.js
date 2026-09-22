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

  // 流動区分の判定ロジックはサーバ側にのみ置く。ここは row.flowQuadrants（Y1/Y3/Y5）から引くだけにする
  // （05 design §3.1）。暦月計算を JS に持ち込まない。
  const QUADRANT_NORMAL_FLOW_KEY = "normal-flow";
  // ランクは S-203（07 で 7 区分に拡張）。未知のキーは通常流動品に倒れるので、
  // ここに載っていない区分は一覧で通常流動品として扱われてしまう点に注意。
  const FLOW_QUADRANT_RANK = {
    "stockout-no-incoming": 0,
    "stockout": 1,
    "low-flow-no-incoming": 2,
    "dormant-stock": 3,
    "low-flow-no-shipment": 4,
    "discontinuation-candidate": 5,
    [QUADRANT_NORMAL_FLOW_KEY]: 6,
  };
  const DEFAULT_PERIOD_KEY = "Y1";
  // 在庫切れリスク（S-204）。判定は取込時にサーバで行い、ここは行の値を使うだけ（06 design §6.4）。
  const STOCKOUT_RISK_RANK = { danger: 0, caution: 1, watch: 2, none: 3 };
  const STOCKOUT_RISK_LABELS = { danger: "危険", caution: "注意", watch: "監視", none: "対象外" };
  const ORDERING_METHOD_KEYS = ["manual", "mrp", "unknown"];

  function rowStockoutRiskKey(row) {
    const key = String(row.stockoutRiskKey || "");
    return Object.prototype.hasOwnProperty.call(STOCKOUT_RISK_RANK, key) ? key : "watch";
  }
  const NO_INCOMING_RECORD_TEXT = "入荷実績なし";
  const CONFIRMATION_STATUS_RANK = {
    unconfirmed: 0,
    in_progress: 1,
    confirmed: 2,
  };

  function flowSelectionKey(state) {
    return String(state.periodKey || DEFAULT_PERIOD_KEY);
  }

  // 状況（S-203）はサーバ由来のテンプレートに判定期間ラベルと行の日付を埋めるだけ（05 design §6.3、NF-005）。
  function renderStatusText(statusTemplate, periodLabel, row) {
    const lastIncoming = row.noIncomingRecord
      ? NO_INCOMING_RECORD_TEXT
      : String(row.display?.last_incoming_date ?? row.last_incoming_date ?? "");
    const lastShip = String(row.display?.last_ship_date ?? row.last_ship_date ?? "");
    return String(statusTemplate || "")
      .replace("{period}", periodLabel)
      .replace("{last_incoming}", lastIncoming)
      .replace("{last_ship}", lastShip);
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
    const periodKey = resolvePeriodKey(defaults.evaluationPeriods || [], params.get("period"), defaults.defaultPeriodKey);
    const quadrantRaw = params.get("flow_quadrant") || "";
    return {
      custCode: custCodeRaw && validCust.has(custCodeRaw) ? custCodeRaw : "",
      custChrgPsnCd,
      itemCd: params.get("item_cd") || "",
      level1ItemCd: params.get("level1_item_cd") || "",
      periodKey,
      flowQuadrant: Object.prototype.hasOwnProperty.call(FLOW_QUADRANT_RANK, quadrantRaw) ? quadrantRaw : "",
      stockoutRisk: Object.prototype.hasOwnProperty.call(STOCKOUT_RISK_RANK, params.get("stockout_risk") || "") ? params.get("stockout_risk") : "",
      orderingMethod: ORDERING_METHOD_KEYS.includes(params.get("ordering_method") || "") ? params.get("ordering_method") : "",
      attentionOnly: (params.get("attentionOnly") || "").toLowerCase() === "true",
      ...Core.readBaseStateFromUrl(defaults, defaultDirectionForColumn),
    };
  }

  // `period` は年数（1/3/5）または Y キー。不正値・旧値（6 など）は既定へ倒す（05 design §6.1）。
  function resolvePeriodKey(evaluationPeriods, rawPeriod, defaultPeriodKey) {
    const raw = String(rawPeriod || "").trim();
    const matched = evaluationPeriods.find(
      (period) => period.key === raw || String(period.years) === raw,
    );
    return matched ? matched.key : String(defaultPeriodKey || DEFAULT_PERIOD_KEY);
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
      if (state.stockoutRisk && rowStockoutRiskKey(row) !== state.stockoutRisk) {
        return false;
      }
      if (state.orderingMethod && String(row.orderingMethodKey || "unknown") !== state.orderingMethod) {
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
        if (quadrantKey === "low-flow-no-incoming") {
          counts.lowFlowNoIncoming += 1;
        } else if (quadrantKey === "dormant-stock") {
          counts.dormantStock += 1;
        } else if (quadrantKey === "low-flow-no-shipment") {
          counts.lowFlowNoShipment += 1;
        } else {
          counts.normalFlow += 1;
        }
        const riskKey = rowStockoutRiskKey(row);
        if (riskKey === "danger") {
          counts.danger += 1;
        } else if (riskKey === "caution") {
          counts.caution += 1;
        } else if (riskKey === "watch") {
          counts.watch += 1;
        } else {
          counts.noneRisk += 1;
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
        lowFlowNoIncoming: 0,
        dormantStock: 0,
        lowFlowNoShipment: 0,
        normalFlow: 0,
        danger: 0,
        caution: 0,
        watch: 0,
        noneRisk: 0,
        confirmed: 0,
        inProgress: 0,
        unconfirmed: 0,
      },
    );
  }

  function sortDirectionOf(state, column) {
    const spec = (state.sortSpecs || []).find((item) => item.column === column);
    return spec ? spec.direction : "asc";
  }

  // 空を昇順・降順とも末尾に置く数値ソートキー（在庫月数・猶予日数）。
  function nullsLastSortValue(raw, state, column) {
    const number = raw === null || raw === undefined || raw === "" ? null : Number(raw);
    const isEmpty = number === null || !Number.isFinite(number);
    if (sortDirectionOf(state, column) === "desc") {
      return isEmpty ? [0, 0] : [1, number];
    }
    return isEmpty ? [1, 0] : [0, number];
  }

  // 在庫月数（V-222）の並び替え。空は昇順・降順とも末尾（05 design §6.1、TC-SFV-D-059）。
  function monthsOfStockSortValue(row, state) {
    return nullsLastSortValue(row.demandForecast?.monthsOfStock ?? row.months_of_stock, state, "months_of_stock");
  }

  function sortValue(row, column, state) {
    const value = row[column] ?? "";
    if (column === "flow_quadrant") {
      return flowQuadrantSortRank(rowFlowQuadrantKey(row, state));
    }
    if (column === "months_of_stock") {
      return monthsOfStockSortValue(row, state);
    }
    if (column === "stockout_risk") {
      return STOCKOUT_RISK_RANK[rowStockoutRiskKey(row)];
    }
    if (column === "days_until_stockout") {
      return nullsLastSortValue(row.daysUntilStockout, state, "days_until_stockout");
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
    // 一覧の列には出さないが並び替えダイアログでは選べる項目（在庫月数）。05 design §6.1
    const sortOnlyColumns = Array.isArray(payload.sortOnlyColumns) ? payload.sortOnlyColumns : [];
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
    const evaluationPeriodSelect = pageRoot.querySelector("#ioa-evaluation-period");
    const flowQuadrantSelect = pageRoot.querySelector("#ioa-flow-quadrant");
    const stockoutRiskSelect = pageRoot.querySelector("#ioa-stockout-risk");
    const orderingMethodSelect = pageRoot.querySelector("#ioa-ordering-method");
    const flowQuadrantLabels = payload.flowQuadrantLabels || {};
    const flowQuadrantDepartments = payload.flowQuadrantDepartments || {};
    const recommendedActions = payload.recommendedActions || {};
    const evaluationPeriods = Array.isArray(payload.evaluationPeriods) ? payload.evaluationPeriods : [];
    const alertRulesDialog = document.getElementById("ioa-alert-rules-dialog");
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

    // 推定在庫推移(V-218)は「照合単位」で逆算する（design.md §6.6、2026/09/11 改訂）。
    // 在庫は得意先品番・出荷は得意先×得意先品番・入荷は内作品番×仕入先と粒度が異なるため、
    // 得意先品番と (内作品番, 仕入先) を節点とする二部グラフの連結成分まで広げて数量を閉じる。
    // 合算は必ず未フィルタの allRows で行う（絞り込みでグラフが変わってはならない）。
    let reconciliationUnits = null;

    function itemKeyOf(row) {
      return `I:${String(row.item_cd || "")}`;
    }

    function pairKeyOf(row) {
      return `P:${String(row.level1_item_cd || "")}|${String(row.level1_vend_cd || "")}`;
    }

    function sumTrendInto(total, trend) {
      if (!Array.isArray(trend)) {
        return;
      }
      trend.forEach((point, index) => {
        if (index >= total.length) {
          return;
        }
        total[index].qty += Number(point?.qty) || 0;
      });
    }

    function buildReconciliationUnits() {
      // Union-Find（経路圧縮のみ。数千件規模なのでランクは持たない）
      const parent = new Map();
      const find = (key) => {
        if (!parent.has(key)) {
          parent.set(key, key);
        }
        let root = key;
        while (parent.get(root) !== root) {
          root = parent.get(root);
        }
        let cursor = key;
        while (parent.get(cursor) !== root) {
          const next = parent.get(cursor);
          parent.set(cursor, root);
          cursor = next;
        }
        return root;
      };
      const union = (a, b) => {
        const rootA = find(a);
        const rootB = find(b);
        if (rootA !== rootB) {
          parent.set(rootA, rootB);
        }
      };

      allRows.forEach((row) => union(itemKeyOf(row), pairKeyOf(row)));

      const grouped = new Map();
      allRows.forEach((row) => {
        const root = find(itemKeyOf(row));
        if (!grouped.has(root)) {
          grouped.set(root, []);
        }
        grouped.get(root).push(row);
      });

      const units = new Map();
      grouped.forEach((unitRows) => {
        const base = unitRows.find((row) => Array.isArray(row.shipment_trend) && row.shipment_trend.length);
        const months = base ? base.shipment_trend.map((point) => point.month) : [];
        const shipmentTrend = months.map((month) => ({ month, qty: 0 }));
        const incomingTrend = months.map((month) => ({ month, qty: 0 }));
        // 出荷: 行は (得意先, 得意先品番) で一意なので、そのまま全行を足す。
        unitRows.forEach((row) => sumTrendInto(shipmentTrend, row.shipment_trend));
        // 入荷: (内作品番, 仕入先) 単位のため、同じ組を共有する行で重複する。組ごとに1回だけ足す。
        const countedPairs = new Set();
        const level1Pairs = [];
        unitRows.forEach((row) => {
          const key = pairKeyOf(row);
          if (countedPairs.has(key)) {
            return;
          }
          countedPairs.add(key);
          level1Pairs.push({
            level1ItemCd: String(row.level1_item_cd || ""),
            level1VendCd: String(row.level1_vend_cd || ""),
          });
          sumTrendInto(incomingTrend, row.incoming_trend);
        });
        // 在庫: 得意先品番ごとに1回。表示文字列を返し、3状態の解釈は呼び出し側に委ねる。
        const countedItems = new Set();
        const stocks = [];
        unitRows.forEach((row) => {
          const itemCd = String(row.item_cd || "");
          if (countedItems.has(itemCd)) {
            return;
          }
          countedItems.add(itemCd);
          stocks.push({ itemCd, stockDisplay: String(row.display?.stock_qty ?? "") });
        });
        const unit = { shipmentTrend, incomingTrend, stocks, level1Pairs };
        countedItems.forEach((itemCd) => units.set(itemCd, unit));
      });
      return units;
    }

    function itemTrendsOf(itemCd) {
      if (!reconciliationUnits) {
        reconciliationUnits = buildReconciliationUnits();
      }
      return (
        reconciliationUnits.get(String(itemCd || "")) || {
          shipmentTrend: [],
          incomingTrend: [],
          stocks: [],
          level1Pairs: [],
        }
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
      // 判定期間は常に URL へ書き戻し、再読み込み後も選択が復元されるようにする（05 design §6.1、REQ-SFV-F-016）。
      params.delete("axis");
      params.set("period", String(currentPeriod().years));
      if (state.flowQuadrant) {
        params.set("flow_quadrant", state.flowQuadrant);
      }
      if (state.stockoutRisk) {
        params.set("stockout_risk", state.stockoutRisk);
      } else {
        params.delete("stockout_risk");
      }
      if (state.orderingMethod) {
        params.set("ordering_method", state.orderingMethod);
      } else {
        params.delete("ordering_method");
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

    function currentPeriod() {
      const matched = evaluationPeriods.find((period) => period.key === state.periodKey);
      return matched || evaluationPeriods[0] || { years: 1, key: DEFAULT_PERIOD_KEY, label: "1年" };
    }

    function flowStatusOf(row, quadrantKey) {
      const template = recommendedActions[quadrantKey]?.statusTemplate || "";
      return renderStatusText(template, currentPeriod().label, row);
    }

    function recommendedActionOf(quadrantKey) {
      return recommendedActions[quadrantKey]?.action || "";
    }

    function responsibleDepartmentOf(quadrantKey) {
      return recommendedActions[quadrantKey]?.departments || flowQuadrantDepartments[quadrantKey] || "";
    }

    // 緊急度（V-223）の文言。需要予測が算出できない行（basis なし・在庫月数なし）は空（05 design §6.3、REQ-SFV-F-009）。
    // 在庫切れ予測月が空（120 か月超）は「十分」。テンプレート側（list.html）の描画と対で維持する。
    function urgencyTextOf(row) {
      const forecast = row.demandForecast || {};
      const months = forecast.monthsOfStock;
      if (!forecast.basis || forecast.basis === "なし" || months === null || months === undefined) {
        return "";
      }
      const stockout = forecast.stockoutForecastMonth ? `${forecast.stockoutForecastMonth} に在庫切れ` : "十分";
      return `約 ${months} か月分 → ${stockout}（${forecast.basis}）`;
    }

    // 流動区分セルは区分名のみ（05 design §6.3、REQ-SFV-F-004。2026-09-17 改訂）。通常流動品は空。
    // 状況・緊急度・推奨アクション・責任部署は詳細ダイアログが getFlowStatus() 等で引く。
    function renderFlowCell(row, quadrantKey) {
      if (quadrantKey === QUADRANT_NORMAL_FLOW_KEY) {
        return `<td class="ioa-flow-cell"></td>`;
      }
      // 区分ごとのバッジ色は CSS（.ioa-flow-quadrant--<key>）。行の色は付けない（07 design §5.1）
      return `<td class="ioa-flow-cell"><span class="ioa-flow-quadrant ioa-flow-quadrant--${Core.escapeHtml(quadrantKey)}">${Core.escapeHtml(flowQuadrantLabels[quadrantKey] || "")}</span></td>`;
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
          const riskKey = rowStockoutRiskKey(row);
          // 行の色は 確認状態 > 在庫切れリスク のみ。流動区分は色に使わない（06 design §6.4、2026/09/18 改訂）。
          const rowClass =
            statusKey === "confirmed" ? "確認済" : statusKey === "in_progress" ? "確認中" : `stockout-${riskKey}`;
          const cells = sortableColumns
            .map((column) => {
              if (column.key === "confirmation_status") {
                return `<td>${renderConfirmationSelect(
                  row.confirmationStatusKey || "unconfirmed",
                  identity,
                )}</td>`;
              }
              // 判定期間を切り替えたら流動区分は引き直す（05 design §3.1）。
              if (column.key === "flow_quadrant") {
                return renderFlowCell(row, quadrantKey);
              }
              // 在庫切れリスク（S-204）はサーバ判定値をそのまま出す。対象外・旧行は空
              if (column.key === "stockout_risk") {
                const label = riskKey === "none" || !row.stockoutRiskKey ? "" : STOCKOUT_RISK_LABELS[riskKey];
                return `<td class="ioa-stockout-risk-cell">${label ? `<span class="ioa-stockout-risk ioa-stockout-risk--${riskKey}">${Core.escapeHtml(label)}</span>` : ""}</td>`;
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
            data-flow-status="${Core.escapeHtml(quadrantKey === QUADRANT_NORMAL_FLOW_KEY ? "" : flowStatusOf(row, quadrantKey))}"
            data-recommended-action="${Core.escapeHtml(recommendedActionOf(quadrantKey))}"
            data-responsible-department="${Core.escapeHtml(responsibleDepartmentOf(quadrantKey))}"
            data-stockout-risk="${Core.escapeHtml(riskKey)}"
            data-demand-forecast-basis="${Core.escapeHtml(row.demandForecast?.basis || "")}"
            data-months-of-stock="${Core.escapeHtml(row.demandForecast?.monthsOfStock ?? "")}"
            data-stockout-forecast-month="${Core.escapeHtml(row.demandForecast?.stockoutForecastMonth || "")}"
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
        `危険 ${counts.danger} 件 / 注意 ${counts.caution} 件 / 監視 ${counts.watch} 件 / 対象外 ${counts.noneRisk} 件`;
      countsRight.textContent =
        `確認済み ${counts.confirmed} 件 / 確認中 ${counts.inProgress} 件 / 未確認 ${counts.unconfirmed} 件`;
    }

    function render() {
      const filtered = applyListFilters(allRows, state);
      const counts = countRows(filtered, state);
      // 同順位の並びはサーバの既定（table_display.sort_rows）と同じ: 猶予日数 → 流動区分 → 得意先コード → 得意先品番
      const sorted = Core.sortRows(filtered, state.sortSpecs, (row, column) => sortValue(row, column, state), [
        { column: "days_until_stockout", direction: "asc" },
        { column: "flow_quadrant", direction: "asc" },
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
      const period = currentPeriod();
      if (evaluationPeriodSelect) {
        evaluationPeriodSelect.value = String(period.years);
      }
      if (flowQuadrantSelect) {
        flowQuadrantSelect.value = state.flowQuadrant || "";
      }
      if (stockoutRiskSelect) {
        stockoutRiskSelect.value = state.stockoutRisk || "";
      }
      if (orderingMethodSelect) {
        orderingMethodSelect.value = state.orderingMethod || "";
      }
      // 判定ルールダイアログの「現在の判定期間」と状況テンプレートの {period} を選択中の判定期間に合わせる。
      if (alertRulesDialog) {
        const periodElement = alertRulesDialog.querySelector(".ioa-alert-rules-period");
        if (periodElement) {
          periodElement.textContent = period.label;
        }
        alertRulesDialog.querySelectorAll(".ioa-alert-rules-status[data-status-template]").forEach((cell) => {
          cell.textContent = String(cell.dataset.statusTemplate || "").replace("{period}", period.label);
        });
      }
    }

    evaluationPeriodSelect?.addEventListener("change", () => {
      // 判定期間を切り替えたらページは 1 へ（REQ-SFV-F-001）。
      setState({ periodKey: resolvePeriodKey(evaluationPeriods, evaluationPeriodSelect.value, payload.defaultPeriodKey), page: 1 });
    });

    flowQuadrantSelect?.addEventListener("change", () => {
      setState({ flowQuadrant: flowQuadrantSelect.value, page: 1 });
    });
    stockoutRiskSelect?.addEventListener("change", () => {
      setState({ stockoutRisk: stockoutRiskSelect.value, page: 1 });
    });
    orderingMethodSelect?.addEventListener("change", () => {
      setState({ orderingMethod: orderingMethodSelect.value, page: 1 });
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
      // 並び替えダイアログ用。一覧の列に加え、ソート専用項目（在庫月数）も選べる（05 design §6.1）。
      getSortableColumns() {
        return sortableColumns.concat(sortOnlyColumns).map((column) => ({ ...column }));
      },
      // 詳細ダイアログの需要予測区分用（05 design §6.4）。
      getDemandForecast(custCode, itemCd) {
        const row = findRow(custCode, itemCd);
        return row?.demandForecast ? { ...row.demandForecast } : null;
      },
      getUnconfirmedOrderTrend(custCode, itemCd) {
        const row = findRow(custCode, itemCd);
        return Array.isArray(row?.unconfirmedOrderTrend) ? row.unconfirmedOrderTrend : [];
      },
      getUrgencyText(custCode, itemCd) {
        const row = findRow(custCode, itemCd);
        return row ? urgencyTextOf(row) : "";
      },
      // 詳細ダイアログの在庫切れリスク（06 design §6.4）。
      getStockoutRisk(custCode, itemCd) {
        const row = findRow(custCode, itemCd);
        if (!row) {
          return null;
        }
        return {
          risk: row.stockoutRisk || "監視",
          key: rowStockoutRiskKey(row),
          reasons: Array.isArray(row.stockoutRiskReasons) ? row.stockoutRiskReasons : [],
          daysUntilStockout: row.daysUntilStockout ?? null,
          shortageQty: row.shortageQty ?? null,
          replenishment: row.replenishment || { qty: 0, laterQty: 0, earliestDue: "", hasOverdue: false, unknown: false },
          leadTimeDays: row.leadTimeDays ?? null,
          leadTimeSource: row.leadTimeSource || "",
          orderingMethod: row.orderingMethod || "不明",
          upstreamOrder: row.upstreamOrder || { qty: 0, overdue: false, earliestDue: "" },
          processChain: Array.isArray(row.processChain) ? row.processChain : [],
        };
      },
      // 詳細ダイアログ用（05 design §6.4）。状況・推奨アクション・責任部署は流動区分からの導出値であり、
      // 判定期間の切替に追随させるため属性ではなく対応表から引く。
      getFlowQuadrantLabel(quadrantKey) {
        return flowQuadrantLabels[quadrantKey] || "";
      },
      getResponsibleDepartment(quadrantKey) {
        return responsibleDepartmentOf(quadrantKey);
      },
      getRecommendedAction(quadrantKey) {
        return recommendedActionOf(quadrantKey);
      },
      getFlowStatus(custCode, itemCd, quadrantKey) {
        const row = findRow(custCode, itemCd);
        if (!row || quadrantKey === QUADRANT_NORMAL_FLOW_KEY) {
          return "";
        }
        return flowStatusOf(row, quadrantKey);
      },
      // 流動区分の理由（07 REQ-FQR-F-005）。理由も判定期間で変わるため、区分と同じく期間キーで引く
      // （判定ロジックは JS に持ち込まない。07 design §1-6）。
      getFlowReasons(custCode, itemCd, periodKey) {
        const row = findRow(custCode, itemCd);
        if (!row) {
          return [];
        }
        const byPeriod = row.flowReasonsByPeriod || {};
        const reasons = byPeriod[periodKey || flowSelectionKey(state)];
        if (Array.isArray(reasons)) {
          return reasons;
        }
        return Array.isArray(row.flowReasons) ? row.flowReasons : [];
      },
      getEvaluationPeriodLabel() {
        return currentPeriod().label;
      },
      // 出荷推移(V-216)は24件の配列のため data-* 属性にせず、findRow() 経由で行データから直接返す(design.md §6.3)。
      getShipmentTrend(custCode, itemCd) {
        const row = findRow(custCode, itemCd);
        return Array.isArray(row?.shipment_trend) ? row.shipment_trend : [];
      },
      // 入荷推移(V-217)も同様に findRow() 経由で返す(design.md §6.1)。
      getIncomingTrend(custCode, itemCd) {
        const row = findRow(custCode, itemCd);
        return Array.isArray(row?.incoming_trend) ? row.incoming_trend : [];
      },
      // 推定在庫推移(V-218)用。照合単位に合算した出荷・入荷と、起点の内訳を返す(design.md §6.6)。
      getItemTrends(itemCd) {
        return itemTrendsOf(itemCd);
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

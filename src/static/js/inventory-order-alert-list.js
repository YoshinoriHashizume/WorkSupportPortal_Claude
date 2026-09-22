(function () {
  const ROW_SELECTOR = ".inventory-order-alert-page .ioa-table tbody tr.ioa-data-row";
  const CONFIRMATION_API = "/api/inventory-order-alert/confirmation";
  const CONFIRMATION_MEMO_API = "/api/inventory-order-alert/confirmation/memos";
  // 5年9組（five-year-nine）の検索結果ページ。既存の API パスと同じ流儀で定数として持つ（design.md §6.7）。
  const GONEN_RESULT_PATH = "/app/production/five-year-nine/result";
  const MAX_MEMO_LENGTH = 500;

  function getCsrfToken() {
    return window.portalCsrfToken || "";
  }

  function getListFilterParams(listClient) {
    if (listClient) {
      return listClient.getListFilterParams();
    }
    const params = new URLSearchParams(window.location.search);
    return {
      custCodeFilter: params.get("cust_code") || "",
      custChrgPsnCdFilter: params.get("cust_chrg_psn_cd") || "",
      itemCdFilter: params.get("item_cd") || "",
      level1ItemCdFilter: params.get("level1_item_cd") || "",
    };
  }

  function readRowKeys(select, row, listClient) {
    const readFromDom = window.IoaListClient?.readRowKeysFromDomElement;
    if (readFromDom) {
      for (const element of [select, row].filter(Boolean)) {
        const keys = readFromDom(element);
        if (keys.custCode && keys.itemCd) {
          return keys;
        }
      }
    }
    if (listClient?.resolveRowKeysFromElement) {
      return listClient.resolveRowKeysFromElement(row, select);
    }
    const sources = [select, row].filter(Boolean);
    for (const element of sources) {
      const custCode = String(element.getAttribute("data-cust-code") || element.dataset?.custCode || "").trim();
      const itemCd = String(element.getAttribute("data-item-cd") || element.dataset?.itemCd || "").trim();
      if (custCode && itemCd) {
        return { custCode, itemCd };
      }
    }
    return {
      custCode: String(row?.getAttribute("data-cust-code") || row?.dataset?.custCode || "").trim(),
      itemCd: String(row?.getAttribute("data-item-cd") || row?.dataset?.itemCd || "").trim(),
    };
  }

  function updateRowConfirmationState(row, payload) {
    row.dataset.confirmationStatus = payload.confirmationStatusKey || "unconfirmed";
    const alertPrefix = "alert-row--";
    [...row.classList].filter((className) => className.startsWith(alertPrefix)).forEach((className) => {
      row.classList.remove(className);
    });
    if (payload.alertRowClass) {
      row.classList.add(`${alertPrefix}${payload.alertRowClass}`);
    }
  }

  async function saveConfirmation(row, { status, custCode, itemCd }, listClient) {
    const keys = {
      custCode: String(custCode || "").trim(),
      itemCd: String(itemCd || "").trim(),
    };
    if (!keys.custCode || !keys.itemCd) {
      throw new Error("行の得意先コードまたは得意先品番を取得できませんでした。ページを再読み込みしてください。");
    }

    const response = await fetch(CONFIRMATION_API, {
      method: "PUT",
      headers: {
        "Content-Type": "application/json",
        "X-CSRFToken": getCsrfToken(),
      },
      body: JSON.stringify({
        ...getListFilterParams(listClient),
        custCode: keys.custCode,
        itemCd: keys.itemCd,
        status,
      }),
    });
    const payload = await response.json();
    if (!response.ok || !payload.ok) {
      throw new Error(payload.message || "確認状態の保存に失敗しました。");
    }
    if (listClient) {
      listClient.updateRowFromConfirmation(keys.custCode, keys.itemCd, payload);
    } else {
      updateRowConfirmationState(row, payload);
      updateTableCounts(payload.counts);
    }
    return payload;
  }

  async function saveConfirmationStatus(select, row, listClient) {
    const previousStatus =
      row.getAttribute("data-confirmation-status") || row.dataset.confirmationStatus || "unconfirmed";
    const nextStatus = select.value;
    if (nextStatus === previousStatus) {
      return;
    }

    const keys = readRowKeys(select, row, listClient);
    select.disabled = true;
    try {
      await saveConfirmation(row, {
        status: nextStatus,
        custCode: keys.custCode,
        itemCd: keys.itemCd,
      }, listClient);
    } catch (error) {
      select.value = previousStatus;
      window.alert(error.message || "確認状態の保存に失敗しました。");
    } finally {
      select.disabled = false;
    }
  }
  const STOCKOUT_RISK_LABEL_BY_KEY = { danger: "危険", caution: "注意", watch: "監視", none: "対象外" };

  function updateTableCounts(counts) {
    const countsElement = document.querySelector(".inventory-order-alert-page .ioa-table-counts");
    if (!countsElement || !counts) {
      return;
    }
    const left = countsElement.querySelector(".ioa-table-counts-left");
    const right = countsElement.querySelector(".ioa-table-counts-right");
    if (left) {
      left.textContent =
        `危険 ${counts.danger ?? 0} 件 / 注意 ${counts.caution ?? 0} 件 / 監視 ${counts.watch ?? 0} 件 / 対象外 ${counts.noneRisk ?? 0} 件`;
    }
    if (right) {
      right.textContent =
        `確認済み ${counts.confirmed} 件 / 確認中 ${counts.inProgress} 件 / 未確認 ${counts.unconfirmed} 件`;
    }
  }

  function initConfirmationStatusSelects(listClient) {
    const tableBody = document.querySelector(".inventory-order-alert-page .ioa-table tbody");
    if (!tableBody) {
      return;
    }
    tableBody.addEventListener("click", (event) => {
      if (event.target.closest(".ioa-confirmation-status")) {
        event.stopPropagation();
      }
    });
    tableBody.addEventListener("change", (event) => {
      const select = event.target.closest(".ioa-confirmation-status");
      if (!select) {
        return;
      }
      const row = select.closest(ROW_SELECTOR);
      if (!row) {
        return;
      }
      void saveConfirmationStatus(select, row, listClient);
    });
  }

  function showImportLoading() {
    const overlay = document.getElementById("ioa-import-overlay");
    if (overlay) {
      overlay.hidden = false;
      overlay.setAttribute("aria-busy", "true");
    }
    document.body.classList.add("ioa-import-loading");
  }

  function initSlimsImport() {
    const form = document.querySelector(".inventory-order-alert-page .ioa-import-form");
    const input = document.querySelector(".inventory-order-alert-page .ioa-file-picker-input");
    if (!form || !input) {
      return;
    }

    let submitting = false;
    input.addEventListener("change", () => {
      if (!input.files || input.files.length === 0 || submitting) {
        return;
      }
      submitting = true;
      const trigger = form.querySelector(".ioa-import-trigger");
      if (trigger) {
        trigger.classList.add("is-disabled");
        trigger.setAttribute("aria-disabled", "true");
      }
      showImportLoading();
      form.submit();
    });
  }

  function initSortDialog(listClient) {
    window.PortalListSortDialog?.init({
      dialog: document.getElementById("ioa-sort-dialog"),
      openButton: document.querySelector(".inventory-order-alert-page .ioa-sort-open"),
      listClient,
      maxSortRows: 5,
      rowClass: "ioa-sort-row",
      orderClass: "ioa-sort-row-order",
      columnClass: "ioa-sort-column",
      directionClass: "ioa-sort-direction",
      removeClass: "ioa-sort-remove",
      formClass: "ioa-sort-form",
      rowsContainerClass: "ioa-sort-rows",
      template: document.querySelector("#ioa-sort-row-template"),
      addButtonClass: "ioa-sort-add",
      cancelButtonClass: "ioa-sort-cancel",
    });
  }

  function initLocationDialog(listClient) {
    const dialog = document.getElementById("ioa-location-dialog");
    const listTableBody = document.querySelector(".inventory-order-alert-page .ioa-table tbody");
    if (!dialog || !listTableBody) {
      return;
    }

    // 詳細ダイアログの 4 区分（design.md §6.3）。値は行の data-* 属性から流し込む（§6.3.1）。
    const detailFields = {
        cust: dialog.querySelector(".ioa-detail-item-cust"),
        itemCd: dialog.querySelector(".ioa-detail-item-cd"),
        vend: dialog.querySelector(".ioa-detail-item-vend"),
        level1ItemCd: dialog.querySelector(".ioa-detail-item-level1-cd"),
        lastIncoming: dialog.querySelector(".ioa-detail-item-last-incoming"),
        lastShip: dialog.querySelector(".ioa-detail-item-last-ship"),
        flowQuadrant: dialog.querySelector(".ioa-detail-flow-quadrant"),
        flowStatus: dialog.querySelector(".ioa-detail-flow-status"),
        flowReasons: dialog.querySelector(".ioa-detail-flow-reasons"),
        flowReasonsLabel: dialog.querySelector(".ioa-detail-flow-reasons-label"),
        recommendedAction: dialog.querySelector(".ioa-detail-recommended-action"),
        department: dialog.querySelector(".ioa-detail-department"),
        evaluationPeriod: dialog.querySelector(".ioa-detail-evaluation-period"),
        stockSlims: dialog.querySelector(".ioa-detail-stock-slims"),
        stockMari: dialog.querySelector(".ioa-detail-stock-mari"),
    };
    const anchoredStockTrendSection = dialog.querySelector(".ioa-detail-anchored-stock-trend-section");
    const anchorBreakdown = dialog.querySelector(".ioa-detail-anchor-breakdown");
    // 需要予測（V-220〜V-222）区分（05 design §6.4）。
    const demandFields = {
      basis: dialog.querySelector(".ioa-detail-demand-basis"),
      monthly: dialog.querySelector(".ioa-detail-demand-monthly"),
      average: dialog.querySelector(".ioa-detail-demand-average"),
      monthsOfStock: dialog.querySelector(".ioa-detail-months-of-stock"),
      stockoutMonth: dialog.querySelector(".ioa-detail-stockout-month"),
      unitBreakdown: dialog.querySelector(".ioa-detail-demand-unit-breakdown"),
      empty: dialog.querySelector(".ioa-detail-demand-empty"),
      fields: dialog.querySelector(".ioa-detail-demand-forecast-fields"),
    };
    // 在庫切れリスク（S-204）区分（06 design §6.4）。
    const riskFields = {
      risk: dialog.querySelector(".ioa-detail-stockout-risk"),
      reasons: dialog.querySelector(".ioa-detail-stockout-risk-reasons"),
      days: dialog.querySelector(".ioa-detail-stockout-days"),
      replenishment: dialog.querySelector(".ioa-detail-stockout-replenishment"),
      shortage: dialog.querySelector(".ioa-detail-stockout-shortage"),
      leadTime: dialog.querySelector(".ioa-detail-stockout-lead-time"),
      orderingMethod: dialog.querySelector(".ioa-detail-stockout-ordering-method"),
      upstream: dialog.querySelector(".ioa-detail-stockout-upstream"),
      chainBody: dialog.querySelector(".ioa-detail-process-chain-body"),
      chainWrap: dialog.querySelector(".ioa-detail-process-chain-wrap"),
      chainEmpty: dialog.querySelector(".ioa-detail-process-chain-empty"),
    };

    const escapeHtml = (value) => (window.PortalListCore?.escapeHtml ? window.PortalListCore.escapeHtml(value) : String(value ?? "").replace(/[&<>"']/g, (ch) => ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;" })[ch]));

    // 工程の連鎖（完成品直下 → 上流）。各工程のリードタイムと発注残（納期・納期超過）を表にする（06 design §4.1a）。
    function renderProcessChain(chain) {
      if (!riskFields.chainBody || !riskFields.chainWrap || !riskFields.chainEmpty) {
        return;
      }
      const stages = Array.isArray(chain) ? chain : [];
      riskFields.chainWrap.hidden = !stages.length;
      riskFields.chainEmpty.hidden = Boolean(stages.length);
      const today = new Date();
      riskFields.chainBody.innerHTML = stages
        .map((stage, index) => {
          const orders = Array.isArray(stage.openOrders) ? stage.openOrders : [];
          const orderText = orders.length
            ? orders
                .map((order) => {
                  const due = String(order.dueDate || "");
                  const overdue = due && new Date(due.replace(/\//g, "-")) < today;
                  return `${formatQty(order.remainingQty)}（${due || "納期未定"}${overdue ? "・納期超過" : ""}）`;
                })
                .join(" / ")
            : "なし";
          const lt = `${stage.leadTimeDays ?? 0} 日${stage.leadTimeSource === "default" ? "（未設定）" : ""}`;
          return `<tr class="${orders.some((order) => order.dueDate && new Date(String(order.dueDate).replace(/\//g, "-")) < today) ? "ioa-detail-process-chain-row--overdue" : ""}">
            <td>${escapeHtml(String(stage.level || index + 1))}</td>
            <td class="mono">${escapeHtml(stage.itemCd || "")}</td>
            <td>${escapeHtml(stage.vendCd || "")} ${escapeHtml(stage.vendName || "")}</td>
            <td>${escapeHtml(lt)}</td>
            <td>${escapeHtml(orderText)}</td>
          </tr>`;
        })
        .join("");
    }

    function renderStockoutRisk(custCode, itemCd, row) {
      const info = listClient?.getStockoutRisk?.(custCode, itemCd);
      if (!riskFields.risk) {
        return;
      }
      if (!info) {
        setDetailText(riskFields.risk, row.dataset.stockoutRisk ? STOCKOUT_RISK_LABEL_BY_KEY[row.dataset.stockoutRisk] || "-" : "-");
        return;
      }
      setDetailText(riskFields.risk, info.risk || "-");
      if (riskFields.risk) {
        riskFields.risk.className = `ioa-detail-stockout-risk ioa-stockout-risk ioa-stockout-risk--${info.key}`;
      }
      setDetailText(riskFields.reasons, info.reasons.length ? info.reasons.join(" / ") : "-");
      setDetailText(riskFields.days, info.daysUntilStockout === null || info.daysUntilStockout === undefined ? "-" : `${info.daysUntilStockout} 日（在庫切れ予測月の 1 日まで）`);
      // 補充見込みは補充期限（V-229）までの発注残。補充期限より後・長期納期超過（V-230）は数えず、注記で示す（2026/09/21）
      const rep = info.replenishment || {};
      let replenishment = "-";
      if (rep.unknown) {
        replenishment = "取得できませんでした";
      } else if (rep.qty > 0) {
        replenishment = `${formatQty(rep.qty)}（最早納期 ${rep.earliestDue || "-"}${rep.hasOverdue ? "・納期超過あり" : ""}）`;
      } else if (info.key !== "watch" || rep.laterQty > 0 || rep.staleQty > 0) {
        replenishment = "なし";
      }
      if (!rep.unknown) {
        const notes = [];
        if (rep.laterQty > 0) notes.push(`補充期限より後の発注残 ${formatQty(rep.laterQty)}`);
        if (rep.staleQty > 0) notes.push(`長期納期超過 ${formatQty(rep.staleQty)} は除外`);
        if (notes.length) replenishment += `（${notes.join("・")}）`;
      }
      setDetailText(riskFields.replenishment, replenishment);
      setDetailText(riskFields.shortage, info.shortageQty === null || info.shortageQty === undefined ? "-" : formatQty(info.shortageQty));
      setDetailText(
        riskFields.leadTime,
        info.leadTimeDays === null || info.leadTimeDays === undefined ? "-" : `${info.leadTimeDays} 日${info.leadTimeSource === "default" ? "（既定値）" : ""}`,
      );
      setDetailText(riskFields.orderingMethod, info.orderingMethod || "-");
      const upstream = info.upstreamOrder || {};
      setDetailText(
        riskFields.upstream,
        upstream.qty > 0
          ? `${formatQty(upstream.qty)}（最早納期 ${upstream.earliestDue || "-"}${upstream.overdue ? "・納期超過" : ""}）`
          : "なし",
      );
      renderProcessChain(info.processChain);
    }
    const gonenLinkRow = dialog.querySelector(".ioa-detail-gonen-link-row");
    const gonenLink = dialog.querySelector(".ioa-detail-gonen-link");
    const locationTableBody = dialog.querySelector(".ioa-location-table-body");
    const tableWrap = dialog.querySelector(".ioa-location-table-wrap");
    const emptyMessage = dialog.querySelector(".ioa-location-empty");
    const asOfLabel = dialog.querySelector(".ioa-location-as-of");
    const closeButton = dialog.querySelector(".ioa-location-close");
    const saveButton = dialog.querySelector(".ioa-detail-save");
    const memoInput = dialog.querySelector(".ioa-detail-memo");
    const memoTableBody = dialog.querySelector(".ioa-detail-memo-table-body");
    const memoTableWrap = dialog.querySelector(".ioa-detail-memo-table-wrap");
    const memoEmptyMessage = dialog.querySelector(".ioa-detail-memo-empty");
    let activeRow = null;

    function parseLocationDetail(text) {
      return String(text || "")
        .split(";")
        .map((part) => part.trim())
        .filter(Boolean)
        .map((part) => {
          const separatorIndex = part.indexOf("=");
          if (separatorIndex <= 0) {
            return null;
          }
          const wloccd = part.slice(0, separatorIndex).trim();
          const remainder = part.slice(separatorIndex + 1).trim();
          const atIndex = remainder.lastIndexOf("@");
          if (atIndex > 0) {
            return {
              wloccd,
              stockQty: remainder.slice(0, atIndex).trim(),
              incomingDate: remainder.slice(atIndex + 1).trim(),
            };
          }
          return {
            wloccd,
            stockQty: remainder,
            incomingDate: "",
          };
        })
        .filter(Boolean)
        .sort((left, right) => {
          const leftDate = left.incomingDate || "\uffff";
          const rightDate = right.incomingDate || "\uffff";
          if (leftDate !== rightDate) {
            return leftDate.localeCompare(rightDate);
          }
          if (left.wloccd !== right.wloccd) {
            return left.wloccd.localeCompare(right.wloccd);
          }
          return String(left.stockQty).localeCompare(String(right.stockQty), undefined, { numeric: true });
        });
    }

    function formatIncomingDate(value) {
      const text = String(value || "").trim();
      if (!text) {
        return "-";
      }
      if (/^\d{8}$/.test(text)) {
        return `${text.slice(0, 4)}/${text.slice(4, 6)}/${text.slice(6, 8)}`;
      }
      return text;
    }

    function formatStockQty(value) {
      const text = String(value || "").trim();
      if (!text) {
        return "-";
      }
      const normalized = text.replace(/,/g, "");
      const number = Number(normalized);
      if (!Number.isFinite(number)) {
        return text;
      }
      return new Intl.NumberFormat("ja-JP", { maximumFractionDigits: 3 }).format(number);
    }

    function renderMemoEntries(memos) {
      if (!memoTableBody || !memoTableWrap || !memoEmptyMessage) {
        return;
      }
      memoTableBody.innerHTML = "";
      if (!memos.length) {
        memoTableWrap.hidden = true;
        memoEmptyMessage.hidden = false;
        return;
      }
      memoTableWrap.hidden = false;
      memoEmptyMessage.hidden = true;
      for (const memo of memos) {
        const tableRow = document.createElement("tr");
        const atCell = document.createElement("td");
        const byCell = document.createElement("td");
        const contentCell = document.createElement("td");
        atCell.textContent = memo.createdAt || "-";
        byCell.textContent = memo.createdBy || "-";
        contentCell.textContent = memo.content || "";
        tableRow.append(atCell, byCell, contentCell);
        memoTableBody.append(tableRow);
      }
    }

    async function loadMemoEntries(row) {
      const custCode = row.dataset.custCode || "";
      const itemCd = row.dataset.itemCd || "";
      if (!custCode || !itemCd) {
        renderMemoEntries([]);
        return;
      }
      const params = new URLSearchParams({ custCode, itemCd });
      const response = await fetch(`${CONFIRMATION_MEMO_API}?${params.toString()}`);
      const payload = await response.json();
      if (!response.ok || !payload.ok) {
        throw new Error(payload.message || "メモの取得に失敗しました。");
      }
      renderMemoEntries(payload.memos || []);
    }

    function setDetailText(element, value) {
      if (element) {
        element.textContent = value;
      }
    }

    // 流動区分の理由（07 REQ-FQR-F-005）。該当がなければ見出しごと隠す。
    function renderFlowReasons(reasons) {
      const list = detailFields.flowReasons;
      const label = detailFields.flowReasonsLabel;
      if (!list) {
        return;
      }
      list.textContent = "";
      const hasReasons = Array.isArray(reasons) && reasons.length > 0;
      for (const reason of hasReasons ? reasons : []) {
        const item = document.createElement("li");
        item.textContent = String(reason);
        list.appendChild(item);
      }
      const hidden = !hasReasons;
      list.hidden = hidden;
      if (list.parentElement) {
        list.parentElement.hidden = hidden;
      }
      if (label) {
        label.hidden = hidden;
      }
    }

    // 日付はローカル時刻から組み立てる。toISOString() は UTC 変換され、JST の深夜〜早朝に
    // 前日・前月へずれるため使わない（design.md §6.7）。
    function pad2(value) {
      return String(value).padStart(2, "0");
    }

    function currentYearMonth(now = new Date()) {
      return `${now.getFullYear()}-${pad2(now.getMonth() + 1)}`;
    }

    function todayIsoDate(now = new Date()) {
      return `${now.getFullYear()}-${pad2(now.getMonth() + 1)}-${pad2(now.getDate())}`;
    }

    // 照合単位の在庫を合算して起点を作る（design.md §6.6）。
    // 該当なし（空）・未取得（－）はいずれも 0 として足すが、全品番が未取得なら算出しない。
    function sumUnitAnchorQty(stocks, fallbackDisplay) {
      const entries = Array.isArray(stocks) && stocks.length
        ? stocks
        : [{ itemCd: "", stockDisplay: String(fallbackDisplay || "") }];
      let total = 0;
      let hasKnown = false;
      entries.forEach((entry) => {
        const qty = parseAnchorQty(entry.stockDisplay);
        if (qty === null) {
          return;
        }
        hasKnown = true;
        total += qty;
      });
      return hasKnown ? total : null;
    }

    // 照合単位が複数の得意先品番を含むときだけ、起点の内訳を出す（単一品番では冗長なため）。
    const ANCHOR_BREAKDOWN_MAX_ITEMS = 5;

    function renderAnchorBreakdown(stocks, anchorQty) {
      if (!anchorBreakdown) {
        return;
      }
      const entries = (Array.isArray(stocks) ? stocks : []).filter(
        (entry) => parseAnchorQty(entry.stockDisplay) !== null,
      );
      if (anchorQty === null || entries.length < 2) {
        anchorBreakdown.hidden = true;
        anchorBreakdown.textContent = "";
        return;
      }
      const shown = entries.slice(0, ANCHOR_BREAKDOWN_MAX_ITEMS);
      const parts = shown.map(
        (entry) => `${entry.itemCd} ${(parseAnchorQty(entry.stockDisplay) || 0).toLocaleString("ja-JP")}`,
      );
      const rest = entries.length - shown.length;
      const restLabel = rest > 0 ? ` ＋ 他${rest}品番` : "";
      anchorBreakdown.textContent =
        `グラフの起点 ${anchorQty.toLocaleString("ja-JP")} = ${parts.join(" ＋ ")}${restLabel}` +
        `（同じ仕入先品番を共有する ${entries.length} 品番の在庫を合算しています）`;
      anchorBreakdown.hidden = false;
    }

    function formatQty(value) {
      const number = Number(value);
      return Number.isFinite(number) ? number.toLocaleString("ja-JP") : String(value ?? "");
    }

    // 需要予測区分。算出できない行（basis なし・旧スナップショット）は項目を隠して案内文だけ出す（REQ-SFV-F-017）。
    function renderDemandForecast(custCode, itemCd, row, stocks) {
      if (!demandFields.fields || !demandFields.empty) {
        return;
      }
      const forecast = listClient?.getDemandForecast?.(custCode, itemCd) || null;
      const trend = listClient?.getUnconfirmedOrderTrend?.(custCode, itemCd) || [];
      const basis = forecast?.basis || row.dataset.demandForecastBasis || "";
      const hasForecast = Boolean(basis) && basis !== "なし";
      demandFields.fields.hidden = !hasForecast;
      demandFields.empty.hidden = hasForecast;
      if (demandFields.unitBreakdown) {
        demandFields.unitBreakdown.hidden = true;
        demandFields.unitBreakdown.textContent = "";
      }
      if (!hasForecast) {
        return;
      }
      const monthly = Array.isArray(trend) && trend.length
        ? trend.map((point) => `${String(point.month || "").replace("-", "/")}: ${formatQty(point.qty)}`).join(" / ")
        : (forecast?.monthly || []).map((qty) => formatQty(qty)).join(" / ");
      setDetailText(demandFields.basis, basis);
      setDetailText(demandFields.monthly, basis === "内示" && monthly ? `${monthly}（先頭は当月残。得意先×内作品番）` : "-");
      setDetailText(demandFields.average, forecast?.monthlyAverage ? `${formatQty(Math.round(forecast.monthlyAverage * 10) / 10)} / 月` : "-");
      const months = forecast?.monthsOfStock ?? row.dataset.monthsOfStock;
      setDetailText(demandFields.monthsOfStock, months === null || months === undefined || months === "" ? "-" : `約 ${months} か月分`);
      const stockout = forecast?.stockoutForecastMonth || row.dataset.stockoutForecastMonth || "";
      setDetailText(demandFields.stockoutMonth, stockout ? stockout : "十分（120 か月以内に尽きません）");
      // 照合単位の在庫内訳（04 §6.6 の renderAnchorBreakdown と同じ規則: 複数品番のときだけ）
      const entries = (Array.isArray(stocks) ? stocks : []).filter((entry) => parseAnchorQty(entry.stockDisplay) !== null);
      if (demandFields.unitBreakdown && entries.length >= 2 && forecast?.stockTotal !== null && forecast?.stockTotal !== undefined) {
        const shown = entries.slice(0, ANCHOR_BREAKDOWN_MAX_ITEMS);
        const parts = shown.map((entry) => `${entry.itemCd} ${(parseAnchorQty(entry.stockDisplay) || 0).toLocaleString("ja-JP")}`);
        const rest = entries.length - shown.length;
        demandFields.unitBreakdown.textContent =
          `在庫月数の分子（照合単位の在庫合計） ${formatQty(forecast.stockTotal)} = ${parts.join(" ＋ ")}${rest > 0 ? ` ＋ 他${rest}品番` : ""}`;
        demandFields.unitBreakdown.hidden = false;
      }
    }

    // 5年9組の検索結果ページへのリンクを組み立てる。設変値（optionChange）は渡さず、
    // 5年9組側の既定「*」に委ねる（在庫発注アラートは設変値を持たない）。
    function updateGonenLink(custCode, itemCd) {
      if (!gonenLink) {
        return;
      }
      // 5年9組は得意先コード・得意先品番の両方を検索条件に要するため、欠けていたら隠す。
      const canSearch = Boolean(custCode && itemCd);
      if (gonenLinkRow) {
        gonenLinkRow.hidden = !canSearch;
      }
      if (!canSearch) {
        gonenLink.removeAttribute("href");
        return;
      }
      const params = new URLSearchParams({
        custCode,
        custItem: itemCd,
        yearMonth: currentYearMonth(),
        asOfDate: todayIsoDate(),
      });
      gonenLink.href = `${GONEN_RESULT_PATH}?${params.toString()}`;
    }

    // 在庫数の 3 状態（値あり / 該当なし / 未取得）で起点を分ける（design.md §6.6）。
    // 該当なし（空文字。SLIMS 取込済みだが SLIMS に品番が無い）は 0 を起点として履歴を描く。
    // 未取得（"－"。SLIMS 未取込・旧スナップショット）は SLIMS を見られていない状態なので、
    // 在庫ゼロと描いてはならず null を返してグラフを出さない。
    function parseAnchorQty(text) {
      const trimmed = String(text || "").trim();
      if (!trimmed) {
        return 0;
      }
      const normalized = trimmed.replace(/,/g, "");
      const number = Number(normalized);
      return Number.isFinite(number) ? number : null;
    }

    function buildAnchoredStockTrend(shipmentTrend, incomingTrend, anchorQty) {
      if (anchorQty === null || !Array.isArray(shipmentTrend) || !shipmentTrend.length) {
        return [];
      }
      const length = shipmentTrend.length;
      const result = new Array(length);
      result[length - 1] = { month: shipmentTrend[length - 1].month, qty: anchorQty };
      for (let index = length - 2; index >= 0; index -= 1) {
        const nextShipped = Number(shipmentTrend[index + 1]?.qty) || 0;
        const nextReceived = Number(incomingTrend[index + 1]?.qty) || 0;
        result[index] = {
          month: shipmentTrend[index].month,
          qty: result[index + 1].qty + nextShipped - nextReceived,
        };
      }
      return result;
    }

    // 月キー "YYYY-MM" に months か月を足す。
    function addMonthsToKey(monthKey, months) {
      const [year, month] = String(monthKey || "").split("-").map((part) => Number(part));
      if (!Number.isFinite(year) || !Number.isFinite(month)) {
        return "";
      }
      const total = year * 12 + (month - 1) + months;
      return `${Math.floor(total / 12)}-${String((total % 12) + 1).padStart(2, "0")}`;
    }

    // 予定入荷（完成品直下の工程の発注残）を納期の月で束ねる。納期超過・納期未定は当月扱い（06 design §6.4a）。
    function plannedIncomingByMonth(processChain, currentMonth) {
      const stage = Array.isArray(processChain) && processChain.length ? processChain[0] : null;
      const orders = stage && Array.isArray(stage.openOrders) ? stage.openOrders : [];
      const byMonth = {};
      orders.forEach((order) => {
        const qty = Number(order.remainingQty) || 0;
        if (qty <= 0) {
          return;
        }
        let key = String(order.dueDate || "").slice(0, 7).replace("/", "-");
        if (!/^\d{4}-\d{2}$/.test(key) || key < currentMonth) {
          key = currentMonth;
        }
        byMonth[key] = (byMonth[key] || 0) + qty;
      });
      return byMonth;
    }

    // 予測在庫（V-218 予測部分）: 現在の在庫から 当月残 と 翌月〜翌々々月の需要 を引き、予定入荷を足した 3 点。
    // 需要は需要予測（照合単位の合計。サーバの在庫切れ予測月と同じ根拠）。
    // 起点の在庫が単位合計なので、行単位の内示推移は使わない。需要なし・在庫未取得は空（06 design §6.4a、2026/09/18 改訂）。
    // 算出根拠は「内示」のみ（07 REQ-FQR-F-002。「なし」と廃止済みの旧根拠は描かない）。
    function buildForecastStockTrend(anchorQty, currentMonth, forecast, processChain) {
      if (anchorQty === null || !forecast || forecast.basis !== "内示" || !currentMonth) {
        return [];
      }
      const monthly = Array.isArray(forecast.monthly) ? forecast.monthly : [];
      const demandFor = (offset) => {
        if (offset === 0) {
          return Number(forecast.currentMonthRemaining) || 0;
        }
        return Number(monthly[offset - 1]) || 0;
      };
      const planned = plannedIncomingByMonth(processChain, currentMonth);
      let qty = Number(anchorQty) - demandFor(0) + (planned[currentMonth] || 0);
      const points = [];
      for (let offset = 1; offset <= 3; offset += 1) {
        const month = addMonthsToKey(currentMonth, offset);
        qty = qty - demandFor(offset) + (planned[month] || 0);
        points.push({ month, qty: Math.round(qty), planned: planned[month] || 0, demand: demandFor(offset) });
      }
      return points;
    }

    // 目盛り間隔の候補 1・2・5 × 10^n から、rawStep 以上で最小のものを返す（0 を基準にした丸い目盛りを作るため）。
    // 数量は整数なので間隔の下限は 1（0.5 刻みだとラベルが丸めで重複する）。
    function niceGridStep(rawStep) {
      const step = Math.max(1, Number(rawStep) || 0);
      const magnitude = Math.pow(10, Math.floor(Math.log10(step)));
      const normalized = step / magnitude;
      const factor = normalized <= 1 ? 1 : normalized <= 2 ? 2 : normalized <= 5 ? 5 : 10;
      return factor * magnitude;
    }

    function renderAnchoredStockChart(sectionEl, slimsSeries, incomingSeries, forecastSeries, stockoutMonth) {
      if (!sectionEl) {
        return;
      }
      const container = sectionEl.querySelector(".ioa-detail-anchored-stock-trend-chart");
      const emptyMessage = sectionEl.querySelector(".ioa-detail-anchored-stock-trend-empty");
      if (!container) {
        return;
      }

      const slims = Array.isArray(slimsSeries) ? slimsSeries : [];
      const incoming = Array.isArray(incomingSeries) ? incomingSeries : [];
      const forecast = Array.isArray(forecastSeries) ? forecastSeries : [];
      container.innerHTML = "";
      if (!slims.length) {
        container.hidden = true;
        if (emptyMessage) {
          emptyMessage.hidden = false;
        }
        return;
      }
      container.hidden = false;
      if (emptyMessage) {
        emptyMessage.hidden = true;
      }

      // 横軸は 実績 24 か月 ＋ 予測 3 か月（予測がなければ実績のみ）。
      const points = slims.concat(forecast);
      const width = 560;
      const height = 140;
      const paddingLeft = 44;
      const paddingTop = 8;
      const paddingBottom = 20;
      const plotWidth = width - paddingLeft - 8;
      const plotHeight = height - paddingTop - paddingBottom;
      // マイナスもそのまま表示するため、0 を必ず範囲に含めてゼロ基準線を描けるようにする（design.md §6.6）。
      // 入荷の棒が切れないよう、値域には入荷数量も算入する（design.md §6.6）。
      const incomingQtys = incoming.slice(0, slims.length).map((point) => Number(point?.qty) || 0);
      const plannedQtys = forecast.map((point) => Number(point?.planned) || 0);
      const rawMinQty = Math.min(0, ...points.map((point) => Number(point.qty) || 0), ...incomingQtys);
      const rawMaxQty = Math.max(1, ...points.map((point) => Number(point.qty) || 0), ...incomingQtys, ...plannedQtys);
      // 目盛りは 0 を基準に丸い間隔（1・2・5 × 10^n）で刻む。軸の下限・上限を間隔の倍数に丸めることで、
      // 0 が必ず目盛り線に乗る（2026/09/18。単純な等分では 0 が目盛りの途中に来て基準線とラベルがずれていた）。
      const GRID_LINE_COUNT = 4;
      const gridStep = niceGridStep((rawMaxQty - rawMinQty) / GRID_LINE_COUNT);
      const minQty = Math.floor(rawMinQty / gridStep) * gridStep;
      const maxQty = Math.ceil(rawMaxQty / gridStep) * gridStep;
      const valueRange = maxQty - minQty || 1;
      const stepX = points.length > 1 ? plotWidth / (points.length - 1) : 0;

      function coordsOf(index, qty) {
        const x = paddingLeft + stepX * index;
        const y = paddingTop + plotHeight - ((Number(qty) - minQty) / valueRange) * plotHeight;
        return [x, y];
      }

      const svgNs = "http://www.w3.org/2000/svg";
      const svg = document.createElementNS(svgNs, "svg");
      svg.setAttribute("viewBox", `0 0 ${width} ${height}`);
      svg.setAttribute("class", "ioa-anchored-stock-trend-svg");
      svg.setAttribute("role", "img");
      svg.setAttribute("aria-label", "推定在庫推移（参考値）と入荷実績");

      // Excel風に、等間隔の目盛り線を描画する。間隔は gridStep（丸い値）、下限〜上限はその倍数なので 0 も目盛りに含まれる。
      // 本数は概ね GRID_LINE_COUNT+1 本（丸めにより 1〜2 本増えることがある）。
      const gridLineTotal = Math.round(valueRange / gridStep);
      for (let gridIndex = 0; gridIndex <= gridLineTotal; gridIndex += 1) {
        const gridQty = minQty + gridStep * gridIndex;
        const [, gridY] = coordsOf(0, gridQty);

        const gridLine = document.createElementNS(svgNs, "line");
        gridLine.setAttribute("x1", String(paddingLeft));
        gridLine.setAttribute("x2", String(width - 8));
        gridLine.setAttribute("y1", String(gridY));
        gridLine.setAttribute("y2", String(gridY));
        gridLine.setAttribute("class", "ioa-anchored-stock-trend-grid-line");
        svg.append(gridLine);

        const gridLabel = document.createElementNS(svgNs, "text");
        gridLabel.setAttribute("x", String(paddingLeft - 4));
        gridLabel.setAttribute("y", String(gridY + 3));
        gridLabel.style.textAnchor = "end";
        gridLabel.setAttribute("class", "ioa-anchored-stock-trend-y-axis-label");
        gridLabel.textContent = Math.round(gridQty).toLocaleString("ja-JP");
        svg.append(gridLabel);
      }

      // 0 が目盛り線の途中に来る場合（マイナス域あり）は、危険水準として破線で強調する。
      // 全点0以上（minQty===0）の場合は最下段の目盛り線が既に0を示しているため重ねて描かない。
      if (minQty < 0) {
        const [, zeroY] = coordsOf(0, 0);
        const zeroLine = document.createElementNS(svgNs, "line");
        zeroLine.setAttribute("x1", String(paddingLeft));
        zeroLine.setAttribute("x2", String(width - 8));
        zeroLine.setAttribute("y1", String(zeroY));
        zeroLine.setAttribute("y2", String(zeroY));
        zeroLine.setAttribute("class", "ioa-anchored-stock-trend-zero-line");
        svg.append(zeroLine);
      }

      // 入荷実績（V-217）の棒。推定在庫の折れ線と同一のY軸に、ゼロ基準から上方向に描く。
      // 折れ線を隠さないよう drawSeries より先に（=背面に）描画する（design.md §6.6）。
      function drawIncomingBars(seriesPoints) {
        if (!seriesPoints.length) {
          return;
        }
        const barWidth = stepX > 0 ? stepX * 0.5 : plotWidth * 0.5;
        const [, zeroY] = coordsOf(0, 0);
        seriesPoints.forEach((point, index) => {
          if (index >= points.length) {
            return;
          }
          const qty = Number(point?.qty) || 0;
          if (qty === 0) {
            return;
          }
          const [centerX, valueY] = coordsOf(index, qty);
          const rect = document.createElementNS(svgNs, "rect");
          rect.setAttribute("x", String(centerX - barWidth / 2));
          rect.setAttribute("y", String(Math.min(zeroY, valueY)));
          rect.setAttribute("width", String(barWidth));
          rect.setAttribute("height", String(Math.abs(zeroY - valueY)));
          rect.setAttribute("class", "ioa-anchored-stock-trend-bar ioa-anchored-stock-trend-bar--incoming");
          const title = document.createElementNS(svgNs, "title");
          title.textContent = `入荷(MARI) ${point.month}: ${qty}`;
          rect.append(title);
          svg.append(rect);
        });
      }

      function drawSeries(seriesPoints, lineClass, pointClass, label) {
        if (!seriesPoints.length) {
          return;
        }
        const linePoints = seriesPoints.map((point, index) => coordsOf(index, point.qty).join(",")).join(" ");
        const polyline = document.createElementNS(svgNs, "polyline");
        polyline.setAttribute("points", linePoints);
        polyline.setAttribute("class", lineClass);
        svg.append(polyline);

        seriesPoints.forEach((point, index) => {
          const [x, y] = coordsOf(index, point.qty);
          const circle = document.createElementNS(svgNs, "circle");
          circle.setAttribute("cx", String(x));
          circle.setAttribute("cy", String(y));
          circle.setAttribute("r", "2");
          circle.setAttribute("class", pointClass);
          const title = document.createElementNS(svgNs, "title");
          title.textContent = `${label} ${point.month}: ${point.qty}`;
          circle.append(title);
          svg.append(circle);
        });
      }

      // 予定入荷（発注残）の棒。予測月の位置に薄く描く（06 design §6.4a）。
      function drawPlannedBars(forecastPoints) {
        const barWidth = stepX > 0 ? stepX * 0.5 : plotWidth * 0.5;
        const [, zeroY] = coordsOf(0, 0);
        forecastPoints.forEach((point, offset) => {
          const qty = Number(point?.planned) || 0;
          if (qty <= 0) {
            return;
          }
          const index = slims.length + offset;
          const [centerX, valueY] = coordsOf(index, qty);
          const rect = document.createElementNS(svgNs, "rect");
          rect.setAttribute("x", String(centerX - barWidth / 2));
          rect.setAttribute("y", String(Math.min(zeroY, valueY)));
          rect.setAttribute("width", String(barWidth));
          rect.setAttribute("height", String(Math.abs(zeroY - valueY)));
          rect.setAttribute("class", "ioa-anchored-stock-trend-bar ioa-anchored-stock-trend-bar--planned");
          const title = document.createElementNS(svgNs, "title");
          title.textContent = `予定入荷(発注残) ${point.month}: ${qty}`;
          rect.append(title);
          svg.append(rect);
        });
      }

      // 予測在庫の点線。実績の最終点（現在の在庫）から右へ延ばす。
      function drawForecastSeries(forecastPoints) {
        if (!forecastPoints.length || !slims.length) {
          return;
        }
        const lastActual = slims[slims.length - 1];
        const linePoints = [coordsOf(slims.length - 1, lastActual.qty).join(",")]
          .concat(forecastPoints.map((point, offset) => coordsOf(slims.length + offset, point.qty).join(",")))
          .join(" ");
        const polyline = document.createElementNS(svgNs, "polyline");
        polyline.setAttribute("points", linePoints);
        polyline.setAttribute("class", "ioa-anchored-stock-trend-line ioa-anchored-stock-trend-line--forecast");
        polyline.style.strokeDasharray = "4 3";
        svg.append(polyline);
        forecastPoints.forEach((point, offset) => {
          const [x, y] = coordsOf(slims.length + offset, point.qty);
          const circle = document.createElementNS(svgNs, "circle");
          circle.setAttribute("cx", String(x));
          circle.setAttribute("cy", String(y));
          circle.setAttribute("r", "2");
          circle.setAttribute("class", "ioa-anchored-stock-trend-point ioa-anchored-stock-trend-point--forecast");
          const title = document.createElementNS(svgNs, "title");
          title.textContent = `予測在庫 ${point.month}: ${point.qty}（需要 ${point.demand}、予定入荷 ${point.planned}）`;
          circle.append(title);
          svg.append(circle);
        });
        // 現在（実績と予測の境）の縦線
        const [nowX] = coordsOf(slims.length - 1, 0);
        const nowLine = document.createElementNS(svgNs, "line");
        nowLine.setAttribute("x1", String(nowX));
        nowLine.setAttribute("x2", String(nowX));
        nowLine.setAttribute("y1", String(paddingTop));
        nowLine.setAttribute("y2", String(paddingTop + plotHeight));
        nowLine.setAttribute("class", "ioa-anchored-stock-trend-now-line");
        svg.append(nowLine);
      }

      // 在庫切れ予測月（V-221）が描画範囲内なら縦の破線とラベル。
      function drawStockoutMarker(month) {
        if (!month) {
          return;
        }
        const index = points.findIndex((point) => point.month === month);
        if (index < 0) {
          return;
        }
        const [x] = coordsOf(index, 0);
        const marker = document.createElementNS(svgNs, "line");
        marker.setAttribute("x1", String(x));
        marker.setAttribute("x2", String(x));
        marker.setAttribute("y1", String(paddingTop));
        marker.setAttribute("y2", String(paddingTop + plotHeight));
        marker.setAttribute("class", "ioa-anchored-stock-trend-stockout-line");
        svg.append(marker);
        const label = document.createElementNS(svgNs, "text");
        label.setAttribute("x", String(Math.min(x + 3, width - 60)));
        label.setAttribute("y", String(paddingTop + 10));
        label.setAttribute("class", "ioa-anchored-stock-trend-stockout-label");
        label.textContent = "在庫切れ予測";
        svg.append(label);
      }

      drawIncomingBars(incoming);
      drawPlannedBars(forecast);
      drawSeries(slims, "ioa-anchored-stock-trend-line ioa-anchored-stock-trend-line--slims", "ioa-anchored-stock-trend-point ioa-anchored-stock-trend-point--slims", "SLIMS起点");
      drawForecastSeries(forecast);
      drawStockoutMarker(stockoutMonth);

      points.forEach((point, index) => {
        if (index % 4 === 0 || index === points.length - 1) {
          const [x] = coordsOf(index, minQty);
          const label = document.createElementNS(svgNs, "text");
          label.setAttribute("x", String(x));
          label.setAttribute("y", String(height - 4));
          label.setAttribute("class", "ioa-anchored-stock-trend-axis-label");
          // text-anchor は setAttribute だと CSS クラス（text-anchor: middle）に負けて
          // 上書きされないため、優先度の高いインライン style で個別上書きする。
          if (index === 0) {
            label.style.textAnchor = "start";
          } else if (index === points.length - 1) {
            label.style.textAnchor = "end";
          }
          label.textContent = String(point.month || "").slice(2).replace("-", "/");
          svg.append(label);
        }
      });

      container.append(svg);

      const legend = document.createElement("div");
      legend.className = "ioa-anchored-stock-trend-legend";
      legend.innerHTML =
        '<span class="ioa-anchored-stock-trend-legend-item ioa-anchored-stock-trend-legend-item--slims">推定在庫(SLIMS起点)</span>' +
        '<span class="ioa-anchored-stock-trend-legend-item ioa-anchored-stock-trend-legend-item--incoming">入荷(MARI)</span>' +
        (forecast.length
          ? '<span class="ioa-anchored-stock-trend-legend-item ioa-anchored-stock-trend-legend-item--forecast">予測在庫(内示・発注残)</span>' +
            '<span class="ioa-anchored-stock-trend-legend-item ioa-anchored-stock-trend-legend-item--planned">予定入荷(発注残)</span>'
          : "");
      container.append(legend);
    }

    function fillDetailSections(row) {
      const custCode = row.dataset.custCode || "";
      const custName = row.dataset.custName || "";
      const vendCd = row.dataset.level1VendCd || "";
      const vendName = row.dataset.level1VendName || "";
      const quadrantKey = row.dataset.flowQuadrant || "";
      const quadrantLabel = listClient?.getFlowQuadrantLabel?.(quadrantKey) || "";

      setDetailText(detailFields.cust, custName ? `${custCode} - ${custName}` : custCode || "-");
      setDetailText(detailFields.itemCd, row.dataset.itemCd || "-");
      setDetailText(detailFields.vend, vendName ? `${vendCd} - ${vendName}` : vendCd || "-");
      setDetailText(detailFields.level1ItemCd, row.dataset.level1ItemCd || "-");
      setDetailText(detailFields.lastIncoming, row.dataset.lastIncomingDate || "-");
      setDetailText(detailFields.lastShip, row.dataset.lastShipDate || "-");
      // 入荷実績なしの注記は出さない（最終入荷日が空欄で分かる。状況の文言には「入荷実績なし」が入る）。
      setDetailText(detailFields.flowQuadrant, quadrantLabel || "-");
      // 状況・推奨アクションは選択中の判定期間で描いた値。listClient がなければ行の data-* を使う（05 design §6.4）。
      const flowStatus =
        listClient?.getFlowStatus?.(custCode, row.dataset.itemCd || "", quadrantKey) ?? row.dataset.flowStatus ?? "";
      const recommendedAction =
        listClient?.getRecommendedAction?.(quadrantKey) ?? row.dataset.recommendedAction ?? "";
      setDetailText(detailFields.flowStatus, flowStatus || "-");
      // 理由（07 REQ-FQR-F-005）は箇条書き。該当がない行では見出しごと隠す。
      // 判定期間で変わるため、listClient が選択中の期間で引き直す（07 design §1-6）
      const flowReasons = listClient?.getFlowReasons?.(custCode, row.dataset.itemCd || "") || [];
      renderFlowReasons(flowReasons);
      setDetailText(detailFields.recommendedAction, recommendedAction || "-");
      setDetailText(
        detailFields.department,
        listClient?.getResponsibleDepartment?.(quadrantKey) || row.dataset.responsibleDepartment || "-",
      );
      setDetailText(detailFields.evaluationPeriod, listClient?.getEvaluationPeriodLabel?.() || "-");
      // 在庫数は一覧と同じ表示文字列をそのまま出す（未取得の「－」と 0 を取り違えないため）。
      setDetailText(detailFields.stockSlims, row.dataset.stockQty || "-");
      setDetailText(detailFields.stockMari, row.dataset.mariStockQty || "-");
      // 出荷推移(V-216)は独立したグラフとしては表示せず、推定在庫推移(V-218)の算出のみに用いる。
      // 入荷推移(V-217)は算出材料に加えて、推定在庫推移グラフに棒として重ねて表示する
      // （2026-09-11、DECISIONS.md ステージ12参照）。
      // 推定在庫推移は「照合単位」（内作品番×仕入先を共有する得意先品番の集合）で逆算する。
      // 在庫・出荷・入荷の粒度が異なるため、この単位まで広げないと数量が閉じない
      // （DECISIONS.md ステージ14・15参照）。
      const itemTrends = listClient?.getItemTrends?.(row.dataset.itemCd || "") || {};
      const shipmentTrend = itemTrends.shipmentTrend || [];
      const incomingTrend = itemTrends.incomingTrend || [];

      const slimsAnchor = sumUnitAnchorQty(itemTrends.stocks, row.dataset.stockQty);
      const slimsAnchoredTrend = buildAnchoredStockTrend(shipmentTrend, incomingTrend, slimsAnchor);
      // 予測部分（点線）: 需要予測・内示推移・工程の連鎖（発注残）は listClient から引く（06 design §6.4a）。
      const forecastInfo = listClient?.getDemandForecast?.(custCode, row.dataset.itemCd || "") || null;
      const riskInfo = listClient?.getStockoutRisk?.(custCode, row.dataset.itemCd || "") || null;
      const currentMonth = slimsAnchoredTrend.length ? String(slimsAnchoredTrend[slimsAnchoredTrend.length - 1].month || "") : "";
      const forecastTrend = buildForecastStockTrend(slimsAnchor, currentMonth, forecastInfo, riskInfo ? riskInfo.processChain : []);
      renderAnchoredStockChart(anchoredStockTrendSection, slimsAnchoredTrend, incomingTrend, forecastTrend, forecastInfo?.stockoutForecastMonth || "");
      renderAnchorBreakdown(itemTrends.stocks, slimsAnchor);
      renderDemandForecast(custCode, row.dataset.itemCd || "", row, itemTrends.stocks);
      renderStockoutRisk(custCode, row.dataset.itemCd || "", row);
      updateGonenLink(custCode, row.dataset.itemCd || "");
    }

    async function openLocationDialog(row) {
      if (!locationTableBody || !tableWrap || !emptyMessage || !asOfLabel || !memoInput) {
        return;
      }

      activeRow = row;
      memoInput.value = "";

      document.querySelectorAll(`${ROW_SELECTOR}.is-selected`).forEach((selectedRow) => {
        selectedRow.classList.remove("is-selected");
      });
      row.classList.add("is-selected");

      fillDetailSections(row);

      const locations = parseLocationDetail(row.dataset.stockLocationDetail || "");
      locationTableBody.innerHTML = "";
      if (locations.length) {
        tableWrap.hidden = false;
        emptyMessage.hidden = true;
        for (const location of locations) {
          const tableRow = document.createElement("tr");
          tableRow.innerHTML = `
            <td>${formatIncomingDate(location.incomingDate)}</td>
            <td class="mono">${location.wloccd}</td>
            <td class="ioa-location-qty">${formatStockQty(location.stockQty)}</td>
          `;
          locationTableBody.append(tableRow);
        }
      } else {
        tableWrap.hidden = true;
        emptyMessage.hidden = false;
      }

      const label = row.dataset.stockAsOfLabel || "";
      asOfLabel.textContent = label ? `${label}（SLIMS 在庫 CSV 取込時点）` : "";

      if (typeof dialog.showModal === "function") {
        dialog.showModal();
      }

      try {
        await loadMemoEntries(row);
      } catch (error) {
        renderMemoEntries([]);
        window.alert(error.message || "メモの取得に失敗しました。");
      }
    }

    closeButton?.addEventListener("click", () => {
      dialog.close();
    });

    saveButton?.addEventListener("click", async () => {
      if (!activeRow || !memoInput) {
        return;
      }
      const content = memoInput.value.trim().slice(0, MAX_MEMO_LENGTH);
      if (!content) {
        window.alert("メモ内容を入力してください。");
        return;
      }
      saveButton.disabled = true;
      try {
        const response = await fetch(CONFIRMATION_MEMO_API, {
          method: "POST",
          headers: {
            "Content-Type": "application/json",
            "X-CSRFToken": getCsrfToken(),
          },
          body: JSON.stringify({
            custCode: activeRow.dataset.custCode || "",
            itemCd: activeRow.dataset.itemCd || "",
            content,
          }),
        });
        const payload = await response.json();
        if (!response.ok || !payload.ok) {
          throw new Error(payload.message || "メモの保存に失敗しました。");
        }
        memoInput.value = "";
        await loadMemoEntries(activeRow);
      } catch (error) {
        window.alert(error.message || "メモの保存に失敗しました。");
      } finally {
        saveButton.disabled = false;
      }
    });

    dialog.addEventListener("click", (event) => {
      if (event.target === dialog) {
        dialog.close();
      }
    });

    dialog.addEventListener("close", () => {
      activeRow = null;
      if (memoInput) {
        memoInput.value = "";
      }
      renderMemoEntries([]);
      document.querySelectorAll(`${ROW_SELECTOR}.is-selected`).forEach((selectedRow) => {
        selectedRow.classList.remove("is-selected");
      });
    });

    listTableBody.addEventListener("click", (event) => {
      const row = event.target.closest(ROW_SELECTOR);
      if (!row) {
        return;
      }
      if (event.target.closest("select, option, button, a, label, textarea")) {
        return;
      }
      void openLocationDialog(row);
    });
  }

  function initAlertRulesDialog() {
    // 判定ルールダイアログは読み取り専用の凡例。開閉のみを担う（design.md §6.6.5）。
    const dialog = document.getElementById("ioa-alert-rules-dialog");
    // 開くボタンは複数箇所に置かれうるため全件に結線する。
    // querySelector 単数だと 2 個目以降が無反応になる。
    const openButtons = document.querySelectorAll(".inventory-order-alert-page .ioa-alert-rules-open");
    const closeButton = dialog?.querySelector(".ioa-alert-rules-close");
    if (!dialog || !openButtons.length || !closeButton) {
      return;
    }

    openButtons.forEach((openButton) => {
      openButton.addEventListener("click", () => {
        if (typeof dialog.showModal === "function") {
          dialog.showModal();
        }
      });
    });

    closeButton.addEventListener("click", () => {
      dialog.close();
    });

    dialog.addEventListener("click", (event) => {
      if (event.target === dialog) {
        dialog.close();
      }
    });
  }

  function initInventoryOrderAlertPage() {
    const listClient = window.IoaListClient?.init?.() || null;
    initSlimsImport();
    initSortDialog(listClient);
    initAlertRulesDialog();
    initLocationDialog(listClient);
    initConfirmationStatusSelects(listClient);
  }

  document.addEventListener("DOMContentLoaded", initInventoryOrderAlertPage);
})();

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
  const RESPONSE_CLASS_LABEL_BY_KEY = {
    "order-overdue": "発注遅れ",
    "delivery-check": "納期確認",
    "order-needed": "要発注",
    watch: "要監視",
    none: "対象外",
  };

  function updateTableCounts(counts) {
    const countsElement = document.querySelector(".inventory-order-alert-page .ioa-table-counts");
    if (!countsElement || !counts) {
      return;
    }
    const left = countsElement.querySelector(".ioa-table-counts-left");
    const right = countsElement.querySelector(".ioa-table-counts-right");
    if (left) {
      left.textContent =
        `発注遅れ ${counts.orderOverdue ?? 0} 件 / 納期確認 ${counts.deliveryCheck ?? 0} 件 / 要発注 ${counts.orderNeeded ?? 0} 件 / 要監視 ${counts.watch ?? 0} 件 / 対象外 ${counts.noneResponse ?? 0} 件`;
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

    // 詳細ダイアログの「品番情報」区分。値は行の data-* 属性から流し込む（§6.3.1）。
    // 流動区分（区分名 / 状況 / 理由 / 判定期間）は 2026-09-30 に撤去した（10 REQ-DDC-F-008）。
    // 一覧の列・絞り込み・件数サマリには残っている。
    const detailFields = {
        cust: dialog.querySelector(".ioa-detail-item-cust"),
        itemCd: dialog.querySelector(".ioa-detail-item-cd"),
        vend: dialog.querySelector(".ioa-detail-item-vend"),
        level1ItemCd: dialog.querySelector(".ioa-detail-item-level1-cd"),
        lastIncoming: dialog.querySelector(".ioa-detail-item-last-incoming"),
        lastShip: dialog.querySelector(".ioa-detail-item-last-ship"),
        stockSlims: dialog.querySelector(".ioa-detail-stock-slims"),
        stockMari: dialog.querySelector(".ioa-detail-stock-mari"),
    };
    const anchoredStockTrendSection = dialog.querySelector(".ioa-detail-anchored-stock-trend-section");
    const stockSimulationSection = dialog.querySelector(".ioa-detail-stock-simulation-section");
    const anchorBreakdown = dialog.querySelector(".ioa-detail-anchor-breakdown");
    // 判定サマリ（T-211）区分（10 design §3.2）。文言は domain が組み立てたものを差し込むだけ。
    const assessmentFields = {
      headline: dialog.querySelector(".ioa-detail-assessment-headline"),
      responseClass: dialog.querySelector(".ioa-detail-assessment-class"),
      deadline: dialog.querySelector(".ioa-detail-assessment-deadline"),
      deadlineLabel: dialog.querySelector(".ioa-detail-assessment-deadline-label"),
      nextAction: dialog.querySelector(".ioa-detail-assessment-next-action"),
      reasons: dialog.querySelector(".ioa-detail-assessment-reasons"),
      reasonsLabel: dialog.querySelector(".ioa-detail-assessment-reasons-label"),
    };
    // 在庫と発注残の区分（10 REQ-DDC-F-002）。判定に使った数字をまとめる。
    const riskFields = {
      overdueOrders: dialog.querySelector(".ioa-detail-overdue-orders"),
      plannedIncoming: dialog.querySelector(".ioa-detail-planned-incoming"),
      safetyStock: dialog.querySelector(".ioa-detail-safety-stock"),
      leadTime: dialog.querySelector(".ioa-detail-stockout-lead-time"),
      orderingMethod: dialog.querySelector(".ioa-detail-stockout-ordering-method"),
      monthlyDemand: dialog.querySelector(".ioa-detail-demand-monthly"),
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

    // 判定サマリ（T-211）。**文言はサーバが組み立てたものを差し込むだけ**（10 REQ-DDC-NF-003）。
    // JS 側で結論の文を組み立てない。判定と言い回しを domain に 1 か所で保つため。
    function renderAssessment(custCode, itemCd) {
      const info = listClient?.getResponseClass?.(custCode, itemCd);
      const summary = info?.summary;
      if (!assessmentFields.headline) {
        return;
      }
      setDetailText(assessmentFields.headline, summary?.headline || "-");
      assessmentFields.headline.className = `ioa-detail-assessment-headline ioa-detail-assessment-headline--${info?.key || "none"}`;
      setDetailText(assessmentFields.responseClass, info?.responseClass || "-");
      if (assessmentFields.responseClass) {
        assessmentFields.responseClass.className = `ioa-detail-assessment-class ioa-response-class ioa-response-class--${info?.key || "none"}`;
      }
      setDetailText(assessmentFields.nextAction, summary?.nextAction || "-");

      // 発注期限は在庫が切れる行にだけ意味がある。無ければ行ごと隠す
      const deadlineText = summary?.deadlineText || "";
      setDetailText(assessmentFields.deadline, deadlineText);
      if (assessmentFields.deadlineLabel) {
        assessmentFields.deadlineLabel.hidden = !deadlineText;
      }
      if (assessmentFields.deadline) {
        assessmentFields.deadline.hidden = !deadlineText;
      }

      const reasons = Array.isArray(summary?.reasons) ? summary.reasons : [];
      if (assessmentFields.reasons) {
        assessmentFields.reasons.innerHTML = reasons.map((reason) => `<li>${escapeHtml(reason)}</li>`).join("");
      }
      if (assessmentFields.reasonsLabel) {
        assessmentFields.reasonsLabel.hidden = !reasons.length;
      }
      if (assessmentFields.reasons) {
        assessmentFields.reasons.parentElement.hidden = !reasons.length;
      }
    }

    // 在庫と発注残（判定に使った数字）。
    function renderStockAndOrders(custCode, itemCd) {
      const info = listClient?.getResponseClass?.(custCode, itemCd);
      if (!info) {
        return;
      }
      // 予定入荷は納期の日に届くもの。納期遅れは在庫の計算に入れていない（REQ-SRR-F-002）
      const planned = Array.isArray(info.simulation?.plannedIncoming) ? info.simulation.plannedIncoming : [];
      const plannedTotal = planned.reduce((total, point) => total + (Number(point.qty) || 0), 0);
      setDetailText(
        riskFields.plannedIncoming,
        plannedTotal > 0
          ? `${formatQty(plannedTotal)}（${planned.map((point) => `${point.date.slice(5).replace("-", "/")} に ${formatQty(point.qty)}`).join("、")}）`
          : "なし",
      );
      setDetailText(
        riskFields.overdueOrders,
        info.overdueOrderQty > 0
          ? `${formatQty(info.overdueOrderQty)}（${info.overdueOrderCount} 件）— 在庫の計算に入れていません`
          : "なし",
      );
      setDetailText(
        riskFields.safetyStock,
        info.safetyStock > 0
          ? `${formatQty(info.safetyStock)}${info.belowSafetyStock ? " — 期間内に下回ります" : ""}`
          : "未設定",
      );
      setDetailText(
        riskFields.leadTime,
        info.leadTimeDays === null || info.leadTimeDays === undefined ? "-" : `${info.leadTimeDays} 日${info.leadTimeSource === "default" ? "（既定値）" : ""}`,
      );
      setDetailText(riskFields.orderingMethod, info.orderingMethod || "-");
      renderProcessChain(info.processChain);
    }

    // 客先の出荷予定（月別）。旧「需要予測」区分から材料だけを引き継いだ（10 REQ-DDC-F-003）。
    function renderMonthlyDemand(custCode, itemCd) {
      if (!riskFields.monthlyDemand) {
        return;
      }
      const forecast = listClient?.getDemandForecast?.(custCode, itemCd);
      const monthly = Array.isArray(forecast?.monthly) ? forecast.monthly : [];
      const hasDemand = forecast?.basis === "内示" && monthly.some((qty) => Number(qty) > 0);
      setDetailText(
        riskFields.monthlyDemand,
        hasDemand
          ? `当月残 ${formatQty(forecast.currentMonthRemaining || 0)} / ${monthly.map((qty) => formatQty(qty)).join(" / ")}（翌月〜翌々々月）`
          : "なし",
      );
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

    // 目盛り間隔の候補 1・2・5 × 10^n から、rawStep 以上で最小のものを返す（0 を基準にした丸い目盛りを作るため）。
    // 数量は整数なので間隔の下限は 1（0.5 刻みだとラベルが丸めで重複する）。
    function niceGridStep(rawStep) {
      const step = Math.max(1, Number(rawStep) || 0);
      const magnitude = Math.pow(10, Math.floor(Math.log10(step)));
      const normalized = step / magnitude;
      const factor = normalized <= 1 ? 1 : normalized <= 2 ? 2 : normalized <= 5 ? 5 : 10;
      return factor * magnitude;
    }

    // ---- 在庫シミュレーション（V-237。09 design §5.3）----
    // サーバが配信する日次の値を**累積するだけ**。重複除去・工程の絞り込み・在庫切れ日の算出は
    // すべてサーバ（domain/value_objects/stock_simulation.py）で済んでいる。判定を JS に持ち込まない。

    function parseIsoDate(text) {
      const match = /^(\d{4})-(\d{2})-(\d{2})$/.exec(String(text || "").trim());
      return match ? new Date(Number(match[1]), Number(match[2]) - 1, Number(match[3])) : null;
    }

    function toIsoDate(value) {
      return `${value.getFullYear()}-${String(value.getMonth() + 1).padStart(2, "0")}-${String(value.getDate()).padStart(2, "0")}`;
    }

    function sumByDate(points) {
      const totals = {};
      (Array.isArray(points) ? points : []).forEach((point) => {
        const key = String(point?.date || "");
        const qty = Number(point?.qty) || 0;
        if (parseIsoDate(key) && qty) {
          totals[key] = (totals[key] || 0) + qty;
        }
      });
      return totals;
    }

    // 起点（取込日の在庫）から、過去は遡って、未来は進んで在庫を並べる。
    //   過去: 前日の在庫 = 当日の在庫 + 当日の出荷 − 当日の入荷
    //   未来: 当日の在庫 = 前日の在庫 − 当日の内示 + 当日の予定入荷
    function buildStockSimulation(anchorQty, asOfText, series) {
      const asOf = parseIsoDate(asOfText);
      if (anchorQty === null || anchorQty === undefined || !asOf) {
        return [];
      }
      const ship = sumByDate(series.dailyShipment);
      const incoming = sumByDate(series.dailyIncoming);
      const demand = sumByDate(series.unconfirmedOrderDaily);
      const planned = sumByDate(series.plannedIncoming);

      // 範囲はサーバが決める固定値（基準日の 1 か月前 〜 翌々々月末）。品目によって端が変わらないようにする。
      // 動きのない日も前日の値を引き継いだ水平線として描く（REQ-SSC-F-002）。
      const first = parseIsoDate(series.rangeStart) || asOf;
      const last = parseIsoDate(series.rangeEnd) || asOf;

      // 過去側（asOf → first）を遡る。asOf 当日の動きは起点に含まれているので、前日へ移すときに戻す。
      const past = [];
      let qty = Number(anchorQty);
      for (let day = new Date(asOf); day >= first; day.setDate(day.getDate() - 1)) {
        const key = toIsoDate(day);
        past.push({ date: key, qty: Math.round(qty), future: false });
        qty = qty + (ship[key] || 0) - (incoming[key] || 0);
      }
      past.reverse();

      // 未来側（asOf の翌日 → last）へ進む。
      const future = [];
      qty = Number(anchorQty);
      const cursor = new Date(asOf);
      cursor.setDate(cursor.getDate() + 1);
      for (; cursor <= last; cursor.setDate(cursor.getDate() + 1)) {
        const key = toIsoDate(cursor);
        qty = qty - (demand[key] || 0) + (planned[key] || 0);
        future.push({ date: key, qty: Math.round(qty), future: true, demand: demand[key] || 0, planned: planned[key] || 0 });
      }
      return past.concat(future);
    }

    // 在庫推移（実績。V-218）。予測は在庫シミュレーション（V-237）へ移したため描かない（09 design §5.3）。
    function renderAnchoredStockChart(sectionEl, slimsSeries, incomingSeries) {
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

      // 横軸は実績 24 か月のみ（予測は在庫シミュレーションへ移した）。
      const points = slims;
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
      const rawMinQty = Math.min(0, ...points.map((point) => Number(point.qty) || 0), ...incomingQtys);
      const rawMaxQty = Math.max(1, ...points.map((point) => Number(point.qty) || 0), ...incomingQtys);
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
      svg.setAttribute("aria-label", "在庫推移（実績）と入荷実績");

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

      drawIncomingBars(incoming);
      drawSeries(slims, "ioa-anchored-stock-trend-line ioa-anchored-stock-trend-line--slims", "ioa-anchored-stock-trend-point ioa-anchored-stock-trend-point--slims", "SLIMS起点");

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
        '<span class="ioa-anchored-stock-trend-legend-item ioa-anchored-stock-trend-legend-item--incoming">入荷(MARI)</span>';
      container.append(legend);
    }

    function fillDetailSections(row) {
      const custCode = row.dataset.custCode || "";
      const custName = row.dataset.custName || "";
      const vendCd = row.dataset.level1VendCd || "";
      const vendName = row.dataset.level1VendName || "";
      setDetailText(detailFields.cust, custName ? `${custCode} - ${custName}` : custCode || "-");
      setDetailText(detailFields.itemCd, row.dataset.itemCd || "-");
      setDetailText(detailFields.vend, vendName ? `${vendCd} - ${vendName}` : vendCd || "-");
      setDetailText(detailFields.level1ItemCd, row.dataset.level1ItemCd || "-");
      setDetailText(detailFields.lastIncoming, row.dataset.lastIncomingDate || "-");
      setDetailText(detailFields.lastShip, row.dataset.lastShipDate || "-");
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
      // グラフ 1 は実績のみ。予測は在庫シミュレーション（V-237）へ移した（09 design §5.3）。
      renderAnchoredStockChart(anchoredStockTrendSection, slimsAnchoredTrend, incomingTrend);
      renderAnchorBreakdown(itemTrends.stocks, slimsAnchor);
      // グラフ 2: 在庫シミュレーション。材料はサーバが重複除去済みのものを配信する
      renderStockSimulation(custCode, row.dataset.itemCd || "", slimsAnchor);
      renderAssessment(custCode, row.dataset.itemCd || "");
      renderStockAndOrders(custCode, row.dataset.itemCd || "");
      renderMonthlyDemand(custCode, row.dataset.itemCd || "");
      updateGonenLink(custCode, row.dataset.itemCd || "");
    }

    // 在庫シミュレーションのグラフ（09 design §5.4）。横軸は日付で、範囲内の**全日**を出す。
    // 日数が多いので本体は横スクロールさせ、Y 軸だけ左に固定する（2026-09-30 ユーザー指示）。
    // 在庫切れ日・発注期限・安全在庫は**サーバの判定値**をそのまま縦線・水平線にする（JS で再計算しない）。
    const SIMULATION_DAY_WIDTH = 28;
    const SIMULATION_AXIS_WIDTH = 46;

    function renderStockSimulationChart(sectionEl, series, marks) {
      if (!sectionEl) {
        return;
      }
      const container = sectionEl.querySelector(".ioa-detail-stock-simulation-chart");
      const emptyMessage = sectionEl.querySelector(".ioa-detail-stock-simulation-empty");
      const note = sectionEl.querySelector(".ioa-detail-stock-simulation-note");
      if (!container) {
        return;
      }
      container.innerHTML = "";
      if (!series.length) {
        container.hidden = true;
        if (emptyMessage) emptyMessage.hidden = false;
        if (note) note.textContent = "";
        return;
      }
      container.hidden = false;
      if (emptyMessage) emptyMessage.hidden = true;

      const height = 168;
      const paddingTop = 10;
      const paddingBottom = 26;
      const plotHeight = height - paddingTop - paddingBottom;
      const plotWidth = series.length * SIMULATION_DAY_WIDTH;

      const qtys = series.map((point) => point.qty);
      const barQtys = series.map((point) => Number(point.planned) || 0).concat([Number(marks.overdueQty) || 0]);
      const safety = Number(marks.safetyStock) || 0;
      const rawMinQty = Math.min(0, ...qtys);
      const rawMaxQty = Math.max(1, ...qtys, ...barQtys, safety);
      const GRID_LINE_COUNT = 4;
      const gridStep = niceGridStep((rawMaxQty - rawMinQty) / GRID_LINE_COUNT);
      const minQty = Math.floor(rawMinQty / gridStep) * gridStep;
      const maxQty = Math.ceil(rawMaxQty / gridStep) * gridStep;
      const valueRange = maxQty - minQty || 1;
      const indexOfDate = {};
      series.forEach((point, index) => {
        indexOfDate[point.date] = index;
      });

      const svgNs = "http://www.w3.org/2000/svg";
      function yOf(qty) {
        return paddingTop + plotHeight - ((Number(qty) - minQty) / valueRange) * plotHeight;
      }
      function xOf(index) {
        return index * SIMULATION_DAY_WIDTH + SIMULATION_DAY_WIDTH / 2;
      }

      // --- 左に固定する Y 軸（本体と同じ縦の尺度） ---
      const axisWrap = document.createElement("div");
      axisWrap.className = "ioa-stock-simulation-axis";
      const axisSvg = document.createElementNS(svgNs, "svg");
      axisSvg.setAttribute("viewBox", `0 0 ${SIMULATION_AXIS_WIDTH} ${height}`);
      axisSvg.setAttribute("width", String(SIMULATION_AXIS_WIDTH));
      axisSvg.setAttribute("height", String(height));
      axisSvg.setAttribute("class", "ioa-stock-simulation-axis-svg");
      axisSvg.setAttribute("aria-hidden", "true");

      const gridLineTotal = Math.round(valueRange / gridStep);
      for (let gridIndex = 0; gridIndex <= gridLineTotal; gridIndex += 1) {
        const gridQty = minQty + gridStep * gridIndex;
        const label = document.createElementNS(svgNs, "text");
        label.setAttribute("x", String(SIMULATION_AXIS_WIDTH - 5));
        label.setAttribute("y", String(yOf(gridQty) + 3));
        label.setAttribute("class", "ioa-stock-simulation-axis-label");
        label.style.textAnchor = "end";
        label.textContent = gridQty.toLocaleString();
        axisSvg.append(label);
      }
      axisWrap.append(axisSvg);
      container.append(axisWrap);

      // --- 横スクロールする本体 ---
      const scroller = document.createElement("div");
      scroller.className = "ioa-stock-simulation-scroll";
      const svg = document.createElementNS(svgNs, "svg");
      svg.setAttribute("viewBox", `0 0 ${plotWidth} ${height}`);
      svg.setAttribute("width", String(plotWidth));
      svg.setAttribute("height", String(height));
      svg.setAttribute("class", "ioa-stock-simulation-svg");
      svg.setAttribute("role", "img");
      svg.setAttribute("aria-label", "在庫シミュレーション（日次）");

      for (let gridIndex = 0; gridIndex <= gridLineTotal; gridIndex += 1) {
        const gridQty = minQty + gridStep * gridIndex;
        const gridLine = document.createElementNS(svgNs, "line");
        gridLine.setAttribute("x1", "0");
        gridLine.setAttribute("x2", String(plotWidth));
        gridLine.setAttribute("y1", String(yOf(gridQty)));
        gridLine.setAttribute("y2", String(yOf(gridQty)));
        gridLine.setAttribute("class", gridQty === 0 ? "ioa-stock-simulation-zero-line" : "ioa-stock-simulation-grid-line");
        svg.append(gridLine);
      }

      function drawVerticalLine(dateText, className, labelText) {
        const index = indexOfDate[String(dateText || "").replace(/\//g, "-")];
        if (index === undefined) {
          return;
        }
        const x = xOf(index);
        const line = document.createElementNS(svgNs, "line");
        line.setAttribute("x1", String(x));
        line.setAttribute("x2", String(x));
        line.setAttribute("y1", String(paddingTop));
        line.setAttribute("y2", String(paddingTop + plotHeight));
        line.setAttribute("class", className);
        svg.append(line);
        const label = document.createElementNS(svgNs, "text");
        label.setAttribute("x", String(x + 3));
        label.setAttribute("y", String(paddingTop + 9));
        label.setAttribute("class", `${className}-label`);
        label.textContent = labelText;
        svg.append(label);
      }

      // 安全在庫（V-231）の水準線。0（未設定）なら描かない
      if (safety > 0) {
        const line = document.createElementNS(svgNs, "line");
        line.setAttribute("x1", "0");
        line.setAttribute("x2", String(plotWidth));
        line.setAttribute("y1", String(yOf(safety)));
        line.setAttribute("y2", String(yOf(safety)));
        line.setAttribute("class", "ioa-stock-simulation-safety-line");
        svg.append(line);
        const label = document.createElementNS(svgNs, "text");
        label.setAttribute("x", "4");
        label.setAttribute("y", String(yOf(safety) - 3));
        label.setAttribute("class", "ioa-stock-simulation-safety-label");
        label.textContent = `安全在庫 ${safety.toLocaleString()}`;
        svg.append(label);
      }

      // 棒: 予定入荷（納期の日）と、納期遅れの発注残（取込日の位置。線には加算しない）
      const barWidth = Math.max(3, SIMULATION_DAY_WIDTH * 0.5);
      const zeroY = yOf(0);
      function drawBar(index, qty, className, titleText) {
        const y = yOf(qty);
        const bar = document.createElementNS(svgNs, "rect");
        bar.setAttribute("x", String(xOf(index) - barWidth / 2));
        bar.setAttribute("y", String(Math.min(y, zeroY)));
        bar.setAttribute("width", String(barWidth));
        bar.setAttribute("height", String(Math.abs(zeroY - y)));
        bar.setAttribute("class", className);
        const title = document.createElementNS(svgNs, "title");
        title.textContent = titleText;
        bar.append(title);
        svg.append(bar);
      }

      series.forEach((point, index) => {
        const planned = Number(point.planned) || 0;
        if (planned > 0) {
          drawBar(index, planned, "ioa-stock-simulation-planned-bar", `予定入荷 ${point.date}: ${planned.toLocaleString()}`);
        }
      });

      const overdueQty = Number(marks.overdueQty) || 0;
      const asOfIndex = indexOfDate[String(marks.asOfDate || "")];
      if (overdueQty > 0 && asOfIndex !== undefined) {
        drawBar(
          asOfIndex,
          overdueQty,
          "ioa-stock-simulation-overdue-bar",
          `納期遅れの発注残 ${overdueQty.toLocaleString()}（線には足していません）`,
        );
      }

      // 折れ線: 取込日までは実線、以降は点線
      function drawSegment(points, className) {
        if (points.length < 2) {
          return;
        }
        const path = document.createElementNS(svgNs, "polyline");
        path.setAttribute("points", points.map(({ index, qty }) => `${xOf(index)},${yOf(qty)}`).join(" "));
        path.setAttribute("class", className);
        svg.append(path);
      }

      const pastPoints = [];
      const futurePoints = [];
      series.forEach((point, index) => {
        (point.future ? futurePoints : pastPoints).push({ index, qty: point.qty });
      });
      if (pastPoints.length && futurePoints.length) {
        futurePoints.unshift(pastPoints[pastPoints.length - 1]);
      }
      drawSegment(pastPoints, "ioa-stock-simulation-line ioa-stock-simulation-line--actual");
      drawSegment(futurePoints, "ioa-stock-simulation-line ioa-stock-simulation-line--outlook");

      drawVerticalLine(marks.asOfDate, "ioa-stock-simulation-now-line", "取込日");
      drawVerticalLine(marks.orderDeadline, "ioa-stock-simulation-deadline-line", "発注期限");
      drawVerticalLine(marks.stockoutDate, "ioa-stock-simulation-stockout-line", "在庫切れ");

      // 横軸ラベル: 範囲内の全日を「月/日」で出す（年は軸が長くなり重なるため出さない。2026-09-30 ユーザー指示）。
      // 月の変わり目だけ区切り線を添えて、どの月かを読めるようにする。
      series.forEach((point, index) => {
        const isMonthFirst = point.date.endsWith("-01");
        if (isMonthFirst) {
          const separator = document.createElementNS(svgNs, "line");
          separator.setAttribute("x1", String(xOf(index) - SIMULATION_DAY_WIDTH / 2));
          separator.setAttribute("x2", String(xOf(index) - SIMULATION_DAY_WIDTH / 2));
          separator.setAttribute("y1", String(paddingTop));
          separator.setAttribute("y2", String(paddingTop + plotHeight + 4));
          separator.setAttribute("class", "ioa-stock-simulation-month-separator");
          svg.append(separator);
        }
        const label = document.createElementNS(svgNs, "text");
        label.setAttribute("x", String(xOf(index)));
        label.setAttribute("y", String(height - 8));
        label.setAttribute(
          "class",
          isMonthFirst
            ? "ioa-stock-simulation-date-label ioa-stock-simulation-date-label--month-first"
            : "ioa-stock-simulation-date-label",
        );
        // 年は出さない（"2026-09-18" → "09/18"）
        label.textContent = point.date.slice(5).replace("-", "/");
        svg.append(label);
      });

      scroller.append(svg);
      container.append(scroller);

      // 取込日が中央あたりに来る位置までスクロールしておく（過去 1 か月と直近の見通しが同時に見える）
      const asOfX = asOfIndex === undefined ? 0 : xOf(asOfIndex);
      scroller.scrollLeft = Math.max(0, asOfX - scroller.clientWidth / 3);

      // 在庫切れ日・発注期限・納期遅れ・安全在庫は判定サマリと「在庫と発注残」で述べるので、
      // ここでは繰り返さない（2026-09-30 ユーザー指示）。グラフだけに必要な案内を残す。
      if (note) {
        note.textContent = series.some((point) => !point.future)
          ? ""
          : "取込日より前は、SLIMS を取り込み直すと表示されます";
      }
    }

    function renderStockSimulation(custCode, itemCd, anchorQty) {
      const info = listClient?.getResponseClass?.(custCode, itemCd);
      const simulation = info?.simulation;
      if (!stockSimulationSection) {
        return;
      }
      const series = simulation ? buildStockSimulation(anchorQty, simulation.asOfDate, simulation) : [];
      renderStockSimulationChart(stockSimulationSection, series, {
        asOfDate: simulation?.asOfDate || "",
        stockoutDate: info?.stockoutDate || "",
        orderDeadline: info?.orderDeadline || "",
        safetyStock: info?.safetyStock || 0,
        overdueQty: info?.overdueOrderQty || 0,
      });
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

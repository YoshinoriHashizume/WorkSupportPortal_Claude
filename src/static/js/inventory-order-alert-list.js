(function () {
  const ROW_SELECTOR = ".inventory-order-alert-page .ioa-table tbody tr.ioa-data-row";
  const CONFIRMATION_API = "/api/inventory-order-alert/confirmation";
  const CONFIRMATION_MEMO_API = "/api/inventory-order-alert/confirmation/memos";
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
  function updateTableCounts(counts) {
    const countsElement = document.querySelector(".inventory-order-alert-page .ioa-table-counts");
    if (!countsElement || !counts) {
      return;
    }
    const left = countsElement.querySelector(".ioa-table-counts-left");
    const right = countsElement.querySelector(".ioa-table-counts-right");
    if (left) {
      left.textContent =
        `供給リスク品 ${counts.supplyRisk} 件 / 在庫死蔵品 ${counts.dormantStock} 件 / 在庫過剰リスク品 ${counts.excessStockRisk} 件 / 通常流動品 ${counts.normalFlow} 件`;
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
        department: dialog.querySelector(".ioa-detail-department"),
        condition: dialog.querySelector(".ioa-detail-condition"),
        stockSlims: dialog.querySelector(".ioa-detail-stock-slims"),
        stockMari: dialog.querySelector(".ioa-detail-stock-mari"),
    };
    const anchoredStockTrendSection = dialog.querySelector(".ioa-detail-anchored-stock-trend-section");
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

    function parseAnchorQty(text) {
      const trimmed = String(text || "").trim();
      if (!trimmed) {
        return null;
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

    function renderAnchoredStockChart(sectionEl, slimsSeries) {
      if (!sectionEl) {
        return;
      }
      const container = sectionEl.querySelector(".ioa-detail-anchored-stock-trend-chart");
      const emptyMessage = sectionEl.querySelector(".ioa-detail-anchored-stock-trend-empty");
      if (!container) {
        return;
      }

      const slims = Array.isArray(slimsSeries) ? slimsSeries : [];
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

      const points = slims;
      const width = 560;
      const height = 140;
      const paddingLeft = 44;
      const paddingTop = 8;
      const paddingBottom = 20;
      const plotWidth = width - paddingLeft - 8;
      const plotHeight = height - paddingTop - paddingBottom;
      // マイナスもそのまま表示するため、0 を必ず範囲に含めてゼロ基準線を描けるようにする（design.md §6.6）。
      const minQty = Math.min(0, ...slims.map((point) => Number(point.qty) || 0));
      const maxQty = Math.max(1, ...slims.map((point) => Number(point.qty) || 0));
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
      svg.setAttribute("aria-label", "推定在庫推移（参考値）");

      // Excel風に、等間隔の目盛り線を GRID_LINE_COUNT 分割（=GRID_LINE_COUNT+1本）描画する。
      const GRID_LINE_COUNT = 4;
      for (let gridIndex = 0; gridIndex <= GRID_LINE_COUNT; gridIndex += 1) {
        const gridQty = minQty + (valueRange * gridIndex) / GRID_LINE_COUNT;
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
        '<span class="ioa-anchored-stock-trend-legend-item ioa-anchored-stock-trend-legend-item--slims">SLIMS起点</span>';
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
      setDetailText(
        detailFields.flowQuadrant,
        row.dataset.noIncomingRecord ? `${quadrantLabel}（入荷実績なし）` : quadrantLabel || "-",
      );
      setDetailText(detailFields.department, listClient?.getResponsibleDepartment?.(quadrantKey) || "-");
      setDetailText(detailFields.condition, listClient?.getFlowConditionLabel?.() || "-");
      // 在庫数は一覧と同じ表示文字列をそのまま出す（未取得の「－」と 0 を取り違えないため）。
      setDetailText(detailFields.stockSlims, row.dataset.stockQty || "-");
      setDetailText(detailFields.stockMari, row.dataset.mariStockQty || "-");
      // 出荷推移(V-216)・入荷推移(V-217)は独立したグラフとしては表示しない。
      // 推定在庫推移(V-218)の算出のみに用いる（DECISIONS.md参照）。
      const shipmentTrend = listClient?.getShipmentTrend?.(custCode, row.dataset.itemCd || "") || [];
      const incomingTrend = listClient?.getIncomingTrend?.(custCode, row.dataset.itemCd || "") || [];

      const slimsAnchor = parseAnchorQty(row.dataset.stockQty);
      const slimsAnchoredTrend = buildAnchoredStockTrend(shipmentTrend, incomingTrend, slimsAnchor);
      renderAnchoredStockChart(anchoredStockTrendSection, slimsAnchoredTrend);
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

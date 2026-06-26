(function () {
  const ROW_SELECTOR = ".inventory-order-alert-page .ioa-table tbody tr.ioa-data-row";
  const CONFIRMATION_API = "/api/inventory-order-alert/confirmation";
  const CONFIRMATION_MEMO_API = "/api/inventory-order-alert/confirmation/memos";
  const CONFIRMATION_RESET_API = "/api/inventory-order-alert/confirmation/reset";
  const MAX_MEMO_LENGTH = 500;
  const TABLE_WRAP_SELECTOR = ".inventory-order-alert-page .ioa-table-wrap";
  const SCROLL_TOP_STORAGE_KEY = "ioa-table-scroll-top";
  const SCROLL_ROW_STORAGE_KEY = "ioa-table-scroll-row";

  function getTableWrap() {
    return document.querySelector(TABLE_WRAP_SELECTOR);
  }

  function saveTableScrollPosition(row) {
    const tableWrap = getTableWrap();
    if (tableWrap) {
      sessionStorage.setItem(SCROLL_TOP_STORAGE_KEY, String(tableWrap.scrollTop));
    }
    if (row) {
      sessionStorage.setItem(
        SCROLL_ROW_STORAGE_KEY,
        `${row.dataset.custCode || ""}|${row.dataset.itemCd || ""}`,
      );
    }
  }

  function findDataRow(custCode, itemCd) {
    return [...document.querySelectorAll(ROW_SELECTOR)].find(
      (candidate) => candidate.dataset.custCode === custCode && candidate.dataset.itemCd === itemCd,
    );
  }

  function restoreTableScrollPosition() {
    const tableWrap = getTableWrap();
    if (!tableWrap) {
      return;
    }

    const savedTop = sessionStorage.getItem(SCROLL_TOP_STORAGE_KEY);
    const savedRow = sessionStorage.getItem(SCROLL_ROW_STORAGE_KEY);
    sessionStorage.removeItem(SCROLL_TOP_STORAGE_KEY);
    sessionStorage.removeItem(SCROLL_ROW_STORAGE_KEY);
    if (savedTop === null && !savedRow) {
      return;
    }

    function applyScroll() {
      if (savedTop !== null) {
        tableWrap.scrollTop = Number(savedTop) || 0;
        return;
      }
      if (savedRow) {
        const separatorIndex = savedRow.indexOf("|");
        const custCode = savedRow.slice(0, separatorIndex);
        const itemCd = savedRow.slice(separatorIndex + 1);
        const row = findDataRow(custCode, itemCd);
        if (row) {
          row.scrollIntoView({ block: "nearest" });
        }
      }
    }

    requestAnimationFrame(() => {
      requestAnimationFrame(applyScroll);
    });
  }

  function reloadInventoryOrderAlertPage(row) {
    saveTableScrollPosition(row);
    window.location.reload();
  }

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

  function getRowConfirmationStatus(row) {
    const select = row.querySelector(".ioa-confirmation-status");
    if (select) {
      return select.value;
    }
    return row.dataset.confirmationStatus || "unconfirmed";
  }

  async function saveConfirmation(row, { status }, listClient) {
    const response = await fetch(CONFIRMATION_API, {
      method: "PUT",
      headers: {
        "Content-Type": "application/json",
        "X-CSRFToken": getCsrfToken(),
      },
      body: JSON.stringify({
        custCode: row.dataset.custCode || "",
        itemCd: row.dataset.itemCd || "",
        status,
        ...getListFilterParams(listClient),
      }),
    });
    const payload = await response.json();
    if (!response.ok || !payload.ok) {
      throw new Error(payload.message || "確認状態の保存に失敗しました。");
    }
    if (listClient) {
      listClient.updateRowFromConfirmation(row.dataset.custCode || "", row.dataset.itemCd || "", payload);
    } else {
      updateRowConfirmationState(row, payload);
      updateTableCounts(payload.counts);
    }
    return payload;
  }

  async function saveConfirmationStatus(select, row, listClient) {
    const previousStatus = getRowConfirmationStatus(row);
    const nextStatus = select.value;
    if (nextStatus === previousStatus) {
      return;
    }

    select.disabled = true;
    try {
      await saveConfirmation(row, {
        status: nextStatus,
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
        `重点 ${counts.critical} 件 / 警告（出荷あり） ${counts.warningShip} 件 / 警告（出荷なし） ${counts.warningIncoming} 件 / アラート無し ${counts.alertNone} 件`;
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

  function initLocationDialog() {
    const dialog = document.getElementById("ioa-location-dialog");
    const listTableBody = document.querySelector(".inventory-order-alert-page .ioa-table tbody");
    if (!dialog || !listTableBody) {
      return;
    }

    const meta = dialog.querySelector(".ioa-location-meta");
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

    async function openLocationDialog(row) {
      if (!meta || !locationTableBody || !tableWrap || !emptyMessage || !asOfLabel || !memoInput) {
        return;
      }

      activeRow = row;
      memoInput.value = "";

      document.querySelectorAll(`${ROW_SELECTOR}.is-selected`).forEach((selectedRow) => {
        selectedRow.classList.remove("is-selected");
      });
      row.classList.add("is-selected");

      const custCode = row.dataset.custCode || "";
      const custName = row.dataset.custName || "";
      const itemCd = row.dataset.itemCd || "";
      const stockQty = row.dataset.stockQty || "";
      const locations = parseLocationDetail(row.dataset.stockLocationDetail || "");
      const customerLabel = custName ? `${custCode} - ${custName}` : custCode;

      meta.textContent = `得意先: ${customerLabel} / 品番: ${itemCd}${
        stockQty ? ` / 在庫数合計: ${formatStockQty(stockQty)}` : ""
      }`;

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

  function initConfirmationReset(listClient) {
    const resetButton = document.querySelector(".inventory-order-alert-page .ioa-confirmation-reset");
    if (!resetButton) {
      return;
    }

    resetButton.addEventListener("click", async () => {
      if (
        !window.confirm(
          "確認中・確認済みの状態をすべて未確認に戻します。メモ履歴は維持されます。よろしいですか？",
        )
      ) {
        return;
      }

      resetButton.disabled = true;
      try {
        const response = await fetch(CONFIRMATION_RESET_API, {
          method: "POST",
          headers: {
            "Content-Type": "application/json",
            "X-CSRFToken": getCsrfToken(),
          },
          body: JSON.stringify(getListFilterParams(listClient)),
        });
        const payload = await response.json();
        if (!response.ok || !payload.ok) {
          window.alert(payload.message || "確認状態のリセットに失敗しました。");
          return;
        }
        if (payload.resetCount === 0) {
          window.alert("リセット対象の確認状態はありません。");
          return;
        }
        reloadInventoryOrderAlertPage();
      } catch (_error) {
        window.alert("確認状態のリセットに失敗しました。");
      } finally {
        resetButton.disabled = false;
      }
    });
  }

  function initAlertRulesDialog() {
    const dialog = document.getElementById("ioa-alert-rules-dialog");
    const openButton = document.querySelector(".inventory-order-alert-page .ioa-alert-rules-open");
    const closeButton = dialog?.querySelector(".ioa-alert-rules-close");
    const saveButton = dialog?.querySelector(".ioa-alert-rules-save");
    const shipmentSelect = document.getElementById("ioa-warning-shipment-months");
    const incomingSelect = document.getElementById("ioa-warning-incoming-months");
    if (!dialog || !openButton || !closeButton || !saveButton || !shipmentSelect || !incomingSelect) {
      return;
    }

    openButton.addEventListener("click", () => {
      if (typeof dialog.showModal === "function") {
        dialog.showModal();
      }
    });

    closeButton.addEventListener("click", () => {
      dialog.close();
    });

    dialog.addEventListener("click", (event) => {
      if (event.target === dialog) {
        dialog.close();
      }
    });

    saveButton.addEventListener("click", async () => {
      saveButton.disabled = true;
      try {
        const response = await fetch("/api/inventory-order-alert/alert-settings", {
          method: "PUT",
          headers: {
            "Content-Type": "application/json",
            "X-CSRFToken": getCsrfToken(),
          },
          body: JSON.stringify({
            warningShipmentMonths: Number(shipmentSelect.value),
            warningIncomingMonths: Number(incomingSelect.value),
          }),
        });
        const payload = await response.json();
        if (!response.ok || !payload.ok) {
          window.alert(payload.message || "警告条件の保存に失敗しました。");
          return;
        }
        window.location.reload();
      } catch (_error) {
        window.alert("警告条件の保存に失敗しました。");
      } finally {
        saveButton.disabled = false;
      }
    });
  }

  function initInventoryOrderAlertPage() {
    const listClient = window.IoaListClient?.init?.() || null;
    restoreTableScrollPosition();
    initSlimsImport();
    initSortDialog(listClient);
    initAlertRulesDialog();
    initLocationDialog();
    initConfirmationStatusSelects(listClient);
    initConfirmationReset(listClient);
  }

  document.addEventListener("DOMContentLoaded", initInventoryOrderAlertPage);
})();

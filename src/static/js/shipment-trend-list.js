(function () {
  const csrfToken = window.portalCsrfToken || "";
  const CHART_API = "/api/shipment-trend/chart";

  function getListClient() {
    return window.__shipmentTrendListClient || null;
  }

  function onReady(callback) {
    if (document.readyState === "loading") {
      document.addEventListener("DOMContentLoaded", callback);
      return;
    }
    callback();
  }

  function bindSortDialog(listClient) {
    if (!window.PortalListSortDialog) {
      return;
    }
    window.PortalListSortDialog.init({
      dialog: document.getElementById("st-sort-dialog"),
      openButton: document.querySelector(".shipment-trend-page .st-sort-open"),
      listClient,
      maxSortRows: 5,
      rowClass: "st-sort-row",
      orderClass: "st-sort-row-order",
      columnClass: "st-sort-column",
      directionClass: "st-sort-direction",
      removeClass: "st-sort-remove",
      formClass: "st-sort-form",
      rowsContainerClass: "st-sort-rows",
      template: document.querySelector("#st-sort-row-template"),
      addButtonClass: "st-sort-add",
      cancelButtonClass: "st-sort-cancel",
    });
  }

  function showRefreshLoading() {
    const overlay = document.getElementById("st-refresh-overlay");
    if (overlay) {
      overlay.hidden = false;
      overlay.setAttribute("aria-busy", "true");
    }
    document.body.classList.add("st-refresh-loading");
  }

  function initRefreshForm() {
    const form = document.querySelector(".shipment-trend-page .st-refresh-form");
    if (!form) {
      return;
    }
    let submitting = false;
    form.addEventListener("submit", () => {
      if (submitting) {
        return;
      }
      submitting = true;
      const button = form.querySelector('button[type="submit"]');
      if (button) {
        button.disabled = true;
        button.classList.add("is-disabled");
      }
      showRefreshLoading();
    });
  }

  function bindAlertSettings() {
    const dialog = document.getElementById("st-alert-rules-dialog");
    const openButton = document.querySelector(".shipment-trend-page .st-alert-rules-open");
    const saveButton = dialog?.querySelector(".st-alert-rules-save");
    const cancelButton = dialog?.querySelector(".st-alert-rules-cancel");
    const decreaseSelect = document.getElementById("st-decrease-threshold");
    const increaseSelect = document.getElementById("st-increase-threshold");
    if (!dialog || !openButton || !saveButton) {
      return;
    }
    openButton.addEventListener("click", () => dialog.showModal());
    cancelButton?.addEventListener("click", () => dialog.close());
    dialog.addEventListener("click", (event) => {
      if (event.target === dialog) {
        dialog.close();
      }
    });
    saveButton.addEventListener("click", async () => {
      const payload = {
        decreaseThresholdPct: Number(decreaseSelect?.value || 20),
        increaseThresholdPct: Number(increaseSelect?.value || 20),
      };
      const response = await fetch("/api/shipment-trend/alert-settings", {
        method: "PUT",
        headers: {
          "Content-Type": "application/json",
          "X-CSRFToken": csrfToken,
        },
        body: JSON.stringify(payload),
      });
      const body = await response.json();
      if (!response.ok || !body.ok) {
        window.alert(body.message || "警告条件の保存に失敗しました。");
        return;
      }
      getListClient()?.updateThresholds(body.decreaseThresholdPct, body.increaseThresholdPct);
      dialog.close();
      window.location.reload();
    });
  }

  const CHART_HEIGHT = 440;
  const CHART_HORIZONTAL_PADDING = 88;

  function escapeChartAttr(value) {
    return String(value)
      .replace(/&/g, "&amp;")
      .replace(/"/g, "&quot;")
      .replace(/</g, "&lt;");
  }

  function buildMarkerTooltipLabel(yearMonth, qty, kind) {
    const kindLabel = kind === "forecast" ? "予測" : "実績";
    return `${yearMonth} ${kindLabel}: ${formatChartQtyLabel(qty)}`;
  }

  function ensureChartCanvasStructure(canvasWrap) {
    let plot = canvasWrap.querySelector(".st-chart-plot");
    let tooltip = canvasWrap.querySelector(".st-chart-tooltip");
    if (!plot || !tooltip) {
      canvasWrap.replaceChildren();
      plot = document.createElement("div");
      plot.className = "st-chart-plot";
      tooltip = document.createElement("div");
      tooltip.className = "st-chart-tooltip";
      tooltip.hidden = true;
      canvasWrap.append(plot, tooltip);
    }
    return { plot, tooltip };
  }

  function clearChartCanvas(canvasWrap) {
    const { plot, tooltip } = ensureChartCanvasStructure(canvasWrap);
    plot.replaceChildren();
    tooltip.hidden = true;
    tooltip.textContent = "";
  }

  function bindChartMarkerTooltips(canvasWrap) {
    if (canvasWrap.dataset.tooltipBound === "true") {
      return;
    }
    canvasWrap.dataset.tooltipBound = "true";
    canvasWrap.addEventListener("mousemove", (event) => {
      const { tooltip } = ensureChartCanvasStructure(canvasWrap);
      const marker = event.target instanceof Element ? event.target.closest(".st-chart-marker-hit") : null;
      if (!marker) {
        tooltip.hidden = true;
        return;
      }
      const yearMonth = marker.getAttribute("data-year-month") || "";
      const qty = marker.getAttribute("data-qty") || "0";
      const kind = marker.getAttribute("data-kind") || "actual";
      tooltip.textContent = buildMarkerTooltipLabel(yearMonth, qty, kind);
      tooltip.hidden = false;
      const rect = canvasWrap.getBoundingClientRect();
      tooltip.style.left = `${event.clientX - rect.left}px`;
      tooltip.style.top = `${event.clientY - rect.top}px`;
    });
    canvasWrap.addEventListener("mouseleave", () => {
      const tooltip = canvasWrap.querySelector(".st-chart-tooltip");
      if (tooltip) {
        tooltip.hidden = true;
      }
    });
  }

  function measureChartContainerWidth(canvasWrap, dialog) {
    const measured = canvasWrap?.clientWidth || canvasWrap?.getBoundingClientRect()?.width || 0;
    if (measured > 0) {
      return measured;
    }
    const content = dialog?.querySelector(".st-detail-content");
    const contentWidth = content?.clientWidth || 0;
    if (contentWidth > 0) {
      return contentWidth;
    }
    if (typeof window !== "undefined" && window.innerWidth) {
      return Math.min(window.innerWidth - 40, 1880);
    }
    return 1280;
  }

  function resolveChartLayout(pointCount, containerWidth) {
    const count = Math.max(pointCount, 1);
    const outerWidth = Math.max(Number(containerWidth) || 0, 320);
    const innerWidth = Math.max(outerWidth - CHART_HORIZONTAL_PADDING, 1);
    const monthSlotWidth = innerWidth / count;
    return {
      monthSlotWidth,
      innerWidth,
      outerWidth,
      height: CHART_HEIGHT,
    };
  }

  function formatMonthAxisLabel(yearMonth) {
    const [year, monthText] = String(yearMonth || "").split("-");
    return `${year}/${Number(monthText)}`;
  }

  function shouldShowSemiannualAxisLabel(yearMonth, index, totalCount) {
    if (index === 0 || index === totalCount - 1) {
      return true;
    }
    const [, monthText] = String(yearMonth || "").split("-");
    const monthNum = Number(monthText);
    return monthNum === 1 || monthNum === 7;
  }

  function formatChartQtyLabel(value) {
    const rounded = Math.round(Number(value) || 0);
    return rounded.toLocaleString("ja-JP");
  }

  function buildYAxisScale(maxValue, tickCount) {
    const max = Math.max(Number(maxValue) || 0, 1);
    const intervalCount = Math.max(tickCount - 1, 1);
    const exponent = Math.floor(Math.log10(max));
    let axisMax = max;
    for (let exp = exponent - 1; exp <= exponent + 1; exp += 1) {
      const magnitude = Math.pow(10, Math.max(exp, 0));
      for (const multiplier of [1, 2, 5, 10]) {
        const step = multiplier * magnitude;
        if (step <= 0) {
          continue;
        }
        const candidate = Math.ceil(max / step) * step;
        if (candidate >= max && candidate < axisMax) {
          axisMax = candidate;
        }
      }
    }
    const ticks = Array.from({ length: tickCount }, (_, index) => (axisMax / intervalCount) * index);
    return { axisMax, ticks };
  }

  function buildChartSvgMarkup(chart, containerWidth) {
    const points = chart.points || [];
    if (!points.length) {
      return "";
    }
    const padding = { top: 24, right: 24, bottom: 72, left: 64 };
    const layout = resolveChartLayout(points.length, containerWidth);
    const monthSlotWidth = layout.monthSlotWidth;
    const innerWidth = layout.innerWidth;
    const height = layout.height;
    const innerHeight = height - padding.top - padding.bottom;
    const maxQty = Math.max(...points.map((point) => Number(point.qty) || 0), 1);
    const yAxis = buildYAxisScale(maxQty, 5);
    const chartBottom = padding.top + innerHeight;
    const width = innerWidth + padding.left + padding.right;
    const markerRadius = monthSlotWidth < 16 ? 2.5 : 3.5;

    function xForIndex(index) {
      return padding.left + index * monthSlotWidth + monthSlotWidth / 2;
    }

    function coordForIndex(index, qty) {
      const x = xForIndex(index);
      const y = padding.top + innerHeight - (Math.max(0, Number(qty) || 0) / yAxis.axisMax) * innerHeight;
      return { x, y };
    }

    function yCoordForValue(value) {
      return padding.top + innerHeight - (Math.max(0, Number(value) || 0) / yAxis.axisMax) * innerHeight;
    }

    function pathFromCoords(coords) {
      if (!coords.length) {
        return "";
      }
      return coords
        .map((point, index) => `${index === 0 ? "M" : "L"} ${point.x.toFixed(1)} ${point.y.toFixed(1)}`)
        .join(" ");
    }

    const plotted = points.map((point, index) => ({
      ...coordForIndex(index, point.qty),
      yearMonth: point.yearMonth,
      qty: Number(point.qty) || 0,
      kind: point.kind === "forecast" ? "forecast" : "actual",
    }));

    const actualCoords = plotted.filter((point) => point.kind === "actual");
    const forecastCoords = plotted.filter((point) => point.kind === "forecast");
    const lastActual = actualCoords[actualCoords.length - 1];
    const forecastLineCoords = lastActual ? [lastActual, ...forecastCoords] : forecastCoords;

    const actualPath =
      actualCoords.length > 1
        ? `<path d="${pathFromCoords(actualCoords)}" fill="none" stroke="#22c55e" stroke-width="2.5" stroke-linejoin="round" stroke-linecap="round" />`
        : "";
    const forecastPath = forecastLineCoords.length > 1
      ? `<path d="${pathFromCoords(forecastLineCoords)}" fill="none" stroke="#60a5fa" stroke-width="2.5" stroke-dasharray="7 5" stroke-linejoin="round" stroke-linecap="round" />`
      : "";
    const markers = plotted
      .map((point) => {
        const fill = point.kind === "forecast" ? "#60a5fa" : "#22c55e";
        const label = buildMarkerTooltipLabel(point.yearMonth, point.qty, point.kind);
        const hitRadius = Math.max(markerRadius + 5, 9);
        const attrs = [
          `data-year-month="${escapeChartAttr(point.yearMonth)}"`,
          `data-qty="${escapeChartAttr(point.qty)}"`,
          `data-kind="${escapeChartAttr(point.kind)}"`,
        ].join(" ");
        return `<g class="st-chart-marker-group"><circle class="st-chart-marker-hit" cx="${point.x.toFixed(1)}" cy="${point.y.toFixed(1)}" r="${hitRadius}" fill="transparent" ${attrs}><title>${escapeChartAttr(label)}</title></circle><circle class="st-chart-marker" cx="${point.x.toFixed(1)}" cy="${point.y.toFixed(1)}" r="${markerRadius}" fill="${fill}" pointer-events="none" /></g>`;
      })
      .join("");
    const monthGridLines = points
      .map((_, index) => {
        const x = padding.left + index * monthSlotWidth;
        return `<line x1="${x.toFixed(1)}" y1="${padding.top}" x2="${x.toFixed(1)}" y2="${chartBottom.toFixed(1)}" stroke="#e2e8f0" stroke-width="1" />`;
      })
      .join("");
    const labels = points
      .filter((point, index) => shouldShowSemiannualAxisLabel(point.yearMonth, index, points.length))
      .map((point) => {
        const index = points.indexOf(point);
        const x = xForIndex(index);
        const label = formatMonthAxisLabel(point.yearMonth);
        return `<text x="${x.toFixed(1)}" y="${height - 24}" font-size="10" fill="#475569" text-anchor="middle">${label}</text>`;
      })
      .join("");
    const yAxisTicks = yAxis.ticks
      .map((value) => {
        const y = yCoordForValue(value);
        const tickEndX = padding.left - 6;
        return `<line x1="${tickEndX}" y1="${y.toFixed(1)}" x2="${padding.left}" y2="${y.toFixed(1)}" stroke="#94a3b8" stroke-width="1" /><text x="${padding.left - 10}" y="${(y + 4).toFixed(1)}" font-size="11" fill="#475569" text-anchor="end">${formatChartQtyLabel(value)}</text>`;
      })
      .join("");
    const yAxisLine = `<line x1="${padding.left}" y1="${padding.top}" x2="${padding.left}" y2="${chartBottom}" stroke="#94a3b8" stroke-width="1" />`;
    const baseline = `<line x1="${padding.left}" y1="${chartBottom}" x2="${width - padding.right}" y2="${chartBottom}" stroke="#cbd5e1" stroke-width="1" />`;
    return `<svg class="st-chart-svg" width="100%" height="${height}" viewBox="0 0 ${width} ${height}" preserveAspectRatio="xMidYMid meet" xmlns="http://www.w3.org/2000/svg" role="img" aria-label="出荷推移グラフ">${monthGridLines}${yAxisLine}${yAxisTicks}${baseline}${actualPath}${forecastPath}${markers}${labels}</svg>`;
  }

  function renderChart(canvasWrap, chart, dialog) {
    if (!canvasWrap) {
      return;
    }
    canvasWrap.style.minHeight = `${CHART_HEIGHT}px`;
    const render = () => {
      const { plot } = ensureChartCanvasStructure(canvasWrap);
      const containerWidth = measureChartContainerWidth(canvasWrap, dialog);
      plot.innerHTML = buildChartSvgMarkup(chart, containerWidth);
    };
    render();
    if (typeof window !== "undefined" && typeof window.requestAnimationFrame === "function") {
      window.requestAnimationFrame(render);
    }
  }

  function formatChangeRateLabel(value) {
    if (value === null || value === undefined || value === "") {
      return "—";
    }
    const number = Number(value);
    if (!Number.isFinite(number)) {
      return "—";
    }
    const sign = number > 0 ? "+" : "";
    return `${sign}${number.toFixed(2)}%`;
  }

  function renderFiscalYearRows(tableBody, fiscalYears) {
    if (!tableBody) {
      return;
    }
    const rows = Array.isArray(fiscalYears) ? fiscalYears : [];
    if (!rows.length) {
      tableBody.innerHTML = `<tr><td colspan="5" class="st-detail-metrics-empty">年度別データがありません。</td></tr>`;
      return;
    }
    tableBody.innerHTML = rows
      .map((row) => {
        const year = row.fiscalYear ?? "";
        return `<tr>
          <td>${escapeChartAttr(year)}</td>
          <td>${escapeChartAttr(formatChartQtyLabel(row.fyTotal))}</td>
          <td>${escapeChartAttr(formatChartQtyLabel(row.fyWithForecastTotal))}</td>
          <td>${escapeChartAttr(formatChartQtyLabel(row.changeQty))}</td>
          <td>${escapeChartAttr(formatChangeRateLabel(row.changeRatePct))}</td>
        </tr>`;
      })
      .join("");
  }

  function buildDetailTitle(custCode, custName) {
    const code = String(custCode || "").trim();
    const name = String(custName || "").trim();
    if (code && name) {
      return `${code} - ${name}`;
    }
    return code || name || "詳細";
  }

  function bindDetailDialog() {
    const pageRoot = document.querySelector(".shipment-trend-page");
    const tableWrap = pageRoot?.querySelector(".st-table-wrap");
    const dialog = document.getElementById("st-detail-dialog");
    const title = dialog?.querySelector(".st-detail-title");
    const meta = dialog?.querySelector(".st-detail-meta");
    const metricsTableBody = dialog?.querySelector(".st-detail-metrics-table-body");
    const canvasWrap = dialog?.querySelector(".st-chart-canvas-wrap");
    const errorEl = dialog?.querySelector(".st-detail-error");
    const closeButton = dialog?.querySelector(".st-detail-close");
    if (!pageRoot || !tableWrap || !dialog || !canvasWrap) {
      return;
    }

    bindChartMarkerTooltips(canvasWrap);

    closeButton?.addEventListener("click", () => dialog.close());
    dialog.addEventListener("click", (event) => {
      if (event.target === dialog) {
        dialog.close();
      }
    });

    tableWrap.addEventListener("click", async (event) => {
      const target = event.target;
      if (!(target instanceof Element)) {
        return;
      }
      const row = target.closest(".st-data-row");
      if (!row) {
        return;
      }
      if (target.closest("select, option, button, a, label, textarea")) {
        return;
      }
      const custCode = row.getAttribute("data-cust-code") || "";
      const custName = row.getAttribute("data-cust-name") || "";
      const itemCd = row.getAttribute("data-item-cd") || "";
      if (!custCode || !itemCd) {
        return;
      }
      if (title) {
        title.textContent = buildDetailTitle(custCode, custName);
      }
      if (meta) {
        meta.textContent = `得意先品番: ${itemCd}`;
      }
      if (errorEl) {
        errorEl.hidden = true;
        errorEl.textContent = "";
      }
      renderFiscalYearRows(metricsTableBody, []);
      clearChartCanvas(canvasWrap);
      if (typeof dialog.showModal === "function") {
        dialog.showModal();
      } else {
        dialog.setAttribute("open", "open");
      }
      try {
        const response = await fetch(
          `${CHART_API}?custCode=${encodeURIComponent(custCode)}&itemCd=${encodeURIComponent(itemCd)}`,
          { credentials: "same-origin", headers: { Accept: "application/json" } },
        );
        let body;
        try {
          body = await response.json();
        } catch (_parseError) {
          throw new Error("詳細の取得に失敗しました。");
        }
        if (!response.ok || !body.ok) {
          const message =
            body?.message ||
            body?.error?.message ||
            "詳細の取得に失敗しました。";
          if (errorEl) {
            errorEl.hidden = false;
            errorEl.textContent = message;
          }
          renderFiscalYearRows(metricsTableBody, []);
          clearChartCanvas(canvasWrap);
          return;
        }
        const chart = body.chart || {};
        if (title) {
          title.textContent = buildDetailTitle(chart.custCode || custCode, chart.custName || custName);
        }
        if (meta) {
          const chrg = chart.custChrgPsnCd ? ` / 担当者コード: ${chart.custChrgPsnCd}` : "";
          meta.textContent = `得意先品番: ${chart.itemCd || itemCd}${chrg}`;
        }
        renderFiscalYearRows(metricsTableBody, chart.fiscalYears || []);
        if (!(chart.points || []).length) {
          if (errorEl) {
            errorEl.hidden = false;
            errorEl.textContent = "グラフ用の月次データがありません。";
          }
          clearChartCanvas(canvasWrap);
          return;
        }
        renderChart(canvasWrap, chart, dialog);
      } catch (_error) {
        if (errorEl) {
          errorEl.hidden = false;
          errorEl.textContent = "詳細の取得に失敗しました。";
        }
        renderFiscalYearRows(metricsTableBody, []);
        clearChartCanvas(canvasWrap);
      }
    });
  }

  function initListClientSafely() {
    try {
      return window.ShipmentTrendListClient?.init?.() || null;
    } catch (_error) {
      return null;
    }
  }

  function initShipmentTrendPage() {
    bindDetailDialog();
    bindAlertSettings();
    initRefreshForm();
    const listClient = initListClientSafely();
    window.__shipmentTrendListClient = listClient;
    bindSortDialog(listClient);
  }

  onReady(initShipmentTrendPage);

  window.ShipmentTrendChart = {
    buildChartSvgMarkup,
    renderChart,
    buildYAxisScale,
    formatChartQtyLabel,
    formatMonthAxisLabel,
    buildMarkerTooltipLabel,
    escapeChartAttr,
    ensureChartCanvasStructure,
    bindChartMarkerTooltips,
    measureChartContainerWidth,
    resolveChartLayout,
    buildDetailTitle,
    formatChangeRateLabel,
    renderFiscalYearRows,
    CHART_HEIGHT,
  };
})();

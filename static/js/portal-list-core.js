(function () {
  const MAX_SORT_SPECS = 5;

  function escapeHtml(value) {
    return String(value ?? "")
      .replace(/&/g, "&amp;")
      .replace(/</g, "&lt;")
      .replace(/>/g, "&gt;")
      .replace(/"/g, "&quot;");
  }

  function parseSortSpecs(sortRaw, dirRaw, defaultSpecs, defaultDirectionForColumn) {
    const columns = String(sortRaw || "")
      .split(",")
      .map((value) => value.trim())
      .filter(Boolean);
    const directions = String(dirRaw || "")
      .split(",")
      .map((value) => value.trim().toLowerCase())
      .filter(Boolean);
    if (!columns.length || columns[0] === "default") {
      return defaultSpecs.map((spec) => ({ ...spec }));
    }
    const specs = [];
    const seen = new Set();
    for (let index = 0; index < columns.length; index += 1) {
      const column = columns[index];
      if (seen.has(column)) {
        continue;
      }
      seen.add(column);
      let direction = directions[index] || directions[directions.length - 1] || defaultDirectionForColumn(column);
      if (direction !== "asc" && direction !== "desc") {
        direction = defaultDirectionForColumn(column);
      }
      specs.push({ column, direction });
      if (specs.length >= MAX_SORT_SPECS) {
        break;
      }
    }
    return specs.length ? specs : defaultSpecs.map((spec) => ({ ...spec }));
  }

  function readBaseStateFromUrl(defaults, defaultDirectionForColumn) {
    const params = new URLSearchParams(window.location.search);
    return {
      sortSpecs: parseSortSpecs(
        params.get("sort"),
        params.get("dir"),
        defaults.defaultSortSpecs,
        defaultDirectionForColumn,
      ),
      page: Math.max(1, Number.parseInt(params.get("page") || "1", 10) || 1),
      pageSize: defaults.pageSizeOptions.includes(Number(params.get("page_size")))
        ? Number(params.get("page_size"))
        : defaults.defaultPageSize,
    };
  }

  function paginateRows(rows, page, pageSize) {
    const totalCount = rows.length;
    if (!totalCount) {
      return {
        rows: [],
        totalCount: 0,
        page: 1,
        pageSize,
        totalPages: 1,
        startIndex: 0,
        endIndex: 0,
        hasPrevious: false,
        hasNext: false,
      };
    }
    const totalPages = Math.max(1, Math.ceil(totalCount / pageSize));
    const currentPage = Math.min(Math.max(page, 1), totalPages);
    const start = (currentPage - 1) * pageSize;
    const pageRows = rows.slice(start, start + pageSize);
    return {
      rows: pageRows,
      totalCount,
      page: currentPage,
      pageSize,
      totalPages,
      startIndex: start + 1,
      endIndex: start + pageRows.length,
      hasPrevious: currentPage > 1,
      hasNext: currentPage < totalPages,
    };
  }

  function toggleSortDirection(sortSpecs, column, defaultDirectionForColumn) {
    const current = sortSpecs.find((spec) => spec.column === column);
    if (current) {
      return current.direction === "asc" ? "desc" : "asc";
    }
    return defaultDirectionForColumn(column);
  }

  function compareSortValues(leftValue, rightValue) {
    const leftParts = Array.isArray(leftValue) ? leftValue : [leftValue];
    const rightParts = Array.isArray(rightValue) ? rightValue : [rightValue];
    for (let index = 0; index < Math.max(leftParts.length, rightParts.length); index += 1) {
      const leftPart = leftParts[index] ?? "";
      const rightPart = rightParts[index] ?? "";
      if (leftPart < rightPart) {
        return -1;
      }
      if (leftPart > rightPart) {
        return 1;
      }
    }
    return 0;
  }

  function sortRows(rows, sortSpecs, sortValue, tiebreakers) {
    const sorted = rows.slice();
    const activeColumns = new Set(sortSpecs.map((spec) => spec.column));
    const fullSpecs = sortSpecs.concat((tiebreakers || []).filter((spec) => !activeColumns.has(spec.column)));
    for (let specIndex = fullSpecs.length - 1; specIndex >= 0; specIndex -= 1) {
      const spec = fullSpecs[specIndex];
      const reverse = spec.direction === "desc";
      sorted.sort((left, right) => {
        const comparison = compareSortValues(sortValue(left, spec.column), sortValue(right, spec.column));
        return reverse ? -comparison : comparison;
      });
    }
    return sorted;
  }

  function appendSortQueryParams(params, sortSpecs, page, pageSize) {
    params.set("sort", sortSpecs.map((spec) => spec.column).join(","));
    params.set("dir", sortSpecs.map((spec) => spec.direction).join(","));
    params.set("page", String(page));
    params.set("page_size", String(pageSize));
  }

  function replaceUrl(pathname, queryString) {
    const nextUrl = queryString ? `${pathname}?${queryString}` : pathname;
    if (`${window.location.pathname}${window.location.search}` !== nextUrl) {
      window.history.replaceState(null, "", nextUrl);
    }
  }

  function renderTableHeaders(tableHead, options) {
    if (!tableHead) {
      return;
    }
    const {
      sortableColumns,
      sortSpecs,
      sortColumnDataAttr,
      sortPriorityClass,
      headerMode,
      headerButtonClass,
      onColumnClick,
    } = options;
    const sortIndexMap = new Map(sortSpecs.map((spec, index) => [spec.column, index + 1]));
    const headerCells = sortableColumns
      .map((column) => {
        const sortIndex = sortIndexMap.get(column.key);
        const sorted = sortIndex !== undefined;
        const direction = sorted
          ? sortSpecs.find((spec) => spec.column === column.key)?.direction || "asc"
          : "";
        const arrow = sorted ? (direction === "asc" ? " ▲" : " ▼") : "";
        const priority = sorted ? `<span class="${sortPriorityClass}">${sortIndex}</span>` : "";
        const thClass = sorted ? `is-sorted is-sorted--${direction}` : "";
        const label = `${priority}${escapeHtml(column.label)}${arrow}`;
        if (headerMode === "button") {
          const buttonClass = headerButtonClass || "portal-sort-header";
          return `<th scope="col" class="${thClass}"><button type="button" class="${buttonClass}" ${sortColumnDataAttr}="${escapeHtml(column.key)}">${label}</button></th>`;
        }
        return `<th scope="col" class="${thClass}"><a href="#" ${sortColumnDataAttr}="${escapeHtml(column.key)}">${label}</a></th>`;
      })
      .join("");
    tableHead.innerHTML = `<tr>${headerCells}</tr>`;
    tableHead.querySelectorAll(`[${sortColumnDataAttr}]`).forEach((element) => {
      element.addEventListener("click", (event) => {
        event.preventDefault();
        const column = element.getAttribute(sortColumnDataAttr);
        if (column) {
          onColumnClick(column);
        }
      });
    });
  }

  function renderPagination(elements, pagination) {
    const { footer, rangeElement, prevButton, nextButton } = elements;
    if (!footer) {
      return;
    }
    footer.hidden = pagination.totalCount === 0;
    if (pagination.totalCount === 0) {
      return;
    }
    if (rangeElement) {
      rangeElement.textContent = `${pagination.startIndex}–${pagination.endIndex} 件目を表示（${pagination.page} / ${pagination.totalPages} ページ）`;
    }
    if (prevButton) {
      prevButton.disabled = !pagination.hasPrevious;
      prevButton.classList.toggle("is-disabled", !pagination.hasPrevious);
    }
    if (nextButton) {
      nextButton.disabled = !pagination.hasNext;
      nextButton.classList.toggle("is-disabled", !pagination.hasNext);
    }
  }

  function bindPaginationControls(elements, getPage, setPage) {
    elements.pageSizeSelect?.addEventListener("change", () => {
      setPage({
        pageSize: Number(elements.pageSizeSelect.value),
        page: 1,
      });
    });
    elements.prevButton?.addEventListener("click", () => {
      const page = getPage();
      if (page > 1) {
        setPage({ page: page - 1 });
      }
    });
    elements.nextButton?.addEventListener("click", () => {
      setPage({ page: getPage() + 1 });
    });
  }

  window.PortalListCore = {
    MAX_SORT_SPECS,
    escapeHtml,
    parseSortSpecs,
    readBaseStateFromUrl,
    paginateRows,
    toggleSortDirection,
    compareSortValues,
    sortRows,
    appendSortQueryParams,
    replaceUrl,
    renderTableHeaders,
    renderPagination,
    bindPaginationControls,
  };
})();

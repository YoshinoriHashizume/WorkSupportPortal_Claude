(function () {
  function refreshSortRowOrders(container, rowClass, orderClass) {
    container.querySelectorAll(`.${rowClass}`).forEach((row, index) => {
      const order = row.querySelector(`.${orderClass}`);
      if (order) {
        order.textContent = String(index + 1);
      }
    });
  }

  function syncSortDialogRows(listClient, rowsContainer, template, bindRow, options) {
    const sortableColumns = listClient.getSortableColumns();
    const sortSpecs = listClient.getSortSpecs();
    rowsContainer.replaceChildren();
    sortSpecs.forEach((spec) => {
      const fragment = template.content.cloneNode(true);
      const row = fragment.querySelector(`.${options.rowClass}`);
      const columnSelect = row.querySelector(`.${options.columnClass}`);
      const directionSelect = row.querySelector(`.${options.directionClass}`);
      columnSelect.replaceChildren();
      sortableColumns.forEach((column) => {
        const option = document.createElement("option");
        option.value = column.key;
        option.textContent = column.label;
        if (column.key === spec.column) {
          option.selected = true;
        }
        columnSelect.append(option);
      });
      directionSelect.value = spec.direction === "desc" ? "desc" : "asc";
      rowsContainer.append(fragment);
      bindRow(row);
    });
    refreshSortRowOrders(rowsContainer, options.rowClass, options.orderClass);
  }

  function initSortDialog(config) {
    const {
      dialog,
      openButton,
      listClient,
      maxSortRows = 5,
      rowClass,
      orderClass,
      columnClass,
      directionClass,
      removeClass,
      formClass,
      rowsContainerClass,
      template,
      addButtonClass,
      cancelButtonClass,
    } = config;

    if (!dialog || !openButton) {
      return;
    }

    const form = dialog.querySelector(`.${formClass}`);
    const rowsContainer = dialog.querySelector(`.${rowsContainerClass}`);
    const addButton = dialog.querySelector(`.${addButtonClass}`);
    const cancelButton = dialog.querySelector(`.${cancelButtonClass}`);
    if (!form || !rowsContainer || !template) {
      return;
    }

    const options = { rowClass, orderClass, columnClass, directionClass, removeClass };
    let draggedSortRow = null;

    function bindSortRowDrag(row) {
      const handle = row.querySelector(`.${orderClass}`);
      if (!handle || handle.dataset.dragBound === "true") {
        return;
      }
      handle.dataset.dragBound = "true";
      handle.setAttribute("draggable", "true");
      handle.setAttribute("aria-label", "ドラッグして順序を変更");
      handle.setAttribute("title", "ドラッグして順序を変更");

      handle.addEventListener("dragstart", (event) => {
        draggedSortRow = row;
        row.classList.add("is-dragging");
        event.dataTransfer.effectAllowed = "move";
        event.dataTransfer.setData("text/plain", "");
      });

      handle.addEventListener("dragend", () => {
        row.classList.remove("is-dragging");
        draggedSortRow = null;
        refreshSortRowOrders(rowsContainer, rowClass, orderClass);
      });
    }

    rowsContainer.addEventListener("dragover", (event) => {
      if (!draggedSortRow) {
        return;
      }
      const targetRow = event.target.closest(`.${rowClass}`);
      if (!targetRow || targetRow === draggedSortRow) {
        return;
      }
      event.preventDefault();
      const rect = targetRow.getBoundingClientRect();
      const insertAfter = event.clientY > rect.top + rect.height / 2;
      rowsContainer.insertBefore(draggedSortRow, insertAfter ? targetRow.nextSibling : targetRow);
    });

    function bindRemoveButton(row) {
      const removeButton = row.querySelector(`.${removeClass}`);
      if (!removeButton) {
        return;
      }
      removeButton.addEventListener("click", () => {
        const rows = rowsContainer.querySelectorAll(`.${rowClass}`);
        if (rows.length <= 1) {
          return;
        }
        row.remove();
        refreshSortRowOrders(rowsContainer, rowClass, orderClass);
      });
    }

    function bindRow(row) {
      bindRemoveButton(row);
      bindSortRowDrag(row);
    }

    rowsContainer.querySelectorAll(`.${rowClass}`).forEach((row) => {
      bindRow(row);
    });

    openButton.addEventListener("click", () => {
      if (listClient) {
        syncSortDialogRows(listClient, rowsContainer, template, bindRow, options);
      }
      if (typeof dialog.showModal === "function") {
        dialog.showModal();
      }
    });

    cancelButton?.addEventListener("click", () => {
      dialog.close();
    });

    dialog.addEventListener("click", (event) => {
      if (event.target === dialog) {
        dialog.close();
      }
    });

    addButton?.addEventListener("click", () => {
      const currentCount = rowsContainer.querySelectorAll(`.${rowClass}`).length;
      if (currentCount >= maxSortRows) {
        return;
      }
      const fragment = template.content.cloneNode(true);
      const row = fragment.querySelector(`.${rowClass}`);
      rowsContainer.appendChild(fragment);
      bindRow(row);
      refreshSortRowOrders(rowsContainer, rowClass, orderClass);
    });

    form.addEventListener("submit", (event) => {
      event.preventDefault();
      const specs = [];
      rowsContainer.querySelectorAll(`.${rowClass}`).forEach((row) => {
        const column = row.querySelector(`.${columnClass}`);
        const direction = row.querySelector(`.${directionClass}`);
        if (!column || !direction) {
          return;
        }
        const columnValue = column.value.trim();
        if (!columnValue || specs.some((spec) => spec.column === columnValue)) {
          return;
        }
        specs.push({
          column: columnValue,
          direction: direction.value === "desc" ? "desc" : "asc",
        });
      });
      if (!specs.length || !listClient) {
        return;
      }
      listClient.applySortSpecs(specs);
      dialog.close();
    });
  }

  window.PortalListSortDialog = {
    init: initSortDialog,
    syncRows: syncSortDialogRows,
  };
})();

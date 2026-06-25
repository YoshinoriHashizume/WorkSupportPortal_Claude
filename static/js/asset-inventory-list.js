(function () {
  const MAX_SORT_ROWS = 5;

  function refreshSortRowOrders(container) {
    container.querySelectorAll(".aiv-sort-row").forEach((row, index) => {
      const order = row.querySelector(".aiv-sort-row-order");
      if (order) {
        order.textContent = String(index + 1);
      }
    });
  }

  function initSortDialog() {
    const dialog = document.getElementById("aiv-sort-dialog");
    const openButton = document.querySelector(".asset-inventory-page .aiv-sort-open");
    if (!dialog || !openButton) {
      return;
    }

    const form = dialog.querySelector(".aiv-sort-form");
    const rowsContainer = dialog.querySelector(".aiv-sort-rows");
    const template = dialog.querySelector("#aiv-sort-row-template");
    const addButton = dialog.querySelector(".aiv-sort-add");
    const cancelButton = dialog.querySelector(".aiv-sort-cancel");
    const sortInput = form.querySelector('input[name="sort"]');
    const dirInput = form.querySelector('input[name="dir"]');
    let draggedSortRow = null;

    function bindSortRowDrag(row) {
      const handle = row.querySelector(".aiv-sort-row-order");
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
        refreshSortRowOrders(rowsContainer);
      });
    }

    rowsContainer.addEventListener("dragover", (event) => {
      if (!draggedSortRow) {
        return;
      }
      const targetRow = event.target.closest(".aiv-sort-row");
      if (!targetRow || targetRow === draggedSortRow) {
        return;
      }
      event.preventDefault();
      const rect = targetRow.getBoundingClientRect();
      const insertAfter = event.clientY > rect.top + rect.height / 2;
      rowsContainer.insertBefore(draggedSortRow, insertAfter ? targetRow.nextSibling : targetRow);
    });

    function bindRemoveButton(row) {
      const removeButton = row.querySelector(".aiv-sort-remove");
      if (!removeButton) {
        return;
      }
      removeButton.addEventListener("click", () => {
        const rows = rowsContainer.querySelectorAll(".aiv-sort-row");
        if (rows.length <= 1) {
          return;
        }
        row.remove();
        refreshSortRowOrders(rowsContainer);
      });
    }

    rowsContainer.querySelectorAll(".aiv-sort-row").forEach((row) => {
      bindRemoveButton(row);
      bindSortRowDrag(row);
    });

    openButton.addEventListener("click", () => {
      if (typeof dialog.showModal === "function") {
        dialog.showModal();
      }
    });

    cancelButton.addEventListener("click", () => {
      dialog.close();
    });

    dialog.addEventListener("click", (event) => {
      if (event.target === dialog) {
        dialog.close();
      }
    });

    addButton.addEventListener("click", () => {
      const currentCount = rowsContainer.querySelectorAll(".aiv-sort-row").length;
      if (currentCount >= MAX_SORT_ROWS || !template) {
        return;
      }
      const fragment = template.content.cloneNode(true);
      const row = fragment.querySelector(".aiv-sort-row");
      rowsContainer.appendChild(fragment);
      bindRemoveButton(row);
      bindSortRowDrag(row);
      refreshSortRowOrders(rowsContainer);
    });

    form.addEventListener("submit", (event) => {
      const columns = [];
      const directions = [];
      rowsContainer.querySelectorAll(".aiv-sort-row").forEach((row) => {
        const column = row.querySelector(".aiv-sort-column");
        const direction = row.querySelector(".aiv-sort-direction");
        if (!column || !direction) {
          return;
        }
        const columnValue = column.value.trim();
        if (!columnValue || columns.includes(columnValue)) {
          return;
        }
        columns.push(columnValue);
        directions.push(direction.value === "desc" ? "desc" : "asc");
      });
      if (!columns.length) {
        event.preventDefault();
        return;
      }
      sortInput.value = columns.join(",");
      dirInput.value = directions.join(",");
    });
  }

  document.addEventListener("DOMContentLoaded", () => {
    initSortDialog();
    initRowColorDialog();
  });

  function initRowColorDialog() {
    const dialog = document.getElementById("aiv-row-color-dialog");
    const openButton = document.querySelector(".asset-inventory-page .aiv-row-color-open");
    const closeButton = dialog?.querySelector(".aiv-row-color-close");
    if (!dialog || !openButton || !closeButton) {
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
  }
})();

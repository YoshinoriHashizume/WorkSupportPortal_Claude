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
    initRowDetailDialog();
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

  function initRowDetailDialog() {
    const dialog = document.getElementById("aiv-row-detail-dialog");
    const detailsElement = document.getElementById("aiv-row-details-data");
    if (!dialog || !detailsElement) {
      return;
    }

    let detailsByKey = {};
    try {
      const parsed = JSON.parse(detailsElement.textContent || "{}");
      detailsByKey = parsed && typeof parsed === "object" && !Array.isArray(parsed) ? parsed : {};
    } catch (_error) {
      return;
    }

    const title = dialog.querySelector(".aiv-row-detail-title");
    const meta = dialog.querySelector(".aiv-row-detail-meta");
    const assetImage = dialog.querySelector(".aiv-row-detail-photo-asset");
    const plateImage = dialog.querySelector(".aiv-row-detail-photo-plate");
    const assetEmpty = dialog.querySelector(".aiv-row-detail-photo-empty--asset");
    const plateEmpty = dialog.querySelector(".aiv-row-detail-photo-empty--plate");
    const compareTableBody = dialog.querySelector(".aiv-row-detail-compare-table tbody");
    const compareScroll = dialog.querySelector(".aiv-row-detail-compare-scroll");
    const closeButton = dialog.querySelector(".aiv-row-detail-close");

    function clearPhoto(image, emptyLabel) {
      if (!image || !emptyLabel) {
        return;
      }
      image.onload = null;
      image.onerror = null;
      image.removeAttribute("src");
      image.hidden = true;
      image.classList.remove("is-clickable");
      image.removeAttribute("role");
      image.removeAttribute("tabindex");
      image.removeAttribute("aria-label");
      emptyLabel.hidden = false;
    }

    function resetDetailDialog() {
      if (title) {
        title.textContent = "";
      }
      if (meta) {
        meta.textContent = "";
      }
      clearPhoto(assetImage, assetEmpty);
      clearPhoto(plateImage, plateEmpty);
      if (compareTableBody) {
        compareTableBody.replaceChildren();
      }
      if (compareScroll) {
        compareScroll.scrollTop = 0;
      }
    }

    function showLoadedPhoto(image, emptyLabel) {
      if (!image || !emptyLabel) {
        return;
      }
      image.hidden = false;
      emptyLabel.hidden = true;
      image.classList.add("is-clickable");
      image.setAttribute("role", "button");
      image.setAttribute("tabindex", "0");
      image.setAttribute("aria-label", `${image.alt || "写真"}を拡大表示`);
      image.onload = null;
      image.onerror = null;
    }

    function setPhoto(image, emptyLabel, href) {
      if (!image || !emptyLabel) {
        return;
      }
      clearPhoto(image, emptyLabel);
      if (!href || !href.startsWith("/")) {
        return;
      }
      image.loading = "eager";
      image.onload = () => {
        showLoadedPhoto(image, emptyLabel);
      };
      image.onerror = () => {
        clearPhoto(image, emptyLabel);
      };
      image.src = href;
      if (image.complete && image.naturalWidth > 0) {
        showLoadedPhoto(image, emptyLabel);
      }
    }

    function openDetail(rowKey) {
      resetDetailDialog();

      const detail = detailsByKey[rowKey];
      if (!detail || !title || !meta) {
        return;
      }

      title.textContent = detail.title || "";
      meta.textContent = `棚卸結果: ${detail.status_label || ""} / 変化状況: ${detail.tone_label || ""}`;

      const photos = Array.isArray(detail.photos) ? detail.photos : [];
      const assetPhoto = photos.find((photo) => photo.label === "資産写真");
      const platePhoto = photos.find((photo) => photo.label === "資産プレート写真");

      const comparisons = Array.isArray(detail.field_comparisons) ? detail.field_comparisons : [];
      if (compareTableBody) {
        comparisons.forEach((item) => {
          const row = document.createElement("tr");
          if (item.is_diff) {
            row.classList.add("is-diff");
          }
          const labelCell = document.createElement("th");
          labelCell.scope = "row";
          labelCell.textContent = item.label || "";
          const assetCell = document.createElement("td");
          assetCell.textContent = item.asset_value || "";
          const inventoryCell = document.createElement("td");
          inventoryCell.textContent = item.inventory_value || "";
          row.append(labelCell, assetCell, inventoryCell);
          compareTableBody.appendChild(row);
        });
      }

      if (typeof dialog.showModal === "function") {
        dialog.showModal();
      }

      setPhoto(assetImage, assetEmpty, assetPhoto?.href || "");
      setPhoto(plateImage, plateEmpty, platePhoto?.href || "");
    }

    const tableBody = document.querySelector(".asset-inventory-page .aiv-table tbody");
    if (!tableBody) {
      return;
    }

    tableBody.addEventListener("click", (event) => {
      const row = event.target.closest(".aiv-table-row--clickable");
      if (!row) {
        return;
      }
      const rowKey = row.getAttribute("data-aiv-row-key");
      if (rowKey) {
        openDetail(rowKey);
      }
    });

    tableBody.addEventListener("keydown", (event) => {
      const row = event.target.closest(".aiv-table-row--clickable");
      if (!row || (event.key !== "Enter" && event.key !== " ")) {
        return;
      }
      event.preventDefault();
      const rowKey = row.getAttribute("data-aiv-row-key");
      if (rowKey) {
        openDetail(rowKey);
      }
    });

    closeButton?.addEventListener("click", () => {
      dialog.close();
      resetDetailDialog();
    });

    dialog.addEventListener("click", (event) => {
      if (event.target === dialog) {
        dialog.close();
        resetDetailDialog();
      }
    });

    initPhotoZoomDialog(dialog);
  }

  function initPhotoZoomDialog(detailDialog) {
    const zoomDialog = document.getElementById("aiv-photo-zoom-dialog");
    const photosContainer = detailDialog?.querySelector(".aiv-row-detail-photos");
    if (!zoomDialog || !photosContainer) {
      return;
    }

    const zoomImage = zoomDialog.querySelector(".aiv-photo-zoom-image");
    const zoomCaption = zoomDialog.querySelector(".aiv-photo-zoom-caption");
    const zoomClose = zoomDialog.querySelector(".aiv-photo-zoom-close");

    function resetPhotoZoom() {
      if (zoomCaption) {
        zoomCaption.textContent = "";
      }
      if (zoomImage) {
        zoomImage.removeAttribute("src");
        zoomImage.alt = "";
      }
    }

    function openPhotoZoom(image) {
      if (!image || image.hidden || !image.src) {
        return;
      }
      if (zoomCaption) {
        zoomCaption.textContent = image.alt || "";
      }
      if (zoomImage) {
        zoomImage.alt = image.alt || "";
        zoomImage.src = image.src;
      }
      if (typeof zoomDialog.showModal === "function") {
        zoomDialog.showModal();
      }
    }

    photosContainer.addEventListener("click", (event) => {
      const image = event.target.closest("img.is-clickable");
      if (!image || image.hidden || !image.src) {
        return;
      }
      event.preventDefault();
      openPhotoZoom(image);
    });

    photosContainer.addEventListener("keydown", (event) => {
      const image = event.target.closest("img.is-clickable");
      if (!image || (event.key !== "Enter" && event.key !== " ")) {
        return;
      }
      event.preventDefault();
      openPhotoZoom(image);
    });

    zoomClose?.addEventListener("click", () => {
      zoomDialog.close();
      resetPhotoZoom();
    });

    zoomDialog.addEventListener("click", (event) => {
      if (event.target === zoomDialog) {
        zoomDialog.close();
        resetPhotoZoom();
      }
    });

    zoomDialog.addEventListener("close", () => {
      resetPhotoZoom();
    });
  }
})();

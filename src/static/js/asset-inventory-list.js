(function () {
  function initSortDialog(listClient) {
    window.PortalListSortDialog?.init({
      dialog: document.getElementById("aiv-sort-dialog"),
      openButton: document.querySelector(".asset-inventory-page .aiv-sort-open"),
      listClient,
      maxSortRows: 5,
      rowClass: "aiv-sort-row",
      orderClass: "aiv-sort-row-order",
      columnClass: "aiv-sort-column",
      directionClass: "aiv-sort-direction",
      removeClass: "aiv-sort-remove",
      formClass: "aiv-sort-form",
      rowsContainerClass: "aiv-sort-rows",
      template: document.querySelector("#aiv-sort-row-template"),
      addButtonClass: "aiv-sort-add",
      cancelButtonClass: "aiv-sort-cancel",
    });
  }

  document.addEventListener("DOMContentLoaded", () => {
    const listClient = window.AivListClient?.init() || null;
    initSortDialog(listClient);
    initRowColorDialog();
    initRowDetailDialog(listClient);
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

  function initRowDetailDialog(listClient) {
    const dialog = document.getElementById("aiv-row-detail-dialog");
    if (!dialog) {
      return;
    }

    let detailsByKey = {};
    if (listClient) {
      detailsByKey = listClient.getRowDetails();
    } else {
      const detailsElement = document.getElementById("aiv-row-details-data");
      if (!detailsElement) {
        return;
      }
      try {
        const parsed = JSON.parse(detailsElement.textContent || "{}");
        detailsByKey = parsed && typeof parsed === "object" && !Array.isArray(parsed) ? parsed : {};
      } catch (_error) {
        return;
      }
    }

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
      if (!detail) {
        return;
      }

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

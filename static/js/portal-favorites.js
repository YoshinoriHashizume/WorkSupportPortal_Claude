(function () {
  function requestJson(url, options) {
    return fetch(url, {
      ...options,
      headers: {
        "Content-Type": "application/json",
        "X-CSRFToken": window.portalCsrfToken || "",
        ...(options.headers || {}),
      },
    });
  }

  function favoriteTogglesFor(menuKey) {
    return document.querySelectorAll(`.favorite-toggle[data-menu-key="${CSS.escape(menuKey)}"]`);
  }

  async function addFavorite(menuKey) {
    const response = await requestJson("/api/favorite-menus", {
      method: "POST",
      body: JSON.stringify({ menuKey }),
    });
    if (!response.ok) throw new Error("favorite add failed");
  }

  async function removeFavorite(menuKey) {
    const response = await requestJson(`/api/favorite-menus/${encodeURIComponent(menuKey)}`, {
      method: "DELETE",
    });
    if (!response.ok) throw new Error("favorite delete failed");
  }

  async function saveFavoriteOrder(menuKeys) {
    const response = await requestJson("/api/favorite-menus/order", {
      method: "PATCH",
      body: JSON.stringify({ menuKeys }),
    });
    if (!response.ok) throw new Error("favorite order failed");
  }

  document.querySelectorAll(".favorite-toggle").forEach((button) => {
    button.addEventListener("click", async (event) => {
      event.preventDefault();
      event.stopPropagation();

      const menuKey = button.dataset.menuKey;
      const menuTitle = button.dataset.menuTitle || "このメニュー";
      const isFavorite = button.classList.contains("is-favorite");
      if (!menuKey) return;

      try {
        if (isFavorite) {
          if (!window.confirm(`「${menuTitle}」をお気に入りから削除します。よろしいですか？`)) return;
          await removeFavorite(menuKey);
        } else {
          await addFavorite(menuKey);
        }
        window.location.reload();
      } catch (error) {
        alert("お気に入りの更新に失敗しました。時間をおいて再度お試しください。");
      }
    });
  });

  const grid = document.querySelector("#favorite-card-grid");
  if (!grid) return;

  let draggedCard = null;
  grid.querySelectorAll(".favorite-card").forEach((card) => {
    card.addEventListener("dragstart", () => {
      draggedCard = card;
      card.classList.add("is-dragging");
    });

    card.addEventListener("dragend", async () => {
      card.classList.remove("is-dragging");
      draggedCard = null;
      const menuKeys = [...grid.querySelectorAll(".favorite-card")].map((item) => item.dataset.menuKey);
      try {
        await saveFavoriteOrder(menuKeys);
      } catch (error) {
        alert("お気に入りの並び順保存に失敗しました。");
      }
    });

    card.addEventListener("dragover", (event) => {
      event.preventDefault();
      if (!draggedCard || draggedCard === card) return;
      const rect = card.getBoundingClientRect();
      const insertAfter = event.clientX > rect.left + rect.width / 2;
      grid.insertBefore(draggedCard, insertAfter ? card.nextSibling : card);
    });
  });
})();

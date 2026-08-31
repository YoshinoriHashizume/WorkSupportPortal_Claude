(function () {
  const STORAGE_KEY = "portal-sidebar-expanded";
  const SCROLL_STORAGE_KEY = "portal-sidebar-nav-scroll-top";
  const SCROLL_SAVE_DEBOUNCE_MS = 100;

  function loadState() {
    try {
      const raw = localStorage.getItem(STORAGE_KEY);
      if (!raw) return { groups: {}, branches: {} };
      const parsed = JSON.parse(raw);
      return {
        groups: parsed.groups || {},
        branches: parsed.branches || {},
      };
    } catch (_error) {
      return { groups: {}, branches: {} };
    }
  }

  function saveState(state) {
    localStorage.setItem(STORAGE_KEY, JSON.stringify(state));
  }

  function saveScrollPosition(nav) {
    sessionStorage.setItem(SCROLL_STORAGE_KEY, String(nav.scrollTop));
  }

  function restoreScrollPosition(nav) {
    const saved = sessionStorage.getItem(SCROLL_STORAGE_KEY);
    if (saved !== null) {
      nav.scrollTop = Number(saved) || 0;
      return;
    }
    const activeLink = nav.querySelector(".sidebar-menu-item.is-active a");
    if (activeLink) {
      activeLink.scrollIntoView({ block: "nearest" });
    }
  }

  function restoreScrollAfterLayout(nav) {
    requestAnimationFrame(() => {
      requestAnimationFrame(() => {
        restoreScrollPosition(nav);
      });
    });
  }

  function bindScrollPersistence(nav) {
    let debounceTimer = null;
    nav.addEventListener("scroll", () => {
      if (debounceTimer !== null) {
        window.clearTimeout(debounceTimer);
      }
      debounceTimer = window.setTimeout(() => {
        debounceTimer = null;
        saveScrollPosition(nav);
      }, SCROLL_SAVE_DEBOUNCE_MS);
    });

    nav.addEventListener("click", (event) => {
      const link = event.target.closest("a[href]");
      if (!link || !nav.contains(link)) {
        return;
      }
      saveScrollPosition(nav);
    });
  }

  function applyStoredState() {
    const state = loadState();

    document.querySelectorAll("details.sidebar-menu-group[data-menu-group-key]").forEach((details) => {
      const key = details.dataset.menuGroupKey;
      const stored = state.groups[key];
      if (details.dataset.sidebarForceOpen === "true") {
        details.open = true;
        return;
      }
      if (typeof stored === "boolean") {
        details.open = stored;
      }
    });

    document.querySelectorAll("details.sidebar-menu-branch[data-menu-key]").forEach((details) => {
      const key = details.dataset.menuKey;
      const stored = state.branches[key];
      if (details.dataset.sidebarForceOpen === "true") {
        details.open = true;
        return;
      }
      if (typeof stored === "boolean") {
        details.open = stored;
      }
    });
  }

  function bindPersistence() {
    document.querySelectorAll("details.sidebar-menu-group[data-menu-group-key]").forEach((details) => {
      details.addEventListener("toggle", () => {
        const state = loadState();
        state.groups[details.dataset.menuGroupKey] = details.open;
        saveState(state);
      });
    });

    document.querySelectorAll("details.sidebar-menu-branch[data-menu-key]").forEach((details) => {
      details.addEventListener("toggle", () => {
        const state = loadState();
        state.branches[details.dataset.menuKey] = details.open;
        saveState(state);
      });
    });
  }

  const nav = document.querySelector(".sidebar-nav");
  applyStoredState();
  bindPersistence();
  if (nav) {
    bindScrollPersistence(nav);
    restoreScrollAfterLayout(nav);
  }
})();

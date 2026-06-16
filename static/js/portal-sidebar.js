(function () {
  const STORAGE_KEY = "portal-sidebar-expanded";

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

  applyStoredState();
  bindPersistence();
})();

/*
 * 利用状況（4 一覧）の画面別設定。
 * 共通エンジン portal-list-core.js の実装は複製せず、列定義・既定の並び替え・
 * CSV 出力の区分だけをここに置く（ポータル一覧表_共通仕様.md / design.md §6.4）。
 *
 * 本画面はサーバー側ページングのため、行データの埋め込み（json_script）は無い。
 * このスクリプトは並び替えダイアログの操作・ページ送り操作・URL 同期
 * （history.replaceState）だけを担当し、実際の絞り込みと並び替えはサーバーが行う。
 * JS が無効でも、テンプレート側の GET フォームだけで同じ操作ができる。
 */
(function () {
  const Core = window.PortalListCore;
  if (!Core) {
    return;
  }

  // ページサイズのクエリキー。共通エンジンの既定は page_size だが、本画面は size を使う。
  const PAGE_SIZE_QUERY_KEY = "size";
  const PAGE_SIZE_OPTIONS = [20, 50, 100, 200];
  const DEFAULT_PAGE_SIZE = 50;

  // 日付・数値の列は降順から始めたほうが読み取りやすい。
  const DESCENDING_FIRST_COLUMNS = new Set([
    "view_count",
    "export_count",
    "user_count",
    "usage_count",
    "last_used_on",
    "last_login_at",
    "granted_on",
    "used_at",
  ]);

  // 画面別設定。sectionKey は CSV 出力の区分（section クエリ）と同じ値。
  // defaultSortSpecs が空配列なのは、既定の並び順を domain 側の自然順
  // （メニュー別＝メニュー定義順／出力操作の記録＝利用日時の降順 等）に委ねるため。
  const SECTIONS = [
    {
      sectionKey: "menus",
      rowsElementId: "menu-usage-rows",
      sortableColumns: [
        { key: "group_title", label: "メニューグループ" },
        { key: "menu_title", label: "メニュー" },
        { key: "view_count", label: "表示回数" },
        { key: "export_count", label: "出力回数" },
        { key: "user_count", label: "利用ユーザー数" },
        { key: "last_used_on", label: "最終利用日" },
      ],
      defaultSortSpecs: [],
    },
    {
      sectionKey: "users",
      rowsElementId: "user-usage-rows",
      sortableColumns: [
        { key: "username", label: "社員番号" },
        { key: "display_name", label: "表示名" },
        { key: "role", label: "権限" },
        { key: "menu_group_titles", label: "使えるグループ" },
        { key: "usage_count", label: "利用回数" },
        { key: "export_count", label: "出力回数" },
        { key: "most_used_menu_title", label: "最多利用メニュー" },
        { key: "last_used_on", label: "最終利用日" },
        { key: "last_login_at", label: "最終ログイン" },
      ],
      defaultSortSpecs: [],
    },
    {
      sectionKey: "unused-grants",
      rowsElementId: "unused-grant-rows",
      sortableColumns: [
        { key: "username", label: "社員番号" },
        { key: "display_name", label: "表示名" },
        { key: "group_title", label: "メニューグループ" },
        { key: "last_used_on", label: "最終利用日" },
        { key: "granted_on", label: "付与日" },
      ],
      defaultSortSpecs: [],
    },
    {
      sectionKey: "exports",
      rowsElementId: "export-log-rows",
      sortableColumns: [
        { key: "used_at", label: "日時" },
        { key: "username", label: "社員番号" },
        { key: "display_name", label: "表示名" },
        { key: "group_title", label: "メニューグループ" },
        { key: "menu_title", label: "メニュー" },
      ],
      defaultSortSpecs: [],
    },
  ];

  function defaultDirectionForColumn(column) {
    return DESCENDING_FIRST_COLUMNS.has(column) ? "desc" : "asc";
  }

  function readPageSizeFromUrl() {
    const params = new URLSearchParams(window.location.search);
    const value = Number.parseInt(params.get(PAGE_SIZE_QUERY_KEY) || "", 10);
    return PAGE_SIZE_OPTIONS.includes(value) ? value : DEFAULT_PAGE_SIZE;
  }

  // 並び替えとページ番号は共通エンジンの readBaseStateFromUrl に任せ、
  // ページサイズだけ本画面のクエリキー（size）で読み替える。
  function readStateFromUrl(section) {
    const base = Core.readBaseStateFromUrl(
      {
        defaultSortSpecs: section.defaultSortSpecs,
        pageSizeOptions: PAGE_SIZE_OPTIONS,
        defaultPageSize: DEFAULT_PAGE_SIZE,
      },
      defaultDirectionForColumn,
    );
    return { ...base, pageSize: readPageSizeFromUrl() };
  }

  function buildQueryString(state) {
    const params = new URLSearchParams(window.location.search);
    Core.appendSortQueryParams(params, state.sortSpecs, state.page, state.pageSize);
    params.set(PAGE_SIZE_QUERY_KEY, String(state.pageSize));
    params.delete("page_size");
    if (!params.get("sort")) {
      params.delete("sort");
      params.delete("dir");
    }
    return params.toString();
  }

  function footerElements(sectionElement) {
    const footer = sectionElement.querySelector(".us-table-footer");
    if (!footer) {
      return null;
    }
    return {
      footer,
      rangeElement: footer.querySelector(".us-table-range"),
      prevButton: footer.querySelector(".us-pagination-prev"),
      nextButton: footer.querySelector(".us-pagination-next"),
      pageSizeSelect: footer.querySelector(".us-page-size-select"),
      applyButton: footer.querySelector(".us-page-size-apply"),
    };
  }

  // ページャの状態はサーバーが描画済み。JS は描画済みの表示範囲を読み取り、
  // 共通エンジンの renderPagination で前へ／次への活性状態と表示範囲を整える。
  function paginationFromDom(elements, state) {
    const rangeText = elements.rangeElement ? elements.rangeElement.textContent : "";
    const range = rangeText.match(/(\d+)[^\d]+(\d+)\s*件目/);
    const pages = rangeText.match(/(\d+)\s*\/\s*(\d+)\s*ページ/);
    if (!range || !pages) {
      return { totalCount: 0, page: 1, pageSize: state.pageSize, totalPages: 1, startIndex: 0, endIndex: 0, hasPrevious: false, hasNext: false };
    }
    const startIndex = Number(range[1]);
    const endIndex = Number(range[2]);
    const page = Number(pages[1]);
    const totalPages = Number(pages[2]);
    return {
      totalCount: endIndex,
      page,
      pageSize: state.pageSize,
      totalPages,
      startIndex,
      endIndex,
      hasPrevious: page > 1,
      hasNext: page < totalPages,
    };
  }

  function initPagination(sectionElement, getState) {
    const elements = footerElements(sectionElement);
    if (!elements) {
      return;
    }
    const pagination = paginationFromDom(elements, getState());
    Core.renderPagination(elements, pagination);

    // JS が有効なときは表示件数の「適用」を押さずに切り替えられる。
    if (elements.applyButton) {
      elements.applyButton.hidden = true;
    }

    function navigate(patch) {
      const state = { ...getState(), ...patch };
      const query = buildQueryString(state);
      Core.replaceUrl(window.location.pathname, query);
      window.location.assign(`${window.location.pathname}?${query}`);
    }

    // フォーム送信ではなく JS で遷移する（二重送信を避ける）。
    [elements.prevButton, elements.nextButton].forEach((button) => {
      button?.addEventListener("click", (event) => {
        event.preventDefault();
      });
    });
    Core.bindPaginationControls(
      elements,
      () => pagination.page,
      (patch) => navigate(patch),
    );
  }

  function initSortDialog(sectionElement, section, getState) {
    const dialog = document.getElementById(`us-sort-dialog-${section.sectionKey}`);
    const openButton = sectionElement.querySelector(".us-sort-open");
    if (!dialog || !openButton) {
      return;
    }
    const columnSelect = dialog.querySelector(".us-sort-column");
    const directionSelect = dialog.querySelector(".us-sort-direction");
    const cancelButton = dialog.querySelector(".us-sort-cancel");

    openButton.addEventListener("click", () => {
      const spec = getState().sortSpecs[0];
      if (spec && columnSelect && directionSelect) {
        columnSelect.value = spec.column;
        directionSelect.value = spec.direction;
      } else if (columnSelect && directionSelect && section.sortableColumns.length) {
        columnSelect.value = section.sortableColumns[0].key;
        directionSelect.value = defaultDirectionForColumn(section.sortableColumns[0].key);
      }
      if (typeof dialog.showModal === "function") {
        dialog.showModal();
      } else {
        dialog.setAttribute("open", "open");
      }
    });

    // 列を変えたら、その列にふさわしい向きを既定にする。
    columnSelect?.addEventListener("change", () => {
      if (directionSelect) {
        directionSelect.value = defaultDirectionForColumn(columnSelect.value);
      }
    });

    cancelButton?.addEventListener("click", (event) => {
      event.preventDefault();
      if (typeof dialog.close === "function") {
        dialog.close();
      } else {
        dialog.removeAttribute("open");
      }
    });
  }

  function syncUrl(section) {
    const params = new URLSearchParams(window.location.search);
    const hasListParams = ["sort", "dir", "page", PAGE_SIZE_QUERY_KEY].some((key) =>
      params.has(key),
    );
    if (!hasListParams) {
      return;
    }
    Core.replaceUrl(window.location.pathname, buildQueryString(readStateFromUrl(section)));
  }

  function init() {
    let synced = false;
    SECTIONS.forEach((section) => {
      const rowsElement = document.getElementById(section.rowsElementId);
      if (!rowsElement) {
        return;
      }
      const sectionElement = rowsElement.closest(".us-list");
      if (!sectionElement) {
        return;
      }
      const getState = () => readStateFromUrl(section);
      initSortDialog(sectionElement, section, getState);
      initPagination(sectionElement, getState);
      if (!synced) {
        // 4 一覧はクエリを共有するため、URL 同期は 1 度だけ行う。
        syncUrl(section);
        synced = true;
      }
    });
  }

  if (document.readyState === "loading") {
    document.addEventListener("DOMContentLoaded", init);
  } else {
    init();
  }
})();

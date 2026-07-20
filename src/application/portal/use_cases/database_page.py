from __future__ import annotations

from application.portal.domain.repositories.ports import DatabaseBrowser
from application.portal.domain.value_objects.constants import VALID_SORT_DIRECTIONS


class DatabasePage:
    ROW_LIMIT = 100

    def __init__(self, browser: DatabaseBrowser) -> None:
        self._browser = browser

    def execute(
        self,
        *,
        selected_table: str,
        sort_column: str,
        sort_direction: str,
    ) -> dict[str, object]:
        table_names = self._browser.list_table_names()
        context: dict[str, object] = {
            "title": "データベース",
            "table_names": table_names,
            "selected_table": selected_table,
            "columns": [],
            "column_headers": [],
            "rows": [],
            "total_count": None,
            "row_limit": self.ROW_LIMIT,
            "sort_column": "",
            "sort_direction": "asc",
            "error": "",
        }

        if not selected_table:
            return context

        if selected_table not in table_names:
            context["error"] = "選択されたテーブルが見つかりません。"
            return context

        direction = sort_direction if sort_direction in VALID_SORT_DIRECTIONS else "asc"
        preview = self._browser.fetch_table_preview(
            selected_table,
            sort_column=sort_column,
            sort_direction=direction,
            row_limit=self.ROW_LIMIT,
        )
        context.update(preview)
        return context

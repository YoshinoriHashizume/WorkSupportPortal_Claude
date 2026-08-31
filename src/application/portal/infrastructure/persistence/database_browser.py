from __future__ import annotations

from django.db import connection

from application.portal.domain.value_objects.constants import VALID_SORT_DIRECTIONS
from application.portal.domain.value_objects.database_display import display_database_value


class DjangoDatabaseBrowser:
    def list_table_names(self) -> list[str]:
        return sorted(connection.introspection.table_names())

    def fetch_table_preview(
        self,
        table_name: str,
        *,
        sort_column: str,
        sort_direction: str,
        row_limit: int,
    ) -> dict[str, object]:
        quoted_table = connection.ops.quote_name(table_name)
        with connection.cursor() as cursor:
            cursor.execute(f"SELECT COUNT(*) FROM {quoted_table}")
            total_count = cursor.fetchone()[0]

            cursor.execute(f"SELECT * FROM {quoted_table} LIMIT 0")
            columns = [column[0] for column in cursor.description]
            resolved_sort_column = sort_column if sort_column in columns else ""
            resolved_direction = sort_direction if sort_direction in VALID_SORT_DIRECTIONS else "asc"
            order_clause = ""
            if resolved_sort_column:
                order_clause = (
                    f" ORDER BY {connection.ops.quote_name(resolved_sort_column)} {resolved_direction.upper()}"
                )

            cursor.execute(f"SELECT * FROM {quoted_table}{order_clause} LIMIT %s", [row_limit])
            rows = [
                [display_database_value(column_name, value) for column_name, value in zip(columns, row, strict=True)]
                for row in cursor.fetchall()
            ]
        return {
            "columns": columns,
            "column_headers": [
                {
                    "name": column,
                    "sort_direction": "desc" if column == resolved_sort_column and resolved_direction == "asc" else "asc",
                    "is_sorted": column == resolved_sort_column,
                }
                for column in columns
            ],
            "rows": rows,
            "total_count": total_count,
            "sort_column": resolved_sort_column,
            "sort_direction": resolved_direction,
        }

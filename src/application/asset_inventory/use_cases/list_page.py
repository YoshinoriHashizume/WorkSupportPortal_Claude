from __future__ import annotations

from application.asset_inventory.domain.value_objects.list_filter import apply_filters, count_rows
from application.asset_inventory.domain.repositories.ports import (
    DEFAULT_PAGE_SIZE,
    ListAllRecordsFn,
    ListPageResult,
    ManagementRow,
)
from application.asset_inventory.domain.value_objects.list_query import (
    ListPageQuery,
    empty_list_page_result,
    parse_list_page_query,
)
from application.asset_inventory.domain.value_objects.reconcile_cache import clear_reconcile_cache
from application.asset_inventory.domain.value_objects.reconcile_data import load_reconciled_data
from application.asset_inventory.domain.value_objects.table_display import (
    DEFAULT_SORT_SPECS,
    paginate_rows,
    sort_rows,
)
from application.asset_inventory.domain.value_objects.desknet_data import list_management_rows
from application.asset_inventory.domain.value_objects.errors import DesknetAccessKeyMissingError, DesknetApiError

__all__ = [
    "ListPage",
    "ListPageQuery",
    "parse_list_page_query",
    "empty_list_page_result",
    "_empty_result",
    "_select_management_row",
]


class ListPage:
    def __init__(self, list_all: ListAllRecordsFn) -> None:
        self._list_all = list_all

    def execute(self, access_key: str, query: ListPageQuery, session: dict | None = None) -> ListPageResult:
        if not access_key:
            return empty_list_page_result(error_message="desknet's のアクセスキーがありません。再ログインしてください。")

        try:
            management_rows = tuple(list_management_rows(self._list_all, access_key))
        except DesknetAccessKeyMissingError as exc:
            return empty_list_page_result(error_message=str(exc))
        except DesknetApiError as exc:
            return empty_list_page_result(error_message=str(exc))

        if not management_rows:
            return empty_list_page_result(management_rows=(), error_message="棚卸データ管理が登録されていません。")

        if not query.management_id:
            if session is not None:
                clear_reconcile_cache(session)
            return _management_only_result(management_rows)

        selected = _select_management_row(management_rows, query.management_id)
        if selected is None:
            if session is not None:
                clear_reconcile_cache(session)
            return empty_list_page_result(
                management_rows=management_rows,
                error_message="指定された棚卸データ管理が見つかりません。",
            )

        try:
            reconciled = load_reconciled_data(
                self._list_all,
                access_key,
                selected,
                session=session,
            )
        except DesknetAccessKeyMissingError as exc:
            return empty_list_page_result(management_rows=management_rows, error_message=str(exc))
        except DesknetApiError as exc:
            return empty_list_page_result(management_rows=management_rows, error_message=str(exc))

        all_rows = reconciled.rows
        filtered_rows = apply_filters(
            all_rows,
            status_filter=query.status,
            site_filter=query.site_filter,
            plate_filter=query.plate_filter,
            asset_number_filter=query.asset_number_filter,
        )
        filtered_counts = count_rows(filtered_rows)
        sorted_rows = sort_rows(filtered_rows, query.table_params.sort_specs)
        table_params = query.table_params
        paginated = paginate_rows(sorted_rows, table_params.page, table_params.page_size)

        return ListPageResult(
            management_rows=management_rows,
            selected_management_id=selected.data_id,
            rows=paginated.rows,
            all_rows=all_rows,
            filtered_rows=filtered_rows,
            counts=reconciled.counts,
            filtered_counts=filtered_counts,
            site_options=reconciled.site_options,
            site_filter=query.site_filter,
            status_filter=query.status,
            plate_filter=query.plate_filter,
            asset_number_filter=query.asset_number_filter,
            asset_number_options=reconciled.asset_number_options,
            page=paginated.page,
            page_size=paginated.page_size,
            total_pages=paginated.total_pages,
            sort_specs=table_params.sort_specs,
            start_index=paginated.start_index,
            end_index=paginated.end_index,
            has_previous=paginated.has_previous,
            has_next=paginated.has_next,
        )


def _select_management_row(rows: tuple[ManagementRow, ...], management_id: str) -> ManagementRow | None:
    if not management_id:
        return None
    for row in rows:
        if row.data_id == management_id:
            return row
    return None


def _management_only_result(
    management_rows: tuple[ManagementRow, ...],
    *,
    error_message: str | None = None,
) -> ListPageResult:
    return ListPageResult(
        management_rows=management_rows,
        selected_management_id="",
        rows=(),
        all_rows=(),
        filtered_rows=(),
        counts=count_rows(()),
        filtered_counts=count_rows(()),
        site_options=(),
        asset_number_options=(),
        site_filter="all",
        status_filter="all",
        plate_filter="all",
        asset_number_filter="",
        page=1,
        page_size=DEFAULT_PAGE_SIZE,
        total_pages=1,
        sort_specs=DEFAULT_SORT_SPECS,
        error_message=error_message,
    )


_empty_result = empty_list_page_result

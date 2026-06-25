from __future__ import annotations

from dataclasses import dataclass

from apps.asset_inventory.domain.list_filter import apply_filters, count_rows, extract_site_names_from_assets
from apps.asset_inventory.domain.ports import (
    DEFAULT_PAGE_SIZE,
    PAGE_SIZE_OPTIONS,
    PLATE_FILTER_OPTIONS,
    ListAllRecordsFn,
    ListPageResult,
    ManagementRow,
)
from apps.asset_inventory.domain.reconcile import reconcile_records
from apps.asset_inventory.domain.table_display import (
    DEFAULT_SORT_SPECS,
    TableDisplayParams,
    paginate_rows,
    parse_table_display_params,
    sort_rows,
)
from apps.asset_inventory.domain.desknet_data import (
    fetch_reconcile_source_data,
    list_management_rows,
)
from apps.asset_inventory.domain.errors import DesknetAccessKeyMissingError, DesknetApiError


@dataclass(frozen=True)
class ListPageQuery:
    management_id: str
    status: str
    site_filter: str
    plate_filter: str
    table_params: TableDisplayParams


def parse_list_page_query(params: dict[str, str], sites: list[str] | None = None) -> ListPageQuery:
    plate_filter = (params.get("plate") or "all").strip() or "all"
    if plate_filter not in {value for value, _label in PLATE_FILTER_OPTIONS}:
        plate_filter = "all"
    site_filter = (params.get("site") or "").strip()
    if not site_filter or site_filter == "all":
        cleaned_sites = [site.strip() for site in (sites or []) if site.strip()]
        site_filter = cleaned_sites[0] if len(cleaned_sites) == 1 else "all"
    return ListPageQuery(
        management_id=(params.get("managementId") or "").strip(),
        status=(params.get("status") or "all").strip() or "all",
        site_filter=site_filter,
        plate_filter=plate_filter,
        table_params=parse_table_display_params(params),
    )


class ListPageUsecase:
    def __init__(self, list_all: ListAllRecordsFn) -> None:
        self._list_all = list_all

    def execute(self, access_key: str, query: ListPageQuery) -> ListPageResult:
        if not access_key:
            return _empty_result(error_message="desknet's のアクセスキーがありません。再ログインしてください。")

        try:
            management_rows = tuple(list_management_rows(self._list_all, access_key))
        except DesknetAccessKeyMissingError as exc:
            return _empty_result(error_message=str(exc))
        except DesknetApiError as exc:
            return _empty_result(error_message=str(exc))

        if not management_rows:
            return _empty_result(management_rows=(), error_message="棚卸データ管理が登録されていません。")

        if not query.management_id:
            return _management_only_result(management_rows)

        selected = _select_management_row(management_rows, query.management_id)
        if selected is None:
            return _management_only_result(
                management_rows,
                error_message="選択した棚卸が見つかりません。",
            )

        try:
            assets, inventory, sites = fetch_reconcile_source_data(self._list_all, access_key, selected)
        except DesknetAccessKeyMissingError as exc:
            return _empty_result(management_rows=management_rows, error_message=str(exc))
        except DesknetApiError as exc:
            return _empty_result(management_rows=management_rows, error_message=str(exc))

        all_rows, counts = reconcile_records(assets, inventory, sites)
        site_options = extract_site_names_from_assets(assets)
        filtered = apply_filters(
            all_rows,
            status_filter=query.status,
            site_filter=query.site_filter,
            plate_filter=query.plate_filter,
        )
        filtered_counts = count_rows(filtered)
        table_params = query.table_params
        sorted_rows = sort_rows(filtered, table_params.sort_specs)
        paginated = paginate_rows(sorted_rows, table_params.page, table_params.page_size)

        return ListPageResult(
            management_rows=management_rows,
            selected_management_id=selected.data_id,
            rows=paginated.rows,
            filtered_rows=sorted_rows,
            counts=counts,
            filtered_counts=filtered_counts,
            site_options=site_options,
            site_filter=query.site_filter,
            status_filter=query.status,
            plate_filter=query.plate_filter,
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
        filtered_rows=(),
        counts=count_rows(()),
        filtered_counts=count_rows(()),
        site_options=(),
        site_filter="all",
        status_filter="all",
        plate_filter="all",
        page=1,
        page_size=DEFAULT_PAGE_SIZE,
        total_pages=1,
        sort_specs=DEFAULT_SORT_SPECS,
        error_message=error_message,
    )


def _empty_result(
    *,
    management_rows: tuple[ManagementRow, ...] = (),
    error_message: str | None = None,
) -> ListPageResult:
    return _management_only_result(management_rows, error_message=error_message)

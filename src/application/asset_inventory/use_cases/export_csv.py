from __future__ import annotations

from application.asset_inventory.domain.value_objects.csv_export import render_export_csv
from application.asset_inventory.domain.value_objects.list_filter import apply_filters
from application.asset_inventory.domain.repositories.ports import ListAllRecordsFn
from application.asset_inventory.domain.value_objects.reconcile_data import load_reconciled_data
from application.asset_inventory.domain.value_objects.table_display import sort_rows
from application.asset_inventory.domain.value_objects.desknet_data import list_management_rows
from application.asset_inventory.domain.value_objects.errors import DesknetAccessKeyMissingError, DesknetApiError
from application.asset_inventory.use_cases.list_page import ListPageQuery, _select_management_row


class ExportCsv:
    def __init__(self, list_all: ListAllRecordsFn) -> None:
        self._list_all = list_all

    def execute(self, access_key: str, query: ListPageQuery, session: dict | None = None) -> bytes:
        management_rows = tuple(list_management_rows(self._list_all, access_key))
        if not management_rows:
            return render_export_csv(())
        if not query.management_id:
            raise ValueError("棚卸が選択されていません。")
        selected = _select_management_row(management_rows, query.management_id)
        if selected is None:
            raise ValueError("選択した棚卸が見つかりません。")
        reconciled = load_reconciled_data(self._list_all, access_key, selected, session=session)
        all_rows = reconciled.rows
        filtered = apply_filters(
            all_rows,
            status_filter=query.status,
            site_filter=query.site_filter,
            plate_filter=query.plate_filter,
            asset_number_filter=query.asset_number_filter,
        )
        sorted_rows = sort_rows(filtered, query.table_params.sort_specs)
        return render_export_csv(sorted_rows)

    def execute_safe(self, access_key: str, query: ListPageQuery, session: dict | None = None) -> tuple[bytes | None, str | None]:
        try:
            return self.execute(access_key, query, session=session), None
        except (DesknetAccessKeyMissingError, DesknetApiError, ValueError) as exc:
            return None, str(exc)

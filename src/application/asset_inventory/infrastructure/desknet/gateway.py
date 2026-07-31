from __future__ import annotations

from application.asset_inventory.domain.value_objects.desknet_data import (
    fetch_reconcile_source_data,
    list_management_rows,
    parse_management_row,
)
from application.asset_inventory.domain.repositories.ports import ListAllRecordsFn, Record
from application.asset_inventory.infrastructure.desknet.client import fetch_all_list_data

__all__ = (
    "fetch_reconcile_source_data",
    "list_management_rows",
    "make_list_all_records_fn",
    "parse_management_row",
)


def make_list_all_records_fn(login_url: str, timeout: float) -> ListAllRecordsFn:
    def list_all(access_key: str, app_id: str, fields: tuple[str, ...] | None) -> list[Record]:
        return fetch_all_list_data(
            login_url=login_url,
            access_key=access_key,
            app_id=app_id,
            fields=fields,
            timeout=timeout,
        )

    return list_all

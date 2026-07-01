from __future__ import annotations

from django.conf import settings

from applications.asset_inventory.infrastructure.desknet.gateway import make_list_all_records_fn
from applications.asset_inventory.usecase.usecase_export_csv import ExportCsvUsecase
from applications.asset_inventory.usecase.usecase_list_page import ListPageUsecase


def _list_all_fn():
    return make_list_all_records_fn(
        settings.DESKNETS_LOGIN_URL,
        float(settings.DESKNETS_TIMEOUT_SECONDS),
    )


def list_page_usecase() -> ListPageUsecase:
    return ListPageUsecase(_list_all_fn())


def export_csv_usecase() -> ExportCsvUsecase:
    return ExportCsvUsecase(_list_all_fn())

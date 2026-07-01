from __future__ import annotations

from applications.shipment_trend.infrastructure.oracle.summary_aggregation import run_summary_aggregation
from applications.shipment_trend.infrastructure.persistence.settings_repository import load_app_settings
from applications.shipment_trend.infrastructure.persistence.summary_repository import load_latest_summary
from applications.shipment_trend.usecase.usecase_chart_data import ChartDataUsecase
from applications.shipment_trend.usecase.usecase_export_csv import ExportCsvUsecase
from applications.shipment_trend.usecase.usecase_list_page import ListPageUsecase
from applications.shipment_trend.usecase.usecase_refresh_data import RefreshDataUsecase
from applications.shipment_trend.usecase.usecase_save_alert_settings import SaveAlertSettingsUsecase


def refresh_data_usecase() -> RefreshDataUsecase:
    return RefreshDataUsecase(run_aggregation=run_summary_aggregation)


def list_page_usecase() -> ListPageUsecase:
    return ListPageUsecase(
        load_summary=load_latest_summary,
        load_settings=load_app_settings,
        refresh_data=refresh_data_usecase(),
    )


def save_alert_settings_usecase() -> SaveAlertSettingsUsecase:
    return SaveAlertSettingsUsecase()


def export_csv_usecase() -> ExportCsvUsecase:
    return ExportCsvUsecase(load_summary=load_latest_summary)


def chart_data_usecase() -> ChartDataUsecase:
    return ChartDataUsecase(
        load_summary=load_latest_summary,
        load_settings=load_app_settings,
    )

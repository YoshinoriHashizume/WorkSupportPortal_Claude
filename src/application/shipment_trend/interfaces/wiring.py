from __future__ import annotations

from application.shipment_trend.infrastructure.oracle.summary_aggregation import run_summary_aggregation
from application.shipment_trend.infrastructure.persistence.settings_repository import load_app_settings, save_alert_settings
from application.shipment_trend.infrastructure.persistence.summary_repository import load_latest_summary
from application.shipment_trend.infrastructure.persistence.summary_snapshot_repository import create_refresh_record
from application.shipment_trend.use_cases.chart_data import ChartData
from application.shipment_trend.use_cases.export_csv import ExportCsv
from application.shipment_trend.use_cases.list_page import ListPage
from application.shipment_trend.use_cases.refresh_data import RefreshData
from application.shipment_trend.use_cases.save_alert_settings import SaveAlertSettings


def refresh_data_usecase() -> RefreshData:
    return RefreshData(
        run_aggregation=run_summary_aggregation,
        create_refresh_record=create_refresh_record,
    )


def list_page_usecase() -> ListPage:
    return ListPage(
        load_summary=load_latest_summary,
        load_settings=load_app_settings,
        refresh_data=refresh_data_usecase(),
    )


def save_alert_settings_usecase() -> SaveAlertSettings:
    return SaveAlertSettings(save_alert_settings)


def export_csv_usecase() -> ExportCsv:
    return ExportCsv(load_summary=load_latest_summary)


def chart_data_usecase() -> ChartData:
    return ChartData(
        load_summary=load_latest_summary,
        load_settings=load_app_settings,
    )

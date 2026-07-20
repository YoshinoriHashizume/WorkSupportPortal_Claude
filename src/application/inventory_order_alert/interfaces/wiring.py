from __future__ import annotations

from application.inventory_order_alert.use_cases.confirmation_memos import ConfirmationMemos
from application.inventory_order_alert.use_cases.export_csv import ExportCsv
from application.inventory_order_alert.use_cases.import_stock import ImportStock
from application.inventory_order_alert.use_cases.list_page import ListPage
from application.inventory_order_alert.use_cases.portal_dashboard import PortalDashboard
from application.inventory_order_alert.use_cases.reset_confirmations import ResetConfirmations
from application.inventory_order_alert.use_cases.save_alert_settings import SaveAlertSettings
from application.inventory_order_alert.use_cases.patch_snapshot_row import PatchSnapshotRow
from application.inventory_order_alert.use_cases.save_confirmation import SaveConfirmation
from application.inventory_order_alert.infrastructure.oracle.list_rows_builder import ListQuery, build_list_rows
from application.inventory_order_alert.infrastructure.persistence.confirmation_repository import (
    add_confirmation_memo,
    has_resettable_confirmations,
    list_confirmation_memos,
    reconcile_confirmations_after_import,
    reset_all_confirmations,
    save_confirmation,
)
from application.inventory_order_alert.infrastructure.persistence.settings_repository import (
    load_app_settings,
    save_warning_month_settings,
)
from application.inventory_order_alert.infrastructure.persistence.slims_stock_repository import import_slims_csv_text
from application.inventory_order_alert.infrastructure.persistence.summary_repository import load_latest_summary
from application.inventory_order_alert.infrastructure.persistence.summary_snapshot_repository import (
    load_latest_editable_snapshot,
    persist_editable_snapshot,
)
from application.inventory_order_alert.infrastructure.persistence.user_display_repository import resolve_user_display_names


def import_stock_usecase() -> ImportStock:
    return ImportStock(import_slims_csv_text)


def list_page_usecase() -> ListPage:
    return ListPage(
        import_stock_usecase(),
        load_latest_summary,
        load_app_settings,
        has_resettable_confirmations,
    )


def save_confirmation_usecase() -> SaveConfirmation:
    return SaveConfirmation(load_latest_summary, save_confirmation)


def confirmation_memos_usecase() -> ConfirmationMemos:
    return ConfirmationMemos(
        list_confirmation_memos,
        add_confirmation_memo,
        resolve_user_display_names,
    )


def reset_confirmations_usecase() -> ResetConfirmations:
    return ResetConfirmations(load_latest_summary, reset_all_confirmations)


def save_alert_settings_usecase() -> SaveAlertSettings:
    return SaveAlertSettings(save_warning_month_settings)


def export_csv_usecase() -> ExportCsv:
    return ExportCsv(load_latest_summary)


def portal_dashboard_usecase() -> PortalDashboard:
    return PortalDashboard(load_latest_summary, load_app_settings)


def patch_snapshot_row_usecase() -> PatchSnapshotRow:
    return PatchSnapshotRow(
        load_app_settings,
        load_latest_editable_snapshot,
        persist_editable_snapshot,
        reconcile_confirmations_after_import,
    )


__all__ = [
    "ListQuery",
    "build_list_rows",
    "confirmation_memos_usecase",
    "export_csv_usecase",
    "import_stock_usecase",
    "list_page_usecase",
    "portal_dashboard_usecase",
    "reset_confirmations_usecase",
    "save_alert_settings_usecase",
    "save_confirmation_usecase",
    "patch_snapshot_row_usecase",
]

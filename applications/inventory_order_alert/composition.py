from __future__ import annotations

from applications.inventory_order_alert.usecase.usecase_confirmation_memos import ConfirmationMemosUsecase
from applications.inventory_order_alert.usecase.usecase_export_csv import ExportCsvUsecase
from applications.inventory_order_alert.usecase.usecase_import_stock import ImportStockUsecase
from applications.inventory_order_alert.usecase.usecase_list_page import ListPageUsecase
from applications.inventory_order_alert.usecase.usecase_portal_dashboard import PortalDashboardUsecase
from applications.inventory_order_alert.usecase.usecase_reset_confirmations import ResetConfirmationsUsecase
from applications.inventory_order_alert.usecase.usecase_save_alert_settings import SaveAlertSettingsUsecase
from applications.inventory_order_alert.usecase.usecase_patch_snapshot_row import PatchSnapshotRowUsecase
from applications.inventory_order_alert.usecase.usecase_save_confirmation import SaveConfirmationUsecase
from applications.inventory_order_alert.infrastructure.oracle.list_rows_builder import ListQuery, build_list_rows
from applications.inventory_order_alert.infrastructure.persistence.confirmation_repository import (
    add_confirmation_memo,
    has_resettable_confirmations,
    list_confirmation_memos,
    reconcile_confirmations_after_import,
    reset_all_confirmations,
    save_confirmation,
)
from applications.inventory_order_alert.infrastructure.persistence.settings_repository import (
    load_app_settings,
    save_warning_month_settings,
)
from applications.inventory_order_alert.infrastructure.persistence.slims_stock_repository import import_slims_csv_text
from applications.inventory_order_alert.infrastructure.persistence.summary_repository import load_latest_summary
from applications.inventory_order_alert.infrastructure.persistence.summary_snapshot_repository import (
    load_latest_editable_snapshot,
    persist_editable_snapshot,
)
from applications.inventory_order_alert.infrastructure.persistence.user_display_repository import resolve_user_display_names


def import_stock_usecase() -> ImportStockUsecase:
    return ImportStockUsecase(import_slims_csv_text)


def list_page_usecase() -> ListPageUsecase:
    return ListPageUsecase(
        import_stock_usecase(),
        load_latest_summary,
        load_app_settings,
        has_resettable_confirmations,
    )


def save_confirmation_usecase() -> SaveConfirmationUsecase:
    return SaveConfirmationUsecase(load_latest_summary, save_confirmation)


def confirmation_memos_usecase() -> ConfirmationMemosUsecase:
    return ConfirmationMemosUsecase(
        list_confirmation_memos,
        add_confirmation_memo,
        resolve_user_display_names,
    )


def reset_confirmations_usecase() -> ResetConfirmationsUsecase:
    return ResetConfirmationsUsecase(load_latest_summary, reset_all_confirmations)


def save_alert_settings_usecase() -> SaveAlertSettingsUsecase:
    return SaveAlertSettingsUsecase(save_warning_month_settings)


def export_csv_usecase() -> ExportCsvUsecase:
    return ExportCsvUsecase(load_latest_summary)


def portal_dashboard_usecase() -> PortalDashboardUsecase:
    return PortalDashboardUsecase(load_latest_summary, load_app_settings)


def patch_snapshot_row_usecase() -> PatchSnapshotRowUsecase:
    return PatchSnapshotRowUsecase(
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

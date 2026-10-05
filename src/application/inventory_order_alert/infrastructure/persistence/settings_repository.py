from __future__ import annotations

from application.inventory_order_alert.domain.value_objects.app_settings import (
    AppSettings,
    clamp_default_lead_time_days,
    clamp_recent_incoming_days,
    clamp_stock_stale_days,
    clamp_warning_days,
)
from application.inventory_order_alert.models import InventoryOrderAlertSettings


def load_app_settings() -> AppSettings:
    settings_row, _ = InventoryOrderAlertSettings.objects.get_or_create(pk=1)
    # 既存行に範囲外の値が残っていても AppSettings の不変条件を満たす形に丸める（§13.1）。
    # 警告条件の残置カラムは読まない（design.md §5.3）。
    return AppSettings(
        warning_days=clamp_warning_days(settings_row.warning_days),
        stock_stale_days=clamp_stock_stale_days(settings_row.stock_stale_days),
        default_lead_time_days=clamp_default_lead_time_days(settings_row.default_lead_time_days),
        recent_incoming_days=clamp_recent_incoming_days(settings_row.recent_incoming_days),
    )


def save_app_settings(
    *,
    warning_days: int,
    stock_stale_days: int,
    default_lead_time_days: int | None = None,
    recent_incoming_days: int | None = None,
    updated_by: object | None = None,
) -> AppSettings:
    """設定画面（§4.2）・設定 API（§8.10）で更新できる項目を保存する。未指定の項目は据え置く。

    安全日数・監視期間のカラムは 2026/09/23 に未使用となった（残置。08 design §2.4）。
    """
    settings_row, _ = InventoryOrderAlertSettings.objects.get_or_create(pk=1)
    settings_row.warning_days = clamp_warning_days(warning_days)
    settings_row.stock_stale_days = clamp_stock_stale_days(stock_stale_days)
    if default_lead_time_days is not None:
        settings_row.default_lead_time_days = clamp_default_lead_time_days(default_lead_time_days)
    if recent_incoming_days is not None:
        settings_row.recent_incoming_days = clamp_recent_incoming_days(recent_incoming_days)
    update_fields = [
        "warning_days",
        "stock_stale_days",
        "default_lead_time_days",
        "recent_incoming_days",
        "updated_at",
    ]
    if updated_by is not None:
        settings_row.updated_by = updated_by
        update_fields.append("updated_by")
    settings_row.save(update_fields=update_fields)
    return load_app_settings()

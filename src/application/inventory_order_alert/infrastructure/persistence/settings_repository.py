from __future__ import annotations

from application.inventory_order_alert.domain.value_objects.app_settings import (
    AppSettings,
    clamp_default_lead_time_days,
    clamp_recent_incoming_days,
    clamp_safety_days,
    clamp_stock_stale_days,
    clamp_warning_days,
    clamp_watch_months,
)
from application.inventory_order_alert.models import InventoryOrderAlertSettings


def load_app_settings() -> AppSettings:
    settings_row, _ = InventoryOrderAlertSettings.objects.get_or_create(pk=1)
    # 既存行に範囲外の値が残っていても AppSettings の不変条件を満たす形に丸める（§13.1）。
    # 警告条件の残置カラムは読まない（design.md §5.3）。
    return AppSettings(
        warning_days=clamp_warning_days(settings_row.warning_days),
        stock_stale_days=clamp_stock_stale_days(settings_row.stock_stale_days),
        safety_days=clamp_safety_days(settings_row.safety_days),
        default_lead_time_days=clamp_default_lead_time_days(settings_row.default_lead_time_days),
        watch_months=clamp_watch_months(settings_row.watch_months),
        recent_incoming_days=clamp_recent_incoming_days(settings_row.recent_incoming_days),
    )


def save_app_settings(
    *,
    warning_days: int,
    stock_stale_days: int,
    safety_days: int | None = None,
    default_lead_time_days: int | None = None,
    watch_months: int | None = None,
    recent_incoming_days: int | None = None,
    updated_by: object | None = None,
) -> AppSettings:
    """設定画面（§4.2）・設定 API（§8.10）で更新できる項目を保存する。在庫切れリスクの閾値は未指定なら据え置く。"""
    settings_row, _ = InventoryOrderAlertSettings.objects.get_or_create(pk=1)
    settings_row.warning_days = clamp_warning_days(warning_days)
    settings_row.stock_stale_days = clamp_stock_stale_days(stock_stale_days)
    if safety_days is not None:
        settings_row.safety_days = clamp_safety_days(safety_days)
    if default_lead_time_days is not None:
        settings_row.default_lead_time_days = clamp_default_lead_time_days(default_lead_time_days)
    if watch_months is not None:
        settings_row.watch_months = clamp_watch_months(watch_months)
    if recent_incoming_days is not None:
        settings_row.recent_incoming_days = clamp_recent_incoming_days(recent_incoming_days)
    update_fields = [
        "warning_days",
        "stock_stale_days",
        "safety_days",
        "default_lead_time_days",
        "watch_months",
        "recent_incoming_days",
        "updated_at",
    ]
    if updated_by is not None:
        settings_row.updated_by = updated_by
        update_fields.append("updated_by")
    settings_row.save(update_fields=update_fields)
    return load_app_settings()

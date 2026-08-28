"""メニュー利用ログの記録対象を判別する（design.md §4.2・§4.4）。"""

from __future__ import annotations

from dataclasses import dataclass

from application.portal.domain.value_objects.constants import RECEIPT_COMPARISON_PATH
from application.portal.domain.value_objects.menu import MENU_ITEMS
from application.portal.domain.value_objects.menu_access import (
    is_menu_path_active,
    receipt_comparison_menu_key,
)

USAGE_TYPE_VIEW = "VIEW"
USAGE_TYPE_EXPORT = "EXPORT"
USAGE_TYPES = (USAGE_TYPE_VIEW, USAGE_TYPE_EXPORT)
USAGE_TYPE_LABELS = {
    USAGE_TYPE_VIEW: "表示",
    USAGE_TYPE_EXPORT: "出力",
}

RECEIPT_COMPARISON_EXPORT_PATH = f"{RECEIPT_COMPARISON_PATH}/export"


@dataclass(frozen=True)
class ExportEndpoint:
    """出力エンドポイントとメニューキーの対応 1 件。"""

    path: str
    menu_key: str


class ExportEndpoints:
    """出力エンドポイントの集合（ファーストクラスコレクション）。"""

    def __init__(self, endpoints: tuple[ExportEndpoint, ...]) -> None:
        self._endpoints = tuple(endpoints)

    def as_tuple(self) -> tuple[ExportEndpoint, ...]:
        return self._endpoints

    def paths(self) -> tuple[str, ...]:
        return tuple(endpoint.path for endpoint in self._endpoints)

    def menu_key_for(self, path: str, comparison_type: str = "") -> str | None:
        for endpoint in self._endpoints:
            if endpoint.path != path:
                continue
            if endpoint.path == RECEIPT_COMPARISON_EXPORT_PATH:
                return receipt_comparison_menu_key(comparison_type)
            return endpoint.menu_key
        return None


EXPORT_ENDPOINTS = ExportEndpoints(
    (
        ExportEndpoint("/api/asset-inventory/export.csv", "asset-inventory"),
        ExportEndpoint("/api/asset-inventory/asp-import.csv", "asset-inventory"),
        ExportEndpoint("/api/gonenkukumi/export", "five-year-nine"),
        ExportEndpoint("/app/production/inventory-order-alert/export.csv", "inventory-order-alert"),
        ExportEndpoint("/api/inventory-order-alert/export.csv", "inventory-order-alert"),
        ExportEndpoint(RECEIPT_COMPARISON_EXPORT_PATH, "receipt-comparison-finished-product"),
        ExportEndpoint("/app/sales/shipment-trend/export.csv", "shipment-trend-list"),
        ExportEndpoint("/api/shipment-trend/export.csv", "shipment-trend-list"),
        ExportEndpoint("/app/management/usage-status/export.csv", "usage-status"),
    )
)


@dataclass(frozen=True)
class UsageRecordTarget:
    """記録すべきメニュー利用 1 件の判別結果。"""

    menu_key: str
    usage_type: str


def resolve_menu_key(path: str, comparison_type: str = "") -> str | None:
    """パスに対応するメニューキーを返す。対応づかない場合は None。"""
    for item in MENU_ITEMS:
        if not item.href:
            continue
        if is_menu_path_active(path, item.href, comparison_type):
            return item.key
    return None


def resolve_usage_record_target(
    *,
    path: str,
    comparison_type: str,
    status_code: int,
    content_type: str,
    is_attachment: bool,
) -> UsageRecordTarget | None:
    """記録すべき利用を判別する。記録しない場合は None（design.md §4.4(a) の判定順）。"""
    if status_code != 200:
        return None

    export_menu_key = EXPORT_ENDPOINTS.menu_key_for(path, comparison_type)
    if export_menu_key is not None:
        if not is_attachment:
            return None
        return UsageRecordTarget(menu_key=export_menu_key, usage_type=USAGE_TYPE_EXPORT)

    if not (content_type or "").startswith("text/html"):
        return None

    menu_key = resolve_menu_key(path, comparison_type)
    if menu_key is None:
        return None
    return UsageRecordTarget(menu_key=menu_key, usage_type=USAGE_TYPE_VIEW)

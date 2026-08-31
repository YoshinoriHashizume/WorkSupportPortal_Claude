"""読み取り専用 API（§8.1 / §8.4 / §8.9 / §8.11）のユースケース。

いずれも Oracle へは問い合わせず、PostgreSQL の集計スナップショットおよび
SLIMS 在庫スナップショットのみを参照する（§4.1.1）。
"""
from __future__ import annotations

from datetime import date, datetime
from decimal import Decimal

from application.inventory_order_alert.domain.repositories.ports import (
    LoadAppSettings,
    LoadStockLines,
    LoadSummary,
)
from application.inventory_order_alert.domain.value_objects.dates import is_stock_stale
from application.inventory_order_alert.domain.value_objects.list_query import (
    merge_query_with_settings,
    parse_list_query,
)
from application.inventory_order_alert.domain.value_objects.list_rows import (
    apply_flow_quadrants_to_rows,
    filter_summary_rows,
    sort_summary_rows,
)
from application.inventory_order_alert.domain.value_objects.row_counts import RowCounts, count_rows
from application.inventory_order_alert.domain.value_objects.slims_stock import (
    aggregate_location_lines,
    group_locations_by_item,
)
from application.inventory_order_alert.use_cases.portal_dashboard import DashboardBannerContext, PortalDashboard


def _jsonable(value: object) -> object:
    if isinstance(value, Decimal):
        if value == value.to_integral_value():
            return int(value)
        return float(value)
    if isinstance(value, datetime):
        return value.isoformat()
    if isinstance(value, date):
        return value.isoformat()
    return value


def _location_payload(lines: list) -> list[dict[str, object]]:
    return [
        {"wloccd": line.wloccd, "stock_qty": _jsonable(line.stock_qty)}
        for line in aggregate_location_lines(lines)
    ]


def _counts_payload(counts: RowCounts) -> dict[str, int]:
    return {
        "total": counts.total,
        "attention": counts.attention,
        "supplyRisk": counts.supply_risk,
        "dormantStock": counts.dormant_stock,
        "excessStockRisk": counts.excess_stock_risk,
        "normalFlow": counts.normal_flow,
        "unconfirmed": counts.unconfirmed,
    }


def _stock_import_payload(stock_info: object | None, *, is_stale: bool) -> dict[str, object] | None:
    if stock_info is None:
        return None
    return {
        "importedAt": _jsonable(stock_info.imported_at),
        "stockAsOfLabel": stock_info.stock_as_of_label,
        "rowCount": stock_info.row_count,
        "isStale": is_stale,
    }



class SummaryApi:
    """§8.1 `GET /api/inventory-order-alert/summary`"""

    def __init__(self, load_summary: LoadSummary, load_app_settings: LoadAppSettings) -> None:
        self._load_summary = load_summary
        self._load_app_settings = load_app_settings

    def execute(self, query_params: dict[str, str], *, today: date | None = None) -> dict[str, object]:
        try:
            query = parse_list_query(query_params, today=today)
        except ValueError as exc:
            raise ValueError("クエリの形式が不正です。") from exc

        settings = self._load_app_settings()
        # 判定軸・判定期間は利用者がクエリで選ぶ値であり、設定値では上書きしない（design.md §6.1）
        query = merge_query_with_settings(query, settings)

        summary = self._load_summary()
        if summary is None:
            return {
                "ok": True,
                "rows": [],
                "counts": _counts_payload(RowCounts()),
                "stockImport": None,
            }

        as_of_date = summary.as_of_date or query.as_of_date
        rows = apply_flow_quadrants_to_rows(summary.rows, as_of_date=as_of_date, query=query)
        rows = sort_summary_rows(filter_summary_rows(rows, query))

        stock_info = summary.stock_info
        stale = is_stock_stale(
            stock_info.stock_as_of_date if stock_info else None,
            settings.stock_stale_days,
            today=today or query.as_of_date,
        )
        return {
            "ok": True,
            "rows": [{key: _jsonable(value) for key, value in row.items()} for row in rows],
            "counts": _counts_payload(count_rows(rows)),
            "stockImport": _stock_import_payload(stock_info, is_stale=stale),
        }


class StockLocations:
    """§8.4 `GET /api/inventory-order-alert/stock-locations`"""

    def __init__(self, load_stock_lines: LoadStockLines) -> None:
        self._load_stock_lines = load_stock_lines

    def execute(self, item_cd: str) -> dict[str, object]:
        normalized = str(item_cd or "").strip()
        if not normalized:
            raise ValueError("itemCd を指定してください。")

        stock_lines, stock_info = self._load_stock_lines()
        grouped = group_locations_by_item(list(stock_lines))
        return {
            "ok": True,
            "itemCd": normalized,
            "stockAsOfLabel": stock_info.stock_as_of_label if stock_info else "",
            "locations": _location_payload(grouped.get(normalized, [])),
        }


class Vendors:
    """§8.9 `GET /api/inventory-order-alert/vendors`"""

    def __init__(self, load_summary: LoadSummary) -> None:
        self._load_summary = load_summary

    def execute(self) -> dict[str, object]:
        summary = self._load_summary()
        rows = summary.rows if summary else []
        seen: dict[str, str] = {}
        for row in rows:
            code = str(row.get("level1_vend_cd") or "").strip()
            if not code or code in seen:
                continue
            seen[code] = str(row.get("level1_vend_name") or "").strip()
        return {
            "ok": True,
            "items": [{"code": code, "name": seen[code]} for code in sorted(seen)],
        }


def dashboard_summary_payload(
    context: DashboardBannerContext,
    *,
    imported_at: object | None = None,
) -> dict[str, object]:
    """§8.11 のレスポンス表現を組み立てる。"""
    return {
        "ok": True,
        "counts": {
            "supplyRisk": context.supply_risk,
            "dormantStock": context.dormant_stock,
            "excessStockRisk": context.excess_stock_risk,
            "attention": context.attention,
            "unconfirmed": context.unconfirmed,
        },
        "stockImport": {
            "importedAt": _jsonable(imported_at) if imported_at is not None else None,
            "stockAsOfLabel": context.stock_as_of_label,
            "isStale": context.stock_stale,
            "hasData": context.has_stock_data,
        },
    }


class DashboardSummary:
    """§8.11 `GET /api/inventory-order-alert/dashboard-summary`"""

    def __init__(self, portal_dashboard: PortalDashboard, load_summary: LoadSummary) -> None:
        self._portal_dashboard = portal_dashboard
        self._load_summary = load_summary

    def execute(self) -> dict[str, object]:
        context = self._portal_dashboard.execute()
        summary = self._load_summary()
        stock_info = summary.stock_info if summary else None
        return dashboard_summary_payload(
            context,
            imported_at=stock_info.imported_at if stock_info else None,
        )

from __future__ import annotations

import csv
import io
from dataclasses import dataclass

from application.shipment_trend.domain.value_objects.fiscal_year import add_months
from application.shipment_trend.domain.value_objects.table_display import format_change_qty, format_change_rate, format_fiscal_year, format_quantity

CSV_BASE_COLUMNS: tuple[tuple[str, str], ...] = (
    ("cust_chrg_psn_cd", "担当者コード"),
    ("cust_code", "得意先コード"),
    ("cust_name", "得意先名"),
    ("item_cd", "内作品番"),
    ("first_fiscal_year", "比較基準年"),
    ("change_rate_pct", "変動率"),
    ("change_qty", "変動数"),
)


@dataclass(frozen=True)
class CsvExportResult:
    content: str
    filename: str


def normalize_row_monthly(row: dict[str, object]) -> dict[str, int]:
    monthly = row.get("monthly")
    if not isinstance(monthly, dict):
        return {}
    return {str(year_month): int(quantity) for year_month, quantity in monthly.items()}


def build_month_range(rows: list[dict[str, object]]) -> list[str]:
    """出力行全体の monthly から最小月〜最大月までの連続月リスト。"""
    all_months: set[str] = set()
    for row in rows:
        all_months.update(normalize_row_monthly(row).keys())
    if not all_months:
        return []
    start = min(all_months)
    end = max(all_months)
    months: list[str] = []
    current = start
    while current <= end:
        months.append(current)
        current = add_months(current, 1)
    return months


def format_monthly_cell(monthly: dict[str, int], year_month: str) -> str:
    if year_month not in monthly:
        return ""
    return format_quantity(monthly[year_month])


def build_csv_headers(month_range: list[str]) -> list[str]:
    return [label for _key, label in CSV_BASE_COLUMNS] + month_range


def build_csv_row(row: dict[str, object], *, month_range: list[str]) -> list[str]:
    monthly = normalize_row_monthly(row)
    base_values = [
        row.get("cust_chrg_psn_cd", ""),
        row.get("cust_code", ""),
        row.get("cust_name", ""),
        row.get("item_cd", ""),
        format_fiscal_year(row.get("first_fiscal_year")),
        format_change_rate(row.get("change_rate_pct")),
        format_change_qty(row.get("change_qty")),
    ]
    monthly_values = [format_monthly_cell(monthly, year_month) for year_month in month_range]
    return [str(value) for value in base_values] + monthly_values


def build_csv_export(rows: list[dict[str, object]], *, as_of_date_label: str) -> CsvExportResult:
    month_range = build_month_range(rows)
    buffer = io.StringIO()
    buffer.write("\ufeff")
    writer = csv.writer(buffer, lineterminator="\r\n")
    writer.writerow(build_csv_headers(month_range))
    for row in rows:
        writer.writerow(build_csv_row(row, month_range=month_range))
    safe_label = as_of_date_label.replace("/", "")
    return CsvExportResult(
        content=buffer.getvalue(),
        filename=f"shipment_trend_{safe_label}.csv",
    )

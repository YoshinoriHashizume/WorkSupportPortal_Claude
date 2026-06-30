from __future__ import annotations

import csv
import io
from typing import Iterable

from apps.inventory_order_alert.domain.format_display import format_cell_display

EXPORT_COLUMNS: list[tuple[str, str]] = [
    ("cust_chrg_psn_cd", "担当者コード"),
    ("cust_code", "得意先コード"),
    ("cust_name", "得意先名"),
    ("item_cd", "得意先品番"),
    ("level1_vend_cd", "仕入先コード"),
    ("level1_vend_name", "仕入先名"),
    ("level1_item_cd", "仕入先品番"),
    ("last_incoming_date", "最終入荷日"),
    ("last_ship_date", "最終出荷日"),
    ("post_shipment_count", "最終入荷日以降の出荷回数"),
    ("post_shipment_total_qty", "最終入荷日以降の出荷数合計"),
    ("stock_qty", "在庫数"),
    ("stock_as_of_label", "在庫時点"),
    ("alert_level", "アラート"),
    ("confirmation_status", "確認状態"),
    ("confirmed_at", "確認日時"),
    ("confirmed_by", "確認者"),
    ("confirmation_memo", "最新メモ"),
    ("confirmation_memo_history", "メモ履歴"),
]

EXPORT_FIELDNAMES = [column for column, _label in EXPORT_COLUMNS]
EXPORT_HEADER_LABELS = {column: label for column, label in EXPORT_COLUMNS}


def render_export_cell(row: dict[str, object], column: str) -> object:
    return format_cell_display(row.get(column, ""), column)


def render_export_csv(rows: Iterable[dict[str, object]]) -> bytes:
    buffer = io.StringIO()
    writer = csv.writer(buffer)
    writer.writerow([EXPORT_HEADER_LABELS[column] for column in EXPORT_FIELDNAMES])
    for row in rows:
        writer.writerow([render_export_cell(row, column) for column in EXPORT_FIELDNAMES])
    return buffer.getvalue().encode("utf-8-sig")

from __future__ import annotations

import csv
import io
from typing import Iterable

from application.inventory_order_alert.domain.value_objects.flow_quadrant import normalize_flow_quadrant
from application.inventory_order_alert.domain.value_objects.format_display import format_cell_display

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
    ("stock_qty", "在庫数(SLIMS)"),
    ("mari_stock_qty", "在庫数(MARI)"),
    ("stock_as_of_label", "在庫時点"),
    ("flow_quadrant", "流動区分"),
    # 判定軸（V-210）は 05 で廃止。既存の CSV 読み込み手順を壊さないよう列だけ残し、値は常に空（design §7.3）。
    ("flow_axis", "判定軸"),
    ("evaluation_period", "判定期間"),
    ("no_incoming_record", "入荷実績なし"),
    ("responsible_department", "責任部署"),
    ("confirmation_status", "確認状態"),
    ("confirmed_at", "確認日時"),
    ("confirmed_by", "確認者"),
    ("confirmation_memo", "最新メモ"),
    ("confirmation_memo_history", "メモ履歴"),
    # 05 第 2 段階（REQ-SFV-F-013）: 既存列の順序は変えず末尾に追加する
    ("months_of_stock", "在庫月数"),
    ("stockout_forecast_month", "在庫切れ予測月"),
    ("demand_forecast_basis", "需要予測の算出根拠"),
    ("recommended_action", "推奨アクション"),
    # 06 在庫切れリスク（REQ-SOR-F-012）: 末尾に追加
    ("stockout_risk", "在庫切れリスク"),
    ("stockout_risk_reasons", "在庫切れリスクの理由"),
    ("days_until_stockout", "猶予日数"),
    ("replenishment_qty", "補充見込み"),
    ("replenishment_earliest_due", "補充見込みの最早納期"),
    ("replenishment_has_overdue", "納期超過"),
    ("shortage_qty", "不足数量"),
    ("lead_time_days", "リードタイム"),
    ("ordering_method", "発注方式"),
    ("upstream_order_qty", "上流工程の発注残"),
    ("upstream_order_overdue", "上流工程の納期超過"),
]

EXPORT_FIELDNAMES = [column for column, _label in EXPORT_COLUMNS]
EXPORT_HEADER_LABELS = {column: label for column, label in EXPORT_COLUMNS}


#: 列は残すが値を出さない列。
EMPTY_COLUMNS = ("flow_axis",)


def render_export_cell(row: dict[str, object], column: str) -> object:
    if column in EMPTY_COLUMNS:
        return ""
    if column == "flow_quadrant":
        # 旧称が行に残っていても新区分名で出す（TC-SFV-D-062）
        return normalize_flow_quadrant(str(row.get(column) or ""))
    if column == "stockout_risk":
        return str(row.get(column) or "")
    if column == "stockout_risk_reasons":
        return "・".join(str(reason) for reason in (row.get(column) or []))
    if column in ("replenishment_has_overdue", "upstream_order_overdue"):
        return "あり" if row.get(column) else ""
    return format_cell_display(row.get(column, ""), column)


def render_export_csv(rows: Iterable[dict[str, object]]) -> bytes:
    buffer = io.StringIO()
    writer = csv.writer(buffer)
    writer.writerow([EXPORT_HEADER_LABELS[column] for column in EXPORT_FIELDNAMES])
    for row in rows:
        writer.writerow([render_export_cell(row, column) for column in EXPORT_FIELDNAMES])
    return buffer.getvalue().encode("utf-8-sig")

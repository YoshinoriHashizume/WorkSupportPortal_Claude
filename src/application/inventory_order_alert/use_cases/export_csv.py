from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from zoneinfo import ZoneInfo

from application.inventory_order_alert.domain.repositories.ports import LoadSummary
from application.inventory_order_alert.domain.value_objects.export_csv import render_export_csv
from application.inventory_order_alert.domain.value_objects.list_query import parse_list_query
from application.inventory_order_alert.domain.value_objects.list_rows import apply_flow_quadrants_to_rows

_TZ = ZoneInfo("Asia/Tokyo")

#: 「入荷実績なし」列は真のときだけ「あり」を出す（design.md §6.3）。
NO_INCOMING_RECORD_LABEL = "あり"


@dataclass(frozen=True)
class ExportCsvResult:
    content: str
    filename: str


class ExportCsv:
    def __init__(self, load_summary: LoadSummary) -> None:
        self._load_summary = load_summary

    def execute(self, *, query_params: dict[str, str] | None = None) -> ExportCsvResult:
        summary = self._load_summary()
        if summary is None or summary.aggregation_error:
            raise ValueError("集計データがありません。SLIMS 在庫 CSV を取り込んでください。")

        query = parse_list_query(query_params or {})
        as_of_date = summary.as_of_date or query.as_of_date
        # 出力は常に全件。絞り込み・ページングは反映しない（design.md §6.3）。
        rows = apply_flow_quadrants_to_rows(summary.rows, as_of_date=as_of_date, query=query)

        selection = query.flow_selection
        rows = [
            {
                **row,
                "flow_axis": selection.axis_label,
                "evaluation_period": selection.period_label,
                "no_incoming_record": (
                    NO_INCOMING_RECORD_LABEL if row.get("no_incoming_record") else ""
                ),
            }
            for row in rows
        ]

        timestamp = datetime.now(_TZ).strftime("%Y%m%d%H%M%S")
        return ExportCsvResult(
            content=render_export_csv(rows),
            filename=f"inventory_order_alert_{timestamp}.csv",
        )

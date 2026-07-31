from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from zoneinfo import ZoneInfo

from application.inventory_order_alert.domain.repositories.ports import LoadSummary
from application.inventory_order_alert.domain.value_objects.export_csv import render_export_csv

_TZ = ZoneInfo("Asia/Tokyo")


@dataclass(frozen=True)
class ExportCsvResult:
    content: str
    filename: str


class ExportCsv:
    def __init__(self, load_summary: LoadSummary) -> None:
        self._load_summary = load_summary

    def execute(self) -> ExportCsvResult:
        summary = self._load_summary()
        if summary is None or summary.aggregation_error:
            raise ValueError("集計データがありません。SLIMS 在庫 CSV を取り込んでください。")
        timestamp = datetime.now(_TZ).strftime("%Y%m%d%H%M%S")
        return ExportCsvResult(
            content=render_export_csv(summary.rows),
            filename=f"inventory_order_alert_{timestamp}.csv",
        )

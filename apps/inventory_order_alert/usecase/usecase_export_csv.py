from __future__ import annotations

from dataclasses import dataclass

from django.utils import timezone

from apps.inventory_order_alert.domain.ports import LoadSummary
from apps.inventory_order_alert.domain.export_csv import render_export_csv


@dataclass(frozen=True)
class ExportCsvResult:
    content: str
    filename: str


class ExportCsvUsecase:
    def __init__(self, load_summary: LoadSummary) -> None:
        self._load_summary = load_summary

    def execute(self) -> ExportCsvResult:
        summary = self._load_summary()
        if summary is None or summary.aggregation_error:
            raise ValueError("集計データがありません。SLIMS 在庫 CSV を取り込んでください。")
        timestamp = timezone.localtime().strftime("%Y%m%d%H%M%S")
        return ExportCsvResult(
            content=render_export_csv(summary.rows),
            filename=f"inventory_order_alert_{timestamp}.csv",
        )

from __future__ import annotations

from dataclasses import dataclass

from application.shipment_trend.domain.value_objects.export_csv import build_csv_export
from application.shipment_trend.domain.value_objects.list_filter import (
    apply_list_filters,
    build_filter_options,
    parse_list_filter_params,
)
from application.shipment_trend.domain.repositories.ports import LoadLatestRows
from application.shipment_trend.domain.value_objects.trend_metrics import hydrate_rows_metrics


@dataclass(frozen=True)
class ExportCsvResult:
    content: str
    filename: str


class ExportCsv:
    def __init__(self, load_summary: LoadLatestRows) -> None:
        self._load_summary = load_summary

    def execute(self, *, query_params: dict[str, str]) -> ExportCsvResult:
        summary = self._load_summary()
        if summary is None or not summary.rows:
            raise ValueError("出力対象のデータがありません。")

        options = build_filter_options(summary.rows)
        filter_params = parse_list_filter_params(query_params, options)
        hydrated_rows = hydrate_rows_metrics(summary.rows, summary.as_of_date)
        rows = apply_list_filters(hydrated_rows, filter_params)
        as_of_label = summary.as_of_date.strftime("%Y%m%d") if summary.as_of_date else "unknown"
        result = build_csv_export(rows, as_of_date_label=as_of_label)
        return ExportCsvResult(content=result.content, filename=result.filename)

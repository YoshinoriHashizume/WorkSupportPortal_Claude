from __future__ import annotations

from dataclasses import dataclass

from application.shipment_trend.domain.value_objects.chart_data import build_chart_payload, find_row
from application.shipment_trend.domain.repositories.ports import LoadAppSettings, LoadBaselineYear, LoadLatestRows


@dataclass(frozen=True)
class ChartDataResult:
    payload: dict[str, object]


class ChartData:
    def __init__(
        self,
        load_summary: LoadLatestRows,
        load_settings: LoadAppSettings,
        load_baseline_year: LoadBaselineYear,
    ) -> None:
        self._load_summary = load_summary
        self._load_settings = load_settings
        self._load_baseline_year = load_baseline_year

    def execute(self, *, cust_code: str, item_cd: str) -> ChartDataResult:
        cust_code = cust_code.strip()
        item_cd = item_cd.strip()
        if not cust_code or not item_cd:
            raise ValueError("custCode と itemCd を指定してください。")

        summary = self._load_summary()
        if summary is None or not summary.rows:
            raise ValueError("集計データがありません。データ更新を実行してください。")
        if summary.as_of_date is None:
            raise ValueError("集計基準日がありません。")

        row = find_row(summary.rows, cust_code=cust_code, item_cd=item_cd)
        if row is None:
            raise ValueError("指定された得意先×内作品番が見つかりません。")

        settings = self._load_settings()
        baseline = self._load_baseline_year(cust_code=cust_code, item_cd=item_cd)
        return ChartDataResult(
            payload=build_chart_payload(
                row,
                as_of_date=summary.as_of_date,
                settings=settings,
                baseline_fiscal_year=baseline,
            ),
        )

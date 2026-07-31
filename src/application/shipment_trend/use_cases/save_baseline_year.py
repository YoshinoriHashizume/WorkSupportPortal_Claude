from __future__ import annotations

from dataclasses import dataclass

from application.shipment_trend.domain.repositories.ports import LoadLatestRows, SaveBaselineYearFn
from application.shipment_trend.domain.value_objects.trend_metrics import (
    available_baseline_years,
    data_first_fiscal_year,
)


@dataclass(frozen=True)
class SaveBaselineYearResult:
    cust_code: str
    item_cd: str
    baseline_fiscal_year: int
    data_first_fiscal_year: int | None


class SaveBaselineYear:
    def __init__(
        self,
        load_summary: LoadLatestRows,
        save_baseline_year: SaveBaselineYearFn,
    ) -> None:
        self._load_summary = load_summary
        self._save_baseline_year = save_baseline_year

    def execute(
        self,
        *,
        cust_code: str,
        item_cd: str,
        baseline_fiscal_year: int,
        updated_by: object,
    ) -> SaveBaselineYearResult:
        cust_code = cust_code.strip()
        item_cd = item_cd.strip()
        if not cust_code or not item_cd:
            raise ValueError("custCode と itemCd を指定してください。")
        try:
            year = int(baseline_fiscal_year)
        except (TypeError, ValueError) as exc:
            raise ValueError("baselineYear は整数で指定してください。") from exc

        summary = self._load_summary()
        if summary is None or not summary.rows:
            raise ValueError("集計データがありません。データ更新を実行してください。")
        if summary.as_of_date is None:
            raise ValueError("集計基準日がありません。")

        row = None
        for candidate in summary.rows:
            if (
                str(candidate.get("cust_code") or "").strip() == cust_code
                and str(candidate.get("item_cd") or "").strip() == item_cd
            ):
                row = candidate
                break
        if row is None:
            raise ValueError("指定された得意先×内作品番が見つかりません。")

        monthly = row.get("monthly") or {}
        if not isinstance(monthly, dict):
            monthly = {}
        monthly_int = {str(key): int(value) for key, value in monthly.items()}
        candidates = available_baseline_years(monthly_int, summary.as_of_date)
        if year not in candidates:
            raise ValueError("比較基準年の候補に含まれない年は設定できません。")

        self._save_baseline_year(
            cust_code=cust_code,
            item_cd=item_cd,
            baseline_fiscal_year=year,
            updated_by=updated_by,
        )
        return SaveBaselineYearResult(
            cust_code=cust_code,
            item_cd=item_cd,
            baseline_fiscal_year=year,
            data_first_fiscal_year=data_first_fiscal_year(monthly_int),
        )

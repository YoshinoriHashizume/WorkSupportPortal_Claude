from __future__ import annotations

from dataclasses import dataclass

from application.shipment_trend.domain.repositories.ports import CreateRefreshRecord, RunAggregation


@dataclass(frozen=True)
class RefreshDataResult:
    message: str
    row_count: int
    error: str


class RefreshData:
    def __init__(
        self,
        run_aggregation: RunAggregation,
        create_refresh_record: CreateRefreshRecord,
    ) -> None:
        self._run_aggregation = run_aggregation
        self._create_refresh_record = create_refresh_record

    def execute(self, *, user: object | None) -> RefreshDataResult:
        refresh_record = self._create_refresh_record(user=user)
        error, row_count = self._run_aggregation(refresh_record)
        if error:
            return RefreshDataResult(
                message="Oracle 集計でエラーが発生しました。",
                row_count=row_count,
                error=error,
            )
        return RefreshDataResult(
            message=f"データを更新しました（{row_count:,} 件）。",
            row_count=row_count,
            error="",
        )

from __future__ import annotations

from dataclasses import dataclass

from apps.shipment_trend.domain.ports import RunAggregation
from apps.shipment_trend.infrastructure.persistence.summary_snapshot_repository import create_refresh_record


@dataclass(frozen=True)
class RefreshDataResult:
    message: str
    row_count: int
    error: str


class RefreshDataUsecase:
    def __init__(self, run_aggregation: RunAggregation) -> None:
        self._run_aggregation = run_aggregation

    def execute(self, *, user: object | None) -> RefreshDataResult:
        refresh_record = create_refresh_record(user=user)
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

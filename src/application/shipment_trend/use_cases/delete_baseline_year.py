from __future__ import annotations

from dataclasses import dataclass

from application.shipment_trend.domain.repositories.ports import DeleteBaselineYearFn


@dataclass(frozen=True)
class DeleteBaselineYearResult:
    cust_code: str
    item_cd: str
    deleted: bool


class DeleteBaselineYear:
    def __init__(self, delete_baseline_year: DeleteBaselineYearFn) -> None:
        self._delete_baseline_year = delete_baseline_year

    def execute(self, *, cust_code: str, item_cd: str) -> DeleteBaselineYearResult:
        cust_code = cust_code.strip()
        item_cd = item_cd.strip()
        if not cust_code or not item_cd:
            raise ValueError("custCode と itemCd を指定してください。")
        deleted = self._delete_baseline_year(cust_code=cust_code, item_cd=item_cd)
        return DeleteBaselineYearResult(cust_code=cust_code, item_cd=item_cd, deleted=deleted)

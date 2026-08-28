from __future__ import annotations

from dataclasses import dataclass

from application.receipt_comparison.domain.value_objects.receipt_flag import ReceiptFlag


@dataclass
class ComparisonRow:
    """検収書比較の1行。

    `existing_id` は保存済み比較結果の同一性を表す識別子であり、値ではなく
    「どの行か」を指す。突合処理は生成後の行に対して受入フラグや備考を
    書き換えるため、値オブジェクトではなくエンティティとして扱う。
    """

    receipt_flag: int
    mari_item_cd: str = ""
    mari_date: str = ""
    mari_qty: str = ""
    delivery_place: str = ""
    supplier_item_cd: str = ""
    supplier_delivery_month_day: str = ""
    supplier_qty: str = ""
    supplier_cancel_qty: str = ""
    supplier_name: str = ""
    remarks: str = ""
    existing_id: int | None = None

    @property
    def flag_label(self) -> str:
        return ReceiptFlag(self.receipt_flag).label


__all__ = ["ComparisonRow"]

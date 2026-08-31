from __future__ import annotations

from enum import IntEnum


class ReceiptFlag(IntEnum):
    """突合結果フラグ（〇 / △ / ×）。Django 非依存の正。"""

    NG = 0
    OK = 1
    PENDING = 2

    @property
    def label(self) -> str:
        return _RECEIPT_FLAG_LABELS[self]

    @classmethod
    def choices(cls) -> list[tuple[int, str]]:
        return [(member.value, member.label) for member in cls]


_RECEIPT_FLAG_LABELS: dict[ReceiptFlag, str] = {
    ReceiptFlag.NG: "×",
    ReceiptFlag.OK: "〇",
    ReceiptFlag.PENDING: "△",
}

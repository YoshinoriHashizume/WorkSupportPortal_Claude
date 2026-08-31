from __future__ import annotations

from dataclasses import dataclass
from datetime import date, datetime


@dataclass(frozen=True)
class SnapshotRowPatchResult:
    cust_code: str
    item_cd: str
    previous_last_ship_date: str
    new_last_ship_date: str
    previous_flow_quadrant: str
    new_flow_quadrant: str
    confirmation_reset_count: int


def parse_patch_date(value: str, *, today: date) -> date:
    text = str(value or "").strip().lower()
    if text in {"today", "今日"}:
        return today
    normalized = text.replace("-", "/")
    for fmt in ("%Y/%m/%d", "%Y%m%d"):
        try:
            return datetime.strptime(normalized, fmt).date()
        except ValueError:
            continue
    raise ValueError(f"日付形式が不正です: {value}")


def find_snapshot_row_index(rows: list[dict[str, object]], *, cust_code: str, item_cd: str) -> int:
    for index, row in enumerate(rows):
        if str(row.get("cust_code") or "") == cust_code and str(row.get("item_cd") or "") == item_cd:
            return index
    raise ValueError(f"スナップショットに cust_code={cust_code}, item_cd={item_cd} の行がありません。")

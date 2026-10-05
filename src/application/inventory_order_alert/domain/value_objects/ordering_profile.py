"""発注方式（V-227）とリードタイム（V-225）（06 design §4.2）。

MARI `M_ITEM.MRP_ODR_TYP`（4 = 手動発注 / 5 = MRP 発注）と `M_ITEM.FIXED_LT`（日）を業務用語に写す。
"""

from __future__ import annotations

ORDERING_MANUAL = "手動発注"
ORDERING_MRP = "MRP 発注"
ORDERING_UNKNOWN = "不明"
ORDERING_METHODS = (ORDERING_MANUAL, ORDERING_MRP, ORDERING_UNKNOWN)

#: URL・ペイロードで使うキー。
ORDERING_METHOD_KEYS = {ORDERING_MANUAL: "manual", ORDERING_MRP: "mrp", ORDERING_UNKNOWN: "unknown"}

LEAD_TIME_SOURCE_MASTER = "master"
LEAD_TIME_SOURCE_DEFAULT = "default"

_CODE_TO_METHOD = {"4": ORDERING_MANUAL, "5": ORDERING_MRP}


def ordering_method_from_code(code: object) -> str:
    text = str(code if code is not None else "").strip()
    if text.endswith(".0"):
        text = text[:-2]
    return _CODE_TO_METHOD.get(text, ORDERING_UNKNOWN)


def resolve_lead_time_days(master_value: object, *, default_days: int) -> tuple[int, str]:
    """品目マスタのリードタイム（日）。空・0・不正は既定値で代替し、その出所を返す。"""
    try:
        days = int(float(master_value)) if master_value is not None and str(master_value).strip() != "" else 0
    except (TypeError, ValueError):
        days = 0
    if days > 0:
        return days, LEAD_TIME_SOURCE_MASTER
    return int(default_days), LEAD_TIME_SOURCE_DEFAULT

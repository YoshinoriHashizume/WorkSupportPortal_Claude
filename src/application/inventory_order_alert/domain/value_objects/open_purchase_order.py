"""発注残（V-224）の読み取り（06 design §4.1、08 design §2.4 で簡素化）。

発注残は MARI `T_RLSD_PUCH_ODR` の状態 2・取消なし・残数 > 0 の明細。取込時に infrastructure が
行へ生データ（`open_purchase_orders`）として付け、ここで照合単位ぶんを集める。
明細は発注コード（`order_cd` = `PUCH_ODR_CD`）で識別する。同品番・同仕入先・同納期・同数量の別明細
（カンバン式の分割発注）は正規のデータなので、値の組では重複とみなさない（2026/09/18 改訂）。

2026/09/23 改訂（spec/08_stockout-risk-rework）: 補充見込み（V-226）・補充期限（V-229）・
長期納期超過（V-230）を撤去した。納期での振り分け（基準日より後は来る／納期遅れは来ない）は
`stock_projection.py` が行う。
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import date

from application.inventory_order_alert.domain.value_objects.dates import parse_optional_ymd


@dataclass(frozen=True)
class OpenPurchaseOrder:
    item_cd: str
    vend_cd: str
    due_date: date | None
    remaining_qty: int
    #: 発注コード（`PUCH_ODR_CD`）。旧スナップショットの行では空
    order_cd: str = ""

    def __post_init__(self) -> None:
        object.__setattr__(self, "remaining_qty", max(int(self.remaining_qty), 0))


def _order_from_dict(raw: object) -> OpenPurchaseOrder | None:
    if not isinstance(raw, dict):
        return None
    due_text = str(raw.get("due_date") or "").strip()
    due: date | None = None
    if due_text:
        try:
            due = parse_optional_ymd(due_text)
        except ValueError:
            due = None
    try:
        qty = int(float(raw.get("remaining_qty") or 0))
    except (TypeError, ValueError):
        qty = 0
    return OpenPurchaseOrder(
        item_cd=str(raw.get("item_cd") or "").strip(),
        vend_cd=str(raw.get("vend_cd") or "").strip(),
        due_date=due,
        remaining_qty=qty,
        order_cd=str(raw.get("order_cd") or "").strip(),
    )


def open_purchase_orders_from_rows(rows: list[dict[str, object]]) -> list[OpenPurchaseOrder]:
    """照合単位の行が持つ発注残（生データ）を集め、同じ明細の重複を除く。

    同一性は発注コード（`order_cd`）で決める。`order_cd` がない旧スナップショットの行だけ
    従来の (品番, 仕入先, 納期, 数量) の組で除く。
    """
    seen: set[object] = set()
    orders: list[OpenPurchaseOrder] = []
    for row in rows:
        for raw in row.get("open_purchase_orders") or []:
            order = _order_from_dict(raw)
            if order is None:
                continue
            key: object = ("cd", order.order_cd) if order.order_cd else (order.item_cd, order.vend_cd, order.due_date, order.remaining_qty)
            if key in seen:
                continue
            seen.add(key)
            orders.append(order)
    return orders

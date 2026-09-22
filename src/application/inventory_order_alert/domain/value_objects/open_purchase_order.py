"""発注残（V-224）と補充見込み（V-226）（06 design §4.1）。

発注残は MARI `T_RLSD_PUCH_ODR` の状態 2・取消なし・残数 > 0 の明細。取込時に infrastructure が
行へ生データ（`open_purchase_orders`）として付け、ここで照合単位ぶんを集めて補充見込みにする。
明細は発注コード（`order_cd` = `PUCH_ODR_CD`）で識別する。同品番・同仕入先・同納期・同数量の別明細
（カンバン式の分割発注）は正規のデータなので、値の組では重複とみなさない（2026/09/18 改訂）。

補充に数えるのは 補充期限（V-229 = max(予測月の 1 日, 基準日) ＋ 安全日数）までに納期がある明細のみ。
納期超過が リードタイム＋安全日数 を超える明細は 長期納期超過（V-230）として補充に数えない（2026/09/21 改訂）。
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import date, timedelta

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


@dataclass(frozen=True)
class ReplenishmentOutlook:
    qty: int
    later_qty: int
    earliest_due: date | None
    has_overdue: bool
    unknown: bool = False
    #: 長期納期超過（V-230）の残数。補充見込みには数えない（2026/09/21）
    stale_qty: int = 0
    #: 上流工程（完成品直下より前の工程）の発注残。補充見込みには数えず、理由と危険の判定に使う（2026/09/18）
    upstream_qty: int = 0
    upstream_overdue: bool = False
    upstream_earliest_due: date | None = None
    #: 上流工程のうち納期超過でなく納期が補充期限以前の残数（納期なしは含めない）。納期超過と混在しても > 0 なら危険にしない（2026/09/18、2026/09/21 納期の窓）
    upstream_pending_qty: int = 0

    @classmethod
    def unknown_outlook(cls) -> "ReplenishmentOutlook":
        return cls(qty=0, later_qty=0, earliest_due=None, has_overdue=False, unknown=True)

    @classmethod
    def empty(cls) -> "ReplenishmentOutlook":
        return cls(qty=0, later_qty=0, earliest_due=None, has_overdue=False, unknown=False)


def _month_first(month: str) -> date:
    year, mon = (int(part) for part in month.split("-"))
    return date(year, mon, 1)


def replenishment_deadline(as_of_date: date, stockout_month: str | None, *, safety_days: int) -> date | None:
    """補充期限（V-229）: max(在庫切れ予測月の 1 日, 基準日) ＋ 安全日数。予測月が空なら None。

    猶予日数（V-228）が予測月の 1 日を基準に保守的に取るのと対で、補充側にも安全日数を効かせる（2026/09/21）。
    """
    if not stockout_month:
        return None
    return max(_month_first(stockout_month), as_of_date) + timedelta(days=safety_days)


def build_replenishment_outlook(
    orders: list[OpenPurchaseOrder],
    *,
    as_of_date: date,
    stockout_month: str | None,
    deadline: date | None,
    stale_after_days: int,
    level1_pairs: set[tuple[str, str]] | None = None,
) -> ReplenishmentOutlook:
    """補充期限（`deadline`）までに納期がある残数を合算する。

    直下の工程の明細は、納期超過が `stale_after_days`（リードタイム＋安全日数）を超えれば 長期納期超過（`stale_qty`）、
    納期 ≤ 補充期限 なら 補充見込み（`qty`）、それ以外（納期なしを含む）は `later_qty`。納期超過は長期を含めて
    `has_overdue` に映す。

    `level1_pairs`（完成品直下の工程の (仕入先品番, 仕入先)）を渡すと、それ以外の発注残は上流工程として
    別に集計する（補充見込みには数えない）。上流のうち「流れている」（`upstream_pending_qty`）とみなすのは
    納期超過でなく納期 ≤ 補充期限 のもののみ。渡さなければ全件を直下の工程として扱う。
    """
    stale_before = as_of_date - timedelta(days=stale_after_days)
    upstream_qty = 0
    upstream_pending = 0
    upstream_overdue = False
    upstream_earliest: date | None = None
    direct: list[OpenPurchaseOrder] = []
    for order in orders:
        if order.remaining_qty <= 0:
            continue
        if level1_pairs is not None and (order.item_cd, order.vend_cd) not in level1_pairs:
            upstream_qty += order.remaining_qty
            if order.due_date is not None and order.due_date < as_of_date:
                upstream_overdue = True
            elif order.due_date is not None and deadline is not None and order.due_date <= deadline:
                upstream_pending += order.remaining_qty
            if order.due_date is not None and (upstream_earliest is None or order.due_date < upstream_earliest):
                upstream_earliest = order.due_date
            continue
        direct.append(order)

    if not stockout_month or deadline is None:
        return ReplenishmentOutlook(
            qty=0, later_qty=0, earliest_due=None, has_overdue=False,
            upstream_qty=upstream_qty, upstream_overdue=upstream_overdue, upstream_earliest_due=upstream_earliest,
            upstream_pending_qty=upstream_pending,
        )
    qty = 0
    later = 0
    stale = 0
    earliest: date | None = None
    has_overdue = False
    for order in direct:
        if order.due_date is None or order.due_date > deadline:
            later += order.remaining_qty
            continue
        if order.due_date < as_of_date:
            has_overdue = True
            if order.due_date < stale_before:
                stale += order.remaining_qty
                continue
        qty += order.remaining_qty
        if earliest is None or order.due_date < earliest:
            earliest = order.due_date
    return ReplenishmentOutlook(
        qty=qty, later_qty=later, earliest_due=earliest, has_overdue=has_overdue, stale_qty=stale,
        upstream_qty=upstream_qty, upstream_overdue=upstream_overdue, upstream_earliest_due=upstream_earliest,
        upstream_pending_qty=upstream_pending,
    )


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

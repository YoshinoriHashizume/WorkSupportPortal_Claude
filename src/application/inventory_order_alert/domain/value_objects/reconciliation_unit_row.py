"""照合単位行（T-213）: 一覧・CSV で照合単位（T-208）を 1 行にまとめた行（spec/13 design §4）。

集計スナップショットは得意先 × 得意先品番の行で保存し、読み込み時にここで照合単位行にまとめる。
合算・重複除去の規則は在庫シミュレーション（`stock_simulation.build_stock_simulation_input`）と同じにし、
グラフの材料を判定（対応区分 S-204）の材料と一致させる（REQ-RUR-F-008）。
"""

from __future__ import annotations

from collections.abc import Iterable
from datetime import date

from application.inventory_order_alert.domain.value_objects.confirmation import (  # noqa: F401  照合単位行の確認記録は confirmation.py に置く
    merge_memo_entries,
    unit_confirmation,
)
from application.inventory_order_alert.domain.value_objects.dates import parse_optional_ymd
from application.inventory_order_alert.domain.value_objects.ordering_profile import ORDERING_MANUAL
from application.inventory_order_alert.domain.value_objects.reconciliation_unit import ReconciliationUnits

#: 系列ごとの重複除去キー（同じ値が複数行に複製されている単位）
CUSTOMER_ITEM_KEYS = ("cust_code", "item_cd")
CUSTOMER_INTERNAL_KEYS = ("cust_code", "internal_item_cd")
LEVEL1_PAIR_KEYS = ("level1_item_cd", "level1_vend_cd")
ITEM_KEYS = ("item_cd",)

#: 得意先 × 得意先品番ごとに合算する系列（出荷）
_SHIPMENT_SERIES = ("daily_shipment", "shipment_trend")
#: 内作品番 × 仕入先の組ごとに 1 回だけ数える系列（入荷）
_INCOMING_SERIES = ("daily_incoming", "incoming_trend", "planned_incoming")
#: 得意先 × 内作品番ごとに 1 回だけ数える系列（内示）
_DEMAND_SERIES = ("unconfirmed_order_daily", "unconfirmed_order_trend")

#: 得意先別内訳（V-242）に載せる値
_BREAKDOWN_KEYS = (
    "cust_code",
    "cust_name",
    "item_cd",
    "cust_chrg_psn_cd",
    "unconfirmed_order_trend",
    "shipment_trend",
    "post_shipment_count",
    "post_shipment_total_qty",
    "last_ship_date",
)


def _text(value: object) -> str:
    return str(value or "").strip()


def _as_int(value: object) -> int:
    try:
        return int(float(value or 0))
    except (TypeError, ValueError):
        return 0


def _as_float(value: object) -> float | None:
    text = _text(value)
    if not text:
        return None
    try:
        return float(text)
    except (TypeError, ValueError):
        return None


def _parse_date(value: object) -> date | None:
    text = _text(value)
    if not text:
        return None
    try:
        return parse_optional_ymd(text)
    except (TypeError, ValueError):
        return None


def _points(value: object) -> list[dict[str, object]]:
    if not isinstance(value, list):
        return []
    return [point for point in value if isinstance(point, dict)]


def _demand_total(row: dict[str, object]) -> int:
    return sum(_as_int(point.get("qty")) for point in _points(row.get("unconfirmed_order_trend")))


def _unique_by(rows: Iterable[dict[str, object]], keys: tuple[str, ...]) -> list[dict[str, object]]:
    seen: set[tuple[str, ...]] = set()
    unique: list[dict[str, object]] = []
    for row in rows:
        pair = tuple(_text(row.get(name)) for name in keys)
        if pair in seen:
            continue
        seen.add(pair)
        unique.append(row)
    return unique


def _merge_series(rows: list[dict[str, object]], key: str, dedupe_keys: tuple[str, ...]) -> list[dict[str, object]]:
    """`dedupe_keys` の重複を除いた行の系列を、日（`date`）または月（`month`）ごとに合算する。"""
    totals: dict[tuple[str, str], int] = {}
    for row in _unique_by(rows, dedupe_keys):
        for point in _points(row.get(key)):
            if point.get("date"):
                period = ("date", _text(point.get("date")))
            elif point.get("month"):
                period = ("month", _text(point.get("month")))
            else:
                continue
            totals[period] = totals.get(period, 0) + _as_int(point.get("qty"))
    return [{name: value, "qty": qty} for (name, value), qty in sorted(totals.items(), key=lambda item: item[0][1])]


def _newest_date_text(rows: list[dict[str, object]], key: str) -> str:
    best: tuple[date, str] | None = None
    for row in rows:
        text = _text(row.get(key))
        parsed = _parse_date(text)
        if parsed is None:
            continue
        if best is None or parsed > best[0]:
            best = (parsed, text)
    return best[1] if best else ""


def _sum_stock(rows: list[dict[str, object]], key: str) -> str:
    """得意先品番の重複を除いて合算する。全品番が空なら空（在庫なしの判定を変えない）。"""
    total = 0.0
    has_value = False
    for row in _unique_by(rows, ITEM_KEYS):
        value = _as_float(row.get(key))
        if value is None:
            continue
        has_value = True
        total += value
    if not has_value:
        return ""
    return str(int(total)) if total.is_integer() else str(total)


def _sum_number(rows: list[dict[str, object]], key: str, dedupe_keys: tuple[str, ...]) -> int | float:
    total = 0.0
    for row in _unique_by(rows, dedupe_keys):
        value = _as_float(row.get(key))
        if value is not None:
            total += value
    return int(total) if total.is_integer() else total


def _merge_location_detail(rows: list[dict[str, object]]) -> str:
    parts: list[str] = []
    for row in _unique_by(rows, ITEM_KEYS):
        for part in _text(row.get("stock_location_detail")).split(";"):
            if part and part not in parts:
                parts.append(part)
    return ";".join(parts)


def _merge_open_orders(rows: list[dict[str, object]]) -> list[dict[str, object]]:
    orders: list[dict[str, object]] = []
    seen: set[str] = set()
    for row in rows:
        for order in _points(row.get("open_purchase_orders")):
            order_cd = _text(order.get("order_cd"))
            if order_cd and order_cd in seen:
                continue
            if order_cd:
                seen.add(order_cd)
            orders.append(dict(order))
    return orders


def _ordered_values(representative: dict[str, object], rows: list[dict[str, object]], key: str) -> list[str]:
    """代表の値を先頭に、以降は得意先コード順で重複を除いた値の一覧。"""
    values: list[str] = []
    first = _text(representative.get(key))
    if first:
        values.append(first)
    for row in sorted(rows, key=lambda r: (_text(r.get("cust_code")), _text(r.get("item_cd")))):
        value = _text(row.get(key))
        if value and value not in values:
            values.append(value)
    return values


def select_representative(unit_rows: list[dict[str, object]]) -> dict[str, object]:
    """代表得意先（V-241）の行: 内示推移の全月合計が最大の得意先、同数は得意先コードの小さい方。

    その得意先が複数の得意先品番を持つときは、内示推移の合計が最大の得意先品番（同数は小さい方）。
    """
    demand_by_customer: dict[str, int] = {}
    for row in _unique_by(unit_rows, CUSTOMER_INTERNAL_KEYS):
        cust_code = _text(row.get("cust_code"))
        demand_by_customer[cust_code] = demand_by_customer.get(cust_code, 0) + _demand_total(row)
    for row in unit_rows:
        demand_by_customer.setdefault(_text(row.get("cust_code")), 0)
    representative_cust = min(demand_by_customer, key=lambda cust: (-demand_by_customer[cust], cust))
    candidates = [row for row in unit_rows if _text(row.get("cust_code")) == representative_cust]
    return min(candidates, key=lambda row: (-_demand_total(row), _text(row.get("item_cd"))))


def _customer_breakdown(rows: list[dict[str, object]]) -> list[dict[str, object]]:
    ordered = sorted(rows, key=lambda r: (_text(r.get("cust_code")), _text(r.get("item_cd"))))
    return [{key: row.get(key) for key in _BREAKDOWN_KEYS} for row in _unique_by(ordered, CUSTOMER_ITEM_KEYS)]


def _merged_values(unit_rows: list[dict[str, object]]) -> dict[str, object]:
    """2 行以上の照合単位で合算する値。どの行にもないキーは作らない（旧データの「未取得」を保つ）。"""
    values: dict[str, object] = {}
    for key in _SHIPMENT_SERIES:
        values[key] = _merge_series(unit_rows, key, CUSTOMER_ITEM_KEYS)
    for key in _INCOMING_SERIES:
        values[key] = _merge_series(unit_rows, key, LEVEL1_PAIR_KEYS)
    for key in _DEMAND_SERIES:
        values[key] = _merge_series(unit_rows, key, CUSTOMER_INTERNAL_KEYS)
    values["stock_qty"] = _sum_stock(unit_rows, "stock_qty")
    values["mari_stock_qty"] = _sum_number(unit_rows, "mari_stock_qty", ITEM_KEYS)
    values["stock_location_detail"] = _merge_location_detail(unit_rows)
    values["last_incoming_date"] = _newest_date_text(unit_rows, "last_incoming_date")
    values["last_ship_date"] = _newest_date_text(unit_rows, "last_ship_date")
    values["post_shipment_count"] = _sum_number(unit_rows, "post_shipment_count", CUSTOMER_ITEM_KEYS)
    values["post_shipment_total_qty"] = _sum_number(unit_rows, "post_shipment_total_qty", CUSTOMER_ITEM_KEYS)
    values["open_purchase_orders"] = _merge_open_orders(unit_rows)
    if any(_text(row.get("ordering_method")) == ORDERING_MANUAL for row in unit_rows):
        values["ordering_method"] = ORDERING_MANUAL
    return {key: value for key, value in values.items() if any(key in row for row in unit_rows)}


def _merge_unit(unit_rows: list[dict[str, object]]) -> dict[str, object]:
    representative = select_representative(unit_rows)
    merged = dict(representative)
    # 1 行だけの照合単位は元の行の値をそのまま使う（並び順・キーの有無を変えない）
    if len(unit_rows) > 1:
        merged.update(_merged_values(unit_rows))

    merged["cust_codes"] = _ordered_values(representative, unit_rows, "cust_code")
    merged["cust_names"] = _ordered_values(representative, unit_rows, "cust_name")
    merged["cust_chrg_psn_cds"] = _ordered_values(representative, unit_rows, "cust_chrg_psn_cd")
    merged["item_cds"] = _ordered_values(representative, unit_rows, "item_cd")
    merged["level1_vend_cds"] = _ordered_values(representative, unit_rows, "level1_vend_cd")
    merged["level1_vend_names"] = _ordered_values(representative, unit_rows, "level1_vend_name")
    merged["level1_item_cds"] = _ordered_values(representative, unit_rows, "level1_item_cd")
    merged["customer_breakdown"] = _customer_breakdown(unit_rows)
    merged["unit_member_count"] = len(_unique_by(unit_rows, CUSTOMER_ITEM_KEYS))
    return merged


def build_reconciliation_unit_rows(rows: list[dict[str, object]]) -> list[dict[str, object]]:
    """行を照合単位ごとに 1 行にまとめる（入力は変更しない。REQ-RUR-F-001・F-002）。

    得意先品番が空で照合単位に属さない行は、そのまま 1 行で返す。返す順は各単位の最初の行の順。
    """
    units = ReconciliationUnits.build(rows)
    grouped: dict[str, list[dict[str, object]]] = {}
    order: list[tuple[str, object]] = []
    for index, row in enumerate(rows):
        unit = units.unit_of(_text(row.get("item_cd")))
        if unit is None:
            order.append(("single", index))
            continue
        if unit.key not in grouped:
            grouped[unit.key] = []
            order.append(("unit", unit.key))
        grouped[unit.key].append(row)

    result: list[dict[str, object]] = []
    for kind, value in order:
        if kind == "single":
            result.append(_merge_unit([rows[value]]))  # type: ignore[index]
        else:
            result.append(_merge_unit(grouped[value]))  # type: ignore[index]
    return result


def find_unit_row(rows: list[dict[str, object]], *, cust_code: str, item_cd: str) -> dict[str, object] | None:
    """（得意先コード, 得意先品番）を含む照合単位行。代表の値で一致する行を優先する（spec/13 design §6.2）。"""
    for row in rows:
        if _text(row.get("cust_code")) == cust_code and _text(row.get("item_cd")) == item_cd:
            return row
    for row in rows:
        item_cds = row.get("item_cds")
        if isinstance(item_cds, list) and item_cd in item_cds:
            return row
    return None


def unit_item_cds_for(rows: list[dict[str, object]], *, cust_code: str, item_cd: str) -> tuple[str, ...]:
    """確認記録を書く得意先品番: 照合単位行の得意先品番すべて。行がなければ受け取った品番だけ。"""
    row = find_unit_row(rows, cust_code=cust_code, item_cd=item_cd)
    item_cds = row.get("item_cds") if row is not None else None
    if isinstance(item_cds, list) and item_cds:
        return tuple(str(value) for value in item_cds)
    return (item_cd,)

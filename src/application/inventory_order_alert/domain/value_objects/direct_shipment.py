"""直送仕入先（V-240）と直送品（T-212）の判定（spec/12_direct-shipment-exclusion design §4）。

直送品は品物が SLIMS の倉庫を通らず得意先へ直送されるため、SLIMS 在庫数から在庫切れを判定できない。
取込の後処理の最初で照合単位ごと取り除き、集計スナップショットに保存しない（design §3.1 案 A）。
"""

from __future__ import annotations

from collections.abc import Iterable
from dataclasses import dataclass
from typing import Literal

from application.inventory_order_alert.domain.value_objects.reconciliation_unit import ReconciliationUnits

MAX_VENDOR_CODE_LENGTH = 20

VendorNameStatus = Literal["found", "not_found", "unavailable"]


def _strip(value: object) -> str:
    return str(value or "").strip()


@dataclass(frozen=True)
class DirectShipmentSuppliers:
    """直送仕入先（V-240）の仕入先コードの集合。昇順・重複なし・0 件を許す。"""

    codes: tuple[str, ...] = ()

    @classmethod
    def parse(cls, values: Iterable[str]) -> "DirectShipmentSuppliers":
        """入力を検証して生成する。空・重複・長すぎは ValueError（design §8）。"""
        seen: set[str] = set()
        for value in values:
            code = _strip(value)
            if not code:
                raise ValueError("直送仕入先に空の仕入先コードは登録できません。")
            if len(code) > MAX_VENDOR_CODE_LENGTH:
                raise ValueError(f"仕入先コードは {MAX_VENDOR_CODE_LENGTH} 文字以内で指定してください。")
            if code in seen:
                raise ValueError(f"直送仕入先に同じ仕入先コードが重複しています: {code}")
            seen.add(code)
        return cls(tuple(sorted(seen)))

    @classmethod
    def from_stored(cls, value: object) -> "DirectShipmentSuppliers":
        """DB の保存値を読む。不正な要素は捨て、配列でなければ 0 件（＝何も除かない）とする。"""
        if not isinstance(value, list):
            return cls()
        codes = {
            code
            for code in (item.strip() for item in value if isinstance(item, str))
            if code and len(code) <= MAX_VENDOR_CODE_LENGTH
        }
        return cls(tuple(sorted(codes)))

    @property
    def is_empty(self) -> bool:
        return not self.codes

    def contains(self, vend_cd: object) -> bool:
        return _strip(vend_cd) in self.codes

    def added_since(self, other: "DirectShipmentSuppliers") -> tuple[str, ...]:
        """`other` になく自分にあるコード（仕入先マスタで実在を確かめる対象）。"""
        return tuple(code for code in self.codes if code not in other.codes)


#: 初期値: 丸栄豊田・テクノス工場（暫定）・丸栄豊田（福岡）（V-240）
DEFAULT_DIRECT_SHIPMENT_SUPPLIERS = DirectShipmentSuppliers(("9100", "9200", "9250"))


@dataclass(frozen=True)
class VendorName:
    """設定画面に出す仕入先名の解決結果。"""

    code: str
    name: str
    status: VendorNameStatus

    def to_payload(self) -> dict[str, str]:
        return {"code": self.code, "name": self.name, "status": self.status}


def is_direct_shipment(unit_rows: list[dict[str, object]], suppliers: DirectShipmentSuppliers) -> bool:
    """照合単位 1 つ分の行が直送品（T-212）か。

    すべての行の仕入先が直送仕入先で、すべての行の SLIMS 在庫数が空のときだけ真。数量 0 は空でない。
    """
    if suppliers.is_empty or not unit_rows:
        return False
    for row in unit_rows:
        if not suppliers.contains(row.get("level1_vend_cd")):
            return False  # 仕入先が空・直送仕入先でない（混在を含む）
        if row.get("stock_qty") not in (None, ""):
            return False
    return True


@dataclass(frozen=True)
class DirectShipmentExclusion:
    kept_rows: list[dict[str, object]]
    excluded_row_count: int
    excluded_unit_count: int


def exclude_direct_shipment_items(
    rows: list[dict[str, object]],
    suppliers: DirectShipmentSuppliers,
) -> DirectShipmentExclusion:
    """直送品の照合単位を丸ごと除く。残る行は入力の並び順のまま（dict は複製しない）。"""
    if suppliers.is_empty:
        return DirectShipmentExclusion(list(rows), 0, 0)

    units = ReconciliationUnits.build(rows)
    excluded_item_cds: set[str] = set()
    excluded_unit_count = 0
    for unit in units:
        if is_direct_shipment(units.rows_of(unit, rows), suppliers):
            excluded_item_cds.update(unit.item_cds)
            excluded_unit_count += 1

    kept: list[dict[str, object]] = []
    excluded_row_count = 0
    for row in rows:
        item_cd = _strip(row.get("item_cd"))
        if item_cd:
            excluded = item_cd in excluded_item_cds
        else:
            # 得意先品番が空の行は照合単位に属さないため、その行だけで判定する
            excluded = is_direct_shipment([row], suppliers)
            excluded_unit_count += 1 if excluded else 0
        if excluded:
            excluded_row_count += 1
        else:
            kept.append(row)
    return DirectShipmentExclusion(kept, excluded_row_count, excluded_unit_count)

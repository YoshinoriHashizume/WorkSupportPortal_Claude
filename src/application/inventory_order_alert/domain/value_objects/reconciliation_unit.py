"""照合単位（T-208）: 得意先品番と (内作品番 × 仕入先) の組を節点とする二部グラフの連結成分（05 design §4.5）。

在庫（得意先品番）・出荷（得意先 × 得意先品番）・入荷（内作品番 × 仕入先）・内示受注（得意先 × 内作品番）の
粒度が異なるため、数量を突き合わせる最小の閉じた集合。04 で JS に実装した Union-Find と同じ辺の定義
（得意先品番 ―― (level1_item_cd, level1_vend_cd)）だが、組が空の行は連結しない（空キーで全部がつながらないように）。
"""

from __future__ import annotations

from collections.abc import Iterator
from dataclasses import dataclass


@dataclass(frozen=True)
class ReconciliationUnit:
    key: str
    item_cds: frozenset[str]
    level1_pairs: frozenset[tuple[str, str]]
    row_keys: tuple[tuple[str, str], ...]


def _item_node(item_cd: str) -> str:
    return f"I:{item_cd}"


def _pair_node(pair: tuple[str, str]) -> str:
    return f"P:{pair[0]}|{pair[1]}"


def _row_item_cd(row: dict[str, object]) -> str:
    return str(row.get("item_cd") or "").strip()


def _row_pair(row: dict[str, object]) -> tuple[str, str]:
    return (str(row.get("level1_item_cd") or "").strip(), str(row.get("level1_vend_cd") or "").strip())


class ReconciliationUnits:
    """照合単位のファーストクラスコレクション。"""

    def __init__(self, units: tuple[ReconciliationUnit, ...]) -> None:
        self._units = tuple(units)
        self._unit_by_item_cd: dict[str, ReconciliationUnit] = {}
        for unit in self._units:
            for item_cd in unit.item_cds:
                self._unit_by_item_cd[item_cd] = unit

    @classmethod
    def build(cls, rows: list[dict[str, object]]) -> "ReconciliationUnits":
        parent: dict[str, str] = {}

        def find(node: str) -> str:
            parent.setdefault(node, node)
            root = node
            while parent[root] != root:
                root = parent[root]
            while parent[node] != root:
                parent[node], node = root, parent[node]
            return root

        def union(a: str, b: str) -> None:
            root_a, root_b = find(a), find(b)
            if root_a != root_b:
                parent[root_a] = root_b

        for row in rows:
            item_cd = _row_item_cd(row)
            if not item_cd:
                continue
            pair = _row_pair(row)
            find(_item_node(item_cd))
            if pair[0] or pair[1]:
                union(_item_node(item_cd), _pair_node(pair))

        members: dict[str, dict[str, object]] = {}
        for row in rows:
            item_cd = _row_item_cd(row)
            if not item_cd:
                continue
            group = members.setdefault(find(_item_node(item_cd)), {"item_cds": set(), "pairs": set(), "row_keys": set()})
            group["item_cds"].add(item_cd)
            pair = _row_pair(row)
            if pair[0] or pair[1]:
                group["pairs"].add(pair)
            group["row_keys"].add((str(row.get("cust_code") or "").strip(), item_cd))

        units = tuple(
            ReconciliationUnit(
                key=min(group["item_cds"]),
                item_cds=frozenset(group["item_cds"]),
                level1_pairs=frozenset(group["pairs"]),
                row_keys=tuple(sorted(group["row_keys"])),
            )
            for group in members.values()
        )
        return cls(tuple(sorted(units, key=lambda unit: unit.key)))

    def unit_of(self, item_cd: str) -> ReconciliationUnit | None:
        return self._unit_by_item_cd.get(str(item_cd or "").strip())

    def rows_of(self, unit: ReconciliationUnit, rows: list[dict[str, object]]) -> list[dict[str, object]]:
        """単位に属する行（入力の並び順のまま）。"""
        return [row for row in rows if _row_item_cd(row) in unit.item_cds]

    def __iter__(self) -> Iterator[ReconciliationUnit]:
        return iter(self._units)

    def __len__(self) -> int:
        return len(self._units)

from __future__ import annotations

from dataclasses import dataclass

from application.inventory_order_alert.domain.value_objects.flow_quadrant import (
    QUADRANT_DISCONTINUATION_CANDIDATE,
    QUADRANT_DORMANT_STOCK,
    QUADRANT_LOW_FLOW_NO_INCOMING,
    QUADRANT_LOW_FLOW_NO_SHIPMENT,
    QUADRANT_NORMAL_FLOW,
    QUADRANT_STOCKOUT,
    QUADRANT_STOCKOUT_NO_INCOMING,
    normalize_flow_quadrant,
)
from application.inventory_order_alert.domain.value_objects.stockout_risk import (
    RISK_CAUTION,
    RISK_DANGER,
    RISK_NONE,
    RISK_WATCH,
    row_stockout_risk,
)
from application.inventory_order_alert.domain.value_objects.row_display import (
    CONFIRMATION_CONFIRMED,
    CONFIRMATION_IN_PROGRESS,
)


@dataclass(frozen=True)
class RowCounts:
    """件数サマリ（02 design.md §6.6.3、05 で新区分名に追随、07 で 7 区分に拡張）。

    流動区分 7 値は排他かつ網羅であるため、7 件数の和は常に `total` に一致する。
    確認状態の3件数とも一致するので、画面左右の合計が揃う。
    """

    total: int = 0
    #: 07 で追加した在庫なしの 3 区分（S-203 ランク 0・1・5）
    stockout_no_incoming: int = 0
    stockout: int = 0
    discontinuation_candidate: int = 0
    low_flow_no_incoming: int = 0
    dormant_stock: int = 0
    low_flow_no_shipment: int = 0
    normal_flow: int = 0
    unconfirmed: int = 0
    in_progress: int = 0
    confirmed: int = 0
    #: 在庫切れリスク（S-204）の件数（06 design §6.4）。旧行は監視
    danger: int = 0
    caution: int = 0
    watch: int = 0
    none_risk: int = 0

    @property
    def by_stockout_risk(self) -> dict[str, int]:
        return {RISK_DANGER: self.danger, RISK_CAUTION: self.caution, RISK_WATCH: self.watch, RISK_NONE: self.none_risk}

    @property
    def attention(self) -> int:
        """通常流動品を除く、対応が要る区分の合計（07 design §2.7）。

        推奨アクション（T-207）が空なのも、一覧の「要対応のみ」が除くのも通常流動品だけなので、
        件数と絞り込みの意味を揃える。
        """
        return self.total - self.normal_flow

    @property
    def by_quadrant(self) -> dict[str, int]:
        """流動区分ラベル → 件数（ランク順）。TC-SFV-D-057、TC-FQR-C-001。"""
        return {
            QUADRANT_STOCKOUT_NO_INCOMING: self.stockout_no_incoming,
            QUADRANT_STOCKOUT: self.stockout,
            QUADRANT_LOW_FLOW_NO_INCOMING: self.low_flow_no_incoming,
            QUADRANT_DORMANT_STOCK: self.dormant_stock,
            QUADRANT_LOW_FLOW_NO_SHIPMENT: self.low_flow_no_shipment,
            QUADRANT_DISCONTINUATION_CANDIDATE: self.discontinuation_candidate,
            QUADRANT_NORMAL_FLOW: self.normal_flow,
        }


def _row_flow_quadrant(row: dict[str, object]) -> str:
    return normalize_flow_quadrant(str(row.get("flow_quadrant") or ""))


def _count_status(rows: list[dict[str, object]], status: str) -> int:
    return sum(1 for row in rows if str(row.get("confirmation_status") or "") == status)


def count_rows(rows: list[dict[str, object]]) -> RowCounts:
    quadrants = [_row_flow_quadrant(row) for row in rows]
    risks = [row_stockout_risk(row) for row in rows]
    return RowCounts(
        total=len(rows),
        stockout_no_incoming=quadrants.count(QUADRANT_STOCKOUT_NO_INCOMING),
        stockout=quadrants.count(QUADRANT_STOCKOUT),
        discontinuation_candidate=quadrants.count(QUADRANT_DISCONTINUATION_CANDIDATE),
        low_flow_no_incoming=quadrants.count(QUADRANT_LOW_FLOW_NO_INCOMING),
        dormant_stock=quadrants.count(QUADRANT_DORMANT_STOCK),
        low_flow_no_shipment=quadrants.count(QUADRANT_LOW_FLOW_NO_SHIPMENT),
        normal_flow=quadrants.count(QUADRANT_NORMAL_FLOW),
        unconfirmed=_count_status(rows, "未確認"),
        in_progress=_count_status(rows, CONFIRMATION_IN_PROGRESS),
        confirmed=_count_status(rows, CONFIRMATION_CONFIRMED),
        danger=risks.count(RISK_DANGER),
        caution=risks.count(RISK_CAUTION),
        watch=risks.count(RISK_WATCH),
        none_risk=risks.count(RISK_NONE),
    )

"""出荷推移のエッジケース・性能テスト（test-design.md §4.3 の TC-SHC-E-001〜002）。"""

from __future__ import annotations

import json

from application.inventory_order_alert.domain.value_objects.confirmation import STATUS_CHOICES
from application.inventory_order_alert.domain.value_objects.flow_quadrant import QUADRANT_SUPPLY_RISK
from application.inventory_order_alert.domain.value_objects.list_client_data import build_list_client_payload
from application.inventory_order_alert.domain.value_objects.list_filter import build_filter_options
from application.inventory_order_alert.domain.value_objects.shipment_trend import build_monthly_shipment_trend

from datetime import date

#: 各テストで使う代表 1 行。他ファイルから import しない（テスト間の暗黙結合を作らないため）。
BASE_ROW: dict[str, object] = {
    "cust_code": "112",
    "cust_name": "テスト得意先",
    "cust_chrg_psn_cd": "A01",
    "item_cd": "90249-10112",
    "level1_item_cd": "90249-10112-9209",
    "level1_vend_cd": "9209",
    "level1_vend_name": "小野メッキ",
    "last_incoming_date": "2022/01/31",
    "last_ship_date": "2025/11/27",
    "post_shipment_count": 2,
    "post_shipment_total_qty": 250,
    "stock_qty": 100,
    "mari_stock_qty": 95,
    "stock_location_detail": "2D0-03-5=100",
    "stock_as_of_label": "2026年6月17日時点の在庫",
    "flow_quadrant": QUADRANT_SUPPLY_RISK,
    "flow_quadrant_key": "supply-risk",
    "flow_quadrants": {key: "supply-risk" for key in ("L1", "L3", "L6", "D1", "D2", "D5")},
    "no_incoming_record": False,
    "responsible_department": "調達G・営業G・生産管理",
    "confirmation_status": "未確認",
}


def _row(**overrides: object) -> dict[str, object]:
    return BASE_ROW | overrides


def _payload_bytes(rows: list[dict[str, object]]) -> int:
    payload = build_list_client_payload(
        all_rows=rows,
        filter_options=build_filter_options(rows),
        confirmation_status_choices=list(STATUS_CHOICES),
    )
    return len(json.dumps(payload, ensure_ascii=False).encode("utf-8"))


def test_TC_SHC_E_001_payload_increase_per_row_is_measured() -> None:
    """1行あたりの配信ペイロード増分を実測する（design.md §6.2 の見積り約500バイトと比較。REQ-SHC-NF-001）。"""
    trend = build_monthly_shipment_trend(
        [(date(2026, m, 1), 10 * m) for m in range(1, 7)],
        as_of_date=date(2026, 6, 17),
    )
    without_trend = _row()
    with_trend = _row(shipment_trend=trend)

    increase = _payload_bytes([with_trend]) - _payload_bytes([without_trend])

    # 上限は要件定義書に明示値がないため、design.md の見積り(約500バイト)に対する余裕を確認するのみ。
    # 乖離が大きい場合は DECISIONS.md に記録し、翌営業日に許容値を確定する。
    assert 0 < increase < 1200, f"1 行あたりの増分: {increase} バイト（見積り約500バイト）"


def test_TC_SHC_E_002_builds_payload_for_five_thousand_rows_with_trend() -> None:
    trend = build_monthly_shipment_trend([], as_of_date=date(2026, 6, 17))
    rows = [
        _row(cust_code=f"{index:05d}", item_cd=f"ITEM-{index:05d}", shipment_trend=trend)
        for index in range(5000)
    ]

    payload = build_list_client_payload(
        all_rows=rows,
        filter_options=build_filter_options(rows),
        confirmation_status_choices=list(STATUS_CHOICES),
    )

    assert len(payload["rows"]) == 5000
    assert len(payload["rows"][-1]["shipment_trend"]) == 24


def test_TC_SHC_E_001_payload_increase_per_row_with_both_trends_is_measured() -> None:
    """入荷推移(V-217)追加後の1行あたり増分を実測する（design.md §6.2、出荷推移+794バイト実測を踏まえた再計測）。"""
    shipment_trend = build_monthly_shipment_trend(
        [(date(2026, m, 1), 10 * m) for m in range(1, 7)],
        as_of_date=date(2026, 6, 17),
    )
    incoming_trend = build_monthly_shipment_trend(
        [(date(2026, m, 1), 5 * m) for m in range(1, 7)],
        as_of_date=date(2026, 6, 17),
    )
    without_trend = _row()
    with_both_trends = _row(shipment_trend=shipment_trend, incoming_trend=incoming_trend)

    increase = _payload_bytes([with_both_trends]) - _payload_bytes([without_trend])

    # 出荷推移単独の実測+794バイトに対し、同形の入荷推移を足すとおよそ倍(+1600バイト前後)になる想定。
    # 上限は要件定義書に明示値がないため、実測して DECISIONS.md に記録する運用とする。
    assert 0 < increase < 2200, f"1 行あたりの増分(出荷+入荷): {increase} バイト"


def test_TC_SHC_E_002_builds_payload_for_five_thousand_rows_with_both_trends() -> None:
    trend = build_monthly_shipment_trend([], as_of_date=date(2026, 6, 17))
    rows = [
        _row(
            cust_code=f"{index:05d}",
            item_cd=f"ITEM-{index:05d}",
            shipment_trend=trend,
            incoming_trend=trend,
        )
        for index in range(5000)
    ]

    payload = build_list_client_payload(
        all_rows=rows,
        filter_options=build_filter_options(rows),
        confirmation_status_choices=list(STATUS_CHOICES),
    )

    assert len(payload["rows"]) == 5000
    assert len(payload["rows"][-1]["shipment_trend"]) == 24
    assert len(payload["rows"][-1]["incoming_trend"]) == 24

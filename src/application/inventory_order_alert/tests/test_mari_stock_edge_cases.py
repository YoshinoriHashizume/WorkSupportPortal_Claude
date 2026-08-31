"""MARI 在庫併記のエッジケース・性能テスト（test-design.md §4.3 の TC-MSV-E-001〜005）。"""

from __future__ import annotations

import json

import pytest

from application.inventory_order_alert.domain.value_objects.confirmation import STATUS_CHOICES
from application.inventory_order_alert.domain.value_objects.export_csv import render_export_csv
from application.inventory_order_alert.domain.value_objects.flow_quadrant import QUADRANT_SUPPLY_RISK
from application.inventory_order_alert.domain.value_objects.list_client_data import (
    build_list_client_payload,
    row_to_client_dict,
)
from application.inventory_order_alert.domain.value_objects.list_filter import build_filter_options
from application.inventory_order_alert.domain.value_objects.stock_quantity import STOCK_NOT_FETCHED

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


def test_TC_MSV_E_001_payload_increase_per_row_is_within_budget() -> None:
    """1 行あたりの配信ペイロード増分が 50 バイト以内であること（REQ-MSV-NF-001）。"""
    without_mari = _row()
    with_mari = _row(mari_stock_qty=95)

    increase = _payload_bytes([with_mari]) - _payload_bytes([without_mari])

    assert increase <= 50, f"1 行あたりの増分が予算を超えた: {increase} バイト"


def test_TC_MSV_E_001_responsible_department_no_longer_shipped_in_display() -> None:
    """責任部署を一覧列から外した分の減分（純増の内訳）。"""
    client_row = row_to_client_dict(_row(mari_stock_qty=95))

    assert "responsible_department" not in client_row["display"]
    # 詳細ダイアログ・CSV では引き続き使うため、行そのものからは消さない。
    assert client_row["responsibleDepartment"] == "調達G・営業G・生産管理"


def test_TC_MSV_E_002_builds_payload_for_five_thousand_rows() -> None:
    rows = [
        _row(cust_code=f"{index:05d}", item_cd=f"ITEM-{index:05d}", mari_stock_qty=index)
        for index in range(5000)
    ]

    payload = build_list_client_payload(
        all_rows=rows,
        filter_options=build_filter_options(rows),
        confirmation_status_choices=list(STATUS_CHOICES),
    )

    assert len(payload["rows"]) == 5000
    assert payload["rows"][-1]["mari_stock_qty"] == 4999


def test_TC_MSV_E_004_common_parts_share_the_same_mari_stock_quantity() -> None:
    """共通品は按分せず同じ在庫数を各行に出す（REQ-MSV-F-011）。"""
    rows = [
        _row(cust_code="112", item_cd="ITEM-A", mari_stock_qty=42),
        _row(cust_code="201", item_cd="ITEM-B", mari_stock_qty=42),
    ]

    payload = build_list_client_payload(
        all_rows=rows,
        filter_options=build_filter_options(rows),
        confirmation_status_choices=list(STATUS_CHOICES),
    )

    assert [row["mari_stock_qty"] for row in payload["rows"]] == [42, 42]
    # 一覧の在庫数を単純合計しても総在庫にはならない（重複計上を許容する）。
    assert sum(row["mari_stock_qty"] for row in payload["rows"]) != 42


@pytest.mark.parametrize(
    ("overrides", "expected_display"),
    [
        pytest.param({"mari_stock_qty": 95}, "95", id="値あり"),
        pytest.param({"mari_stock_qty": 0}, "0", id="在庫ゼロ"),
        pytest.param({"mari_stock_qty": ""}, "", id="該当なし"),
    ],
)
def test_TC_MSV_E_005_screen_shows_three_states(
    overrides: dict[str, object], expected_display: str
) -> None:
    client_row = row_to_client_dict(_row(**overrides))

    assert client_row["display"]["mari_stock_qty"] == expected_display


def test_TC_MSV_E_005_screen_shows_marker_when_not_fetched() -> None:
    client_row = row_to_client_dict(_row())

    assert client_row["display"]["mari_stock_qty"] == STOCK_NOT_FETCHED


@pytest.mark.parametrize(
    ("overrides", "expected_cell"),
    [
        pytest.param({"mari_stock_qty": 95}, "95", id="値あり"),
        pytest.param({"mari_stock_qty": 0}, "0", id="在庫ゼロ"),
        pytest.param({"mari_stock_qty": ""}, "", id="該当なし"),
        pytest.param({}, "", id="未取得（CSV では空）"),
    ],
)
def test_TC_MSV_E_005_csv_shows_three_states(
    overrides: dict[str, object], expected_cell: str
) -> None:
    payload = render_export_csv([_row(**overrides)]).decode("utf-8-sig")
    header, data = payload.strip().splitlines()[:2]
    index = header.split(",").index("在庫数(MARI)")

    assert data.split(",")[index] == expected_cell

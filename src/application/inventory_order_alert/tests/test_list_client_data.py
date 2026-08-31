from __future__ import annotations

from application.inventory_order_alert.domain.value_objects.confirmation import STATUS_CHOICES
from application.inventory_order_alert.domain.value_objects.flow_quadrant import (
    EVALUATION_PERIODS,
    FLOW_AXIS_DORMANT,
    FLOW_AXIS_LOW_FLOW,
    QUADRANT_SUPPLY_RISK,
)
from application.inventory_order_alert.domain.value_objects.list_client_data import (
    build_list_client_payload,
    build_row_key,
    row_to_client_dict,
)
from application.inventory_order_alert.domain.value_objects.list_filter import build_filter_options
from application.inventory_order_alert.domain.value_objects.stock_quantity import STOCK_NOT_FETCHED

PERIOD_KEYS = {period.key for period in EVALUATION_PERIODS}
LEGACY_PAYLOAD_KEYS = ("alertLevel", "alertOnly")


def _row(**kwargs: object) -> dict[str, object]:
    base: dict[str, object] = {
        "cust_code": "112",
        "cust_name": "テスト得意先",
        "cust_chrg_psn_cd": "A01",
        "item_cd": "90249-10112",
        "level1_item_cd": "90249-10112-9209",
        "level1_vend_cd": "9209",
        "level1_vend_name": "小野メッキ",
        "last_incoming_date": "",
        "last_ship_date": "2026/06/15",
        "post_shipment_count": 1,
        "post_shipment_total_qty": 250,
        "stock_qty": "100",
        "flow_quadrant": QUADRANT_SUPPLY_RISK,
        "flow_quadrant_key": "supply-risk",
        "flow_quadrants": {
            "L1": "supply-risk",
            "L3": "supply-risk",
            "L6": "supply-risk",
            "D1": "supply-risk",
            "D2": "supply-risk",
            "D5": "supply-risk",
        },
        "no_incoming_record": True,
        "responsible_department": "調達G・営業G・生産管理",
        "confirmation_status": "未確認",
    }
    base.update(kwargs)
    return base


def _payload(rows: list[dict[str, object]]) -> dict[str, object]:
    return build_list_client_payload(
        all_rows=rows,
        filter_options=build_filter_options(rows),
        confirmation_status_choices=list(STATUS_CHOICES),
    )


def test_build_list_client_payload_includes_flow_axes_and_periods():
    payload = _payload([_row()])

    assert [axis["value"] for axis in payload["flowAxes"]] == [FLOW_AXIS_LOW_FLOW, FLOW_AXIS_DORMANT]
    assert [period["key"] for period in payload["flowPeriods"][FLOW_AXIS_LOW_FLOW]] == ["L1", "L3", "L6"]
    assert [period["key"] for period in payload["flowPeriods"][FLOW_AXIS_DORMANT]] == ["D1", "D2", "D5"]


def test_build_list_client_payload_includes_flow_quadrant_labels_and_order():
    payload = _payload([_row()])

    assert len(payload["flowQuadrantLabels"]) == 4
    assert payload["flowQuadrantOrder"] == [
        "supply-risk",
        "dormant-stock",
        "excess-stock-risk",
        "normal-flow",
    ]


def test_build_list_client_payload_includes_default_flow_selection():
    payload = _payload([_row()])

    assert payload["defaultFlowSelection"] == {"axis": FLOW_AXIS_LOW_FLOW, "period": 3}


def test_build_list_client_payload_row_includes_six_flow_quadrants():
    payload = _payload([_row()])

    assert set(payload["rows"][0]["flowQuadrants"]) == PERIOD_KEYS


def test_build_list_client_payload_row_includes_no_incoming_record_flag():
    payload = _payload([_row(last_incoming_date="", no_incoming_record=True)])

    assert payload["rows"][0]["noIncomingRecord"] is True


def test_build_list_client_payload_row_includes_responsible_department():
    payload = _payload([_row()])

    assert payload["rows"][0]["responsibleDepartment"] == "調達G・営業G・生産管理"


def test_payload_row_includes_mari_stock_quantity():
    payload = _payload([_row(mari_stock_qty=95)])

    assert payload["rows"][0]["mariStockQty"] == 95


def test_payload_display_includes_both_stock_columns():
    payload = _payload([_row(stock_qty="100", mari_stock_qty=95)])

    display = payload["rows"][0]["display"]
    assert display["stock_qty"] == "100"
    assert display["mari_stock_qty"] == "95"


def test_payload_display_shows_marker_for_not_fetched_mari_stock():
    row = _row()
    row.pop("mari_stock_qty", None)

    payload = _payload([row])

    # 未取得（キーなし）は「－」。該当なし（空）と区別する
    assert payload["rows"][0]["display"]["mari_stock_qty"] == STOCK_NOT_FETCHED
    assert "mariStockQty" not in payload["rows"][0]


def test_payload_display_shows_empty_for_missing_mari_stock():
    payload = _payload([_row(mari_stock_qty="")])

    assert payload["rows"][0]["display"]["mari_stock_qty"] == ""


def test_payload_display_has_no_responsible_department():
    payload = _payload([_row()])

    # 責任部署は詳細ダイアログへ移した
    assert "responsible_department" not in payload["rows"][0]["display"]


def test_build_list_client_payload_has_no_alert_level_keys():
    payload = _payload([_row()])

    for key in LEGACY_PAYLOAD_KEYS:
        assert key not in payload
        assert key not in payload["rows"][0]


def test_TC_IOA_DOM_07G_row_to_client_dict_includes_display_and_keys():
    row = _row()
    client_row = row_to_client_dict(row)
    assert client_row["cust_code"] == "112"
    assert client_row["item_cd"] == "90249-10112"
    assert client_row["alertRowClass"] == "supply-risk"
    assert client_row["confirmationStatusKey"] == "unconfirmed"
    assert client_row["display"]["stock_qty"] == "100"
    assert client_row["display"]["flow_quadrant"] == QUADRANT_SUPPLY_RISK


def test_row_to_client_dict_normalizes_row_identity_keys():
    client_row = row_to_client_dict({"item_cd": 90249, "cust_code": None})
    assert client_row["cust_code"] == ""
    assert client_row["item_cd"] == "90249"
    assert client_row["rowKey"] == ""


def test_build_row_key_joins_cust_code_and_item_cd():
    assert build_row_key("112", "90249-10112") == "112|90249-10112"
    assert build_row_key("", "90249-10112") == ""
    assert build_row_key("112", "") == ""


def test_TC_IOA_DOM_07G_row_to_client_dict_includes_row_key():
    client_row = row_to_client_dict(_row())
    assert client_row["rowKey"] == "112|90249-10112"


def test_TC_IOA_DOM_07H_build_list_client_payload():
    rows = [_row(), _row(item_cd="ITEM-2", cust_code="201", cust_name="別得意先")]
    payload = _payload(rows)
    assert len(payload["rows"]) == 2
    assert payload["rows"][0]["item_cd"] == "90249-10112"
    assert payload["defaultPageSize"] == 50
    assert payload["defaultSortSpecs"] == [{"column": "flow_quadrant", "direction": "asc"}]
    assert len(payload["sortableColumns"]) >= 10
    assert payload["filterOptions"]["custOptions"][0]["value"] == "112"
    assert payload["itemCdOptions"] == ["90249-10112", "ITEM-2"]
    assert payload["level1ItemCdOptions"] == ["90249-10112-9209"]
    assert payload["confirmationStatusChoices"][0]["value"] == "unconfirmed"

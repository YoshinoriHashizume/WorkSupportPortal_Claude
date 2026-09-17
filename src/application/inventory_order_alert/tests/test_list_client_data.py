from __future__ import annotations

from application.inventory_order_alert.domain.value_objects.confirmation import STATUS_CHOICES
"""クライアント配信ペイロードのテスト（TC-SFV-D-054〜056）。"""

from application.inventory_order_alert.domain.value_objects.flow_quadrant import (
    EVALUATION_PERIODS,
    FLOW_QUADRANT_KEYS,
    FLOW_QUADRANTS,
    QUADRANT_LOW_FLOW_NO_INCOMING,
)
from application.inventory_order_alert.domain.value_objects.list_client_data import (
    build_list_client_payload,
    build_row_key,
    row_to_client_dict,
)
from application.inventory_order_alert.domain.value_objects.list_filter import build_filter_options
from application.inventory_order_alert.domain.value_objects.recommended_action import (
    DEFAULT_RECOMMENDED_ACTIONS,
)
from application.inventory_order_alert.domain.value_objects.stock_quantity import STOCK_NOT_FETCHED

PERIOD_KEYS = {period.key for period in EVALUATION_PERIODS}
LEGACY_PAYLOAD_KEYS = ("alertLevel", "alertOnly", "flowAxes", "flowPeriods", "defaultFlowSelection")


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
        "flow_quadrant": QUADRANT_LOW_FLOW_NO_INCOMING,
        "flow_quadrant_key": "low-flow-no-incoming",
        "flow_quadrants": {
            "Y1": "low-flow-no-incoming",
            "Y3": "low-flow-no-incoming",
            "Y5": "low-flow-no-incoming",
        },
        "no_incoming_record": True,
        "flow_status": "出荷は継続、最終入荷 入荷実績なし（1年以上入荷なし）",
        "recommended_action": "仕入先へ生産継続可否・設備/金型の有無を確認。在庫切れ予測月が近いものから",
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


def test_d054_payload_includes_evaluation_periods_and_default_key():
    payload = _payload([_row()])

    assert payload["evaluationPeriods"] == [
        {"years": 1, "key": "Y1", "label": "1年"},
        {"years": 3, "key": "Y3", "label": "3年"},
        {"years": 5, "key": "Y5", "label": "5年"},
    ]
    assert payload["defaultPeriodKey"] == "Y1"
    assert "flowAxes" not in payload
    assert "flowPeriods" not in payload


def test_d055_payload_includes_recommended_actions_for_four_quadrants():
    payload = _payload([_row()])

    actions = payload["recommendedActions"]
    assert set(actions) == set(FLOW_QUADRANT_KEYS.values())
    for quadrant in FLOW_QUADRANTS:
        expected = DEFAULT_RECOMMENDED_ACTIONS.for_quadrant(quadrant)
        entry = actions[FLOW_QUADRANT_KEYS[quadrant]]
        assert entry["statusTemplate"] == expected.status_template
        assert entry["action"] == expected.action
        assert entry["departments"] == "・".join(expected.departments)


def test_d055_payload_uses_injected_recommended_actions():
    overridden = DEFAULT_RECOMMENDED_ACTIONS.with_action_texts({"low-flow-no-incoming": "上書き文言"})

    payload = build_list_client_payload(
        all_rows=[_row()],
        filter_options=build_filter_options([_row()]),
        confirmation_status_choices=list(STATUS_CHOICES),
        recommended_actions=overridden,
    )

    assert payload["recommendedActions"]["low-flow-no-incoming"]["action"] == "上書き文言"
    assert payload["recommendedActions"]["dormant-stock"]["action"] == DEFAULT_RECOMMENDED_ACTIONS.for_quadrant("在庫死蔵品").action


def test_d056_payload_row_flow_quadrants_use_year_keys():
    payload = _payload([_row()])

    assert set(payload["rows"][0]["flowQuadrants"]) == {"Y1", "Y3", "Y5"}


def test_payload_row_includes_flow_status_and_recommended_action():
    payload = _payload([_row()])

    row = payload["rows"][0]
    assert row["flowStatus"] == "出荷は継続、最終入荷 入荷実績なし（1年以上入荷なし）"
    assert row["recommendedAction"].startswith("仕入先へ")


def test_payload_has_no_legacy_quadrant_names():
    import json

    text = json.dumps(_payload([_row()]), ensure_ascii=False)
    for legacy in ("供給リスク品", "在庫過剰リスク品", "supply-risk", "excess-stock-risk", "判定軸"):
        assert legacy not in text


def test_build_list_client_payload_includes_flow_quadrant_labels_and_order():
    payload = _payload([_row()])

    assert len(payload["flowQuadrantLabels"]) == 4
    assert payload["flowQuadrantOrder"] == [
        "low-flow-no-incoming",
        "dormant-stock",
        "low-flow-no-shipment",
        "normal-flow",
    ]
    assert payload["flowQuadrantLabels"]["low-flow-no-incoming"] == "低流動品（入荷なし）"
    assert payload["flowQuadrantLabels"]["low-flow-no-shipment"] == "低流動品（出荷なし）"


def test_build_list_client_payload_row_flow_quadrants_cover_all_evaluation_periods():
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

    # ソートは行の生値を引く。camelCase の別名は配信しない（同じ値の二重配信になるため）。
    assert payload["rows"][0]["mari_stock_qty"] == 95
    assert "mariStockQty" not in payload["rows"][0]


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
    assert client_row["alertRowClass"] == "low-flow-no-incoming"
    assert client_row["confirmationStatusKey"] == "unconfirmed"
    assert client_row["display"]["stock_qty"] == "100"
    assert client_row["display"]["flow_quadrant"] == QUADRANT_LOW_FLOW_NO_INCOMING


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


# --- 05_single-flow-view 第 2 段階: ペイロードの需要予測キー ---


def _stage2_row(**kwargs: object) -> dict[str, object]:
    return _row(
        internal_item_cd="96160-00500-9065",
        unconfirmed_order_trend=[
            {"month": "2026-09", "qty": 0},
            {"month": "2026-10", "qty": 224},
            {"month": "2026-11", "qty": 216},
            {"month": "2026-12", "qty": 197},
        ],
        reconciliation_unit_key="10523-X0A02",
        demand_forecast_basis="内示",
        demand_forecast_current_month_remaining=0,
        demand_forecast_monthly=[224, 216, 197],
        demand_forecast_monthly_average=212.3333,
        demand_forecast_stock_total=31970.0,
        months_of_stock=150.6,
        stockout_forecast_month=None,
        **kwargs,
    )


def test_stage2_payload_row_includes_demand_forecast_keys():
    payload = _payload([_stage2_row()])

    row = payload["rows"][0]
    assert row["internalItemCd"] == "96160-00500-9065"
    assert [point["qty"] for point in row["unconfirmedOrderTrend"]] == [0, 224, 216, 197]
    assert row["reconciliationUnitKey"] == "10523-X0A02"
    assert row["demandForecast"] == {
        "basis": "内示",
        "currentMonthRemaining": 0,
        "monthly": [224, 216, 197],
        "monthlyAverage": 212.3333,
        "stockTotal": 31970.0,
        "monthsOfStock": 150.6,
        "stockoutForecastMonth": None,
    }


def test_stage2_payload_row_without_forecast_keys_has_none_basis():
    payload = _payload([_row()])

    row = payload["rows"][0]
    assert row["internalItemCd"] == ""
    assert row["unconfirmedOrderTrend"] == []
    assert row["reconciliationUnitKey"] == ""
    assert row["demandForecast"]["basis"] == "なし"
    assert row["demandForecast"]["monthsOfStock"] is None
    assert row["demandForecast"]["stockTotal"] is None
    assert row["demandForecast"]["stockoutForecastMonth"] is None
    assert row["demandForecast"]["monthly"] == [0, 0, 0]


def test_stage2_payload_lists_sort_only_columns_separately():
    payload = _payload([_row()])

    assert payload["sortOnlyColumns"] == [{"key": "months_of_stock", "label": "在庫月数"}]
    assert "months_of_stock" not in [column["key"] for column in payload["sortableColumns"]]

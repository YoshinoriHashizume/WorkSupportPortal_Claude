from __future__ import annotations

from apps.inventory_order_alert.domain.confirmation import STATUS_CHOICES
from apps.inventory_order_alert.domain.list_client_data import build_list_client_payload, row_to_client_dict
from apps.inventory_order_alert.domain.list_filter import build_filter_options


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
        "alert_level": "重点",
        "confirmation_status": "未確認",
    }
    base.update(kwargs)
    return base


def test_TC_IOA_DOM_07G_row_to_client_dict_includes_display_and_keys():
    row = _row()
    client_row = row_to_client_dict(row)
    assert client_row["cust_code"] == "112"
    assert client_row["alertRowClass"] == "重点"
    assert client_row["confirmationStatusKey"] == "unconfirmed"
    assert client_row["display"]["stock_qty"] == "100"
    assert client_row["display"]["alert_level"] == "重点"


def test_TC_IOA_DOM_07H_build_list_client_payload():
    rows = [_row(), _row(item_cd="ITEM-2", cust_code="201", cust_name="別得意先")]
    options = build_filter_options(rows)
    payload = build_list_client_payload(
        all_rows=rows,
        filter_options=options,
        confirmation_status_choices=list(STATUS_CHOICES),
    )
    assert len(payload["rows"]) == 2
    assert payload["rows"][0]["item_cd"] == "90249-10112"
    assert payload["defaultPageSize"] == 50
    assert payload["defaultSortSpecs"] == [{"column": "alert_level", "direction": "asc"}]
    assert len(payload["sortableColumns"]) >= 10
    assert payload["filterOptions"]["custOptions"][0]["value"] == "112"
    assert payload["itemCdOptions"] == ["90249-10112", "ITEM-2"]
    assert payload["level1ItemCdOptions"] == ["90249-10112-9209"]
    assert payload["confirmationStatusChoices"][0]["value"] == "unconfirmed"

from __future__ import annotations

from datetime import date

import pytest

from application.inventory_order_alert.infrastructure.persistence.summary_snapshot_repository import store_summary_snapshot
from application.inventory_order_alert.interfaces.wiring import portal_dashboard_usecase
from application.inventory_order_alert.models import SlimsStockImport
from application.inventory_order_alert.use_cases.portal_dashboard import DashboardBannerContext

AS_OF = date(2026, 6, 17)
#: 帯は基準判定条件（低流動判定軸・3か月）で固定する（design.md §6.4）。
#: 基準日 2026/6/17 の3か月前は 2026/3/17。
SUPPLY_RISK_DATES = ("", "2026/06/15")
DORMANT_STOCK_DATES = ("2022/01/31", "2025/02/01")
EXCESS_STOCK_RISK_DATES = ("2026/05/01", "2024/01/01")
NORMAL_FLOW_DATES = ("2026/05/01", "2026/06/15")
REMOVED_BANNER_FIELDS = ("critical", "warning", "warning_ship", "warning_incoming")


def _row(dates: tuple[str, str], *, item_cd: str, confirmation_status: str = "未確認") -> dict[str, object]:
    last_incoming_date, last_ship_date = dates
    return {
        "cust_code": "100",
        "cust_name": "テスト得意先",
        "item_cd": item_cd,
        "level1_item_cd": item_cd,
        "level1_vend_cd": "9209",
        "level1_vend_name": "仕入先",
        "last_incoming_date": last_incoming_date,
        "last_ship_date": last_ship_date,
        "post_shipment_count": 1,
        "post_shipment_total_qty": 10,
        "stock_qty": "100",
        "stock_as_of_label": "2026年6月17日時点の在庫",
        "confirmation_status": confirmation_status,
    }


def _store(rows: list[dict[str, object]], *, aggregation_error: str = "") -> None:
    # row_count が 0 だと在庫未取込扱いになるため、集計エラーの検証でも 1 以上にする。
    import_record = SlimsStockImport.objects.create(file_name="sample.csv", row_count=max(len(rows), 1))
    store_summary_snapshot(
        import_record,
        rows,
        as_of_date=AS_OF,
        aggregation_error=aggregation_error,
    )


def _two_of_each_quadrant() -> list[dict[str, object]]:
    dates_by_quadrant = (
        SUPPLY_RISK_DATES,
        DORMANT_STOCK_DATES,
        EXCESS_STOCK_RISK_DATES,
        NORMAL_FLOW_DATES,
    )
    return [
        _row(dates, item_cd=f"ITEM-{index}-{copy}")
        for index, dates in enumerate(dates_by_quadrant)
        for copy in range(2)
    ]


@pytest.mark.django_db
def test_dashboard_banner_counts_each_flow_quadrant():
    _store(_two_of_each_quadrant())

    banner = portal_dashboard_usecase().execute()

    assert banner.supply_risk == 2
    assert banner.dormant_stock == 2
    assert banner.excess_stock_risk == 2
    assert banner.unconfirmed == 8


@pytest.mark.django_db
def test_dashboard_banner_attention_excludes_normal_flow():
    _store(_two_of_each_quadrant())

    banner = portal_dashboard_usecase().execute()

    assert banner.attention == 6


@pytest.mark.django_db
def test_dashboard_banner_tone_is_critical_when_supply_risk_exists():
    _store(
        [
            _row(SUPPLY_RISK_DATES, item_cd="ITEM-A"),
            _row(DORMANT_STOCK_DATES, item_cd="ITEM-B"),
        ]
    )

    banner = portal_dashboard_usecase().execute()

    assert banner.tone == "critical"
    assert not banner.error_message


@pytest.mark.django_db
@pytest.mark.parametrize("dates", [DORMANT_STOCK_DATES, EXCESS_STOCK_RISK_DATES])
def test_dashboard_banner_tone_is_warning_when_only_dormant_or_excess_exist(dates):
    _store([_row(dates, item_cd="ITEM-A")])

    banner = portal_dashboard_usecase().execute()

    assert banner.tone == "warning"


@pytest.mark.django_db
def test_dashboard_banner_tone_is_ok_when_only_normal_flow_exists():
    _store([_row(NORMAL_FLOW_DATES, item_cd="ITEM-A")])

    banner = portal_dashboard_usecase().execute()

    assert banner.tone == "ok"
    assert banner.has_alerts is False


@pytest.mark.django_db
def test_dashboard_banner_includes_confirmed_rows_in_quadrant_counts():
    _store(
        [
            _row(SUPPLY_RISK_DATES, item_cd="ITEM-A", confirmation_status="確認済み"),
            _row(SUPPLY_RISK_DATES, item_cd="ITEM-B"),
        ]
    )

    banner = portal_dashboard_usecase().execute()

    assert banner.supply_risk == 2
    assert banner.unconfirmed == 1


@pytest.mark.django_db
def test_dashboard_banner_always_uses_reference_flow_selection():
    # 死蔵5年で見れば通常流動品になる行でも、帯は低流動3か月で在庫死蔵品として数える。
    _store([_row(DORMANT_STOCK_DATES, item_cd="ITEM-A")])

    banner = portal_dashboard_usecase().execute()

    assert banner.dormant_stock == 1
    assert banner.flow_condition_label == "低流動判定軸・3か月"


@pytest.mark.django_db
def test_dashboard_banner_returns_zero_counts_without_stock_import():
    banner = portal_dashboard_usecase().execute()

    assert banner.supply_risk == 0
    assert banner.dormant_stock == 0
    assert banner.excess_stock_risk == 0
    assert banner.attention == 0
    assert not banner.has_stock_data


def test_dashboard_banner_has_no_critical_or_warning_fields():
    banner = DashboardBannerContext(
        supply_risk=0,
        dormant_stock=0,
        excess_stock_risk=0,
        unconfirmed=0,
        stock_as_of_label="",
        has_stock_data=False,
        stock_stale=False,
    )

    for field_name in REMOVED_BANNER_FIELDS:
        assert not hasattr(banner, field_name)


@pytest.mark.django_db
def test_dashboard_banner_tone_is_neutral_when_error_message_present():
    _store([], aggregation_error="Oracle 未設定")

    banner = portal_dashboard_usecase().execute()

    assert banner.error_message
    assert banner.has_stock_data is True
    assert banner.tone == "neutral"

from __future__ import annotations

from datetime import date
from unittest.mock import MagicMock, patch

import pytest

from application.inventory_order_alert.infrastructure.oracle.summary_aggregation import run_summary_aggregation
from application.inventory_order_alert.infrastructure.oracle.summary_queries import build_summary_rows
from application.inventory_order_alert.infrastructure.persistence.summary_snapshot_repository import (
    store_summary_snapshot,
)
from application.inventory_order_alert.models import (
    InventoryOrderAlertSummarySnapshot,
    SlimsStockImport,
)


@patch(
    "application.inventory_order_alert.infrastructure.oracle.summary_queries.fetch_last_incoming_by_item_vend",
    return_value={},
)
@patch(
    "application.inventory_order_alert.infrastructure.oracle.summary_queries.fetch_vendor_by_component",
    return_value={},
)
@patch(
    "application.inventory_order_alert.infrastructure.oracle.summary_queries.fetch_bom_level1_by_root",
    return_value={},
)
@patch(
    "application.inventory_order_alert.infrastructure.oracle.summary_queries.fetch_finished_roots",
    return_value={},
)
@patch(
    "application.inventory_order_alert.infrastructure.oracle.summary_queries.fetch_all_shipments",
    return_value=[],
)
@patch(
    "application.inventory_order_alert.infrastructure.oracle.summary_queries.fetch_internal_items_from_m_cust_item",
    return_value=({}, {}),
)
@patch(
    "application.inventory_order_alert.infrastructure.oracle.summary_queries.fetch_ship_customer_items",
    return_value=[],
)
@patch(
    "application.inventory_order_alert.infrastructure.oracle.summary_queries.fetch_customer_names",
    return_value={"137": "テスト得意先"},
)
def test_build_summary_rows_ignores_legacy_stock_item_cds(
    *_mocks: object,
) -> None:
    rows = build_summary_rows(
        MagicMock(),
        date(2026, 6, 29),
        stock_item_cds={"SLIMS-ONLY-ITEM"},
    )
    assert rows == []


@patch(
    "application.inventory_order_alert.infrastructure.oracle.summary_queries.fetch_last_incoming_by_item_vend",
    return_value={},
)
@patch(
    "application.inventory_order_alert.infrastructure.oracle.summary_queries.fetch_vendor_by_component",
    return_value={},
)
@patch(
    "application.inventory_order_alert.infrastructure.oracle.summary_queries.fetch_bom_level1_by_root",
    return_value={"96160-00500": []},
)
@patch(
    "application.inventory_order_alert.infrastructure.oracle.summary_queries.fetch_finished_roots",
    return_value={"96160-00500": {"96160-00500"}},
)
@patch(
    "application.inventory_order_alert.infrastructure.oracle.summary_queries.fetch_all_shipments",
    return_value=[("137", "10523-X0A02", date(2026, 6, 1), 10)],
)
@patch(
    "application.inventory_order_alert.infrastructure.oracle.summary_queries.fetch_internal_items_from_m_cust_item",
    return_value=({("137", "10523-X0A02"): "96160-00500"}, {"10523-X0A02": "96160-00500"}),
)
@patch(
    "application.inventory_order_alert.infrastructure.oracle.summary_queries.fetch_ship_customer_items",
    return_value=[("137", "10523-X0A02", "001", "96160-00500")],
)
@patch(
    "application.inventory_order_alert.infrastructure.oracle.summary_queries.fetch_customer_names",
    return_value={"137": "テスト得意先"},
)
def test_build_summary_rows_includes_shipped_cust_item_pairs(
    *_mocks: object,
) -> None:
    rows = build_summary_rows(MagicMock(), date(2026, 6, 29))
    assert len(rows) == 1
    assert rows[0]["cust_code"] == "137"
    assert rows[0]["item_cd"] == "10523-X0A02"


def _shipped_pair_patches(mari_stock_totals: dict[str, object] | None = None, **overrides):
    """出荷実績のある 1 行を組み立てるためのパッチ群。"""
    defaults = {
        "fetch_customer_names": {"137": "テスト得意先"},
        "fetch_ship_customer_items": [("137", "10523-X0A02", "001", "96160-00500")],
        "fetch_internal_items_from_m_cust_item": (
            {("137", "10523-X0A02"): "96160-00500"},
            {"10523-X0A02": "96160-00500"},
        ),
        "fetch_all_shipments": [("137", "10523-X0A02", date(2026, 6, 1), 10)],
        "fetch_finished_roots": {"96160-00500": {"96160-00500"}},
        "fetch_bom_level1_by_root": {"96160-00500": []},
        "fetch_vendor_by_component": {},
        "fetch_last_incoming_by_item_vend": {},
        "fetch_mari_stock_totals": mari_stock_totals if mari_stock_totals is not None else {},
        "fetch_incoming_receipts": [],
        "fetch_cust_item_phase_out_dates": {},
    }
    defaults.update(overrides)
    return [
        patch(
            f"application.inventory_order_alert.infrastructure.oracle.summary_queries.{name}",
            return_value=value,
        )
        for name, value in defaults.items()
    ]


def _build_rows_with(mari_stock_totals: dict[str, object] | None = None, **overrides):
    patches = _shipped_pair_patches(mari_stock_totals, **overrides)
    for p in patches:
        p.start()
    try:
        return build_summary_rows(MagicMock(), date(2026, 6, 29))
    finally:
        for p in patches:
            p.stop()


# --- TC-FQR-I-002: 適用終了日（07 design §4.1） ---


def test_fqr_build_summary_rows_attaches_phase_out_date() -> None:
    rows = _build_rows_with(
        {},
        fetch_cust_item_phase_out_dates={("137", "10523-X0A02"): date(2026, 3, 31)},
    )

    assert rows[0]["phase_out_date"] == "2026/03/31"


def test_fqr_build_summary_rows_leaves_phase_out_date_empty_when_absent() -> None:
    rows = _build_rows_with({}, fetch_cust_item_phase_out_dates={})

    assert rows[0]["phase_out_date"] == ""


def test_fqr_i002_phase_out_date_fetch_failure_only_warns() -> None:
    """適用終了日の取得失敗は取込を止めず、警告文を残して空扱いにする。"""
    from application.inventory_order_alert.infrastructure.oracle.summary_queries import (
        PHASE_OUT_DATE_FETCH_ERROR_PREFIX,
    )
    from application.sales.infrastructure.oracle.client import OracleQueryError

    warnings: list[str] = []
    patches = _shipped_pair_patches({})
    for p in patches:
        p.start()
    failing = patch(
        "application.inventory_order_alert.infrastructure.oracle.summary_queries.fetch_cust_item_phase_out_dates",
        side_effect=OracleQueryError("ORA-00942: 表またはビューが存在しません。"),
    )
    failing.start()
    try:
        rows = build_summary_rows(MagicMock(), date(2026, 6, 29), warnings=warnings)
    finally:
        failing.stop()
        for p in patches:
            p.stop()

    assert rows[0]["phase_out_date"] == ""
    assert any(warning.startswith(PHASE_OUT_DATE_FETCH_ERROR_PREFIX) for warning in warnings)


def test_build_summary_rows_attaches_mari_stock_qty() -> None:
    rows = _build_rows_with({"96160-00500": 42})

    assert rows[0]["mari_stock_qty"] == 42


def test_build_summary_rows_leaves_mari_stock_empty_when_not_found() -> None:
    rows = _build_rows_with({})

    # 該当在庫が無い場合は空。0 にしない
    assert rows[0]["mari_stock_qty"] == ""


def test_build_summary_rows_keeps_zero_mari_stock_qty() -> None:
    rows = _build_rows_with({"96160-00500": 0})

    # 在庫 0 は空にしない
    assert rows[0]["mari_stock_qty"] == 0


def test_build_summary_rows_leaves_mari_stock_empty_when_internal_item_unresolved() -> None:
    rows = _build_rows_with(
        {"96160-00500": 42},
        fetch_ship_customer_items=[("137", "10523-X0A02", "001", "")],
        fetch_internal_items_from_m_cust_item=({}, {}),
    )

    assert rows[0]["mari_stock_qty"] == ""
    # 他の列は従来どおり組み立てられる
    assert rows[0]["cust_code"] == "137"
    assert rows[0]["item_cd"] == "10523-X0A02"


def test_TC_SHC_I_004_build_summary_rows_attaches_shipment_trend() -> None:
    rows = _build_rows_with({})

    trend = rows[0]["shipment_trend"]
    assert len(trend) == 24
    june = next(point for point in trend if point["month"] == "2026-06")
    assert june["qty"] == 10


def test_TC_SHC_I_005_build_summary_rows_does_not_add_oracle_calls() -> None:
    """出荷推移の追加で fetch_all_shipments の呼び出し回数が増えないこと（REQ-SHC-NF-001）。"""
    patches = _shipped_pair_patches({})
    started = {p.attribute: p.start() for p in patches}
    try:
        build_summary_rows(MagicMock(), date(2026, 6, 29))
    finally:
        for p in patches:
            p.stop()

    assert started["fetch_all_shipments"].call_count == 1


def test_TC_SHC_I_011_build_summary_rows_calls_fetch_incoming_receipts_once() -> None:
    patches = _shipped_pair_patches({})
    started = {p.attribute: p.start() for p in patches}
    try:
        build_summary_rows(MagicMock(), date(2026, 6, 29))
    finally:
        for p in patches:
            p.stop()

    assert started["fetch_incoming_receipts"].call_count == 1


def test_TC_SHC_I_006_existing_shipment_stats_are_unchanged() -> None:
    """出荷推移の追加で既存の post_shipment_count 等が変わらないこと（非回帰）。"""
    rows = _build_rows_with({})

    assert rows[0]["post_shipment_count"] == 1
    assert rows[0]["post_shipment_total_qty"] == 10
    assert rows[0]["last_ship_date"] == "2026/06/01"


def test_TC_SHC_I_010_build_summary_rows_attaches_incoming_trend() -> None:
    """入荷推移(V-217)は level1_item_cd x level1_vend_cd で突合する(design.md §3.3)。"""
    rows = _build_rows_with(
        {},
        fetch_bom_level1_by_root={"96160-00500": ["L1-A"]},
        fetch_vendor_by_component={"L1-A": ("9209", "小野メッキ")},
        fetch_last_incoming_by_item_vend={("L1-A", "9209"): date(2026, 1, 15)},
        fetch_incoming_receipts=[("L1-A", "9209", date(2026, 6, 10), 30)],
    )

    assert rows[0]["level1_item_cd"] == "L1-A"
    trend = rows[0]["incoming_trend"]
    assert len(trend) == 24
    june = next(point for point in trend if point["month"] == "2026-06")
    assert june["qty"] == 30


def test_TC_SHC_I_010_incoming_trend_is_all_zero_when_level1_item_unresolved() -> None:
    # デフォルトフィクスチャは level1_item が解決できない（fetch_bom_level1_by_root が空）。
    rows = _build_rows_with({})

    trend = rows[0]["incoming_trend"]
    assert len(trend) == 24
    assert all(point["qty"] == 0 for point in trend)


def _failing_aggregation(import_record, message: str):
    with (
        patch(
            "application.inventory_order_alert.infrastructure.oracle.summary_aggregation.oracle_connection"
        ) as connection,
        patch(
            "application.inventory_order_alert.infrastructure.oracle.summary_aggregation.build_list_rows",
            side_effect=RuntimeError(message),
        ),
    ):
        connection.return_value.__enter__.return_value = MagicMock()
        return run_summary_aggregation(import_record, [])


@pytest.mark.django_db
def test_run_summary_aggregation_fails_whole_import_when_stock_query_raises() -> None:
    """MARI 在庫の取得に失敗したら取込全体を失敗させる（REQ-MSV-F-009）。"""
    import_record = SlimsStockImport.objects.create(file_name="sample.csv", row_count=1)

    aggregation_error, reset_count, warning = _failing_aggregation(
        import_record, "ORA-00942: table or view does not exist"
    )

    assert "ORA-00942" in aggregation_error
    assert reset_count == 0
    assert warning == ""

    snapshot = InventoryOrderAlertSummarySnapshot.objects.filter(import_record=import_record).latest("id")
    assert snapshot.aggregation_error
    # MARI 在庫だけ欠けた中途半端なスナップショットを作らない。
    assert snapshot.rows == []


@pytest.mark.django_db
def test_run_summary_aggregation_keeps_previous_snapshot_on_failure() -> None:
    """失敗しても直前のスナップショットは残る（REQ-MSV-F-009）。"""
    healthy_import = SlimsStockImport.objects.create(file_name="ok.csv", row_count=1)
    store_summary_snapshot(
        healthy_import,
        [{"cust_code": "112", "item_cd": "90249-10112", "mari_stock_qty": 95}],
        as_of_date=date(2026, 6, 17),
    )

    failing_import = SlimsStockImport.objects.create(file_name="ng.csv", row_count=1)
    _failing_aggregation(failing_import, "MARI 在庫の取得に失敗")

    healthy = InventoryOrderAlertSummarySnapshot.objects.filter(import_record=healthy_import).latest("id")
    assert healthy.rows[0]["mari_stock_qty"] == 95
    assert healthy.aggregation_error == ""


# --- 05_single-flow-view 第 2 段階: TC-SFV-I-003〜005 ---


def _stage2_overrides(**extra):
    base = {
        "fetch_bom_level1_by_root": {"96160-00500": ["96160-00500-9065"]},
        "fetch_vendor_by_component": {"96160-00500-9065": ("9065", "ミズタニ")},
        "fetch_last_incoming_by_item_vend": {("96160-00500-9065", "9065"): date(2025, 4, 2)},
    }
    base.update(extra)
    return base


def test_i003_build_summary_rows_calls_fetch_unconfirmed_orders_once() -> None:
    patches = _shipped_pair_patches({}, fetch_unconfirmed_orders_or_warn=([], ""))
    started = {p.attribute: p.start() for p in patches}
    try:
        build_summary_rows(MagicMock(), date(2026, 6, 29))
    finally:
        for p in patches:
            p.stop()

    assert started["fetch_unconfirmed_orders_or_warn"].call_count == 1
    kwargs = started["fetch_unconfirmed_orders_or_warn"].call_args.kwargs
    assert kwargs["as_of_date"] == date(2026, 6, 29)


def test_i004_build_summary_rows_attaches_internal_item_cd_and_unconfirmed_order_trend() -> None:
    rows = _build_rows_with(
        {},
        fetch_unconfirmed_orders_or_warn=(
            [
                ("137", "96160-00500", date(2026, 7, 5), 30),
                ("137", "96160-00500", date(2026, 8, 1), 28),
                ("137", "96160-00500", date(2026, 6, 10), 999),  # 基準日 6/29 より前 → 当月残に含めない
                ("104", "96160-00500", date(2026, 7, 5), 194),  # 別の得意先 → この行には付かない
            ],
            "",
        ),
    )

    assert rows[0]["cust_code"] == "137"
    assert rows[0]["internal_item_cd"] == "96160-00500"
    trend = rows[0]["unconfirmed_order_trend"]
    assert [point["month"] for point in trend] == ["2026-06", "2026-07", "2026-08", "2026-09"]
    assert [point["qty"] for point in trend] == [0, 30, 28, 0]


def test_i004_unresolved_internal_item_falls_back_to_cust_item_cd_and_zero_trend() -> None:
    """内作品番が解決できない行は既存規則どおり得意先品番で代替する（`resolve_internal_item_cd`）。内示は突合しないため全 0。"""
    rows = _build_rows_with(
        {},
        fetch_ship_customer_items=[("137", "10523-X0A02", "001", "")],
        fetch_internal_items_from_m_cust_item=({}, {}),
        fetch_unconfirmed_orders_or_warn=([("137", "96160-00500", date(2026, 7, 5), 30)], ""),
    )

    assert rows[0]["internal_item_cd"] == "10523-X0A02"
    assert [point["qty"] for point in rows[0]["unconfirmed_order_trend"]] == [0, 0, 0, 0]


def test_i005_build_summary_rows_does_not_compute_demand_forecast() -> None:
    rows = _build_rows_with({}, fetch_unconfirmed_orders_or_warn=([], ""))

    for key in ("demand_forecast_basis", "months_of_stock", "stockout_forecast_month", "reconciliation_unit_key"):
        assert key not in rows[0]


def test_i006_build_summary_rows_records_warning_and_keeps_rows() -> None:
    warnings: list[str] = []
    patches = _shipped_pair_patches({}, fetch_unconfirmed_orders_or_warn=([], "内示受注の取得に失敗: ORA-00942"))
    for p in patches:
        p.start()
    try:
        rows = build_summary_rows(MagicMock(), date(2026, 6, 29), warnings=warnings)
    finally:
        for p in patches:
            p.stop()

    assert len(rows) == 1
    assert [point["qty"] for point in rows[0]["unconfirmed_order_trend"]] == [0, 0, 0, 0]
    assert warnings == ["内示受注の取得に失敗: ORA-00942"]


@pytest.mark.django_db
def test_a001_run_summary_aggregation_applies_enrich_rows_before_store_and_returns_warning() -> None:
    """集計 → 後処理 → 保存 の順で、後処理の結果が保存される（TC-SFV-A-001）。警告は戻り値で返す。"""
    import_record = SlimsStockImport.objects.create(file_name="sample.csv", row_count=1)
    calls: list[str] = []

    def fake_build_list_rows(connection, query, *, stock_lines=None, stock_as_of_date=None, warnings=None):
        calls.append("aggregate")
        if warnings is not None:
            warnings.append("内示受注の取得に失敗: ORA-00942")
        return [{"cust_code": "137", "item_cd": "10523-X0A02", "flow_quadrant": "通常流動品"}]

    def enrich(rows, as_of_date):
        calls.append("enrich")
        return [dict(row, demand_forecast_basis="なし") for row in rows]

    with (
        patch("application.inventory_order_alert.infrastructure.oracle.summary_aggregation.oracle_connection") as connection,
        patch("application.inventory_order_alert.infrastructure.oracle.summary_aggregation.build_list_rows", side_effect=fake_build_list_rows),
    ):
        connection.return_value.__enter__.return_value = MagicMock()
        error, reset_count, warning = run_summary_aggregation(import_record, [], enrich_rows=enrich)

    snapshot = InventoryOrderAlertSummarySnapshot.objects.get(import_record=import_record)
    assert calls == ["aggregate", "enrich"]
    assert error == ""
    assert reset_count == 0
    assert warning == "内示受注の取得に失敗: ORA-00942"
    assert snapshot.rows[0]["demand_forecast_basis"] == "なし"
    assert snapshot.aggregation_error == ""


# --- 06_stockout-risk: TC-SOR-I-004〜006 ---


def _stage3_patches(**overrides):
    base = {
        "fetch_unconfirmed_orders_or_warn": ([], ""),
        "fetch_bom_level1_by_root": {"96160-00500": ["X-9065"]},
        "fetch_vendor_by_component": {"X-9065": ("9065", "ミズタニ")},
        "fetch_last_incoming_by_item_vend": {("X-9065", "9065"): date(2025, 4, 2)},
        "fetch_open_purchase_orders_or_warn": ([("PO-1", "X-9065", "9065", date(2026, 8, 5), 100), ("PO-2", "OTHER", "9065", date(2026, 8, 5), 9)], ""),
        "fetch_item_ordering_profiles_or_warn": ({"X-9065": (3, "4", None), "96160-00500": (None, None, 50)}, ""),
    }
    base.update(overrides)
    return base


def test_i004_build_summary_rows_attaches_open_orders_and_ordering_profile_without_assessing() -> None:
    rows = _build_rows_with({}, **_stage3_patches())

    row = rows[0]
    assert row["level1_item_cd"] == "X-9065"
    assert row["open_purchase_orders"] == [{"order_cd": "PO-1", "item_cd": "X-9065", "vend_cd": "9065", "due_date": "2026/08/05", "remaining_qty": 100}]
    assert row["open_purchase_orders_unknown"] is False
    assert row["lead_time_days"] == 3
    assert row["lead_time_source"] == "master"
    assert row["ordering_method"] == "手動発注"
    for key in ("stockout_risk", "response_class", "replenishment_qty", "days_until_stockout"):
        assert key not in row


def test_srr_i002_rows_carry_safety_stock_and_daily_unconfirmed_orders() -> None:
    """TC-SRR-I-002: 安全在庫（内作品番）と日次の内示（基準日より後のみ・疎な配列）が行に付く。"""
    rows = _build_rows_with(
        {},
        **_stage3_patches(
            fetch_unconfirmed_orders_or_warn=(
                [
                    ("137", "96160-00500", date(2026, 6, 29), 40),  # 基準日ちょうど → 落ちる
                    ("137", "96160-00500", date(2026, 6, 20), 10),  # 基準日より前 → 落ちる
                    ("137", "96160-00500", date(2026, 7, 10), 60),
                    ("137", "96160-00500", date(2026, 7, 10), 30),  # 同じ日は合算する
                    ("137", "96160-00500", date(2026, 7, 5), 0),  # 数量 0 は落とす
                ],
                "",
            )
        ),
    )

    row = rows[0]
    assert row["safety_stock"] == 50.0
    assert row["unconfirmed_order_daily"] == [{"date": "2026-07-10", "qty": 90}]


def test_srr_i003_item_master_failure_leaves_safety_stock_at_zero() -> None:
    """TC-SRR-I-003: 安全在庫が取れなくても取込は止めず、安全在庫なし（0）で続行する。"""
    rows = _build_rows_with({}, **_stage3_patches(fetch_item_ordering_profiles_or_warn=({}, "品目マスタの取得に失敗: ORA-00942")))

    assert rows[0]["safety_stock"] == 0.0


def test_i004_unresolved_level1_has_no_open_orders_and_default_profile() -> None:
    rows = _build_rows_with({}, **_stage3_patches(fetch_bom_level1_by_root={"96160-00500": []}, fetch_vendor_by_component={}, fetch_last_incoming_by_item_vend={}))

    row = rows[0]
    assert row["level1_item_cd"] == ""
    assert row["open_purchase_orders"] == []
    assert row["lead_time_source"] == "default"
    assert row["ordering_method"] == "不明"


def test_i005_open_order_fetch_failure_marks_rows_unknown_and_warns() -> None:
    warnings: list[str] = []
    patches = _shipped_pair_patches({}, **_stage3_patches(fetch_open_purchase_orders_or_warn=([], "発注残の取得に失敗: ORA-00942")))
    for p in patches:
        p.start()
    try:
        rows = build_summary_rows(MagicMock(), date(2026, 6, 29), warnings=warnings)
    finally:
        for p in patches:
            p.stop()

    assert rows[0]["open_purchase_orders_unknown"] is True
    assert rows[0]["open_purchase_orders"] == []
    assert warnings == ["発注残の取得に失敗: ORA-00942"]


def test_i006_item_master_fetch_failure_uses_defaults_and_warns() -> None:
    warnings: list[str] = []
    patches = _shipped_pair_patches({}, **_stage3_patches(fetch_item_ordering_profiles_or_warn=({}, "品目マスタの取得に失敗: ORA-00942")))
    for p in patches:
        p.start()
    try:
        rows = build_summary_rows(MagicMock(), date(2026, 6, 29), warnings=warnings)
    finally:
        for p in patches:
            p.stop()

    assert rows[0]["lead_time_source"] == "default"
    assert rows[0]["ordering_method"] == "不明"
    assert "品目マスタの取得に失敗: ORA-00942" in warnings


def test_i003_open_order_and_item_master_queries_are_called_once() -> None:
    patches = _shipped_pair_patches({}, **_stage3_patches())
    started = {p.attribute: p.start() for p in patches}
    try:
        build_summary_rows(MagicMock(), date(2026, 6, 29))
    finally:
        for p in patches:
            p.stop()

    assert started["fetch_open_purchase_orders_or_warn"].call_count == 1
    assert started["fetch_item_ordering_profiles_or_warn"].call_count == 1


# --- 2026/09/18: 工程の連鎖（BOM 全段の外注工程）と全工程の発注残 ---


def _chain_patches(**extra):
    base = _stage3_patches(
        fetch_bom_level1_by_root={"96160-00500": ["X-9133"]},
        fetch_vendor_by_component={"X-9133": ("9133", "丸栄NW"), "X-9213": ("9213", "サーテック"), "X-9106": ("9106", "誠豊電子")},
        fetch_last_incoming_by_item_vend={("X-9133", "9133"): date(2025, 1, 13)},
        fetch_bom_chain_by_root={"96160-00500": [(1, "X-9133"), (2, "X-9213"), (3, "X-9106")]},
        fetch_open_purchase_orders_or_warn=(
            [("PO-A", "X-9106", "9106", date(2026, 6, 15), 240), ("PO-B", "X-9133", "9133", date(2026, 10, 5), 10), ("PO-C", "OTHER", "9106", date(2026, 8, 5), 9)],
            "",
        ),
        fetch_item_ordering_profiles_or_warn=({"X-9133": (0, "5", None), "X-9213": (4, "5", None), "X-9106": (5, "4", None)}, ""),
    )
    base.update(extra)
    return base


def test_chain_build_summary_rows_attaches_process_chain_and_all_stage_orders() -> None:
    rows = _build_rows_with({}, **_chain_patches())

    row = rows[0]
    assert row["level1_item_cd"] == "X-9133"
    assert [stage["item_cd"] for stage in row["process_chain"]] == ["X-9133", "X-9213", "X-9106"]
    assert row["process_chain"][0] == {"level": 1, "item_cd": "X-9133", "vend_cd": "9133", "vend_name": "丸栄NW", "lead_time_days": 0, "lead_time_source": "default"}
    assert row["process_chain"][2] == {"level": 3, "item_cd": "X-9106", "vend_cd": "9106", "vend_name": "誠豊電子", "lead_time_days": 5, "lead_time_source": "master"}
    assert sorted((o["order_cd"], o["item_cd"], o["remaining_qty"]) for o in row["open_purchase_orders"]) == [("PO-A", "X-9106", 240), ("PO-B", "X-9133", 10)]
    assert row["ordering_method"] == "MRP 発注"  # 直下の工程の発注方式


def test_chain_falls_back_to_level1_only_when_bom_chain_is_empty() -> None:
    rows = _build_rows_with({}, **_chain_patches(fetch_bom_chain_by_root={}))

    row = rows[0]
    assert [stage["item_cd"] for stage in row["process_chain"]] == ["X-9133"]
    assert [o["item_cd"] for o in row["open_purchase_orders"]] == ["X-9133"]


def test_chain_fetch_is_called_once_with_all_roots() -> None:
    patches = _shipped_pair_patches({}, **_chain_patches())
    started = {p.attribute: p.start() for p in patches}
    try:
        build_summary_rows(MagicMock(), date(2026, 6, 29))
    finally:
        for p in patches:
            p.stop()

    assert started["fetch_bom_chain_by_root"].call_count == 1


# --- 09_stock-simulation-chart: TC-SSC-I-001〜005 ---


def test_ssc_i001_rows_carry_daily_shipment_and_incoming() -> None:
    """在庫シミュレーション（V-237）の過去側。基準日の30日前〜基準日の疎な配列。"""
    rows = _build_rows_with(
        {},
        **_stage3_patches(
            fetch_all_shipments=[
                ("137", "10523-X0A02", date(2026, 6, 20), 10),   # 範囲内（基準日 6/29 の 9 日前）
                ("137", "10523-X0A02", date(2026, 6, 20), 5),    # 同じ日は合算
                ("137", "10523-X0A02", date(2026, 5, 29), 99),   # 31 日前 → 範囲外
                ("137", "10523-X0A02", date(2026, 6, 29), 7),    # 基準日当日
            ],
            fetch_incoming_receipts=[("X-9065", "9065", date(2026, 6, 25), 40)],
        ),
    )

    row = rows[0]
    assert row["daily_shipment"] == [{"date": "2026-06-20", "qty": 15}, {"date": "2026-06-29", "qty": 7}]
    assert row["daily_incoming"] == [{"date": "2026-06-25", "qty": 40}]


def test_ssc_i002_rows_carry_planned_incoming_without_overdue() -> None:
    """予定入荷（V-236）は納期 > 基準日 のみ・発注番号で重複除去済み。"""
    rows = _build_rows_with(
        {},
        **_stage3_patches(
            fetch_open_purchase_orders_or_warn=(
                [
                    ("PO-1", "X-9065", "9065", date(2026, 7, 10), 100),   # 未来 → 含む
                    ("PO-2", "X-9065", "9065", date(2026, 7, 10), 40),    # 同じ納期は合算
                    ("PO-3", "X-9065", "9065", date(2026, 6, 10), 70),    # 納期遅れ → 含まない
                    ("PO-4", "X-9065", "9065", date(2026, 6, 29), 30),    # 基準日当日 → 含まない
                    ("PO-5", "OTHER", "9065", date(2026, 7, 20), 9),      # 直下の工程でない → 含まない
                ],
                "",
            )
        ),
    )

    assert rows[0]["planned_incoming"] == [{"date": "2026-07-10", "qty": 140}]


def test_ssc_i003_daily_series_does_not_add_oracle_queries() -> None:
    """TC-SSC-I-003: 日次化で Oracle の問い合わせ回数は増えない。"""
    patches = _shipped_pair_patches({}, **_stage3_patches())
    started = {p.attribute: p.start() for p in patches}
    try:
        build_summary_rows(MagicMock(), date(2026, 6, 29))
    finally:
        for p in patches:
            p.stop()

    assert started["fetch_all_shipments"].call_count == 1
    assert started["fetch_incoming_receipts"].call_count == 1
    assert started["fetch_open_purchase_orders_or_warn"].call_count == 1


def test_ssc_i004_monthly_trends_are_kept() -> None:
    """月次推移（V-216/V-217）は推定在庫推移（V-218）のために残る。"""
    rows = _build_rows_with({}, **_stage3_patches(fetch_all_shipments=[("137", "10523-X0A02", date(2026, 6, 20), 10)]))

    row = rows[0]
    assert len(row["shipment_trend"]) == 24
    assert len(row["incoming_trend"]) == 24

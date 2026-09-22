from __future__ import annotations

from datetime import date

from application.inventory_order_alert.domain.value_objects.export_csv import (
    EXPORT_COLUMNS,
    EXPORT_HEADER_LABELS,
    render_export_csv,
)
from application.inventory_order_alert.domain.value_objects.flow_quadrant import (
    QUADRANT_DORMANT_STOCK,
    QUADRANT_LOW_FLOW_NO_INCOMING,
    QUADRANT_LOW_FLOW_NO_SHIPMENT,
    QUADRANT_NORMAL_FLOW,
)

#: 05 時点の既存 24 列。第 2 段階（TC-SFV-D-061）で末尾に列を足す際もこの順序は変えない。
EXISTING_COLUMNS_IN_ORDER = [
    "cust_chrg_psn_cd",
    "cust_code",
    "cust_name",
    "item_cd",
    "level1_vend_cd",
    "level1_vend_name",
    "level1_item_cd",
    "last_incoming_date",
    "last_ship_date",
    "post_shipment_count",
    "post_shipment_total_qty",
    "stock_qty",
    "mari_stock_qty",
    "stock_as_of_label",
    "flow_quadrant",
    "flow_axis",
    "evaluation_period",
    "no_incoming_record",
    "responsible_department",
    "confirmation_status",
    "confirmed_at",
    "confirmed_by",
    "confirmation_memo",
    "confirmation_memo_history",
]

#: `confirmation_status` 以降は既存の CSV 読み込み手順を壊さないため順序を固定する（NF-002）。
TRAILING_COLUMNS = [
    "confirmation_status",
    "confirmed_at",
    "confirmed_by",
    "confirmation_memo",
    "confirmation_memo_history",
]


def _sample_row() -> dict[str, object]:
    return {
        "cust_code": "112",
        "cust_name": "テスト得意先",
        "cust_chrg_psn_cd": "A01",
        "item_cd": "90249-10112",
        "level1_item_cd": "90249-10112-9209",
        "level1_vend_cd": "9209",
        "level1_vend_name": "小野メッキ",
        "last_incoming_date": date(2026, 6, 11),
        "last_ship_date": date(2026, 6, 15),
        "post_shipment_count": 1,
        "post_shipment_total_qty": 250,
        "stock_qty": 100,
        "mari_stock_qty": 95,
        "stock_location_summary": "2D0-03-5 他1",
        "stock_location_detail": "2D0-03-5=90@20161228;2E1-03-4=10@20161228",
        "stock_as_of_label": "2026年6月17日時点の在庫",
        "flow_quadrant": QUADRANT_LOW_FLOW_NO_INCOMING,
        "flow_axis": "",
        "evaluation_period": "1年",
        "no_incoming_record": "あり",
        "responsible_department": "調達G・営業G・生産管理",
        "confirmation_status": "未確認",
        "confirmed_at": "",
        "confirmed_by": "",
        "confirmation_memo": "最新のみ",
        "confirmation_memo_history": "2026/06/19 10:00 10001: 最新のみ",
    }


def test_export_columns_replace_alert_level_with_flow_quadrant():
    columns = [column for column, _label in EXPORT_COLUMNS]

    assert ("flow_quadrant", "流動区分") in EXPORT_COLUMNS
    assert "alert_level" not in columns


def test_export_columns_keep_flow_axis_column_for_compatibility_and_evaluation_period():
    # `判定軸` 列は既存の CSV 読み込み手順を壊さないために残し、値は常に空にする（05 design §7.3）
    assert ("flow_axis", "判定軸") in EXPORT_COLUMNS
    assert ("evaluation_period", "判定期間") in EXPORT_COLUMNS


def test_export_columns_existing_24_columns_keep_their_order():
    columns = [column for column, _label in EXPORT_COLUMNS]

    assert columns[: len(EXISTING_COLUMNS_IN_ORDER)] == EXISTING_COLUMNS_IN_ORDER


def test_export_columns_include_no_incoming_record_and_responsible_department():
    assert ("no_incoming_record", "入荷実績なし") in EXPORT_COLUMNS
    assert ("responsible_department", "責任部署") in EXPORT_COLUMNS


def test_export_columns_keep_order_after_confirmation_status():
    columns = [column for column, _label in EXPORT_COLUMNS]
    start = columns.index("confirmation_status")

    # 確認関連 5 列は連続。05 第 2 段階の列はその後ろに付く（TC-SFV-D-061）
    assert columns[start : start + len(TRAILING_COLUMNS)] == TRAILING_COLUMNS


def test_export_columns_label_slims_and_mari_stock():
    assert ("stock_qty", "在庫数(SLIMS)") in EXPORT_COLUMNS
    assert ("mari_stock_qty", "在庫数(MARI)") in EXPORT_COLUMNS


def test_export_columns_keep_responsible_department():
    columns = [column for column, _label in EXPORT_COLUMNS]

    # 一覧からは外すが CSV には残す（持ち出し用途のため。design.md §6.2）
    assert "responsible_department" in columns


def test_export_csv_writes_empty_for_not_fetched_mari_stock():
    row = _sample_row()
    del row["mari_stock_qty"]

    payload = render_export_csv([row]).decode("utf-8-sig")
    header, data = payload.strip().splitlines()[:2]

    # CSV では「－」を出さず空にする（Excel で文字列として扱われるため）
    mari_index = header.split(",").index("在庫数(MARI)")
    assert data.split(",")[mari_index] == ""


def test_export_headers_are_japanese():
    assert EXPORT_HEADER_LABELS["last_incoming_date"] == "最終入荷日"
    assert EXPORT_HEADER_LABELS["item_cd"] == "得意先品番"
    assert EXPORT_HEADER_LABELS["cust_chrg_psn_cd"] == "担当者コード"
    assert EXPORT_HEADER_LABELS["level1_item_cd"] == "仕入先品番"
    assert EXPORT_HEADER_LABELS["flow_quadrant"] == "流動区分"
    assert "stock_location_summary" not in EXPORT_HEADER_LABELS


def test_render_export_csv_has_utf8_bom():
    payload = render_export_csv([_sample_row()])
    assert payload.startswith(b"\xef\xbb\xbf")


def test_render_export_csv_includes_stock_and_flow_quadrant_columns():
    payload = render_export_csv([_sample_row()]).decode("utf-8-sig")
    lines = payload.strip().splitlines()
    header = lines[0]
    data = lines[1]
    assert "在庫数" in header
    assert "ロケーション" not in header
    assert "流動区分" in header
    assert "判定軸" in header
    assert "判定期間" in header
    assert "責任部署" in header
    assert "最新メモ" in header
    assert "メモ履歴" in header
    assert "90249-10112" in data
    assert QUADRANT_LOW_FLOW_NO_INCOMING in data
    assert "250" in data


def test_render_export_csv_empty_rows_outputs_header_only():
    payload = render_export_csv([]).decode("utf-8-sig")
    lines = [line for line in payload.strip().splitlines() if line]
    assert len(lines) == 1
    assert "得意先コード" in lines[0]


def _csv_record(row: dict[str, object]) -> dict[str, str]:
    import csv
    import io

    payload = render_export_csv([row]).decode("utf-8-sig")
    return next(csv.DictReader(io.StringIO(payload)))


# --- TC-SFV-D-060: CSV の流動区分は新区分名、判定軸列は空 ---


def test_d060_flow_quadrant_is_new_name_and_axis_column_is_empty():
    record = _csv_record(_sample_row())

    assert record["流動区分"] == "低流動品（入荷なし）"
    assert record["判定軸"] == ""
    assert record["判定期間"] == "1年"


def test_fqr_c004_flow_quadrant_column_carries_all_seven_quadrants():
    """流動区分の値が 7 種になるだけで、列は増えない（07 design §2.8、TC-FQR-C-004）。"""
    from application.inventory_order_alert.domain.value_objects.flow_quadrant import FLOW_QUADRANTS

    for quadrant in FLOW_QUADRANTS:
        row = _sample_row()
        row["flow_quadrant"] = quadrant
        assert _csv_record(row)["流動区分"] == quadrant

    assert len(EXPORT_COLUMNS) == 39


def test_d060_axis_column_is_empty_even_if_row_carries_a_value():
    row = _sample_row()
    row["flow_axis"] = "低流動判定軸"

    assert _csv_record(row)["判定軸"] == ""


# --- TC-SFV-D-062: CSV に旧称が出ない ---


def test_d062_legacy_quadrant_names_never_appear():
    rows = []
    for quadrant in (
        QUADRANT_LOW_FLOW_NO_INCOMING,
        QUADRANT_DORMANT_STOCK,
        QUADRANT_LOW_FLOW_NO_SHIPMENT,
        QUADRANT_NORMAL_FLOW,
        "供給リスク品",
        "在庫過剰リスク品",
    ):
        row = _sample_row()
        row["flow_quadrant"] = quadrant
        rows.append(row)

    payload = render_export_csv(rows).decode("utf-8-sig")

    assert "供給リスク品" not in payload
    assert "在庫過剰リスク品" not in payload
    assert payload.count("低流動品（入荷なし）") == 2
    assert payload.count("低流動品（出荷なし）") == 2


# --- TC-SFV-D-061: CSV の既存列順は不変で新規列は末尾 ---

STAGE2_TRAILING_COLUMNS = [
    ("months_of_stock", "在庫月数"),
    ("stockout_forecast_month", "在庫切れ予測月"),
    ("demand_forecast_basis", "需要予測の算出根拠"),
    ("recommended_action", "推奨アクション"),
]


def test_d061_existing_columns_unchanged_and_new_columns_appended():
    columns = [column for column, _label in EXPORT_COLUMNS]

    assert columns[: len(EXISTING_COLUMNS_IN_ORDER)] == EXISTING_COLUMNS_IN_ORDER
    # 05 第 2 段階の 4 列の後ろに 06 の 11 列が続く
    assert EXPORT_COLUMNS[len(EXISTING_COLUMNS_IN_ORDER) : len(EXISTING_COLUMNS_IN_ORDER) + 4] == STAGE2_TRAILING_COLUMNS
    assert len(EXPORT_COLUMNS) == 39


def test_d061_new_columns_render_values_and_empty_for_missing():
    row = _sample_row() | {
        "months_of_stock": 150.6,
        "stockout_forecast_month": "2028-12",
        "demand_forecast_basis": "内示",
        "recommended_action": "仕入先へ生産継続可否・設備/金型の有無を確認。在庫切れ予測月が近いものから",
    }
    record = _csv_record(row)

    assert record["在庫月数"] == "150.6"
    assert record["在庫切れ予測月"] == "2028-12"
    assert record["需要予測の算出根拠"] == "内示"
    assert record["推奨アクション"].startswith("仕入先へ")

    legacy = _csv_record(_sample_row())

    assert legacy["在庫月数"] == ""
    assert legacy["在庫切れ予測月"] == ""
    assert legacy["需要予測の算出根拠"] == ""
    assert legacy["推奨アクション"] == ""


def test_d061_none_months_of_stock_renders_empty():
    row = _sample_row() | {"months_of_stock": None, "stockout_forecast_month": None, "demand_forecast_basis": "なし"}
    record = _csv_record(row)

    assert record["在庫月数"] == ""
    assert record["在庫切れ予測月"] == ""
    assert record["需要予測の算出根拠"] == "なし"

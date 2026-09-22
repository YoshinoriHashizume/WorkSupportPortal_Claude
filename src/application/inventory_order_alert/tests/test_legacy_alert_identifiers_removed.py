"""旧アラートレベルの識別子が残っていないことを検証する（test-design.md §1.4）。

「置換」方式の完了条件そのものであり、撤去漏れが後から混入した場合もここで検出する。
"""

from __future__ import annotations

from pathlib import Path

import pytest

SRC_ROOT = Path(__file__).resolve().parents[3]

#: 走査対象（02 tasks.md タスク70、05 タスク19）。
SCAN_TARGETS = (
    ("application/inventory_order_alert", (".py",)),
    ("static/js", (".js",)),
    ("static/css", (".css",)),
    ("templates/inventory_order_alert", (".html",)),
    ("templates/portal", (".html",)),
    ("scripts", (".py",)),
)

#: 05_single-flow-view で廃止した旧称・旧キー・判定軸（TC-SFV-D-025、F-019）。
#: `flow_quadrant.py` は互換写像 `LEGACY_QUADRANT_ALIASES` として旧称・旧キーを持つため除外する。
LEGACY_QUADRANT_TERMS = (
    "供給リスク品",
    "在庫過剰リスク品",
    "supply-risk",
    "excess-stock-risk",
    "supply_risk",
    "excess_stock_risk",
    "supplyRisk",
    "excessStockRisk",
)
LEGACY_AXIS_TERMS = (
    "FLOW_AXIS",
    "flowAxis",
    "flow_axis_",
    "低流動判定軸",
    "死蔵判定軸",
    "for_axis",
    "default_for_axis",
)
LEGACY_ALIAS_HOLDER = "domain/value_objects/flow_quadrant.py"

#: 07_flow-quadrant-refinement で廃止した識別子・文言（TC-FQR-C-007）。
#: 「欠品（入荷即出荷）」「stockout-pass-through」は `LEGACY_QUADRANT_ALIASES` にのみ残す。
LEGACY_FLOW_QUADRANT_REFINEMENT_TERMS = (
    "欠品（入荷即出荷）",
    "stockout-pass-through",
    "stockoutPassThrough",
    "QUADRANT_STOCKOUT_PASS_THROUGH",
    "通過品",
    "BASIS_ACTUAL",
    "ACTUAL_BASIS_MONTHS",
    "REASON_ACTUAL_BASIS",
    "実績ベース",
    "demand_window",
    "{demand_window}",
    "DEMAND_WINDOW_MONTHS",
    # 旧 4 区分のランク（通常流動品 = 3）。7 区分では 6
    "[QUADRANT_NORMAL_FLOW_KEY]: 3",
)

LEGACY_IDENTIFIERS = (
    "alert_level",
    "alertLevel",
    "alert_only",
    "alertOnly",
    "save_alert_settings",
)

#: 仕様書・旧名を含むのが正当なマイグレーション・
#: 「旧識別子が存在しないこと」を書くために旧名を引用するテストは除外する。
EXCLUDED_PARTS = ("docs", "__pycache__", "migrations", "tests")


def _scanned_files() -> list[Path]:
    files: list[Path] = []
    for relative, suffixes in SCAN_TARGETS:
        root = SRC_ROOT / relative
        if not root.exists():
            continue
        for path in sorted(root.rglob("*")):
            if not path.is_file() or path.suffix not in suffixes:
                continue
            if any(part in EXCLUDED_PARTS for part in path.relative_to(SRC_ROOT).parts):
                continue
            files.append(path)
    return files


def test_scan_covers_expected_files():
    # 走査対象が空だと検証が素通りするため、件数そのものを固定する。
    assert len(_scanned_files()) > 40


@pytest.mark.parametrize("identifier", LEGACY_IDENTIFIERS)
def test_legacy_alert_identifier_is_absent(identifier):
    hits = [
        str(path.relative_to(SRC_ROOT))
        for path in _scanned_files()
        if identifier in path.read_text(encoding="utf-8")
    ]

    assert hits == []


@pytest.mark.parametrize("term", LEGACY_QUADRANT_TERMS)
def test_legacy_quadrant_term_is_absent(term):
    hits = [
        str(path.relative_to(SRC_ROOT))
        for path in _scanned_files()
        if not str(path).replace("\\", "/").endswith(LEGACY_ALIAS_HOLDER)
        and term in path.read_text(encoding="utf-8")
    ]

    assert hits == []


@pytest.mark.parametrize("term", LEGACY_FLOW_QUADRANT_REFINEMENT_TERMS)
def test_fqr_c007_legacy_flow_quadrant_refinement_term_is_absent(term):
    hits = [
        str(path.relative_to(SRC_ROOT))
        for path in _scanned_files()
        if not str(path).replace("\\", "/").endswith(LEGACY_ALIAS_HOLDER)
        and term in path.read_text(encoding="utf-8")
    ]

    assert hits == []


@pytest.mark.parametrize("term", LEGACY_AXIS_TERMS)
def test_legacy_axis_term_is_absent(term):
    hits = [
        str(path.relative_to(SRC_ROOT))
        for path in _scanned_files()
        if term in path.read_text(encoding="utf-8")
    ]

    assert hits == []


def test_flow_quadrant_module_mentions_legacy_names_only_in_alias_map():
    text = (SRC_ROOT / "application/inventory_order_alert" / LEGACY_ALIAS_HOLDER).read_text(encoding="utf-8")
    start = text.index("LEGACY_QUADRANT_ALIASES = {")
    end = text.index("}", start)
    outside = text[:start] + text[end:]

    for term in ("供給リスク品", "在庫過剰リスク品", "supply-risk", "excess-stock-risk"):
        assert term not in outside


def test_save_alert_settings_use_case_module_does_not_exist():
    with pytest.raises(ModuleNotFoundError):
        __import__("application.inventory_order_alert.use_cases.save_alert_settings")


def test_alert_level_domain_module_does_not_exist():
    with pytest.raises(ModuleNotFoundError):
        __import__("application.inventory_order_alert.domain.value_objects.alert_level")


def test_alert_rules_domain_module_does_not_exist():
    with pytest.raises(ModuleNotFoundError):
        __import__("application.inventory_order_alert.domain.value_objects.alert_rules")


def test_wiring_has_no_save_alert_settings_usecase():
    from application.inventory_order_alert.interfaces import wiring

    assert not hasattr(wiring, "save_alert_settings_usecase")
    assert "save_alert_settings_usecase" not in wiring.__all__


def test_stock_column_labels_always_state_their_source():
    """出所を示さない「在庫数」単独の見出しを残さない（TC-MSV-X-012 / REQ-MSV-NF-005）。

    SLIMS と MARI のどちらの値か分からない見出しは、発注判断を誤らせる。
    """
    from application.inventory_order_alert.domain.value_objects.export_csv import EXPORT_COLUMNS
    from application.inventory_order_alert.domain.value_objects.table_display import SORTABLE_COLUMNS

    for label in [label for _key, label in SORTABLE_COLUMNS] + [label for _key, label in EXPORT_COLUMNS]:
        assert label != "在庫数"


def test_app_css_has_no_japanese_flow_quadrant_selectors():
    css = (SRC_ROOT / "static" / "css" / "app.css").read_text(encoding="utf-8")

    for legacy_selector in (
        ".alert-row--重点",
        ".alert-row--警告（出荷あり）",
        ".alert-row--警告（出荷なし）",
        ".alert-row--アラート無し",
    ):
        assert legacy_selector not in css
    # 確認状態のクラスは本要件の対象外・据え置き（design.md §6.6.7）。
    assert ".alert-row--確認済" in css
    assert ".alert-row--確認中" in css

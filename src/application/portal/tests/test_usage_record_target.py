from __future__ import annotations

from dataclasses import FrozenInstanceError

import pytest

from application.portal.domain.value_objects.menu import MENU_ITEMS
from application.portal.domain.value_objects.menu_access import is_menu_path_active
from application.portal.domain.value_objects.usage_record import (
    EXPORT_ENDPOINTS,
    USAGE_TYPE_EXPORT,
    USAGE_TYPE_VIEW,
    UsageRecordTarget,
    resolve_menu_key,
    resolve_usage_record_target,
)

# design.md §4.4(b) の出力エンドポイント一覧（`?type=` 無しの既定）
EXPECTED_EXPORT_ENDPOINTS = {
    "/api/asset-inventory/export.csv": "asset-inventory",
    "/api/asset-inventory/asp-import.csv": "asset-inventory",
    "/api/gonenkukumi/export": "five-year-nine",
    "/app/production/inventory-order-alert/export.csv": "inventory-order-alert",
    "/api/inventory-order-alert/export.csv": "inventory-order-alert",
    "/app/production/receipt-comparison/export": "receipt-comparison-finished-product",
    "/app/sales/shipment-trend/export.csv": "shipment-trend-list",
    "/api/shipment-trend/export.csv": "shipment-trend-list",
    "/app/management/usage-status/export.csv": "usage-status",
}

# パスに export を含むが記録対象外のルート（旧 URL のリダイレクト。302 のため判定順 1 で除外される）
EXCLUDED_EXPORT_ROUTES = {
    "/app/production/receipt-comparison/<slug:comparison_slug>/export",
}


# --- 出力エンドポイント一覧（ExportEndpoints） ---


@pytest.mark.parametrize(("path", "expected"), sorted(EXPECTED_EXPORT_ENDPOINTS.items()))
def test_export_endpoints_returns_menu_key_for_known_path(path, expected):
    """出力エンドポイントのパスから対応するメニューキーを返す。"""
    assert EXPORT_ENDPOINTS.menu_key_for(path, "") == expected


@pytest.mark.parametrize(
    ("comparison_type", "expected"),
    [
        ("finished-product", "receipt-comparison-finished-product"),
        ("supplied-parts", "receipt-comparison-supplied-parts"),
        ("", "receipt-comparison-finished-product"),
    ],
)
def test_export_endpoints_branch_receipt_comparison_by_type(comparison_type, expected):
    """検収書比較の出力は比較区分でメニューキーが分岐する。"""
    path = "/app/production/receipt-comparison/export"

    assert EXPORT_ENDPOINTS.menu_key_for(path, comparison_type) == expected


@pytest.mark.parametrize(
    "path",
    ["/api/asset-inventory/attachment", "/api/gonenkukumi/search"],
)
def test_export_endpoints_returns_none_for_unknown_path(path):
    """出力エンドポイント以外のパスにはメニューキーを返さない。"""
    assert EXPORT_ENDPOINTS.menu_key_for(path, "") is None


def test_export_endpoints_are_immutable():
    """出力エンドポイント一覧は外部から書き換えられない。"""
    endpoints = EXPORT_ENDPOINTS.as_tuple()
    before = len(endpoints)

    with pytest.raises(FrozenInstanceError):
        endpoints[0].path = "/app/changed"

    assert isinstance(endpoints, tuple)
    assert len(EXPORT_ENDPOINTS.as_tuple()) == before


# --- 記録対象（UsageRecordTarget） ---


def test_usage_record_target_equals_when_same_values():
    """記録対象は値が同じであれば等しい。"""
    left = UsageRecordTarget(menu_key="shipment-trend-list", usage_type=USAGE_TYPE_VIEW)
    right = UsageRecordTarget(menu_key="shipment-trend-list", usage_type=USAGE_TYPE_VIEW)

    assert left == right
    assert hash(left) == hash(right)


# --- メニューキーの解決（resolve_menu_key） ---


def test_resolve_menu_key_returns_key_for_exact_href():
    """メニュー項目のリンク先と完全一致するパスからメニューキーを返す。"""
    assert resolve_menu_key("/app/sales/shipment-trend", "") == "shipment-trend-list"


def test_resolve_menu_key_returns_parent_key_for_child_path():
    """メニュー項目の配下のパスからも同じメニューキーを返す。"""
    assert resolve_menu_key("/app/sales/shipment-trend/detail", "") == "shipment-trend-list"


def test_resolve_menu_key_never_returns_parent_without_href():
    """子を束ねるだけの親メニューのキーは返さず、子の既定のキーを返す。"""
    menu_key = resolve_menu_key("/app/production/receipt-comparison", "")

    assert menu_key != "receipt-comparison"
    assert menu_key == "receipt-comparison-finished-product"


@pytest.mark.parametrize(
    ("comparison_type", "expected"),
    [
        ("finished-product", "receipt-comparison-finished-product"),
        ("supplied-parts", "receipt-comparison-supplied-parts"),
        ("", "receipt-comparison-finished-product"),
    ],
)
def test_resolve_menu_key_branches_receipt_comparison_by_type(comparison_type, expected):
    """検収書比較の画面は比較区分でメニューキーが分岐する。"""
    assert resolve_menu_key("/app/production/receipt-comparison/list", comparison_type) == expected


def test_resolve_menu_key_uses_default_type_on_settings_page():
    """比較区分を伴わない配下のパスは既定の比較区分に従う。"""
    path = "/app/production/receipt-comparison/settings"

    assert resolve_menu_key(path, "") == "receipt-comparison-finished-product"


@pytest.mark.parametrize("path", ["/app", "/app/access-status", "/favicon.ico"])
def test_resolve_menu_key_returns_none_for_unmapped_path(path):
    """メニュー項目に対応づかないパスにはメニューキーを返さない。"""
    assert resolve_menu_key(path, "") is None


def test_resolve_menu_key_returns_usage_status_key_for_own_page():
    """利用状況の画面自身のパスからもメニューキーを返す。"""
    assert resolve_menu_key("/app/management/usage-status", "") == "usage-status"


def test_resolve_menu_key_agrees_with_is_menu_path_active():
    """メニューキーの解決は既存の選択中判定と同じ一致規則に従う。"""
    targets = [item for item in MENU_ITEMS if item.href]

    for item in targets:
        path = item.href.split("?")[0]
        if not is_menu_path_active(path, item.href):
            continue
        assert resolve_menu_key(path, "") == item.key


# --- 記録対象の判別（resolve_usage_record_target） ---


def _resolve(path, *, comparison_type="", status_code=200, content_type="text/html; charset=utf-8", is_attachment=False):
    return resolve_usage_record_target(
        path=path,
        comparison_type=comparison_type,
        status_code=status_code,
        content_type=content_type,
        is_attachment=is_attachment,
    )


def test_resolve_target_records_view_for_html_response():
    """画面が正常に表示された応答は表示として記録する。"""
    target = _resolve("/app/sales/shipment-trend")

    assert target == UsageRecordTarget(menu_key="shipment-trend-list", usage_type=USAGE_TYPE_VIEW)


def test_resolve_target_records_export_for_attachment_response():
    """出力エンドポイントがファイルを返した応答は出力として記録する。"""
    target = _resolve(
        "/api/shipment-trend/export.csv",
        content_type="text/csv",
        is_attachment=True,
    )

    assert target == UsageRecordTarget(menu_key="shipment-trend-list", usage_type=USAGE_TYPE_EXPORT)


def test_resolve_target_skips_export_endpoint_without_attachment():
    """出力エンドポイントでもファイルを返していない応答は記録しない。"""
    target = _resolve(
        "/api/shipment-trend/export.csv",
        content_type="text/csv",
        is_attachment=False,
    )

    assert target is None


@pytest.mark.parametrize("status_code", [302, 400, 403, 404, 500])
def test_resolve_target_skips_non_200_response(status_code):
    """正常に完了していない応答は記録しない。"""
    view = _resolve("/app/sales/shipment-trend", status_code=status_code)
    export = _resolve(
        "/api/shipment-trend/export.csv",
        status_code=status_code,
        content_type="text/csv",
        is_attachment=True,
    )

    assert view is None
    assert export is None


def test_resolve_target_skips_non_html_response():
    """画面内の非同期問い合わせの応答は記録しない。"""
    target = _resolve("/api/gonenkukumi/search", content_type="application/json")

    assert target is None


def test_resolve_target_skips_attachment_relay_endpoint():
    """添付ファイルを中継する経路は出力操作として記録しない。"""
    target = _resolve(
        "/api/asset-inventory/attachment",
        content_type="application/pdf",
        is_attachment=True,
    )

    assert target is None


def test_resolve_target_skips_path_without_menu():
    """メニュー項目に対応づかない画面は記録しない。"""
    target = _resolve("/app")

    assert target is None


def test_resolve_target_records_usage_status_page_view():
    """利用状況の画面自身の表示も記録する。"""
    target = _resolve("/app/management/usage-status")

    assert target == UsageRecordTarget(menu_key="usage-status", usage_type=USAGE_TYPE_VIEW)


def test_resolve_target_records_usage_status_csv_export():
    """利用状況の CSV 出力も出力操作として記録する。"""
    target = _resolve(
        "/app/management/usage-status/export.csv",
        content_type="text/csv",
        is_attachment=True,
    )

    assert target == UsageRecordTarget(menu_key="usage-status", usage_type=USAGE_TYPE_EXPORT)


def test_resolve_target_checks_export_endpoint_before_content_type():
    """出力エンドポイントの判定は応答の種類による除外より先に行う。"""
    target = _resolve(
        "/app/production/inventory-order-alert/export.csv",
        content_type="text/csv",
        is_attachment=True,
    )

    assert target == UsageRecordTarget(
        menu_key="inventory-order-alert",
        usage_type=USAGE_TYPE_EXPORT,
    )


# --- 出力エンドポイントの追加漏れ検知（REQ-NF-008） ---


def _iter_route_paths(patterns, prefix=""):
    from django.urls import URLPattern, URLResolver

    for entry in patterns:
        if isinstance(entry, URLResolver):
            yield from _iter_route_paths(entry.url_patterns, prefix + str(entry.pattern))
        elif isinstance(entry, URLPattern):
            yield "/" + prefix + str(entry.pattern)


def test_export_endpoints_match_all_export_urlpatterns():
    """出力を返す全ルートが出力エンドポイント一覧に登録されている。"""
    from django.urls import get_resolver

    routes = set(_iter_route_paths(get_resolver().url_patterns))
    named_export_routes = {path for path in routes if "export" in path}

    expected_named = {path for path in EXPECTED_EXPORT_ENDPOINTS if "export" in path}

    assert named_export_routes == expected_named | EXCLUDED_EXPORT_ROUTES
    assert set(EXPORT_ENDPOINTS.paths()) == set(EXPECTED_EXPORT_ENDPOINTS)
    assert set(EXPORT_ENDPOINTS.paths()) <= routes

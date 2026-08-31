from __future__ import annotations

from application.asset_inventory.domain.value_objects.errors import DesknetApiError
from application.asset_inventory.use_cases.export_csv import ExportCsv

from application.asset_inventory.use_cases.list_page import ListPage

from .test_usecase_list_page import (
    RECONCILE_APP_IDS,
    _counting_mock_list_all,
    _list_all_site_master_down,
    _list_page_query,
    _mock_list_all,
)


def test_TC_AIV_UC_005_export_csv_bytes():
    usecase = ExportCsv(_mock_list_all)
    query = _list_page_query()
    content = usecase.execute("key", query)
    assert content.startswith(b"\xef\xbb\xbf")
    assert "資産番号" in content.decode("utf-8-sig")


def test_TC_AIV_UC_007_export_csv_uses_session_cache():
    list_all, counts = _counting_mock_list_all(_mock_list_all)
    session: dict = {}
    ListPage(list_all).execute("key", _list_page_query(), session=session)
    assert counts["reconcile"] == len(RECONCILE_APP_IDS)
    ExportCsv(list_all).execute("key", _list_page_query(), session=session)
    assert counts["reconcile"] == len(RECONCILE_APP_IDS)


def test_TC_AIV_UC_006_export_csv_safe_on_api_error():
    def failing_list_all(access_key, app_id, fields):
        raise DesknetApiError("api down")

    usecase = ExportCsv(failing_list_all)
    query = _list_page_query()
    content, error = usecase.execute_safe("key", query)
    assert content is None
    assert error is not None


def test_TC_AIV_UC_034_export_csv_survives_site_master_failure():
    """拠点マスタのみの取得失敗では CSV 出力を失敗させない（機能仕様書 §7.4.1）。"""
    content, error = ExportCsv(_list_all_site_master_down).execute_safe("key", _list_page_query())
    assert error is None
    assert content is not None
    assert "資産番号" in content.decode("utf-8-sig")

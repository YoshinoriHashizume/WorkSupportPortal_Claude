from __future__ import annotations

from applications.asset_inventory.domain.errors import DesknetApiError
from applications.asset_inventory.usecase.usecase_export_csv import ExportCsvUsecase

from applications.asset_inventory.usecase.usecase_list_page import ListPageUsecase

from tests.asset_inventory.test_usecase_list_page import (
    RECONCILE_APP_IDS,
    _counting_mock_list_all,
    _list_page_query,
    _mock_list_all,
)


def test_TC_AIV_UC_005_export_csv_bytes():
    usecase = ExportCsvUsecase(_mock_list_all)
    query = _list_page_query()
    content = usecase.execute("key", query)
    assert content.startswith(b"\xef\xbb\xbf")
    assert "資産番号" in content.decode("utf-8-sig")


def test_TC_AIV_UC_007_export_csv_uses_session_cache():
    list_all, counts = _counting_mock_list_all(_mock_list_all)
    session: dict = {}
    ListPageUsecase(list_all).execute("key", _list_page_query(), session=session)
    assert counts["reconcile"] == len(RECONCILE_APP_IDS)
    ExportCsvUsecase(list_all).execute("key", _list_page_query(), session=session)
    assert counts["reconcile"] == len(RECONCILE_APP_IDS)


def test_TC_AIV_UC_006_export_csv_safe_on_api_error():
    def failing_list_all(access_key, app_id, fields):
        raise DesknetApiError("api down")

    usecase = ExportCsvUsecase(failing_list_all)
    query = _list_page_query()
    content, error = usecase.execute_safe("key", query)
    assert content is None
    assert error is not None

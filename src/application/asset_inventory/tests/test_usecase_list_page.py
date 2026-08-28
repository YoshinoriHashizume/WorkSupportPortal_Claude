from __future__ import annotations

from application.asset_inventory.domain.repositories.ports import DEFAULT_PAGE_SIZE, MANAGEMENT_APP_ID, ManagementRow
from application.asset_inventory.domain.value_objects.table_display import DEFAULT_SORT_SPECS, TableDisplayParams
from application.asset_inventory.domain.value_objects.desknet_data import SITE_MASTER_UNAVAILABLE_MESSAGE
from application.asset_inventory.domain.value_objects.errors import DesknetApiError
from application.asset_inventory.domain.value_objects.reconcile_cache import SESSION_KEY, load_reconcile_cache
from application.asset_inventory.domain.value_objects.reconcile_data import load_reconciled_data
from application.asset_inventory.use_cases.list_page import ListPageQuery, ListPage, parse_list_page_query


def _list_page_query(**overrides) -> ListPageQuery:
    table_overrides = overrides.pop("table_params", None)
    params = {
        "management_id": "1",
        "status": "all",
        "site_filter": "all",
        "plate_filter": "all",
        "asset_number_filter": "",
        "table_params": table_overrides
        or TableDisplayParams(sort_specs=DEFAULT_SORT_SPECS, page=1, page_size=DEFAULT_PAGE_SIZE),
    }
    params.update(overrides)
    return ListPageQuery(**params)


MANAGEMENT = [
    {
        "データID": "1",
        "棚卸項目": "2025年",
        "年度": "2025",
        "会社マスタ": "394",
        "拠点マスタ": "395",
        "資産データ": "415",
        "棚卸データ": "408",
    }
]

ASSETS = [
    {
        "データID": "A1",
        "資産番号": "5262",
        "資産枝番": "0001",
        "管理部門名称": "宮崎工場",
        "管理部門コード": "001",
        "メーカー": "M",
        "管理者名称": "MODEL",
        "型番": "SN",
        "旧資産番号コード": "OLD",
        "使用区分": "使用",
        "摘要": "A",
        "生産品番⑧コード": "1",
    },
    {
        "データID": "A2",
        "資産番号": "1",
        "資産枝番": "0000",
        "管理部門名称": "本社",
        "管理部門コード": "002",
        "メーカー": "M2",
        "管理者名称": "M2",
        "型番": "SN2",
        "旧資産番号コード": "",
        "使用区分": "使用",
        "摘要": "",
        "生産品番⑧コード": "1",
    },
]

INVENTORY = [
    {
        "データID": "I1",
        "資産番号": "L5262",
        "資産枝番": "0001",
        "管理部門名称": "宮崎工場",
        "管理部門コード": "001",
        "メーカー": "M",
        "管理者名称": "MODEL",
        "型番": "SN",
        "旧資産番号コード": "OLD",
        "使用区分": "使用",
        "摘要": "A",
        "棚卸日時": "2026/01/16 18:46:01",
        "棚卸実施者": "担当",
        "プレート作成": "1",
    },
    {
        "データID": "I2",
        "資産番号": "9999",
        "資産枝番": "0000",
        "管理部門名称": "本社",
        "管理部門コード": "002",
        "メーカー": "X",
        "管理者名称": "X",
        "型番": "X",
        "旧資産番号コード": "",
        "使用区分": "使用",
        "摘要": "",
        "棚卸日時": "2026/01/10 10:00:00",
        "棚卸実施者": "担当",
        "プレート作成": "",
    },
]

SITES = [
    {"データID": "S1", "管理部門コード": "001", "拠点名": "宮崎工場"},
    {"データID": "S2", "管理部門コード": "002", "拠点名": "本社"},
]


def _mock_list_all(access_key: str, app_id: str, fields):
    data = {
        MANAGEMENT_APP_ID: MANAGEMENT,
        "415": ASSETS,
        "408": INVENTORY,
        "395": SITES,
    }
    return data.get(app_id, [])


def test_TC_AIV_UC_001_reconcile_via_usecase():
    usecase = ListPage(_mock_list_all)
    query = _list_page_query()
    result = usecase.execute("key", query)
    assert result.counts.matched == 1
    assert result.counts.asset_only == 1
    assert result.counts.inventory_only == 1


def test_TC_AIV_UC_002_status_filter_matched():
    usecase = ListPage(_mock_list_all)
    query = _list_page_query(status="matched")
    result = usecase.execute("key", query)
    assert all(row.status_label == "棚卸済み" for row in result.filtered_rows)


def test_TC_AIV_UC_004_site_filter():
    usecase = ListPage(_mock_list_all)
    query = _list_page_query(
        site_filter="宮崎工場",
    )
    result = usecase.execute("key", query)
    assert all(row.site_name == "宮崎工場" for row in result.filtered_rows)


def test_TC_AIV_UC_006_parse_list_page_query_site_select():
    query = parse_list_page_query({"site": "宮崎工場", "status": "all"})
    assert query.site_filter == "宮崎工場"
    query_all = parse_list_page_query({})
    assert query_all.site_filter == "all"
    query_legacy = parse_list_page_query({}, ["宮崎工場"])
    assert query_legacy.site_filter == "宮崎工場"
    query_legacy_multi = parse_list_page_query({}, ["宮崎工場", "本社"])
    assert query_legacy_multi.site_filter == "all"


def test_TC_AIV_UC_005_site_options_from_assets():
    usecase = ListPage(_mock_list_all)
    result = usecase.execute("key", _list_page_query())
    assert result.site_options == ("宮崎工場", "本社")


def test_TC_AIV_UC_007_no_management_selected():
    usecase = ListPage(_mock_list_all)
    query = _list_page_query(management_id="")
    result = usecase.execute("key", query)
    assert result.selected_management_id == ""
    assert result.rows == ()
    assert result.management_rows


def test_TC_AIV_UC_003_missing_access_key():
    usecase = ListPage(_mock_list_all)
    query = _list_page_query()
    result = usecase.execute("", query)
    assert result.error_message is not None


RECONCILE_APP_IDS = frozenset({"415", "408", "395"})


def _counting_mock_list_all(base_mock):
    counts = {"reconcile": 0}

    def list_all(access_key: str, app_id: str, fields):
        if app_id in RECONCILE_APP_IDS:
            counts["reconcile"] += 1
        return base_mock(access_key, app_id, fields)

    return list_all, counts


def test_TC_AIV_UC_008_list_page_refetches_on_every_display():
    """一覧表示のたびに desknet's から取得し直す（機能仕様書 §3・§4.1.1 手順7）。"""
    list_all, counts = _counting_mock_list_all(_mock_list_all)
    usecase = ListPage(list_all)
    session: dict = {}
    usecase.execute("key", _list_page_query(), session=session)
    assert counts["reconcile"] == len(RECONCILE_APP_IDS)
    usecase.execute("key", _list_page_query(), session=session)
    assert counts["reconcile"] == len(RECONCILE_APP_IDS) * 2


def test_TC_AIV_UC_008b_list_page_overwrites_snapshot_on_refetch():
    """再取得した突合結果でスナップショットを上書きする（同一 managementId でも上書き）。"""
    list_all, _counts = _counting_mock_list_all(_mock_list_all)
    usecase = ListPage(list_all)
    session: dict = {}
    usecase.execute("key", _list_page_query(management_id="1"), session=session)
    cached = load_reconcile_cache(session)
    assert cached is not None and cached.management_id == "1"
    usecase.execute("key", _list_page_query(management_id="1"), session=session)
    refreshed = load_reconcile_cache(session)
    assert refreshed is not None and refreshed.management_id == "1"
    assert len(refreshed.rows) == len(cached.rows)


def test_TC_AIV_UC_009_session_cache_refetches_on_management_change():
    management_two = [
        *MANAGEMENT,
        {
            "データID": "2",
            "棚卸項目": "2024年",
            "年度": "2024",
            "会社マスタ": "394",
            "拠点マスタ": "395",
            "資産データ": "415",
            "棚卸データ": "408",
        },
    ]

    def list_all(access_key: str, app_id: str, fields):
        if app_id == MANAGEMENT_APP_ID:
            return management_two
        return _mock_list_all(access_key, app_id, fields)

    list_all_counting, counts = _counting_mock_list_all(list_all)
    usecase = ListPage(list_all_counting)
    session: dict = {}
    usecase.execute("key", _list_page_query(management_id="1"), session=session)
    assert counts["reconcile"] == len(RECONCILE_APP_IDS)
    usecase.execute("key", _list_page_query(management_id="2"), session=session)
    assert counts["reconcile"] == len(RECONCILE_APP_IDS) * 2


def test_TC_AIV_UC_010_session_cache_cleared_when_management_unselected():
    from application.asset_inventory.domain.value_objects.reconcile_cache import SESSION_KEY

    list_all, _counts = _counting_mock_list_all(_mock_list_all)
    usecase = ListPage(list_all)
    session: dict = {}
    usecase.execute("key", _list_page_query(), session=session)
    assert SESSION_KEY in session
    usecase.execute("key", _list_page_query(management_id=""), session=session)
    assert SESSION_KEY not in session


def _list_all_site_master_down(access_key: str, app_id: str, fields):
    # 拠点マスタ（395）だけが desknet's API 障害となる状況を再現する
    if app_id == "395":
        raise DesknetApiError("desknet's API に接続できませんでした。")
    return _mock_list_all(access_key, app_id, fields)


def test_TC_AIV_UC_030_site_master_failure_keeps_list_with_warning():
    """拠点マスタのみ失敗しても一覧を表示し、警告を併記する（機能仕様書 §7.4.1）。"""
    usecase = ListPage(_list_all_site_master_down)
    result = usecase.execute("key", _list_page_query())

    assert result.error_message is None
    assert result.warning_message == SITE_MASTER_UNAVAILABLE_MESSAGE
    assert result.counts.matched == 1
    assert result.counts.asset_only == 1
    assert result.counts.inventory_only == 1


def test_TC_AIV_UC_031_site_master_failure_keeps_site_filter_options():
    """拠点フィルタ候補・拠点名は資産データ由来のため縮退しない（機能仕様書 §7.4.1）。"""
    usecase = ListPage(_list_all_site_master_down)
    result = usecase.execute("key", _list_page_query())

    assert result.site_options == ("宮崎工場", "本社")
    assert any(row.site_name for row in result.filtered_rows)


SELECTED_MANAGEMENT = ManagementRow(
    data_id="1",
    inventory_name="2025年",
    fiscal_year="2025",
    company_app_id="394",
    site_app_id="395",
    asset_app_id="415",
    inventory_app_id="408",
)


def test_TC_AIV_UC_032_site_master_failure_is_saved_but_not_reused_from_snapshot():
    """縮退した突合結果も保存するが、スナップショット利用の経路では採用せず再取得する（DD-02）。"""
    session: dict = {}
    ListPage(_list_all_site_master_down).execute("key", _list_page_query(), session=session)
    assert SESSION_KEY in session

    # スナップショットを使う経路でも縮退結果は採用せず、復旧後は警告なしの結果へ更新される
    reconciled, site_warning = load_reconciled_data(
        _mock_list_all, "key", SELECTED_MANAGEMENT, session=session, use_snapshot=True
    )
    assert site_warning == ""
    assert reconciled.site_warning is False

    recovered = ListPage(_mock_list_all).execute("key", _list_page_query(), session=session)
    assert recovered.warning_message is None
    assert SESSION_KEY in session


def test_TC_AIV_DOM_07L_degraded_result_is_saved_with_site_warning():
    """拠点マスタ取得失敗の突合結果も `site_warning=True` で保存されること（対応 DD-02）。"""
    session: dict = {}
    ListPage(_list_all_site_master_down).execute("key", _list_page_query(), session=session)

    snapshot = load_reconcile_cache(session)
    assert snapshot is not None
    assert snapshot.site_warning is True


def test_TC_AIV_UC_033_asset_master_failure_returns_error():
    """資産データの失敗は突合が成立しないためエラーとする（機能仕様書 §7.4.1）。"""

    def list_all(access_key: str, app_id: str, fields):
        if app_id == "415":
            raise DesknetApiError("desknet's API に接続できませんでした。")
        return _mock_list_all(access_key, app_id, fields)

    result = ListPage(list_all).execute("key", _list_page_query())
    assert result.error_message == "desknet's API に接続できませんでした。"
    assert result.warning_message is None
    assert result.filtered_rows == ()

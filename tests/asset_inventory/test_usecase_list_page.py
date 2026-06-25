from __future__ import annotations

from apps.asset_inventory.domain.ports import DEFAULT_PAGE_SIZE, MANAGEMENT_APP_ID
from apps.asset_inventory.domain.table_display import DEFAULT_SORT_SPECS, TableDisplayParams
from apps.asset_inventory.usecase.usecase_list_page import ListPageQuery, ListPageUsecase, parse_list_page_query


def _list_page_query(**overrides) -> ListPageQuery:
    table_overrides = overrides.pop("table_params", None)
    params = {
        "management_id": "1",
        "status": "all",
        "site_filter": "all",
        "plate_filter": "all",
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
    usecase = ListPageUsecase(_mock_list_all)
    query = _list_page_query()
    result = usecase.execute("key", query)
    assert result.counts.matched == 1
    assert result.counts.asset_only == 1
    assert result.counts.inventory_only == 1


def test_TC_AIV_UC_002_status_filter_matched():
    usecase = ListPageUsecase(_mock_list_all)
    query = _list_page_query(status="matched")
    result = usecase.execute("key", query)
    assert all(row.status_label == "棚卸済み" for row in result.filtered_rows)


def test_TC_AIV_UC_004_site_filter():
    usecase = ListPageUsecase(_mock_list_all)
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
    usecase = ListPageUsecase(_mock_list_all)
    result = usecase.execute("key", _list_page_query())
    assert result.site_options == ("宮崎工場", "本社")


def test_TC_AIV_UC_007_no_management_selected():
    usecase = ListPageUsecase(_mock_list_all)
    query = _list_page_query(management_id="")
    result = usecase.execute("key", query)
    assert result.selected_management_id == ""
    assert result.rows == ()
    assert result.management_rows


def test_TC_AIV_UC_003_missing_access_key():
    usecase = ListPageUsecase(_mock_list_all)
    query = _list_page_query()
    result = usecase.execute("", query)
    assert result.error_message is not None

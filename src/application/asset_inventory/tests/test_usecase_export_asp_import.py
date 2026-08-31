from __future__ import annotations

from application.asset_inventory.domain.repositories.ports import MANAGEMENT_APP_ID
from application.asset_inventory.domain.value_objects.asp_import import (
    ASP_COLUMN_COUNT,
    EMPTY_MESSAGE,
    SITE_UNAVAILABLE_MESSAGE,
    UNAVAILABLE_MESSAGE,
)
from application.asset_inventory.domain.value_objects.errors import DesknetApiError
from application.asset_inventory.domain.value_objects.reconcile_cache import SESSION_KEY
from application.asset_inventory.use_cases.export_asp_import import AspImportStatus, ExportAspImport
from application.asset_inventory.use_cases.list_page import ListPage

from .test_usecase_list_page import (
    MANAGEMENT,
    RECONCILE_APP_IDS,
    SITES,
    _counting_mock_list_all,
    _list_page_query,
    _mock_list_all,
)

# 資産データ側（台帳）
DIFF_ASSETS = [
    {
        "データID": "A1",
        "資産番号": "5262",
        "資産枝番": "0001",
        "管理部門名称": "宮崎工場",
        "管理部門コード": "001",
        "メーカー": "M",
        "メーカーコード": "MK-OLD",
        "管理者名称": "MODEL",
        "管理者コード": "MGR-OLD",
        "型番": "SN-OLD",
        "旧資産番号コード": "OLD",
        "使用区分": "使用",
        "使用区分コード": "U-OLD",
        "摘要": "旧摘要",
        "生産品番⑧コード": "1",
    },
    {
        "データID": "A2",
        "資産番号": "7000",
        "資産枝番": "0002",
        "管理部門名称": "本社",
        "管理部門コード": "002",
        "メーカー": "M2",
        "メーカーコード": "MK2",
        "管理者名称": "M2",
        "管理者コード": "MGR2",
        "型番": "SN2",
        "旧資産番号コード": "",
        "使用区分": "使用",
        "使用区分コード": "U2",
        "摘要": "",
        "生産品番⑧コード": "1",
    },
]

# 棚卸データ側。A1 は変化点判定の 7 項目すべてが変化（9 列すべてに値が入る）、A2 は変化なし
DIFF_INVENTORY = [
    {
        "データID": "I1",
        "資産番号": "5262",
        "資産枝番": "0001",
        "管理部門名称": "本社",
        "管理部門コード": "002",
        "メーカー": "M-NEW",
        "メーカーコード": "MK1",
        "管理者名称": "MODEL-NEW",
        "管理者コード": "MGR1",
        "型番": "SN-NEW",
        "旧資産番号コード": "OLD1",
        "使用区分": "貸与",
        "使用区分コード": "U1",
        "摘要": "新摘要",
        "棚卸日時": "2026/01/16 18:46:01",
        "棚卸実施者": "担当",
        "プレート作成": "1",
    },
    {
        "データID": "I2",
        "資産番号": "7000",
        "資産枝番": "0002",
        "管理部門名称": "本社",
        "管理部門コード": "002",
        "メーカー": "M2",
        "メーカーコード": "MK2",
        "管理者名称": "M2",
        "管理者コード": "MGR2",
        "型番": "SN2",
        "旧資産番号コード": "",
        "使用区分": "使用",
        "使用区分コード": "U2",
        "摘要": "",
        "棚卸日時": "2026/01/10 10:00:00",
        "棚卸実施者": "担当",
        "プレート作成": "",
    },
]


def _diff_list_all(access_key: str, app_id: str, fields):
    data = {
        MANAGEMENT_APP_ID: MANAGEMENT,
        "415": DIFF_ASSETS,
        "408": DIFF_INVENTORY,
        "395": SITES,
    }
    return data.get(app_id, [])


def _diff_list_all_site_master_down(access_key: str, app_id: str, fields):
    """拠点マスタ（395）だけが desknet's API 障害となる状況を再現する。"""
    if app_id == "395":
        raise DesknetApiError("desknet's API に接続できませんでした。")
    return _diff_list_all(access_key, app_id, fields)


def _with_inventory(inventory):
    """棚卸データだけを差し替えたゲートウェイを返す。"""

    def list_all(access_key: str, app_id: str, fields):
        if app_id == "408":
            return inventory
        return _diff_list_all(access_key, app_id, fields)

    return list_all


def _snapshot_session(list_all, **overrides) -> dict:
    """一覧表示を 1 回実行して突合結果スナップショットを作ったセッションを返す。"""
    session: dict = {}
    ListPage(list_all).execute("key", _list_page_query(**overrides), session=session)
    return session


def _csv_lines(content: bytes) -> list[str]:
    """CSV 本文を行に分解する（末尾の空要素は除く）。"""
    return content.decode("utf-8-sig").split("\r\n")[:-1]


SESSION_BROKEN = {SESSION_KEY: {"management_id": "1", "rows": "壊れたデータ"}}


def test_TC_AIV_UC_040_outputs_only_amended_rows():
    """変化点のある棚卸済み行だけを 75 列で出力する（REQ-F-002・REQ-F-003）。"""
    result = ExportAspImport().execute(_list_page_query(), _snapshot_session(_diff_list_all))

    assert result.status == AspImportStatus.OK
    assert result.content is not None
    assert result.row_count == 1
    lines = _csv_lines(result.content)
    assert len(lines) == 1
    columns = lines[0].split(",")
    assert len(columns) == ASP_COLUMN_COUNT
    # 資産番号・資産枝番は常に、残り 7 列は差異があるため出力される
    assert columns[0] == "5262"
    assert columns[1] == "0001"
    assert columns[2] == "002"
    assert columns[15] == "SN-NEW"
    assert columns[37] == "新摘要"
    assert columns[43] == "MGR1"  # 44 列目 管理者コード（判定は画面の「型番」）
    assert columns[58] == "U1"  # 59 列目 抽出コード１３（使用区分コード）
    assert columns[63] == "MK1"  # 64 列目 抽出コード１８（メーカーコード）
    assert columns[64] == "OLD1"  # 65 列目 抽出コード１９（旧資産番号コード）
    assert columns[5] == ""  # 6 列目 取得日付は常に空欄（D-12）


def test_TC_AIV_UC_041_ignores_screen_filters():
    """画面のフィルタ状態に依存せず全行を対象とする（REQ-F-002・C-08）。"""
    session = _snapshot_session(_diff_list_all)
    usecase = ExportAspImport()

    plain = usecase.execute(_list_page_query(), session)
    filtered = usecase.execute(
        _list_page_query(status="inventory_only", site_filter="宮崎工場", asset_number_filter="9999"),
        session,
    )

    assert filtered.row_count == plain.row_count
    assert filtered.content == plain.content


def test_TC_AIV_UC_042_empty_when_no_changes():
    """変化点が 1 件もなければ CSV を返さずメッセージを返す（REQ-F-008・C-07）。"""
    result = ExportAspImport().execute(_list_page_query(), _snapshot_session(_mock_list_all))

    assert result.status == AspImportStatus.EMPTY
    assert result.content is None
    assert result.row_count == 0
    assert result.message == EMPTY_MESSAGE


def test_TC_AIV_UC_043_uses_session_snapshot():
    """取り込み用データの作成では desknet's API を呼ばない（REQ-NF-003・C-09）。"""
    list_all, counts = _counting_mock_list_all(_diff_list_all)
    session: dict = {}
    ListPage(list_all).execute("key", _list_page_query(), session=session)
    assert counts["reconcile"] == len(RECONCILE_APP_IDS)

    result = ExportAspImport().execute(_list_page_query(), session)

    assert result.status == AspImportStatus.OK
    assert counts["reconcile"] == len(RECONCILE_APP_IDS)


def test_TC_AIV_UC_044_no_management_selected():
    """棚卸未選択なら出力せず選び直しを促す（REQ-F-009・C-16）。"""
    result = ExportAspImport().execute(
        _list_page_query(management_id=""), _snapshot_session(_diff_list_all)
    )

    assert result.status == AspImportStatus.UNAVAILABLE
    assert result.content is None
    assert result.message == UNAVAILABLE_MESSAGE


def test_TC_AIV_UC_046_survives_site_master_failure():
    """拠点マスタ縮退のスナップショットでも出力を中止しない（REQ-F-009・DD-02）。"""
    result = ExportAspImport().execute(
        _list_page_query(), _snapshot_session(_diff_list_all_site_master_down)
    )

    assert result.status == AspImportStatus.OK
    assert result.content is not None
    assert SITE_UNAVAILABLE_MESSAGE in result.warning_message


def test_TC_AIV_UC_047_reports_check_violations():
    """チェック仕様違反があっても出力し、警告を返す（REQ-F-007・C-10）。"""
    long_summary = [{**DIFF_INVENTORY[0], "摘要": "あ" * 40}, DIFF_INVENTORY[1]]

    result = ExportAspImport().execute(
        _list_page_query(), _snapshot_session(_with_inventory(long_summary))
    )

    assert result.status == AspImportStatus.OK
    assert result.content is not None
    assert result.warning_message
    assert "5262" in result.warning_message


def test_TC_AIV_UC_048_no_snapshot_does_not_call_desknet():
    """スナップショットが無いときは出力せず desknet's も呼ばない（REQ-F-009・REQ-NF-003）。"""
    _list_all, counts = _counting_mock_list_all(_diff_list_all)

    result = ExportAspImport().execute(_list_page_query(), {})

    assert result.status == AspImportStatus.UNAVAILABLE
    assert result.message == UNAVAILABLE_MESSAGE
    # ユースケースは desknet's ゲートウェイを受け取らないため、呼び出しは発生しない（DD-01）
    assert counts["reconcile"] == 0


def test_TC_AIV_UC_049_snapshot_of_another_inventory_is_not_used():
    """スナップショットの棚卸が要求と異なるときは出力しない（REQ-F-009）。"""
    session = _snapshot_session(_diff_list_all, management_id="1")

    result = ExportAspImport().execute(_list_page_query(management_id="2"), session)

    assert result.status == AspImportStatus.UNAVAILABLE
    assert result.content is None


def test_TC_AIV_UC_050_usecase_needs_no_desknet_gateway():
    """ユースケースは desknet's ゲートウェイを受け取らずに生成・実行できる（DD-01）。"""
    usecase = ExportAspImport()

    result = usecase.execute(_list_page_query(), _snapshot_session(_diff_list_all))

    assert result.status == AspImportStatus.OK


def test_TC_AIV_UC_051_repeated_execution_is_idempotent():
    """同じスナップショットから繰り返し作成しても内容が変わらない（REQ-NF-005・C-17）。"""
    session = _snapshot_session(_diff_list_all)
    usecase = ExportAspImport()

    first = usecase.execute(_list_page_query(), session)
    second = usecase.execute(_list_page_query(), session)

    assert first.content == second.content
    assert first.row_count == second.row_count


def test_TC_AIV_UC_052_row_count_matches_the_number_of_amendment_rows():
    """出力行数が修正対象行数と一致する（REQ-F-002）。"""
    inventory = [
        {**DIFF_INVENTORY[0], "摘要": "新摘要1"},
        {**DIFF_INVENTORY[1], "型番": "SN2-NEW"},
        {
            **DIFF_INVENTORY[0],
            "データID": "I3",
            "資産番号": "8000",
            "資産枝番": "0003",
            "摘要": "新摘要3",
        },
    ]
    assets = [
        *DIFF_ASSETS,
        {**DIFF_ASSETS[0], "データID": "A3", "資産番号": "8000", "資産枝番": "0003"},
    ]

    def list_all(access_key: str, app_id: str, fields):
        if app_id == "408":
            return inventory
        if app_id == "415":
            return assets
        return _diff_list_all(access_key, app_id, fields)

    result = ExportAspImport().execute(_list_page_query(), _snapshot_session(list_all))

    assert result.row_count == 3
    assert result.content is not None
    assert len(_csv_lines(result.content)) == 3


def test_TC_AIV_UC_053_broken_session_does_not_raise():
    """セッションが壊れていても例外を送出せず選び直しを促す（REQ-F-009）。"""
    result = ExportAspImport().execute(_list_page_query(), SESSION_BROKEN)

    assert result.status == AspImportStatus.UNAVAILABLE
    assert result.message == UNAVAILABLE_MESSAGE


def test_TC_AIV_UC_054_newline_in_summary_is_replaced_and_warned():
    """摘要の改行は置換して出力し、警告に該当資産番号を含める（REQ-F-006・C-15）。"""
    inventory = [{**DIFF_INVENTORY[0], "摘要": "1行目\r\n2行目"}, DIFF_INVENTORY[1]]

    result = ExportAspImport().execute(
        _list_page_query(), _snapshot_session(_with_inventory(inventory))
    )

    assert result.content is not None
    lines = _csv_lines(result.content)
    assert len(lines) == 1
    assert lines[0].split(",")[37] == "1行目 2行目"
    assert "5262" in result.warning_message

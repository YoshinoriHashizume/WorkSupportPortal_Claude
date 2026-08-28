from __future__ import annotations

import dataclasses

import pytest
from django.contrib.auth import get_user_model
from django.contrib.auth.models import Group

from application.asset_inventory.domain.value_objects.table_display import DEFAULT_SORT_SPECS
from application.asset_inventory.domain.repositories.ports import (
    ListPageResult,
    ManagementRow,
    MatchStatus,
    ReconcileCounts,
    ReconcileRow,
    RowTone,
)
from application.asset_inventory.domain.value_objects.reconcile_cache import (
    ReconcileCache,
    save_reconcile_cache,
)
from application.asset_inventory.domain.value_objects.row_detail import FieldComparisonItem
from application.portal.models import PortalMenuGroupAccess, UserAccessRequest


@pytest.fixture
def general_affairs_user(db):
    user = get_user_model().objects.create_user(username="10003", last_name="総務", first_name="担当")
    general_group, _ = Group.objects.get_or_create(name="一般ユーザー")
    user.groups.add(general_group)
    PortalMenuGroupAccess.objects.get_or_create(user=user, group_key="general-affairs")
    access_request, _ = UserAccessRequest.objects.get_or_create(user=user)
    access_request.status = UserAccessRequest.Status.APPROVED
    access_request.save()
    return user


@pytest.fixture
def production_only_user(db):
    user = get_user_model().objects.create_user(username="10002", last_name="生産", first_name="担当")
    PortalMenuGroupAccess.objects.get_or_create(user=user, group_key="production")
    access_request, _ = UserAccessRequest.objects.get_or_create(user=user)
    access_request.status = UserAccessRequest.Status.APPROVED
    access_request.save()
    return user


def _sample_list_result() -> ListPageResult:
    row = ReconcileRow(
        match_status=MatchStatus.MATCHED,
        row_tone=RowTone.MATCH_CLEAN,
        status_label="棚卸済み",
        tone_label="一致",
        asset_number="1",
        branch_number="0",
        site_name="宮崎工場",
        manufacturer="",
        model_name="",
        serial_number="",
        old_asset_number="",
        usage_category="",
        summary="",
        plate_created="",
        inventory_operator="",
        inventory_datetime="",
    )
    counts = ReconcileCounts(matched=1)
    return ListPageResult(
        management_rows=(ManagementRow("1", "2025年", "2025", "", "", "415", "408"),),
        selected_management_id="1",
        rows=(row,),
        all_rows=(row,),
        filtered_rows=(row,),
        counts=counts,
        filtered_counts=counts,
        site_options=(),
        site_filter="all",
        status_filter="all",
        plate_filter="all",
        asset_number_filter="",
        asset_number_options=(),
        page=1,
        page_size=50,
        total_pages=1,
        sort_specs=DEFAULT_SORT_SPECS,
        start_index=1,
        end_index=1,
        has_previous=False,
        has_next=False,
    )


@pytest.mark.django_db
def test_TC_AIV_API_001_unauthenticated_redirects(client):
    response = client.get("/app/general-affairs/asset-inventory")
    assert response.status_code == 302
    assert "/login" in response.url


@pytest.mark.django_db
def test_TC_AIV_API_002_production_user_forbidden(client, production_only_user):
    client.force_login(production_only_user)
    response = client.get("/app/general-affairs/asset-inventory")
    assert response.status_code == 403


def _unselected_list_result() -> ListPageResult:
    return ListPageResult(
        management_rows=(ManagementRow("1", "2025年", "2025", "", "", "415", "408"),),
        selected_management_id="",
        rows=(),
        all_rows=(),
        filtered_rows=(),
        counts=ReconcileCounts(),
        filtered_counts=ReconcileCounts(),
        site_options=(),
        site_filter="all",
        status_filter="all",
        plate_filter="all",
        asset_number_filter="",
        asset_number_options=(),
        page=1,
        page_size=50,
        total_pages=1,
        sort_specs=DEFAULT_SORT_SPECS,
    )


@pytest.mark.django_db
def test_TC_AIV_API_007_unselected_shows_results_panel(client, general_affairs_user, monkeypatch):
    client.force_login(general_affairs_user)
    session = client.session
    session["desknet_access_key"] = "test-key"
    session.save()

    monkeypatch.setattr(
        "application.asset_inventory.interfaces.views.list_page_usecase",
        lambda: type(
            "U",
            (),
            {"execute": lambda self, access_key, query, session=None: _unselected_list_result()},
        )(),
    )

    response = client.get("/app/general-affairs/asset-inventory")
    assert response.status_code == 200
    html = response.content.decode("utf-8")
    assert "棚卸結果" in html
    assert 'class="favorite-empty"' in html
    assert "棚卸を選択してください。" in html
    assert "aiv-results-card" in html
    assert "receipt-results-card" in html


@pytest.mark.django_db
def test_TC_AIV_API_003_general_affairs_user_ok(client, general_affairs_user, monkeypatch):
    client.force_login(general_affairs_user)
    session = client.session
    session["desknet_access_key"] = "test-key"
    session.save()

    monkeypatch.setattr(
        "application.asset_inventory.interfaces.views.list_page_usecase",
        lambda: type(
            "U",
            (),
            {"execute": lambda self, access_key, query, session=None: _sample_list_result()},
        )(),
    )

    response = client.get("/app/general-affairs/asset-inventory")
    assert response.status_code == 200
    html = response.content.decode("utf-8")
    assert "資産棚卸結果" in html
    assert 'class="aiv-filter-field-label"' in html
    assert "変化状況" in html
    assert "突合結果" not in html
    assert 'class="portal-filter-select' in html
    assert "生産品番⑧コードが 1" not in html
    assert "表示件数" in html
    assert "aiv-page-size-select" in html
    assert "棚卸の色分け" in html
    assert "<label>棚卸" in html
    assert "2025年度" in html
    assert "資産台帳と棚卸データを突合し、棚卸結果を表示します。" in html
    assert 'class="portal-page-description"' in html
    assert 'id="aiv-row-color-dialog"' in html
    assert 'id="aiv-row-detail-dialog"' in html
    assert 'id="aiv-photo-zoom-dialog"' in html
    assert 'class="aiv-photo-zoom-image"' in html
    assert 'class="aiv-row-detail-compare-col-label"' in html
    assert 'class="aiv-row-detail-compare-col-asset"' in html
    assert 'class="aiv-row-detail-compare-col-inventory"' in html
    import json
    import re

    script_match = re.search(
        r'<script id="aiv-list-data" type="application/json">(.*?)</script>',
        html,
        re.DOTALL,
    )
    assert script_match is not None
    payload = json.loads(script_match.group(1))
    assert isinstance(payload, dict)
    assert payload.get("managementId") == "1"
    assert "rowDetails" in payload
    assert "棚卸結果" in html and "差異" in html and "行の色" in html
    assert "緑: 一致" not in html
    assert "aiv-sort-priority" in html
    assert "プレート作成" in html
    assert '<select name="site"' in html
    assert 'name="assetNumber"' in html
    assert 'list="aiv-asset-number-options"' in html
    assert 'portal-list-prefix-filter.js' in html
    assert "aiv-filter-asset-number" in html
    assert 'id="aiv-list-data"' in html
    assert 'onchange="this.form.submit()"' not in html.split("aiv-filter-panel")[1].split("aiv-table-toolbar")[0]


@pytest.mark.django_db
def test_TC_AIV_API_010_list_client_payload_embedded(client, general_affairs_user, monkeypatch):
    client.force_login(general_affairs_user)
    session = client.session
    session["desknet_access_key"] = "test-key"
    session.save()

    monkeypatch.setattr(
        "application.asset_inventory.interfaces.views.list_page_usecase",
        lambda: type(
            "U",
            (),
            {"execute": lambda self, access_key, query, session=None: _sample_list_result()},
        )(),
    )

    response = client.get("/app/general-affairs/asset-inventory?managementId=1")
    assert response.status_code == 200
    html = response.content.decode("utf-8")
    assert 'id="aiv-list-data"' in html
    assert "exportCsvPath" in html
    assert "rowDetails" in html


@pytest.mark.django_db
def test_TC_AIV_API_004_export_csv_bom(client, general_affairs_user, monkeypatch):
    from application.asset_inventory.domain.value_objects.csv_export import render_export_csv
    from application.asset_inventory.domain.repositories.ports import MatchStatus, ReconcileRow, RowTone

    row = ReconcileRow(
        match_status=MatchStatus.MATCHED,
        row_tone=RowTone.MATCH_CLEAN,
        status_label="棚卸済み",
        tone_label="一致",
        asset_number="1",
        branch_number="0",
        site_name="宮崎工場",
        manufacturer="",
        model_name="",
        serial_number="",
        old_asset_number="",
        usage_category="",
        summary="",
        plate_created="",
        inventory_operator="",
        inventory_datetime="",
    )
    client.force_login(general_affairs_user)
    session = client.session
    session["desknet_access_key"] = "test-key"
    session.save()

    monkeypatch.setattr(
        "application.asset_inventory.interfaces.views.export_csv_usecase",
        lambda: type(
            "U",
            (),
            {
                "execute_safe": lambda self, access_key, query, session=None: (
                    render_export_csv((row,)),
                    None,
                )
            },
        )(),
    )

    response = client.get("/api/asset-inventory/export.csv")
    assert response.status_code == 200
    assert response["Content-Type"].startswith("text/csv")
    assert response.content.startswith(b"\xef\xbb\xbf")


def _amendment_row(asset_number: str = "5262", summary: str = "新摘要") -> ReconcileRow:
    """摘要に変化点のある棚卸済み行（修正対象行）を組み立てる。"""
    return ReconcileRow(
        match_status=MatchStatus.MATCHED,
        row_tone=RowTone.MATCH_DIFF,
        status_label="一致",
        tone_label="変化あり",
        asset_number=asset_number,
        branch_number="0001",
        site_name="本社",
        manufacturer="M",
        model_name="MODEL",
        serial_number="SN-NEW",
        old_asset_number="OLD",
        usage_category="使用",
        summary=summary,
        plate_created="",
        inventory_operator="担当",
        inventory_datetime="2026/01/16 18:46:01",
        site_code="002",
        has_diff=True,
        field_comparisons=(
            FieldComparisonItem(
                label="摘要", asset_value="旧摘要", inventory_value=summary, is_diff=True
            ),
        ),
    )


def _matched_row() -> ReconcileRow:
    """変化点のない棚卸済み行（修正対象外）を組み立てる。"""
    row = _amendment_row(asset_number="7000", summary="")
    return dataclasses.replace(row, row_tone=RowTone.MATCH_CLEAN, has_diff=False, field_comparisons=())


def _save_snapshot(client, rows, management_id: str = "1") -> None:
    """突合結果スナップショットをセッションへ保存する（REQ-NF-003）。"""
    session = client.session
    session["desknet_access_key"] = "test-key"
    save_reconcile_cache(
        session,
        ReconcileCache(
            management_id=management_id,
            rows=tuple(rows),
            counts=ReconcileCounts(matched=len(rows)),
            site_options=("本社",),
            asset_number_options=tuple(row.asset_number for row in rows),
        ),
    )
    session.save()


def _stub_list_page(monkeypatch, result) -> None:
    """一覧ユースケースを差し替える。"""
    monkeypatch.setattr(
        "application.asset_inventory.interfaces.views.list_page_usecase",
        lambda: type(
            "U",
            (),
            {"execute": lambda self, access_key, query, session=None: result},
        )(),
    )


def _asp_import_button_tag(html: str) -> str:
    """描画された「取り込み用データの作成」ボタンの開始タグを取り出す。"""
    return html.split("aiv-asp-import-button")[1].split(">")[0]


@pytest.mark.django_db
def test_TC_AIV_API_011_asp_import_unauthenticated_redirects(client):
    """未ログインはログイン画面へ誘導する（REQ-NF-001）。"""
    response = client.get("/api/asset-inventory/asp-import.csv")
    assert response.status_code == 302
    assert "/login" in response.url


@pytest.mark.django_db
def test_TC_AIV_API_012_asp_import_downloads_csv(client, general_affairs_user):
    """総務メニューグループの利用者は取り込み用データをダウンロードできる（REQ-F-005）。"""
    client.force_login(general_affairs_user)
    _save_snapshot(client, [_amendment_row()])

    response = client.get("/api/asset-inventory/asp-import.csv?managementId=1")

    assert response.status_code == 200
    assert response["Content-Type"].startswith("text/csv")
    assert response["X-Asp-Import-Status"] == "ok"
    assert "X-Asp-Import-Warning" not in response
    assert "attachment; filename=\"asp_import_" in response["Content-Disposition"]
    assert response.content.startswith(b"\xef\xbb\xbf")
    assert response.content.decode("utf-8-sig").split("\r\n")[0].split(",")[:2] == ["5262", "0001"]


@pytest.mark.django_db
def test_TC_AIV_API_013_asp_import_empty_is_not_downloaded(client, general_affairs_user):
    """変化点が無いときはダウンロードさせずメッセージを返す（REQ-F-008・C-07）。"""
    from application.asset_inventory.domain.value_objects.asp_import import EMPTY_MESSAGE

    client.force_login(general_affairs_user)
    _save_snapshot(client, [_matched_row()])

    response = client.get("/api/asset-inventory/asp-import.csv?managementId=1")

    assert response.status_code == 200
    assert response["X-Asp-Import-Status"] == "empty"
    assert "Content-Disposition" not in response
    assert response.content.decode("utf-8") == EMPTY_MESSAGE


@pytest.mark.django_db
def test_TC_AIV_API_014_asp_import_warning_header_is_url_encoded(client, general_affairs_user):
    """チェック仕様違反があっても出力し、警告をヘッダーで返す（REQ-F-007・C-10）。"""
    from urllib.parse import unquote

    client.force_login(general_affairs_user)
    _save_snapshot(client, [_amendment_row(summary="あ" * 40)])

    response = client.get("/api/asset-inventory/asp-import.csv?managementId=1")

    assert response.status_code == 200
    assert response["X-Asp-Import-Status"] == "ok"
    warning = unquote(response["X-Asp-Import-Warning"])
    assert "5262-0001" in warning


@pytest.mark.django_db
def test_TC_AIV_API_015b_asp_import_without_snapshot_asks_to_reselect(client, general_affairs_user):
    """スナップショットが無いときは棚卸の選び直しを促す（REQ-F-009・C-16）。"""
    from application.asset_inventory.domain.value_objects.asp_import import UNAVAILABLE_MESSAGE

    client.force_login(general_affairs_user)
    session = client.session
    session["desknet_access_key"] = "test-key"
    session.save()

    response = client.get("/api/asset-inventory/asp-import.csv?managementId=1")

    assert response.status_code == 200
    assert response["X-Asp-Import-Status"] == "unavailable"
    assert "Content-Disposition" not in response
    assert response.content.decode("utf-8") == UNAVAILABLE_MESSAGE


@pytest.mark.django_db
def test_TC_AIV_API_016_asp_import_button_is_enabled_while_results_are_shown(
    client, general_affairs_user, monkeypatch
):
    """突合結果を表示している間はボタンを活性で描画する（REQ-F-001・DD-05）。"""
    client.force_login(general_affairs_user)
    _save_snapshot(client, [_amendment_row()])
    _stub_list_page(monkeypatch, _sample_list_result())

    response = client.get("/app/general-affairs/asset-inventory")
    html = response.content.decode("utf-8")

    assert "取り込み用データの作成" in html
    assert "aiv-asp-import-message" in html
    assert 'data-asp-import-url="/api/asset-inventory/asp-import.csv?managementId=1"' in html
    button = _asp_import_button_tag(html)
    assert "disabled" not in button
    # 既存の CSV 出力ボタンと同じツールバー内にある
    toolbar = html.split("aiv-results-head-actions")[1].split("</div>")[0]
    assert "aiv-export-csv-link" in toolbar and "aiv-asp-import-button" in toolbar


@pytest.mark.django_db
def test_TC_AIV_API_017_asp_import_button_is_disabled_when_no_inventory_selected(
    client, general_affairs_user, monkeypatch
):
    """棚卸未選択でもボタンは描画し、非活性にする（REQ-F-001・D-09）。"""
    client.force_login(general_affairs_user)
    session = client.session
    session["desknet_access_key"] = "test-key"
    session.save()
    _stub_list_page(monkeypatch, _unselected_list_result())

    response = client.get("/app/general-affairs/asset-inventory")
    html = response.content.decode("utf-8")

    assert "aiv-asp-import-button" in html
    button = _asp_import_button_tag(html)
    assert "disabled" in button
    assert 'title="棚卸を選ぶと作成できます。"' in button


@pytest.mark.django_db
def test_TC_AIV_API_018_asp_import_button_is_disabled_when_list_failed(
    client, general_affairs_user, monkeypatch
):
    """一覧の取得に失敗しているときはボタンを非活性にする（REQ-F-009・DD-05）。"""
    client.force_login(general_affairs_user)
    _save_snapshot(client, [_amendment_row()])
    _stub_list_page(
        monkeypatch,
        dataclasses.replace(
            _sample_list_result(), error_message="desknet's API に接続できませんでした。"
        ),
    )

    response = client.get("/app/general-affairs/asset-inventory")
    html = response.content.decode("utf-8")

    assert "aiv-asp-import-button" in html
    assert "disabled" in _asp_import_button_tag(html)


@pytest.mark.django_db
def test_TC_AIV_API_019_asp_import_does_not_call_desknet(client, general_affairs_user, monkeypatch):
    """取り込み用データの作成では desknet's API を呼ばない（REQ-NF-003・C-09・DD-01）。"""
    calls = {"factory": 0, "list_all": 0}

    def _counting_list_all_fn():
        calls["factory"] += 1

        def list_all(access_key: str, app_id: str, fields):
            calls["list_all"] += 1
            return []

        return list_all

    monkeypatch.setattr(
        "application.asset_inventory.interfaces.wiring._list_all_fn", _counting_list_all_fn
    )

    client.force_login(general_affairs_user)
    _save_snapshot(client, [_amendment_row()])

    response = client.get("/api/asset-inventory/asp-import.csv?managementId=1")

    assert response.status_code == 200
    assert response["X-Asp-Import-Status"] == "ok"
    assert calls == {"factory": 0, "list_all": 0}


@pytest.mark.django_db
def test_TC_AIV_API_020_asp_import_production_user_forbidden(client, production_only_user):
    """総務メニューグループを持たない利用者は作成できない（REQ-NF-001）。"""
    client.force_login(production_only_user)

    response = client.get("/api/asset-inventory/asp-import.csv?managementId=1")

    assert response.status_code == 403


@pytest.mark.django_db
def test_TC_AIV_API_021_asp_import_reports_row_count(client, general_affairs_user):
    """出力行数をヘッダーで返す（REQ-F-002）。"""
    client.force_login(general_affairs_user)
    rows = [
        _amendment_row(asset_number="5262"),
        _amendment_row(asset_number="7000"),
        _amendment_row(asset_number="8000"),
    ]
    _save_snapshot(client, rows)

    response = client.get("/api/asset-inventory/asp-import.csv?managementId=1")

    assert response["X-Asp-Import-Rows"] == "3"
    assert len(response.content.decode("utf-8-sig").split("\r\n")[:-1]) == 3


@pytest.mark.django_db
def test_TC_AIV_API_022_asp_import_filename_has_timestamp(client, general_affairs_user):
    """ファイル名は asp_import_YYYYMMDDhhmmss.csv 形式とする（REQ-F-005）。"""
    import re

    client.force_login(general_affairs_user)
    _save_snapshot(client, [_amendment_row()])

    response = client.get("/api/asset-inventory/asp-import.csv?managementId=1")

    assert re.fullmatch(
        r'attachment; filename="asp_import_\d{14}\.csv"', response["Content-Disposition"]
    )

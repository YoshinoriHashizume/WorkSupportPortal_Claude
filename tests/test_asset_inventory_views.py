from __future__ import annotations

import pytest
from django.contrib.auth import get_user_model
from django.contrib.auth.models import Group

from apps.asset_inventory.domain.table_display import DEFAULT_SORT_SPECS
from apps.asset_inventory.domain.ports import (
    ListPageResult,
    ManagementRow,
    MatchStatus,
    ReconcileCounts,
    ReconcileRow,
    RowTone,
)
from apps.portal.models import PortalMenuGroupAccess, UserAccessRequest


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
        "apps.asset_inventory.views.list_page_usecase",
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
        "apps.asset_inventory.views.list_page_usecase",
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
        "apps.asset_inventory.views.list_page_usecase",
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
    from apps.asset_inventory.domain.csv_export import render_export_csv
    from apps.asset_inventory.domain.ports import MatchStatus, ReconcileRow, RowTone

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
        "apps.asset_inventory.views.export_csv_usecase",
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

from __future__ import annotations

from pathlib import Path

from django.conf import settings


def _css() -> str:
    return (Path(settings.BASE_DIR) / "static" / "css" / "app.css").read_text(encoding="utf-8")


def test_portal_page_description_css_places_text_beside_favorite():
    source = _css()
    block = source.split(".portal-page-title-row .portal-page-description", 1)[1].split("}", 1)[0]
    assert "margin: 0;" in block
    assert "color: #64748b;" in block
    title_row = source.split(".portal-page-title-row {", 1)[1].split("}", 1)[0]
    assert "flex-wrap: wrap;" in title_row


def test_asset_inventory_page_description_is_beside_favorite():
    html = (Path(settings.BASE_DIR) / "templates" / "asset_inventory" / "list.html").read_text(encoding="utf-8")
    title_row = html.split('class="portal-page-title-row"', 1)[1].split("</div>", 1)[0]
    assert "portal-title-favorite" in title_row
    assert 'class="portal-page-description"' in title_row
    assert "資産台帳と棚卸データを突合し、棚卸結果を表示します。" in title_row
    assert title_row.index("portal-title-favorite") < title_row.index("portal-page-description")


def test_receipt_comparison_page_description_is_beside_favorite():
    html = (Path(settings.BASE_DIR) / "templates" / "receipt_comparison" / "comparison.html").read_text(
        encoding="utf-8",
    )
    title_row = html.split('class="portal-page-title-row"', 1)[1].split("</div>", 1)[0]
    assert "portal-title-favorite" in title_row
    assert 'class="portal-page-description"' in title_row
    assert "取引先受領書と MARI のデータを比較します。" in title_row


def test_gonen_search_page_has_description_beside_favorite():
    html = (Path(settings.BASE_DIR) / "templates" / "gonenkukumi" / "search.html").read_text(encoding="utf-8")
    title_row = html.split('class="portal-page-title-row"', 1)[1].split("</div>", 1)[0]
    assert "portal-title-favorite" in title_row
    assert 'class="portal-page-description"' in title_row
    assert "得意先品目の内示・受注・出荷・仕入・入荷の推移を検索します。" in title_row
    assert title_row.index("portal-title-favorite") < title_row.index("portal-page-description")


def test_inventory_order_alert_page_has_description_beside_favorite():
    html = (Path(settings.BASE_DIR) / "templates" / "inventory_order_alert" / "list.html").read_text(encoding="utf-8")
    title_row = html.split('class="portal-page-title-row"', 1)[1].split("</div>", 1)[0]
    assert "portal-title-favorite" in title_row
    assert 'class="portal-page-description"' in title_row
    assert "SLIMS 在庫と基幹入出荷から、仕入先確認が必要な品目を一覧します。" in title_row


def test_management_pages_use_portal_page_description():
    pages = {
        "portal/user_management.html": "登録済みユーザーの情報、権限、利用可能グループを確認できます。",
        "portal/database.html": "テーブルを選択して、先頭100件を参照できます。",
        "portal/notices.html": "ポータルに表示するお知らせを追加・編集・削除できます。",
        "portal/access_requests.html": "初回ログインしたユーザーの利用可否と権限を設定します。",
    }
    for relative_path, description in pages.items():
        html = (Path(settings.BASE_DIR) / "templates" / relative_path).read_text(encoding="utf-8")
        title_row = html.split('class="portal-page-title-row"', 1)[1].split("</div>", 1)[0]
        assert 'class="portal-page-description"' in title_row
        assert description in title_row
        assert "page_favorite_toggle.html" in title_row

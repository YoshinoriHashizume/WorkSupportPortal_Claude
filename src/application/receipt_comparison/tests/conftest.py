"""検収書比較アプリのテスト用フィクスチャ。

検収書比較は EXPJC 移行に伴い本番で一時的に非表示（menu.py の hidden=True）だが、
このアプリの機能テストは「表示・アクセスできる状態」での動作を検証する。
hidden 自体の挙動（メニュー非表示・URL 直打ち 403）は portal 側
（test_portal_favorites.py）で検証するため、ここでは hidden を一時解除する。
検収書比較を正式に復活させるときは、menu.py の hidden を外し、この conftest を削除する。
"""
from __future__ import annotations

import dataclasses

import pytest

from application.portal.domain.value_objects import menu

_RECEIPT_KEYS = (
    "receipt-comparison",
    "receipt-comparison-finished-product",
    "receipt-comparison-supplied-parts",
)


@pytest.fixture(autouse=True)
def _unhide_receipt_comparison_menu():
    # MENU_ITEMS / MENU_BY_KEY は各モジュールが同一オブジェクトを import 共有しているため、
    # 中身を差し替えれば can_access_menu_item まで一貫して反映される。
    original_items = list(menu.MENU_ITEMS)
    original_by_key = dict(menu.MENU_BY_KEY)
    for key in _RECEIPT_KEYS:
        item = menu.MENU_BY_KEY.get(key)
        if item is not None and item.hidden:
            menu.MENU_BY_KEY[key] = dataclasses.replace(item, hidden=False)
    menu.MENU_ITEMS[:] = [menu.MENU_BY_KEY.get(i.key, i) for i in menu.MENU_ITEMS]
    try:
        yield
    finally:
        menu.MENU_ITEMS[:] = original_items
        menu.MENU_BY_KEY.clear()
        menu.MENU_BY_KEY.update(original_by_key)

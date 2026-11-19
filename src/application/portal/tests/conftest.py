"""portal アプリのテスト用フィクスチャ。"""
from __future__ import annotations

import dataclasses

import pytest

from application.portal.domain.value_objects import menu

_RECEIPT_KEYS = (
    "receipt-comparison",
    "receipt-comparison-finished-product",
    "receipt-comparison-supplied-parts",
)


@pytest.fixture
def unhide_receipt_comparison():
    """検収書比較を一時的に表示状態へ戻す（EXPJC 移行で hidden=True のため）。

    検収書比較ページの機能（検索ディスクロージャ描画・利用ログ記録等）を検証する
    テストだけがこのフィクスチャを受け取る。hidden 自体の挙動は test_portal_favorites.py
    で検証するため autouse にはしない。復活時は menu.py の hidden を外し本フィクスチャを削除する。
    同等のフィクスチャが receipt_comparison/tests/conftest.py にも autouse で置いてある。
    """
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

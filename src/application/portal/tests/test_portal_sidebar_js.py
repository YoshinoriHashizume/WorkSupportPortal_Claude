from __future__ import annotations

from pathlib import Path

from django.conf import settings


JS_PATH = Path(settings.BASE_DIR) / "static" / "js" / "portal-sidebar.js"
BASE_TEMPLATE_PATH = Path(settings.BASE_DIR) / "templates" / "base.html"


def test_portal_sidebar_js_persists_nav_scroll_position():
    source = JS_PATH.read_text(encoding="utf-8")
    assert "portal-sidebar-nav-scroll-top" in source
    assert "sessionStorage.setItem(SCROLL_STORAGE_KEY" in source
    assert "sessionStorage.getItem(SCROLL_STORAGE_KEY)" in source
    assert "bindScrollPersistence" in source
    assert "restoreScrollAfterLayout" in source
    assert "requestAnimationFrame" in source


def test_portal_sidebar_js_saves_scroll_before_sidebar_link_navigation():
    source = JS_PATH.read_text(encoding="utf-8")
    click_block = source.split('nav.addEventListener("click"', 1)[1].split("});", 1)[0]
    assert 'closest("a[href]")' in click_block
    assert "saveScrollPosition(nav)" in click_block


def test_portal_sidebar_js_scrolls_active_item_when_no_saved_position():
    source = JS_PATH.read_text(encoding="utf-8")
    restore_block = source.split("function restoreScrollPosition", 1)[1].split("function restoreScrollAfterLayout", 1)[0]
    assert ".sidebar-menu-item.is-active a" in restore_block
    assert 'scrollIntoView({ block: "nearest" })' in restore_block


def test_base_template_loads_portal_sidebar_js():
    template = BASE_TEMPLATE_PATH.read_text(encoding="utf-8")
    assert "portal-sidebar.js" in template

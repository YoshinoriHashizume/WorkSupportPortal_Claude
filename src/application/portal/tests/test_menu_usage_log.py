from __future__ import annotations

from datetime import datetime, timedelta, timezone

import pytest

from application.portal.domain.entities.menu_usage_log import MenuUsageLog

JST = timezone(timedelta(hours=9))


def test_menu_usage_log_keeps_given_attributes():
    """メニュー利用ログは与えられた5属性をそのまま保持する。"""
    used_at = datetime(2026, 8, 27, 9, 0, tzinfo=JST)

    log = MenuUsageLog(
        log_id=None,
        user_id=7,
        menu_key="shipment-trend-list",
        usage_type="VIEW",
        used_at=used_at,
    )

    assert log.log_id is None
    assert log.user_id == 7
    assert log.menu_key == "shipment-trend-list"
    assert log.usage_type == "VIEW"
    assert log.used_at == used_at


def test_menu_usage_log_accepts_export_usage_type():
    """利用種別が出力の場合も生成できる。"""
    used_at = datetime(2026, 8, 27, 9, 0, tzinfo=JST)

    log = MenuUsageLog(
        log_id=None,
        user_id=7,
        menu_key="shipment-trend-list",
        usage_type="EXPORT",
        used_at=used_at,
    )

    assert log.usage_type == "EXPORT"


@pytest.mark.parametrize("usage_type", ["DOWNLOAD", "", "view", None])
def test_menu_usage_log_rejects_unknown_usage_type(usage_type):
    """利用種別が表示・出力のいずれでもない場合は生成できない。"""
    used_at = datetime(2026, 8, 27, 9, 0, tzinfo=JST)

    with pytest.raises(ValueError):
        MenuUsageLog(
            log_id=None,
            user_id=7,
            menu_key="shipment-trend-list",
            usage_type=usage_type,
            used_at=used_at,
        )


def test_menu_usage_log_allows_none_user_id():
    """利用者が物理削除された後のログとして利用者IDなしでも生成できる。"""
    used_at = datetime(2026, 8, 27, 9, 0, tzinfo=JST)

    log = MenuUsageLog(
        log_id=12,
        user_id=None,
        menu_key="shipment-trend-list",
        usage_type="VIEW",
        used_at=used_at,
    )

    assert log.user_id is None


def test_menu_usage_log_has_no_state_changing_method():
    """メニュー利用ログは追記のみで、状態を変える手段を持たない。"""
    prefixes = ("set_", "update_", "delete_", "remove_")

    changing = [
        name
        for name in dir(MenuUsageLog)
        if name.startswith(prefixes) and callable(getattr(MenuUsageLog, name, None))
    ]

    assert changing == []

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class PortalMenuGroup:
    key: str
    title: str


@dataclass(frozen=True)
class PortalMenuItem:
    key: str
    title: str
    href: str
    group_key: str
    parent_key: str | None = None


MENU_GROUPS = [
    PortalMenuGroup(key="company", title="全社"),
    PortalMenuGroup(key="hr", title="人事"),
    PortalMenuGroup(key="general-affairs", title="総務"),
    PortalMenuGroup(key="finance", title="財務"),
    PortalMenuGroup(key="sales", title="営業"),
    PortalMenuGroup(key="production", title="生産管理"),
    PortalMenuGroup(key="quality", title="品保"),
    PortalMenuGroup(key="management", title="管理"),
]


MENU_ITEMS = [
    PortalMenuItem(
        key="five-year-nine",
        title="5年9組",
        href="/app/production/five-year-nine",
        group_key="production",
    ),
    PortalMenuItem(
        key="receipt-comparison",
        title="検収書比較",
        href="",
        group_key="production",
    ),
    PortalMenuItem(
        key="receipt-comparison-finished-product",
        title="完成品",
        href="/app/production/receipt-comparison?type=finished-product",
        group_key="production",
        parent_key="receipt-comparison",
    ),
    PortalMenuItem(
        key="receipt-comparison-supplied-parts",
        title="支給品",
        href="/app/production/receipt-comparison?type=supplied-parts",
        group_key="production",
        parent_key="receipt-comparison",
    ),
    PortalMenuItem(
        key="inventory-order-alert",
        title="在庫発注アラート",
        href="/app/production/inventory-order-alert",
        group_key="production",
    ),
    PortalMenuItem(
        key="shipment-trend-list",
        title="出荷トレンド一覧",
        href="/app/sales/shipment-trend",
        group_key="sales",
    ),
    PortalMenuItem(
        key="asset-inventory",
        title="資産棚卸結果",
        href="/app/general-affairs/asset-inventory",
        group_key="general-affairs",
    ),
    PortalMenuItem(
        key="notices",
        title="お知らせ",
        href="/app/management/notices",
        group_key="management",
    ),
    PortalMenuItem(
        key="access-requests",
        title="承認依頼",
        href="/app/management/access-requests",
        group_key="management",
    ),
    PortalMenuItem(
        key="user-management",
        title="ユーザー管理",
        href="/app/management/users",
        group_key="management",
    ),
    PortalMenuItem(
        key="database",
        title="データベース",
        href="/app/management/database",
        group_key="management",
    ),
]


MENU_BY_KEY = {item.key: item for item in MENU_ITEMS}
MENU_GROUP_BY_KEY = {group.key: group for group in MENU_GROUPS}
MENU_GROUP_KEY_BY_TITLE = {group.title: group.key for group in MENU_GROUPS}

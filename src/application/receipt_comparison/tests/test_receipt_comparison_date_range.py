"""比較日の妥当性（開始日 > 終了日）の検証。

L3レビュー指摘 L3-2 の是正（[tasks.md](../../../docs/spec/l3-review-remediation/tasks.md) B-1）。
以前は比較画面のみ暗黙にスワップし CSV 出力はスワップしなかったため、画面と CSV で
対象期間が食い違っていた。現在は双方でエラーとし、比較を行わない。
"""

from __future__ import annotations

from datetime import date

import pytest
from django.contrib.auth import get_user_model
from django.contrib.auth.models import Group

from application.portal.models import PortalMenuGroupAccess
from application.receipt_comparison.domain.value_objects.comparison_urls import (
    INVALID_DATE_RANGE_MESSAGE,
    date_range_error,
)
from application.receipt_comparison.models import FinishedProductReceiptSupplier


@pytest.fixture
def production_user(db):
    user = get_user_model().objects.create_user(username="receipt-date-range-user")
    group, _ = Group.objects.get_or_create(name="一般ユーザー")
    user.groups.add(group)
    PortalMenuGroupAccess.objects.create(user=user, group_key="production")
    return user


@pytest.fixture
def supplier(db):
    return FinishedProductReceiptSupplier.objects.create(customer_code="001", name="テスト取引先")


def test_date_range_error_returns_message_only_when_reversed():
    assert date_range_error(date(2026, 8, 2), date(2026, 8, 1)) == INVALID_DATE_RANGE_MESSAGE
    assert date_range_error(date(2026, 8, 1), date(2026, 8, 1)) is None
    assert date_range_error(date(2026, 8, 1), date(2026, 8, 2)) is None


@pytest.mark.django_db
def test_comparison_page_rejects_reversed_dates_without_swapping(client, production_user, supplier):
    client.force_login(production_user)

    response = client.get(
        "/app/production/receipt-comparison"
        f"?type=finished-product&supplier_id={supplier.id}&start_date=2026-08-02&end_date=2026-08-01&display=1"
    )
    html = response.content.decode("utf-8")

    assert response.status_code == 200
    assert INVALID_DATE_RANGE_MESSAGE in html
    # 入力値をそのまま保持し、入れ替えない
    assert 'value="2026-08-02"' in html
    assert 'value="2026-08-01"' in html


@pytest.mark.django_db
def test_export_csv_rejects_reversed_dates(client, production_user, supplier):
    client.force_login(production_user)

    response = client.get(
        "/app/production/receipt-comparison/export"
        f"?type=finished-product&supplier_id={supplier.id}&start_date=2026-08-02&end_date=2026-08-01"
    )

    assert response.status_code == 400
    assert INVALID_DATE_RANGE_MESSAGE in response.content.decode("utf-8")
    # §10.1: CSV ではなくプレーンテキストで返す（ダウンロード内容にエラー文を混入させない）
    assert response["Content-Type"] == "text/plain; charset=utf-8"


@pytest.mark.django_db
def test_export_csv_allows_same_day_range(client, production_user, supplier):
    client.force_login(production_user)

    response = client.get(
        "/app/production/receipt-comparison/export"
        f"?type=finished-product&supplier_id={supplier.id}&start_date=2026-08-01&end_date=2026-08-01"
    )

    assert response.status_code == 200

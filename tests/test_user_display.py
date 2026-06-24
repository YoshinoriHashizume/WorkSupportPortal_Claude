from __future__ import annotations

import pytest
from django.contrib.auth import get_user_model

from apps.inventory_order_alert.domain.user_display import (
    format_user_display_name,
    user_display_name_from_model,
)
from apps.inventory_order_alert.infrastructure.persistence.user_display_repository import resolve_user_display_names


def test_format_user_display_name_prefers_full_name():
    assert format_user_display_name(last_name="橋爪", first_name="良典", username="10001") == "橋爪良典"


def test_format_user_display_name_falls_back_to_username():
    assert format_user_display_name(last_name="", first_name="", username="10001") == "10001"


@pytest.mark.django_db
def test_resolve_user_display_names():
    user = get_user_model().objects.create_user(
        username="10099",
        password="pass",
        last_name="テスト",
        first_name="太郎",
    )
    names = resolve_user_display_names({"10099", "99999"})
    assert names[user.username] == "テスト太郎"
    assert names["99999"] == "99999"


@pytest.mark.django_db
def test_user_display_name_from_model():
    user = get_user_model().objects.create_user(username="10100", password="pass", last_name="生産", first_name="担当")
    assert user_display_name_from_model(user) == "生産担当"

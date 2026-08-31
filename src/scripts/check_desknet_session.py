#!/usr/bin/env python
from __future__ import annotations

import os
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "config.settings")

import django

django.setup()

from django.contrib.auth import get_user_model
from django.contrib.sessions.models import Session
from django.utils import timezone

from application.asset_inventory.infrastructure.desknet.client import fetch_list_data_page
from application.asset_inventory.domain.repositories.ports import MANAGEMENT_APP_ID, MANAGEMENT_FIELDS
from django.conf import settings


def main() -> int:
    user_model = get_user_model()
    print("=== Users matching 橋 ===")
    for user in user_model.objects.filter(last_name__contains="橋").order_by("username"):
        print(
            {
                "id": user.id,
                "username": user.username,
                "name": f"{user.last_name}{user.first_name}",
                "last_login": user.last_login,
            }
        )

    print()
    print("=== Active sessions (auth or desknet key) ===")
    now = timezone.now()
    keys_for_api_test: list[tuple[str, str]] = []
    for session in Session.objects.filter(expire_date__gte=now):
        data = session.get_decoded()
        access_key = str(data.get("desknet_access_key") or "").strip()
        user_id = data.get("_auth_user_id")
        if not access_key and not user_id:
            continue
        user = user_model.objects.filter(pk=user_id).first() if user_id else None
        label = f"{user.last_name}{user.first_name} ({user.username})" if user else "unknown"
        print(
            {
                "user": label,
                "has_desknet_access_key": bool(access_key),
                "key_len": len(access_key),
                "key_preview": f"{access_key[:8]}..." if len(access_key) > 8 else access_key,
                "desknet_user_id": data.get("desknet_user_id"),
            }
        )
        if access_key and user and "橋" in (user.last_name or ""):
            keys_for_api_test.append((label, access_key))

    if not keys_for_api_test:
        print()
        print("橋爪ユーザーのセッションに desknet_access_key は見つかりませんでした。")
        return 1

    print()
    print("=== API probe (app_id=401) for 橋爪 session ===")
    for label, access_key in keys_for_api_test:
        try:
            records = fetch_list_data_page(
                login_url=settings.DESKNETS_LOGIN_URL,
                access_key=access_key,
                app_id=MANAGEMENT_APP_ID,
                offset=0,
                limit=3,
                fields=MANAGEMENT_FIELDS,
                timeout=float(settings.DESKNETS_TIMEOUT_SECONDS),
            )
            print({"user": label, "api_status": "ok", "record_count": len(records)})
            if records:
                print({"sample": {k: records[0].get(k) for k in ("データID", "棚卸項目", "年度")}})
        except Exception as exc:
            print({"user": label, "api_status": "error", "error": str(exc)})
    return 0


if __name__ == "__main__":
    sys.exit(main())

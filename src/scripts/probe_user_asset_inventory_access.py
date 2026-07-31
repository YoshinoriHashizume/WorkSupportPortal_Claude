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

from django.conf import settings
from django.contrib.auth import get_user_model
from django.contrib.sessions.models import Session
from django.test import Client
from django.utils import timezone

from application.asset_inventory.domain.repositories.ports import MANAGEMENT_APP_ID, MANAGEMENT_FIELDS
from application.asset_inventory.infrastructure.desknet.client import fetch_list_data_page
from application.portal.interfaces.favorites import can_access_menu_item


def desknet_access_key_for_user(user_id: int) -> tuple[str, str | None]:
    for session in Session.objects.filter(expire_date__gte=timezone.now()):
        data = session.get_decoded()
        if str(data.get("_auth_user_id")) != str(user_id):
            continue
        access_key = str(data.get("desknet_access_key") or "").strip()
        if access_key:
            return session.session_key, access_key
    return "", None


def main() -> int:
    username = sys.argv[1] if len(sys.argv) > 1 else "40167"
    user_model = get_user_model()
    user = user_model.objects.get(username=username)
    print(
        {
            "username": user.username,
            "name": f"{user.last_name}{user.first_name}",
            "role": list(user.groups.values_list("name", flat=True)),
            "menu_groups": list(user.portal_menu_group_accesses.values_list("group_key", flat=True)),
            "can_access_asset_inventory": can_access_menu_item(user, "asset-inventory"),
        }
    )

    session_key, access_key = desknet_access_key_for_user(user.id)
    print({"has_desknet_access_key": bool(access_key), "session_key": session_key[:8] if session_key else ""})
    if access_key:
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
            print({"desknet_api": "ok", "record_count": len(records)})
        except Exception as exc:
            print({"desknet_api": "error", "message": str(exc)})

    client = Client()
    client.force_login(user)
    if session_key:
        client.cookies["sessionid"] = session_key
    response = client.get("/app/general-affairs/asset-inventory")
    body = response.content.decode("utf-8")
    print({"http_status": response.status_code, "is_plain_403": body.strip() == "権限がありません。"})
    if 'class="error"' in body:
        start = body.index('class="error"')
        end = body.index("</p>", start)
        print({"page_error": body[start:end]})
    elif response.status_code == 200:
        print({"page": "ok", "has_title": "資産棚卸結果" in body})
    else:
        print({"body_preview": body[:300]})
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

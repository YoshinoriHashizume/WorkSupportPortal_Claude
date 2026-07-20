#!/usr/bin/env python
from __future__ import annotations

import json
import os
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "config.settings")

import django

django.setup()

from django.conf import settings
from django.contrib.auth import get_user_model
from django.contrib.sessions.models import Session
from django.utils import timezone

from application.asset_inventory.domain.repositories.ports import SITE_FIELDS
from application.asset_inventory.infrastructure.desknet.client import (
    encode_fields_parameter,
    fetch_all_list_data,
    fetch_list_data_page,
)


def pick_access_key() -> str:
    for session in Session.objects.filter(expire_date__gte=timezone.now()).order_by("-expire_date"):
        key = str(session.get_decoded().get("desknet_access_key") or "").strip()
        if key:
            return key
    return ""


def main() -> int:
    access_key = pick_access_key()
    if not access_key:
        print("no access key")
        return 1

    site_app = "395"
    timeout = float(settings.DESKNETS_TIMEOUT_SECONDS)
    login_url = settings.DESKNETS_LOGIN_URL

    print("SITE_FIELDS:", SITE_FIELDS)
    for label, fields in [
        ("with SITE_FIELDS", SITE_FIELDS),
        ("no fields (all)", None),
    ]:
        records = fetch_all_list_data(
            login_url=login_url,
            access_key=access_key,
            app_id=site_app,
            fields=fields,
            timeout=timeout,
        )
        print(f"\n{label}: count={len(records)}")
        if records:
            print("keys:", list(records[0].keys())[:20])
            print("sample:", records[0])

    # raw first page without normalize issues
    import urllib.parse
    import urllib.request

    form = {
        "action": "list_data",
        "app_id": site_app,
        "offset": "0",
        "limit": "3",
    }
    body = urllib.parse.urlencode(form).encode()
    req = urllib.request.Request(
        login_url.replace("dneo.cgi", "appsr.cgi"),
        data=body,
        method="POST",
        headers={"X-Desknets-Auth": access_key, "Content-Type": "application/x-www-form-urlencoded"},
    )
    with urllib.request.urlopen(req, timeout=timeout) as resp:
        payload = json.loads(resp.read().decode())
    print("\nraw status:", payload.get("status"), "errorno:", payload.get("errorno"))
    items = (payload.get("list") or {}).get("item") or []
    if isinstance(items, dict):
        items = [items]
    if items:
        print("raw item keys:", list(items[0].keys())[:15])

    return 0


if __name__ == "__main__":
    sys.exit(main())

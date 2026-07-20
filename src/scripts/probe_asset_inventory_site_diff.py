#!/usr/bin/env python
"""資産棚卸結果: 拠点違い行の有無を desknet's API 実データで調査する。"""
from __future__ import annotations

import os
import sys
from collections import Counter
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
from django.utils import timezone

from application.asset_inventory.domain.value_objects.desknet_data import fetch_reconcile_source_data, list_management_rows
from application.asset_inventory.domain.value_objects.field_compare import (
    build_site_code_map,
    has_factory_change,
    has_field_diff,
)
from application.asset_inventory.domain.value_objects.inventory_dedup import dedupe_inventory_records
from application.asset_inventory.domain.value_objects.match_key import build_match_key
from application.asset_inventory.infrastructure.desknet.gateway import make_list_all_records_fn


def _pick_access_key() -> str:
    now = timezone.now()
    user_model = get_user_model()
    for session in Session.objects.filter(expire_date__gte=now).order_by("-expire_date"):
        data = session.get_decoded()
        access_key = str(data.get("desknet_access_key") or "").strip()
        if not access_key:
            continue
        user_id = data.get("_auth_user_id")
        user = user_model.objects.filter(pk=user_id).first() if user_id else None
        if user:
            return access_key
    return ""


def _site_name_diff_samples(
    assets_by_key: dict[str, dict],
    inventory_by_key: dict[str, dict],
    *,
    limit: int = 10,
) -> list[dict]:
    samples: list[dict] = []
    for key in sorted(set(assets_by_key) & set(inventory_by_key)):
        asset = assets_by_key[key]
        inv = inventory_by_key[key]
        asset_name = (asset.get("管理部門名称") or "").strip()
        inv_name = (inv.get("管理部門名称") or "").strip()
        if asset_name == inv_name:
            continue
        samples.append(
            {
                "key": key,
                "asset_site_name": asset_name,
                "inventory_site_name": inv_name,
                "asset_dept_code": (asset.get("管理部門コード") or "").strip(),
                "inventory_dept_code": (inv.get("管理部門コード") or "").strip(),
            }
        )
        if len(samples) >= limit:
            break
    return samples


def main() -> int:
    access_key = _pick_access_key()
    if not access_key:
        print("desknet_access_key を持つ有効セッションがありません。ブラウザでログイン後に再実行してください。")
        return 1

    timeout = float(settings.DESKNETS_TIMEOUT_SECONDS)
    login_url = settings.DESKNETS_LOGIN_URL
    list_all = make_list_all_records_fn(login_url=login_url, timeout=timeout)

    management_rows = list_management_rows(list_all, access_key)
    print(f"棚卸データ管理: {len(management_rows)} 件")
    if not management_rows:
        return 1

    for management_row in management_rows:
        print()
        print("=" * 72)
        print(
            f"管理行 data_id={management_row.data_id} "
            f"name={management_row.inventory_name} year={management_row.fiscal_year}"
        )
        print(
            f"  asset_app={management_row.asset_app_id} "
            f"inventory_app={management_row.inventory_app_id} "
            f"site_app={management_row.site_app_id}"
        )

        try:
            assets, inventory, sites = fetch_reconcile_source_data(list_all, access_key, management_row)
        except Exception as exc:
            print(f"  取得エラー: {exc}")
            continue

        site_map = build_site_code_map(sites)

        assets_by_key = {
            build_match_key(r.get("資産番号", ""), r.get("資産枝番", "")): r for r in assets
        }
        inventory_by_key = dedupe_inventory_records(inventory)
        matched_keys = set(assets_by_key) & set(inventory_by_key)

        name_diff_count = 0
        code_diff_count = 0
        factory_true = 0
        diff_only = 0
        name_diff_factory_false: list[dict] = []

        for key in matched_keys:
            asset = assets_by_key[key]
            inv = inventory_by_key[key]
            asset_name = (asset.get("管理部門名称") or "").strip()
            inv_name = (inv.get("管理部門名称") or "").strip()
            asset_code = (asset.get("管理部門コード") or "").strip()
            inv_code = (inv.get("管理部門コード") or "").strip()

            if asset_name != inv_name:
                name_diff_count += 1
            if asset_code != inv_code:
                code_diff_count += 1

            if not has_field_diff(asset, inv):
                continue

            if has_factory_change(asset, inv, site_map):
                factory_true += 1
            else:
                diff_only += 1
                if asset_name != inv_name and len(name_diff_factory_false) < 8:
                    ac_site = site_map.get(asset_code, "(未解決)")
                    ic_site = site_map.get(inv_code, "(未解決)")
                    name_diff_factory_false.append(
                        {
                            "key": key,
                            "asset_name": asset_name,
                            "inv_name": inv_name,
                            "asset_code": asset_code or "(空)",
                            "inv_code": inv_code or "(空)",
                            "asset_site_id": ac_site,
                            "inv_site_id": ic_site,
                        }
                    )

        print(f"  資産(対象): {len(assets)} / 棚卸: {len(inventory)} / 拠点マスタ: {len(sites)}")
        print(f"  拠点マスタ 管理部門コード件数: {len(site_map)}")
        if sites[:3]:
            print(f"  拠点マスタサンプル: {sites[:3]}")
        print(f"  棚卸済み(突合): {len(matched_keys)}")
        print(f"  管理部門名称が異なる棚卸済み: {name_diff_count}")
        print(f"  管理部門コードが異なる棚卸済み: {code_diff_count}")
        print(f"  変化あり+拠点変更(factory_change=true): {factory_true}")
        print(f"  変化あり+拠点変更なし(MATCH_DIFF): {diff_only}")

        if _site_name_diff_samples(assets_by_key, inventory_by_key, limit=5):
            print("  拠点名差異サンプル(先頭5件):")
            for row in _site_name_diff_samples(assets_by_key, inventory_by_key, limit=5):
                print(f"    {row}")

        if name_diff_factory_false:
            print("  拠点名は違うが拠点変更と判定されない例:")
            for row in name_diff_factory_false:
                print(f"    {row}")

        print("  管理部門コード差異の全件:")
        for key in sorted(matched_keys):
            asset = assets_by_key[key]
            inv = inventory_by_key[key]
            asset_code = (asset.get("管理部門コード") or "").strip()
            inv_code = (inv.get("管理部門コード") or "").strip()
            if asset_code and inv_code and asset_code != inv_code:
                print(
                    f"    {asset.get('資産番号')}-{asset.get('資産枝番')}: "
                    f"台帳[{asset_code}] {asset.get('管理部門名称')} -> "
                    f"棚卸[{inv_code}] {inv.get('管理部門名称')}"
                )

        empty_asset_code = sum(
            1
            for key in matched_keys
            if not (assets_by_key[key].get("管理部門コード") or "").strip()
        )
        empty_inv_code = sum(
            1
            for key in matched_keys
            if not (inventory_by_key[key].get("管理部門コード") or "").strip()
        )
        if empty_asset_code or empty_inv_code:
            print(f"  管理部門コード空(資産/棚卸): {empty_asset_code} / {empty_inv_code}")

        code_counter = Counter((r.get("管理部門コード") or "").strip() for r in sites if (r.get("管理部門コード") or "").strip())
        if len(code_counter) != len(sites):
            print(f"  拠点マスタ: 管理部門コード重複あり (unique={len(code_counter)} total={len(sites)})")

    return 0


if __name__ == "__main__":
    sys.exit(main())

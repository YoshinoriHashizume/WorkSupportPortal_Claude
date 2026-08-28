from __future__ import annotations

from application.asset_inventory.domain.value_objects.desknet_data import fetch_reconcile_source_data
from application.asset_inventory.domain.value_objects.list_filter import extract_asset_numbers_from_rows, extract_site_names_from_assets
from application.asset_inventory.domain.repositories.ports import ListAllRecordsFn, ManagementRow, ReconcileCounts
from application.asset_inventory.domain.value_objects.reconcile import reconcile_records
from application.asset_inventory.domain.value_objects.reconcile_cache import ReconcileCache, save_reconcile_cache


def load_reconciled_data(
    list_all: ListAllRecordsFn,
    access_key: str,
    selected: ManagementRow,
    *,
    session: dict | None,
    use_snapshot: bool = True,
) -> tuple[ReconcileCache, str]:
    """突合結果と、拠点マスタ取得失敗時の警告文（成功時は空文字）を返す（機能仕様書 §7.4.1）。

    ``use_snapshot=False`` のときは突合結果スナップショットを読まず、必ず desknet's から
    取得し直してスナップショットを上書きする（一覧画面の表示ごとの再取得。機能仕様書 §3・§4.1.1 手順7）。
    """
    from application.asset_inventory.domain.value_objects.reconcile_cache import load_reconcile_cache

    if use_snapshot and session is not None:
        cached = load_reconcile_cache(session)
        # 拠点マスタを取得できなかった縮退結果は採用せず取得し直す（DD-02）
        if cached is not None and cached.management_id == selected.data_id and not cached.site_warning:
            return cached, ""

    assets, inventory, sites, site_warning = fetch_reconcile_source_data(list_all, access_key, selected)
    all_rows, counts = reconcile_records(assets, inventory, sites)
    cache = ReconcileCache(
        management_id=selected.data_id,
        rows=all_rows,
        counts=counts,
        site_options=extract_site_names_from_assets(assets),
        asset_number_options=extract_asset_numbers_from_rows(all_rows),
        site_warning=bool(site_warning),
    )
    # 縮退結果も画面に表示した内容として保存する。取り込み用データ作成が同じ内容を参照できるようにするため
    # であり、`use_snapshot=True` の経路では採用しない（DD-02）
    if session is not None:
        save_reconcile_cache(session, cache)
    return cache, site_warning

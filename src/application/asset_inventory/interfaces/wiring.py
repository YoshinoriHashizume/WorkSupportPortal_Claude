from __future__ import annotations

from django.conf import settings

from application.asset_inventory.infrastructure.desknet.attachment import fetch_attachment_content
from application.asset_inventory.infrastructure.desknet.gateway import make_list_all_records_fn
from application.asset_inventory.infrastructure.desknet.service_access_key import (
    resolve_asset_inventory_access_key,
)
from application.asset_inventory.use_cases.export_asp_import import ExportAspImport
from application.asset_inventory.use_cases.export_csv import ExportCsv
from application.asset_inventory.use_cases.fetch_attachment import FetchAttachment
from application.asset_inventory.use_cases.list_page import ListPage
from application.asset_inventory.use_cases.resolve_access_key import ResolveAccessKey


def _list_all_fn():
    return make_list_all_records_fn(
        settings.DESKNETS_LOGIN_URL,
        float(settings.DESKNETS_TIMEOUT_SECONDS),
    )


def list_page_usecase() -> ListPage:
    return ListPage(_list_all_fn())


def export_csv_usecase() -> ExportCsv:
    return ExportCsv(_list_all_fn())


def export_asp_import_usecase() -> ExportAspImport:
    # 画面が表示した突合結果スナップショットだけを入力とするため、desknet's ゲートウェイは渡さない（DD-01）
    return ExportAspImport()


def resolve_access_key_usecase() -> ResolveAccessKey:
    return ResolveAccessKey(resolve_asset_inventory_access_key)


def fetch_attachment_usecase() -> FetchAttachment:
    return FetchAttachment(
        fetch_attachment_content,
        desknet_login_url=str(settings.DESKNETS_LOGIN_URL),
    )

from __future__ import annotations

import json
import urllib.error
import urllib.parse
import urllib.request
from typing import Any

from django.conf import settings

from application.asset_inventory.domain.repositories.ports import Record
from application.asset_inventory.domain.value_objects.errors import DesknetAccessKeyMissingError, DesknetApiError, format_desknet_user_error_message


def appsr_api_url(login_url: str) -> str:
    return login_url.replace("dneo.cgi", "appsr.cgi").replace("dneor.cgi", "appsr.cgi")


def extract_attachment_url(field_payload: Any) -> str:
    if not isinstance(field_payload, dict):
        return ""
    val = field_payload.get("val")
    if not isinstance(val, dict):
        return ""
    attach = val.get("attach") or {}
    items = attach.get("item") or []
    if isinstance(items, dict):
        items = [items]
    for item in items:
        if not isinstance(item, dict):
            continue
        url = str(item.get("url") or "").strip()
        if url:
            return url
    return ""


def _format_date_field_value(val: Any) -> str:
    if not isinstance(val, dict):
        return ""
    year = val.get("year")
    month = val.get("month")
    day = val.get("day")
    if year in (None, "") or month in (None, "") or day in (None, ""):
        return ""
    try:
        return f"{int(year):04d}-{int(month):02d}-{int(day):02d}"
    except (TypeError, ValueError):
        return ""


def record_field_value(field_payload: Any) -> str:
    if field_payload is None:
        return ""
    if isinstance(field_payload, dict):
        val = field_payload.get("val")
        if isinstance(val, dict) and "attach" in val:
            return extract_attachment_url(field_payload)
        if isinstance(val, dict):
            date_text = _format_date_field_value(val)
            if date_text:
                return date_text
        return str(val or "").strip()
    return str(field_payload).strip()


def encode_fields_parameter(fields: tuple[str, ...] | None) -> str | None:
    if not fields:
        return None
    return json.dumps([{"field_name": name} for name in fields], ensure_ascii=False)


def extract_api_error_message(payload: dict[str, Any]) -> str:
    for key in ("errormessage", "message", "error", "hint", "detail"):
        value = payload.get(key)
        if value:
            return str(value)
    return "desknet's API エラー"


def is_no_data_response(payload: dict[str, Any]) -> bool:
    errorno = payload.get("errorno")
    if errorno in (-110,):
        return True
    message = extract_api_error_message(payload)
    return "該当データが存在しません" in message


def normalize_list_response(payload: dict[str, Any]) -> list[Record]:
    if str(payload.get("status") or "").lower() != "ok":
        if is_no_data_response(payload):
            return []
        raise DesknetApiError(
            format_desknet_user_error_message(
                extract_api_error_message(payload),
                has_service_account=bool(
                    str(getattr(settings, "DESKNETS_ASSET_INVENTORY_LOGIN_ID", "") or "").strip()
                ),
            )
        )

    list_block = payload.get("list") or {}
    items = list_block.get("item") or []
    if isinstance(items, dict):
        items = [items]

    records: list[Record] = []
    for item in items:
        if not isinstance(item, dict):
            continue
        record: Record = {}
        for field_name, field_value in item.items():
            record[str(field_name)] = record_field_value(field_value)
        records.append(record)
    return records


def fetch_list_data_page(
    *,
    login_url: str,
    access_key: str,
    app_id: str,
    offset: int,
    limit: int,
    fields: tuple[str, ...] | None,
    timeout: float,
) -> list[Record]:
    if not access_key:
        raise DesknetAccessKeyMissingError("desknet's のアクセスキーがありません。再ログインしてください。")

    base_url = appsr_api_url(login_url)
    form_data: dict[str, str] = {
        "action": "list_data",
        "app_id": str(app_id),
        "offset": str(offset),
        "limit": str(limit),
    }
    fields_param = encode_fields_parameter(fields)
    if fields_param:
        form_data["fields"] = fields_param

    encoded_body = urllib.parse.urlencode(form_data).encode("utf-8")
    request = urllib.request.Request(
        base_url,
        data=encoded_body,
        method="POST",
        headers={
            "X-Desknets-Auth": access_key,
            "Content-Type": "application/x-www-form-urlencoded",
        },
    )
    try:
        with urllib.request.urlopen(request, timeout=timeout) as response:
            body = response.read().decode("utf-8")
    except urllib.error.HTTPError as exc:
        raise DesknetApiError(f"desknet's API HTTP エラー: {exc.code}") from exc
    except urllib.error.URLError as exc:
        raise DesknetApiError(f"desknet's API 接続エラー: {exc.reason}") from exc

    payload = json.loads(body)
    return normalize_list_response(payload)


def fetch_all_list_data(
    *,
    login_url: str,
    access_key: str,
    app_id: str,
    fields: tuple[str, ...] | None,
    timeout: float,
    page_size: int = 5000,
) -> list[Record]:
    all_records: list[Record] = []
    offset = 0
    while True:
        page = fetch_list_data_page(
            login_url=login_url,
            access_key=access_key,
            app_id=app_id,
            offset=offset,
            limit=page_size,
            fields=fields,
            timeout=timeout,
        )
        all_records.extend(page)
        if len(page) < page_size:
            break
        offset += page_size
    return all_records

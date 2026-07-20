from __future__ import annotations

import csv
import io
from pathlib import Path
from typing import Iterable

from .comparison_type import ReceiptComparisonType
from .records import ReceiptFileRow


FINISHED_PRODUCT_REQUIRED_COLUMNS = {"カードNO", "品番", "納入月日", "納入数", "納入取消数"}


def decode_uploaded_content(content: bytes) -> str:
    for encoding in ("cp932", "utf-8-sig", "utf-8"):
        try:
            return content.decode(encoding)
        except UnicodeDecodeError:
            continue
    return content.decode("cp932", errors="replace")


def normalize_supplied_parts_item_cd(value: str) -> str:
    """旧 clsReceiptFileData / MARI の SUBSTR(ITEM_CD, 1, LENGTH-5) に合わせて品番を正規化する。"""
    item_cd = str(value or "").strip().replace("-", "")
    if len(item_cd) > 10:
        return item_cd[: len(item_cd) - 5]
    return item_cd


def parse_supplied_parts_qty(value: str) -> int | None:
    """6列目の納入数を整数化する。旧 VB の CInt 相当。変換不能のみ対象外。"""
    raw = str(value or "").strip()
    if not raw:
        return None
    try:
        return int(float(raw))
    except ValueError:
        return None


def expand_partner_match_codes(
    subcontractor_codes: Iterable[str],
    parent_customer_code: str = "",
) -> set[str]:
    """旧 SubcontractorInfo の CUSTOMER_CODE / VENDOR_CODE 照合候補を組み立てる。"""
    allowed: set[str] = set()
    for code in subcontractor_codes:
        normalized = str(code or "").strip()
        if normalized:
            allowed.add(normalized)
    parent = str(parent_customer_code or "").strip()
    if parent:
        allowed.add(parent)
    return allowed


def subcontractor_partner_allowed(partner_code: str, allowed_codes: set[str]) -> bool:
    """旧 GetSuppliedPartsData の SubcontractorInfo 照合（2列目 = CUSTOMER_CODE or VENDOR_CODE）。"""
    if not allowed_codes:
        return False
    return str(partner_code or "").strip() in allowed_codes


def receiving_place_allowed(
    raw_delivery_place: str,
    receiving_places: Iterable[str],
    exclusion: bool,
) -> bool:
    """旧 GetSuppliedPartsData の ReceiptReceivingInfo 照合（4列目 = DELIVERY_PLACE）。"""
    places = {str(place).strip() for place in receiving_places if str(place).strip()}
    raw = str(raw_delivery_place or "").strip()
    if not places:
        return exclusion
    matched = raw in places
    if exclusion:
        return not matched
    return matched


def parse_receipt_file(
    *,
    comparison_type: str,
    file_name: str,
    content: bytes,
    subcontractor_codes: Iterable[str] = (),
    receiving_places: Iterable[str] = (),
    exclusion: bool = False,
    parent_customer_code: str = "",
) -> list[ReceiptFileRow]:
    suffix = Path(file_name).suffix.lower()
    if comparison_type == ReceiptComparisonType.FINISHED_PRODUCT:
        if suffix != ".csv":
            raise ValueError("受領書データ(csv)を選択してください。")
        return parse_finished_product_csv(content)
    if comparison_type == ReceiptComparisonType.SUPPLIED_PARTS:
        if suffix != ".txt":
            raise ValueError("受領書データ(txt)を選択してください。")
        allowed_codes = expand_partner_match_codes(subcontractor_codes, parent_customer_code)
        return parse_supplied_parts_txt(content, allowed_codes, receiving_places, exclusion)
    raise ValueError("正しい比較区分が読み込まれませんでした。")


def parse_finished_product_csv(content: bytes) -> list[ReceiptFileRow]:
    text = decode_uploaded_content(content)
    reader = csv.DictReader(io.StringIO(text))
    missing = FINISHED_PRODUCT_REQUIRED_COLUMNS - set(reader.fieldnames or [])
    if missing:
        raise ValueError(f"取込ファイルに必要な列がありません: {', '.join(sorted(missing))}")

    rows = []
    for row in reader:
        if (row.get("カードNO") or "").strip() == "S":
            continue
        rows.append(
            ReceiptFileRow(
                item_cd=(row.get("品番") or "").strip(),
                delivery_month_day=(row.get("納入月日") or "").strip(),
                qty=(row.get("納入数") or "").strip(),
                cancel_qty=(row.get("納入取消数") or "").strip(),
            )
        )
    return rows


def parse_supplied_parts_txt(
    content: bytes,
    subcontractor_codes: set[str],
    receiving_places: Iterable[str],
    exclusion: bool,
) -> list[ReceiptFileRow]:
    """旧 ReceiptForm.GetSuppliedPartsData 相当の TXT 行絞り込み・変換。"""
    text = decode_uploaded_content(content)
    reader = csv.reader(io.StringIO(text))
    rows = []
    for row in reader:
        if len(row) < 6:
            continue

        partner_code = row[1].strip()
        if not subcontractor_partner_allowed(partner_code, subcontractor_codes):
            continue

        raw_item = row[3]
        if not receiving_place_allowed(raw_item, receiving_places, exclusion):
            continue

        parts_name = str(raw_item or "").strip()
        if len(parts_name) != 10:
            continue

        date_text = str(row[2] or "").strip().strip('"').replace("/", "")
        qty_value = parse_supplied_parts_qty(row[5])
        if qty_value is None:
            continue

        rows.append(
            ReceiptFileRow(
                item_cd=parts_name,
                delivery_month_day=date_text[-4:] if date_text else "",
                qty=str(qty_value),
                cancel_qty="0",
                supplier_name=partner_code,
            )
        )
    return rows

"""SLIMS 在庫 CSV のパースと在庫内訳集計。"""
from __future__ import annotations

import csv
import io
import re
from collections import defaultdict
from dataclasses import dataclass
from decimal import Decimal
from pathlib import Path


REQUIRED_KEY_FIELDS = ("WSHOCD", "WLOCCD")
STOCK_QTY_FIELD = "WKSBQT"


def resolve_stock_qty_field(header_index: dict[str, int]) -> str:
    if STOCK_QTY_FIELD not in header_index:
        raise ValueError(f"必須列がありません: {STOCK_QTY_FIELD}")
    return STOCK_QTY_FIELD


def validate_slims_headers(header_index: dict[str, int]) -> str:
    missing = [field for field in REQUIRED_KEY_FIELDS if field not in header_index]
    if missing:
        raise ValueError(f"必須列がありません: {', '.join(missing)}")
    return resolve_stock_qty_field(header_index)
WLOCCD_PATTERN = re.compile(r"^[0-9][0-9A-Z][0-9]-\d{2}-\d$")


@dataclass(frozen=True)
class SlimsStockLocationLine:
    item_cd: str
    wloccd: str
    stock_qty: Decimal
    wmfglt: str = ""
    wnyudt: str = ""


def is_target_wloccd(wloccd: str) -> bool:
    return bool(WLOCCD_PATTERN.match(wloccd.strip()))


def read_csv_text(path: Path, encoding: str | None = None) -> str:
    if encoding:
        return path.read_text(encoding=encoding)
    for candidate in ("utf-8-sig", "utf-8", "cp932"):
        try:
            return path.read_text(encoding=candidate)
        except UnicodeDecodeError:
            continue
    return path.read_text(encoding="cp932", errors="replace")


def decode_slims_csv_bytes(raw: bytes) -> str:
    for encoding in ("utf-8-sig", "utf-8", "cp932"):
        try:
            return raw.decode(encoding)
        except UnicodeDecodeError:
            continue
    return raw.decode("cp932", errors="replace")


def format_stock_qty_value(qty: Decimal) -> str:
    if qty == qty.to_integral_value():
        return str(int(qty))
    return format(qty, "f").rstrip("0").rstrip(".")


def parse_slims_stock_csv(text: str) -> list[SlimsStockLocationLine]:
    """SLIMS CSV をパースし、有効行を **集約せず** 1 CSV 行 = 1 件で返す。"""
    reader = csv.reader(io.StringIO(text))
    try:
        fieldnames = next(reader)
    except StopIteration as exc:
        raise ValueError("CSV が空です") from exc

    header_index = {name.strip(): index for index, name in enumerate(fieldnames)}
    qty_field = validate_slims_headers(header_index)

    try:
        next(reader)
    except StopIteration as exc:
        raise ValueError("データ行がありません") from exc

    item_index = header_index["WSHOCD"]
    location_index = header_index["WLOCCD"]
    qty_index = header_index[qty_field]
    wmfglt_index = header_index.get("WMFGLT")
    wnyudt_index = header_index.get("WNYUDT")

    lines: list[SlimsStockLocationLine] = []
    for row in reader:
        if not row or all(not cell.strip() for cell in row):
            continue
        if max(item_index, location_index, qty_index) >= len(row):
            continue
        item_cd = row[item_index].strip()
        wloccd = row[location_index].strip()
        if not item_cd or not is_target_wloccd(wloccd):
            continue
        qty_text = row[qty_index].strip().replace(",", "")
        qty = Decimal(qty_text or "0")
        wmfglt = ""
        if wmfglt_index is not None and wmfglt_index < len(row):
            wmfglt = row[wmfglt_index].strip()
        wnyudt = ""
        if wnyudt_index is not None and wnyudt_index < len(row):
            wnyudt = row[wnyudt_index].strip()
        lines.append(
            SlimsStockLocationLine(
                item_cd=item_cd,
                wloccd=wloccd,
                stock_qty=qty,
                wmfglt=wmfglt,
                wnyudt=wnyudt,
            )
        )

    if not lines:
        raise ValueError("有効な在庫行がありません")

    return lines


def aggregate_location_lines(lines: list[SlimsStockLocationLine]) -> list[SlimsStockLocationLine]:
    """同一品番 + 同一ロケーションの在庫数を SUM し、要約用に 1 行へ集約する。"""
    aggregated: dict[tuple[str, str], tuple[Decimal, str, str]] = defaultdict(
        lambda: (Decimal("0"), "", "")
    )
    for line in lines:
        current_qty, current_wmfglt, current_wnyudt = aggregated[(line.item_cd, line.wloccd)]
        aggregated[(line.item_cd, line.wloccd)] = (
            current_qty + line.stock_qty,
            line.wmfglt or current_wmfglt,
            line.wnyudt or current_wnyudt,
        )

    return [
        SlimsStockLocationLine(
            item_cd=item_cd,
            wloccd=wloccd,
            stock_qty=qty,
            wmfglt=wmfglt,
            wnyudt=wnyudt,
        )
        for (item_cd, wloccd), (qty, wmfglt, wnyudt) in sorted(aggregated.items())
    ]


def location_detail_sort_key(line: SlimsStockLocationLine) -> tuple[str, str, Decimal]:
    """在庫内訳ポップアップ用。入荷日昇順（空は末尾）、同日内はロケーション・在庫数。"""
    incoming = line.wnyudt or "\xff"
    return (incoming, line.wloccd, line.stock_qty)


def group_locations_by_item(lines: list[SlimsStockLocationLine]) -> dict[str, list[SlimsStockLocationLine]]:
    grouped: dict[str, list[SlimsStockLocationLine]] = defaultdict(list)
    for line in lines:
        grouped[line.item_cd].append(line)
    for item_cd in grouped:
        grouped[item_cd].sort(key=location_detail_sort_key)
    return dict(grouped)


def total_stock_qty(lines: list[SlimsStockLocationLine]) -> Decimal:
    return sum((line.stock_qty for line in lines), start=Decimal("0"))


def build_location_summary(lines: list[SlimsStockLocationLine]) -> str:
    if not lines:
        return ""
    if len(lines) == 1:
        return lines[0].wloccd
    primary = max(lines, key=lambda line: (line.stock_qty, line.wloccd))
    return f"{primary.wloccd} 他{len(lines) - 1}"


def format_location_detail_csv(lines: list[SlimsStockLocationLine]) -> str:
    """ポップアップ用。同一ロケーションの重複行もすべて含める。入荷日昇順。"""
    parts: list[str] = []
    for line in sorted(lines, key=location_detail_sort_key):
        qty_str = format_stock_qty_value(line.stock_qty)
        if line.wnyudt:
            parts.append(f"{line.wloccd}={qty_str}@{line.wnyudt}")
        else:
            parts.append(f"{line.wloccd}={qty_str}")
    return ";".join(parts)


def parse_location_detail(text: str) -> list[dict[str, str]]:
    entries: list[dict[str, str]] = []
    for part in str(text or "").split(";"):
        part = part.strip()
        if not part or "=" not in part:
            continue
        wloccd, _, remainder = part.partition("=")
        wloccd = wloccd.strip()
        if "@" in remainder:
            qty, _, wnyudt = remainder.rpartition("@")
            qty = qty.strip()
            wnyudt = wnyudt.strip()
        else:
            qty = remainder.strip()
            wnyudt = ""
        if wloccd:
            entries.append({"wloccd": wloccd, "stock_qty": qty, "wnyudt": wnyudt})
    return entries

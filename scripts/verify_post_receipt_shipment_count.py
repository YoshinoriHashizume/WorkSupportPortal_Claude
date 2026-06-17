"""入荷なし出荷の検証: 階層1入荷実績と得意先出荷実績を突合し CSV 出力する。

5年9組と同じ Oracle テーブルを使用する。
- 最終入荷日: 仕入先ブロック 階層1 の入荷実績（T_PAST_INSPC_ACPT / NYDATA_GET 相当）
- 最終入荷日以降の出荷回数・出荷数合計: 得意先ブロックの出荷実績（T_SHIP / SKDATA_GET 相当）

使用例:
  python scripts/verify_post_receipt_shipment_count.py

環境変数 ORACLE_USE_MOCK=false と Oracle 接続情報が必要。
"""
from __future__ import annotations

import argparse
import csv
import os
import sys
from datetime import date, datetime
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
os.chdir(ROOT)
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "config.settings")

import django

django.setup()

from apps.gonenkukumi.infrastructure.oracle.client import (  # noqa: E402
    OracleNotConfiguredError,
    OracleQueryError,
    oracle_connection,
    rows_as_dicts,
    use_mock,
)

SUMMARY_COLUMNS = [
    ("cust_code", "得意先コード"),
    ("cust_name", "得意先名"),
    ("item_cd", "品番"),
    ("level1_item_cd", "階層1品番"),
    ("level1_vend_cd", "仕入先コード"),
    ("level1_vend_name", "仕入先名"),
    ("last_incoming_date", "最終入荷日"),
    ("last_ship_date", "最終出荷日"),
    ("post_shipment_count", "最終入荷日以降の出荷回数"),
    ("post_shipment_total_qty", "最終入荷日以降の出荷数合計"),
]
SUMMARY_FIELDNAMES = [column for column, _label in SUMMARY_COLUMNS]
SUMMARY_HEADER_LABELS = {column: label for column, label in SUMMARY_COLUMNS}


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="階層1入荷実績と得意先出荷実績を突合し、入荷なし出荷を CSV 出力"
    )
    parser.add_argument(
        "--output-dir",
        default="var/exports/post_receipt_shipment",
        help="CSV 出力先ディレクトリ",
    )
    parser.add_argument(
        "--as-of-date",
        default="",
        help="BOM 有効期間の基準日 YYYY/MM/DD（省略時は本日）",
    )
    return parser.parse_args()


def parse_optional_ymd(value: str) -> date:
    if not value.strip():
        return date.today()
    normalized = value.strip().replace("-", "/")
    return datetime.strptime(normalized, "%Y/%m/%d").date()


def to_date(value: object) -> date | None:
    if value is None:
        return None
    if isinstance(value, datetime):
        return value.date()
    if isinstance(value, date):
        return value
    return None


def fetch_customer_names(connection: object) -> dict[str, str]:
    cursor = connection.cursor()
    cursor.execute("SELECT TRIM(CUST_CD) AS CUST_CD, TRIM(CUST_NAME) AS CUST_NAME FROM M_CUST")
    return {str(row["cust_cd"]).strip(): str(row.get("cust_name") or "").strip() for row in rows_as_dicts(cursor)}


def fetch_ship_customer_items(connection: object) -> list[tuple[str, str]]:
    sql = """
        SELECT DISTINCT TRIM(CUST_CD) AS CUST_CD, TRIM(ITEM_CD) AS ITEM_CD
          FROM T_SHIP
         WHERE DEL_FLG != 1
         ORDER BY CUST_CD, ITEM_CD
    """
    cursor = connection.cursor()
    cursor.execute(sql)
    return [(str(row["cust_cd"]).strip(), str(row["item_cd"]).strip()) for row in rows_as_dicts(cursor)]


def chunked(items: list[str], size: int = 900) -> list[list[str]]:
    return [items[index : index + size] for index in range(0, len(items), size)]


def fetch_finished_roots(connection: object, finished_items: set[str]) -> dict[str, set[str]]:
    if not finished_items:
        return {}
    roots_by_finished: dict[str, set[str]] = {item: {item} for item in finished_items}
    for batch in chunked(sorted(finished_items)):
        placeholders = ", ".join(f":item_{index}" for index, _ in enumerate(batch))
        params = {f"item_{index}": item_cd for index, item_cd in enumerate(batch)}
        sql = f"""
            SELECT TRIM(ITEM_CD) AS ITEM_CD,
                   TRIM(SUB_ITEM_CD_01) AS SUB_ITEM_CD_01,
                   TRIM(SUB_ITEM_CD_02) AS SUB_ITEM_CD_02,
                   TRIM(SUB_ITEM_CD_03) AS SUB_ITEM_CD_03,
                   TRIM(SUB_ITEM_CD_04) AS SUB_ITEM_CD_04,
                   TRIM(SUB_ITEM_CD_05) AS SUB_ITEM_CD_05
              FROM M_ITEM
             WHERE TRIM(ITEM_CD) IN ({placeholders})
        """
        cursor = connection.cursor()
        cursor.execute(sql, params)
        for row in rows_as_dicts(cursor):
            finished = str(row["item_cd"]).strip()
            roots = roots_by_finished.setdefault(finished, {finished})
            for key in ("sub_item_cd_01", "sub_item_cd_02", "sub_item_cd_03", "sub_item_cd_04", "sub_item_cd_05"):
                sub_item = str(row.get(key) or "").strip()
                if sub_item:
                    roots.add(sub_item)
    return roots_by_finished


def fetch_bom_level1_by_root(connection: object, roots: set[str], as_of_date: date) -> dict[str, list[str]]:
    if not roots:
        return {}
    level1_by_root: dict[str, list[str]] = {}
    for batch in chunked(sorted(roots)):
        placeholders = ", ".join(f":root_{index}" for index, _ in enumerate(batch))
        params = {f"root_{index}": root for index, root in enumerate(batch)}
        params["as_of_date"] = as_of_date
        sql = f"""
            SELECT CONNECT_BY_ROOT ps.PARENT_ITEM_CD AS ROOT_ITEM,
                   TRIM(ps.COMP_ITEM_CD) AS L1_ITEM_CD
              FROM M_PS ps
              JOIN M_ITEM item
                ON item.ITEM_CD = ps.COMP_ITEM_CD
             WHERE item.OUTSIDE_TYP = '2'
               AND ps.EFF_PHASE_IN_DATE <= :as_of_date
               AND ps.EFF_PHASE_OUT_DATE >= :as_of_date
               AND LEVEL = 1
             START WITH ps.PARENT_ITEM_CD IN ({placeholders})
           CONNECT BY PRIOR ps.COMP_ITEM_CD = ps.PARENT_ITEM_CD
               AND ps.EFF_PHASE_IN_DATE <= :as_of_date
               AND ps.EFF_PHASE_OUT_DATE >= :as_of_date
        """
        cursor = connection.cursor()
        cursor.execute(sql, params)
        for row in rows_as_dicts(cursor):
            root_item = str(row["root_item"]).strip()
            l1_item = str(row["l1_item_cd"]).strip()
            if not root_item or not l1_item:
                continue
            level1_by_root.setdefault(root_item, [])
            if l1_item not in level1_by_root[root_item]:
                level1_by_root[root_item].append(l1_item)
    return level1_by_root


def fetch_vendor_by_component(connection: object) -> dict[str, tuple[str, str]]:
    """M_PUCH_UNIT_COST_H の最終行を採用（5年9組 SICODE_GET2 相当）。"""
    sql = """
        SELECT TRIM(cost.ITEM_CD) AS ITEM_CD,
               TRIM(cost.VEND_CD) AS VEND_CD,
               TRIM(vend.VEND_ANAME) AS VEND_NAME
          FROM M_PUCH_UNIT_COST_H cost
          LEFT JOIN M_VEND_CTRL vend
            ON cost.VEND_CD = vend.VEND_CD
    """
    cursor = connection.cursor()
    cursor.execute(sql)
    vendor_by_item: dict[str, tuple[str, str]] = {}
    for row in rows_as_dicts(cursor):
        item_cd = str(row["item_cd"]).strip()
        if item_cd:
            vendor_by_item[item_cd] = (
                str(row.get("vend_cd") or "").strip(),
                str(row.get("vend_name") or "").strip(),
            )
    return vendor_by_item


def fetch_last_incoming_by_item_vend(connection: object) -> dict[tuple[str, str], date]:
    sql = """
        SELECT TRIM(ITEM_CD) AS ITEM_CD,
               TRIM(VEND_CD) AS VEND_CD,
               MAX(ACPT_DATE) AS LAST_INCOMING_DATE
          FROM T_PAST_INSPC_ACPT
         GROUP BY ITEM_CD, VEND_CD
    """
    cursor = connection.cursor()
    cursor.execute(sql)
    result: dict[tuple[str, str], date] = {}
    for row in rows_as_dicts(cursor):
        item_cd = str(row["item_cd"]).strip()
        vend_cd = str(row["vend_cd"]).strip()
        incoming = to_date(row.get("last_incoming_date"))
        if item_cd and vend_cd and incoming:
            result[(item_cd, vend_cd)] = incoming
    return result


def resolve_last_incoming_for_finished(
    finished_item: str,
    roots_by_finished: dict[str, set[str]],
    level1_by_root: dict[str, list[str]],
    vendor_by_component: dict[str, tuple[str, str]],
    incoming_by_item_vend: dict[tuple[str, str], date],
) -> tuple[date | None, str, str, str]:
    best_date: date | None = None
    best_l1 = ""
    best_vend = ""
    best_vend_name = ""
    fallback_l1 = ""
    fallback_vend = ""
    fallback_vend_name = ""

    for root in roots_by_finished.get(finished_item, {finished_item}):
        for l1_item in level1_by_root.get(root, []):
            vend_cd, vend_name = vendor_by_component.get(l1_item, ("", ""))
            if not vend_cd or vend_cd == "?":
                continue
            if not fallback_l1:
                fallback_l1 = l1_item
                fallback_vend = vend_cd
                fallback_vend_name = vend_name
            incoming = incoming_by_item_vend.get((l1_item, vend_cd))
            if incoming is None:
                continue
            if best_date is None or incoming > best_date:
                best_date = incoming
                best_l1 = l1_item
                best_vend = vend_cd
                best_vend_name = vend_name

    if best_l1:
        return best_date, best_l1, best_vend, best_vend_name
    return None, fallback_l1, fallback_vend, fallback_vend_name


def fetch_customer_shipment_stats(
    connection: object,
    cust_code: str,
    internal_item_cd: str,
    last_incoming_date: date | None,
) -> tuple[date | None, int, int]:
    conditions = ["TRIM(CUST_CD) = :cust_code", "TRIM(ITEM_CD) = :item_cd", "DEL_FLG != 1"]
    params: dict[str, object] = {"cust_code": cust_code, "item_cd": internal_item_cd}
    if last_incoming_date is not None:
        conditions.append("SHIP_DATE > :last_incoming_date")
        params["last_incoming_date"] = last_incoming_date

    sql = f"""
        SELECT MAX(SHIP_DATE) AS LAST_SHIP_DATE,
               COUNT(*) AS POST_SHIPMENT_COUNT,
               SUM(NVL(SHIP_QTY, 0)) AS POST_SHIPMENT_TOTAL_QTY
          FROM T_SHIP
         WHERE {" AND ".join(conditions)}
    """
    cursor = connection.cursor()
    cursor.execute(sql, params)
    row = cursor.fetchone()
    if row is None:
        return None, 0, 0
    return to_date(row[0]), int(row[1] or 0), int(row[2] or 0)


def fetch_all_shipments(connection: object) -> list[tuple[str, str, date, int]]:
    sql = """
        SELECT TRIM(CUST_CD) AS CUST_CD,
               TRIM(ITEM_CD) AS ITEM_CD,
               SHIP_DATE,
               NVL(SHIP_QTY, 0) AS SHIP_QTY
          FROM T_SHIP
         WHERE DEL_FLG != 1
    """
    cursor = connection.cursor()
    cursor.execute(sql)
    shipments: list[tuple[str, str, date, int]] = []
    for row in rows_as_dicts(cursor):
        ship_date = to_date(row.get("ship_date"))
        if ship_date is None:
            continue
        shipments.append(
            (
                str(row["cust_cd"]).strip(),
                str(row["item_cd"]).strip(),
                ship_date,
                int(row.get("ship_qty") or 0),
            )
        )
    return shipments


def aggregate_shipment_stats(
    shipments: list[tuple[str, str, date, int]],
    cust_code: str,
    finished_item: str,
    last_incoming_date: date | None,
) -> tuple[date | None, int, int]:
    last_ship: date | None = None
    post_count = 0
    post_total_qty = 0
    for ship_cust, ship_item, ship_date, ship_qty in shipments:
        if ship_cust != cust_code or ship_item != finished_item:
            continue
        if last_ship is None or ship_date > last_ship:
            last_ship = ship_date
        if last_incoming_date is not None and ship_date <= last_incoming_date:
            continue
        post_count += 1
        post_total_qty += ship_qty
    return last_ship, post_count, post_total_qty


def build_summary_rows(connection: object, as_of_date: date) -> list[dict[str, object]]:
    customer_names = fetch_customer_names(connection)
    ship_pairs = fetch_ship_customer_items(connection)
    finished_items = {item for _, item in ship_pairs}
    all_shipments = fetch_all_shipments(connection)

    roots_by_finished = fetch_finished_roots(connection, finished_items)
    all_roots = {root for roots in roots_by_finished.values() for root in roots}
    level1_by_root = fetch_bom_level1_by_root(connection, all_roots, as_of_date)
    vendor_by_component = fetch_vendor_by_component(connection)
    incoming_by_item_vend = fetch_last_incoming_by_item_vend(connection)

    incoming_cache: dict[str, tuple[date | None, str, str, str]] = {}
    rows: list[dict[str, object]] = []

    for cust_code, finished_item in ship_pairs:
        if finished_item not in incoming_cache:
            incoming_cache[finished_item] = resolve_last_incoming_for_finished(
                finished_item,
                roots_by_finished,
                level1_by_root,
                vendor_by_component,
                incoming_by_item_vend,
            )
        last_incoming, level1_item, level1_vend, level1_vend_name = incoming_cache[finished_item]
        last_ship, post_count, post_total_qty = aggregate_shipment_stats(
            all_shipments,
            cust_code,
            finished_item,
            last_incoming,
        )
        rows.append(
            {
                "cust_code": cust_code,
                "cust_name": customer_names.get(cust_code, ""),
                "item_cd": finished_item,
                "level1_item_cd": level1_item,
                "level1_vend_cd": level1_vend,
                "level1_vend_name": level1_vend_name,
                "last_incoming_date": last_incoming.strftime("%Y/%m/%d") if last_incoming else "",
                "last_ship_date": last_ship.strftime("%Y/%m/%d") if last_ship else "",
                "post_shipment_count": post_count,
                "post_shipment_total_qty": post_total_qty,
            }
        )
    return rows


def write_summary_csv(path: Path, rows: list[dict[str, object]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8-sig", newline="") as handle:
        writer = csv.writer(handle)
        writer.writerow([SUMMARY_HEADER_LABELS[column] for column in SUMMARY_FIELDNAMES])
        for row in rows:
            writer.writerow([row.get(column, "") for column in SUMMARY_FIELDNAMES])


def main() -> int:
    args = parse_args()
    if use_mock():
        print("ERROR: ORACLE_USE_MOCK=false と Oracle 接続情報を設定してください。", file=sys.stderr)
        return 1

    as_of_date = parse_optional_ymd(args.as_of_date)
    output_dir = Path(args.output_dir)
    timestamp = datetime.now().strftime("%Y%m%d%H%M%S")
    summary_path = output_dir / f"{timestamp}_gonenkukumi_summary.csv"

    try:
        with oracle_connection() as connection:
            summary_rows = build_summary_rows(connection, as_of_date)
    except OracleNotConfiguredError as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        return 1
    except OracleQueryError as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        return 1
    except Exception as exc:
        print(f"ERROR: Oracle クエリ実行に失敗しました: {exc}", file=sys.stderr)
        return 1

    write_summary_csv(summary_path, summary_rows)

    with_post = sum(1 for row in summary_rows if int(row.get("post_shipment_count") or 0) > 0)
    print(f"as_of_date={as_of_date}")
    print(f"summary={len(summary_rows)} rows (post_shipment>0: {with_post}) -> {summary_path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

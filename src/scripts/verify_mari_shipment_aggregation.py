"""完成品 MARI 取得が旧 WinForms 版と同じ明細行を返すことを Oracle で検証する。"""
from __future__ import annotations

import argparse
import os
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
os.chdir(ROOT)
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "config.settings")

import django

django.setup()

from application.gonenkukumi.infrastructure.oracle.client import oracle_connection, rows_as_dicts

ITEM_CD = "265623-0492"
TARGET_DATE = "2026/06/19"
DELIVERY_PLACE = "61"

LEGACY_T_SHIP_SQL = """
    SELECT
        T_SHIP1.CUST_CD,
        T_SHIP1.CUST_ITEM_CD AS ITEM_CD,
        TO_CHAR(T_SHIP1.SHIP_DATE, 'yyyy/mm/dd') AS SHIP_DATE,
        T_SHIP1.SHIP_QTY,
        T_SHIP1.CUST_DESINATED_DLV_LOC_CD AS DELIVERY_PLACE,
        T_SHIP1.SHIP_ODR_NO,
        T_SHIP1.SHIP_SEQ_NO
    FROM T_SHIP T_SHIP1, T_SHIP_ODR T_SHIP_ODR1
    WHERE T_SHIP1.COMPANY_CD = T_SHIP_ODR1.COMPANY_CD
      AND T_SHIP1.SHIP_ODR_NO = T_SHIP_ODR1.SHIP_ODR_NO
      AND T_SHIP1.CUST_CD = T_SHIP_ODR1.CUST_CD
      AND TRIM(T_SHIP1.CUST_ITEM_CD) IN (:item_cd, REPLACE(:item_cd, '-', ''))
      AND T_SHIP1.SHIP_DATE = TO_DATE(:target_date, 'YYYY/MM/DD')
      AND TRIM(T_SHIP1.CUST_DESINATED_DLV_LOC_CD) = :delivery_place
      AND T_SHIP1.SHIP_QTY > 0
    ORDER BY T_SHIP1.CUST_CD, T_SHIP1.SHIP_ODR_NO, T_SHIP1.SHIP_SEQ_NO
"""

DJANGO_T_SHIP_SQL = """
    SELECT
        T_SHIP1.CUST_CD,
        T_SHIP1.CUST_ITEM_CD AS ITEM_CD,
        TO_CHAR(T_SHIP1.SHIP_DATE, 'yyyy/mm/dd') AS SHIP_DATE,
        T_SHIP1.SHIP_QTY,
        T_SHIP1.CUST_DESINATED_DLV_LOC_CD AS DELIVERY_PLACE
    FROM T_SHIP T_SHIP1, T_SHIP_ODR T_SHIP_ODR1
    WHERE T_SHIP1.COMPANY_CD = T_SHIP_ODR1.COMPANY_CD
      AND T_SHIP1.SHIP_ODR_NO = T_SHIP_ODR1.SHIP_ODR_NO
      AND T_SHIP1.CUST_CD = T_SHIP_ODR1.CUST_CD
      AND TRIM(T_SHIP1.CUST_ITEM_CD) IN (:item_cd, REPLACE(:item_cd, '-', ''))
      AND T_SHIP1.SHIP_DATE = TO_DATE(:target_date, 'YYYY/MM/DD')
      AND TRIM(T_SHIP1.CUST_DESINATED_DLV_LOC_CD) = :delivery_place
      AND T_SHIP1.SHIP_QTY > 0
    ORDER BY T_SHIP1.CUST_CD, T_SHIP1.CUST_ITEM_CD
"""

LEGACY_T_SALES_SQL = """
    SELECT
        CUST_CD,
        ITEM_CD,
        TO_CHAR(SALES_DATE, 'yyyy/mm/dd') AS SHIP_DATE,
        SALES_QTY AS SHIP_QTY,
        CUST_DESINATED_DLV_LOC_CD AS DELIVERY_PLACE,
        SHIP_SEQ_NO
    FROM T_SALES_TEMP
    WHERE TRIM(ITEM_CD) IN (:item_cd, REPLACE(:item_cd, '-', ''))
      AND SALES_DATE = TO_DATE(:target_date, 'YYYY/MM/DD')
      AND TRIM(CUST_DESINATED_DLV_LOC_CD) = :delivery_place
      AND SHIP_SEQ_NO IS NULL
      AND SALES_QTY > 0
    ORDER BY CUST_CD, ITEM_CD
"""

DJANGO_T_SALES_SQL = """
    SELECT
        CUST_CD,
        ITEM_CD,
        TO_CHAR(SALES_DATE, 'yyyy/mm/dd') AS SHIP_DATE,
        SALES_QTY AS SHIP_QTY,
        CUST_DESINATED_DLV_LOC_CD AS DELIVERY_PLACE
    FROM T_SALES_TEMP
    WHERE TRIM(ITEM_CD) IN (:item_cd, REPLACE(:item_cd, '-', ''))
      AND SALES_DATE = TO_DATE(:target_date, 'YYYY/MM/DD')
      AND TRIM(CUST_DESINATED_DLV_LOC_CD) = :delivery_place
      AND SHIP_SEQ_NO IS NULL
      AND SALES_QTY > 0
    ORDER BY CUST_CD, ITEM_CD
"""


def run_query(title: str, sql: str, params: dict[str, object]) -> list[dict[str, object]]:
    print(f"\n=== {title} ===")
    with oracle_connection() as connection:
        cursor = connection.cursor()
        cursor.execute(sql, params)
        rows = rows_as_dicts(cursor)
    if not rows:
        print("(0 rows)")
        return rows
    for row in rows:
        print(row)
    return rows


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--item-cd", default=ITEM_CD)
    parser.add_argument("--target-date", default=TARGET_DATE)
    parser.add_argument("--delivery-place", default=DELIVERY_PLACE)
    args = parser.parse_args()
    params = {
        "item_cd": args.item_cd,
        "target_date": args.target_date,
        "delivery_place": args.delivery_place,
    }

    legacy_ship = run_query("T_SHIP legacy (明細行)", LEGACY_T_SHIP_SQL, params)
    django_ship = run_query("T_SHIP Django (明細行)", DJANGO_T_SHIP_SQL, params)
    legacy_sales = run_query("T_SALES_TEMP legacy (明細行)", LEGACY_T_SALES_SQL, params)
    django_sales = run_query("T_SALES_TEMP Django (明細行)", DJANGO_T_SALES_SQL, params)

    legacy_qty = [float(r.get("ship_qty") or 0) for r in legacy_ship + legacy_sales]
    django_qty = [float(r.get("ship_qty") or 0) for r in django_ship + django_sales]
    print("\n=== summary ===")
    print(f"legacy row count: {len(legacy_ship) + len(legacy_sales)}")
    print(f"django row count: {len(django_ship) + len(django_sales)}")
    print(f"legacy qty list: {legacy_qty}")
    print(f"django qty list: {django_qty}")
    if len(legacy_ship) != len(django_ship) or legacy_qty != django_qty:
        print("=> mismatch")
        return 1
    print("=> Django SQL matches legacy detail rows")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

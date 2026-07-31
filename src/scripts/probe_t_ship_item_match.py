"""T_SHIP で品番が ITEM_CD / CUST_ITEM_CD のどちらでヒットするか確認する。

使用例:
  python scripts/probe_t_ship_item_match.py 10523-X0A02
  python scripts/probe_t_ship_item_match.py 10523-X0A02 --cust-code 112

環境変数: ORACLE_USE_MOCK=false と Oracle 接続情報（.env またはシェル）が必要。
"""
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

from application.gonenkukumi.infrastructure.oracle.client import (  # noqa: E402
    OracleNotConfiguredError,
    oracle_connection,
    rows_as_dicts,
    use_mock,
)

ITEM_CD_SQL = """
    SELECT TRIM(CUST_CD) AS CUST_CD,
           TRIM(ITEM_CD) AS ITEM_CD,
           TRIM(CUST_ITEM_CD) AS CUST_ITEM_CD,
           COUNT(*) AS ROW_COUNT,
           MAX(SHIP_DATE) AS LAST_SHIP_DATE,
           SUM(NVL(SHIP_QTY, 0)) AS TOTAL_SHIP_QTY
      FROM T_SHIP
     WHERE DEL_FLG != 1
       AND TRIM(ITEM_CD) = :item_cd
     GROUP BY TRIM(CUST_CD), TRIM(ITEM_CD), TRIM(CUST_ITEM_CD)
     ORDER BY CUST_CD, ITEM_CD, CUST_ITEM_CD
"""

CUST_ITEM_CD_SQL = """
    SELECT TRIM(CUST_CD) AS CUST_CD,
           TRIM(ITEM_CD) AS ITEM_CD,
           TRIM(CUST_ITEM_CD) AS CUST_ITEM_CD,
           COUNT(*) AS ROW_COUNT,
           MAX(SHIP_DATE) AS LAST_SHIP_DATE,
           SUM(NVL(SHIP_QTY, 0)) AS TOTAL_SHIP_QTY
      FROM T_SHIP
     WHERE DEL_FLG != 1
       AND TRIM(CUST_ITEM_CD) = :item_cd
     GROUP BY TRIM(CUST_CD), TRIM(ITEM_CD), TRIM(CUST_ITEM_CD)
     ORDER BY CUST_CD, CUST_ITEM_CD, ITEM_CD
"""

CUST_ITEM_CD_WITH_CUST_SQL = """
    SELECT TRIM(CUST_CD) AS CUST_CD,
           TRIM(ITEM_CD) AS ITEM_CD,
           TRIM(CUST_ITEM_CD) AS CUST_ITEM_CD,
           COUNT(*) AS ROW_COUNT,
           MAX(SHIP_DATE) AS LAST_SHIP_DATE,
           SUM(NVL(SHIP_QTY, 0)) AS TOTAL_SHIP_QTY
      FROM T_SHIP
     WHERE DEL_FLG != 1
       AND TRIM(CUST_CD) = :cust_code
       AND TRIM(CUST_ITEM_CD) = :item_cd
     GROUP BY TRIM(CUST_CD), TRIM(ITEM_CD), TRIM(CUST_ITEM_CD)
     ORDER BY CUST_CD, CUST_ITEM_CD, ITEM_CD
"""

M_CUST_ITEM_SQL = """
    SELECT TRIM(CUST_CD) AS CUST_CD,
           TRIM(CUST_ITEM_CD) AS CUST_ITEM_CD,
           TRIM(ITEM_CD) AS ITEM_CD,
           COUNT(*) AS ROW_COUNT
      FROM M_CUST_ITEM
     WHERE DLV_LOC_CD = '*'
       AND (TRIM(CUST_ITEM_CD) = :item_cd OR TRIM(ITEM_CD) = :item_cd)
     GROUP BY TRIM(CUST_CD), TRIM(CUST_ITEM_CD), TRIM(ITEM_CD)
     ORDER BY CUST_CD, CUST_ITEM_CD, ITEM_CD
"""


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="T_SHIP の ITEM_CD / CUST_ITEM_CD 突合を確認")
    parser.add_argument("item_cd", help="確認する品番（例: 10523-X0A02）")
    parser.add_argument("--cust-code", default="", help="得意先コードで絞り込む場合")
    return parser.parse_args()


def run_query(connection: object, title: str, sql: str, params: dict[str, object]) -> list[dict[str, object]]:
    print(f"\n=== {title} ===")
    cursor = connection.cursor()
    cursor.execute(sql, params)
    rows = rows_as_dicts(cursor)
    if not rows:
        print("(0 件)")
        return rows
    for row in rows:
        print(
            f"  cust={row.get('cust_cd')} "
            f"item_cd={row.get('item_cd')} "
            f"cust_item_cd={row.get('cust_item_cd')} "
            f"rows={row.get('row_count')} "
            f"last_ship={row.get('last_ship_date')} "
            f"total_qty={row.get('total_ship_qty')}"
        )
    return rows


def main() -> int:
    args = parse_args()
    item_cd = args.item_cd.strip()
    if use_mock():
        print("ERROR: ORACLE_USE_MOCK=false と Oracle 接続情報を設定してください。", file=sys.stderr)
        return 1

    try:
        with oracle_connection() as connection:
            params = {"item_cd": item_cd}
            item_hits = run_query(connection, f"T_SHIP.ITEM_CD = '{item_cd}'", ITEM_CD_SQL, params)
            cust_item_hits = run_query(
                connection,
                f"T_SHIP.CUST_ITEM_CD = '{item_cd}'",
                CUST_ITEM_CD_SQL,
                params,
            )
            if args.cust_code.strip():
                cust_params = {"item_cd": item_cd, "cust_code": args.cust_code.strip()}
                run_query(
                    connection,
                    f"T_SHIP CUST_CD={cust_params['cust_code']} AND CUST_ITEM_CD='{item_cd}'",
                    CUST_ITEM_CD_WITH_CUST_SQL,
                    cust_params,
                )
            run_query(
                connection,
                f"M_CUST_ITEM (CUST_ITEM_CD or ITEM_CD = '{item_cd}')",
                M_CUST_ITEM_SQL,
                params,
            )

            print("\n=== サマリ ===")
            print(f"  ITEM_CD ヒット: {len(item_hits)} グループ")
            print(f"  CUST_ITEM_CD ヒット: {len(cust_item_hits)} グループ")
            if item_hits and not cust_item_hits:
                print("  → 内作品番 ITEM_CD のみ存在（CUST_ITEM_CD では未ヒット）")
            elif cust_item_hits and not item_hits:
                print("  → 得意先品番 CUST_ITEM_CD のみ存在（ITEM_CD では未ヒット）")
            elif item_hits and cust_item_hits:
                print("  → 両方ヒット（値が同一かは上記の行を確認）")
            else:
                print("  → T_SHIP に未出荷（在庫発注アラートの「得意先コード空」行の原因候補）")
    except OracleNotConfiguredError as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        return 1
    except Exception as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

"""入荷なし出荷の検証: 階層1入荷実績と得意先出荷実績を突合し CSV 出力する。

5年9組と同じ Oracle テーブルを使用する。
- 最終入荷日: 仕入先ブロック 階層1 の入荷実績（T_PAST_INSPC_ACPT / NYDATA_GET 相当）
- 最終入荷日以降の出荷回数・出荷数合計: 得意先ブロックの出荷実績（T_SHIP / SKDATA_GET 相当）

使用例:
  python scripts/verify_post_receipt_shipment_count.py
  python scripts/verify_post_receipt_shipment_count.py --slims-csv path/to/slims.csv

環境変数 ORACLE_USE_MOCK=false と Oracle 接続情報が必要。
"""
from __future__ import annotations

import argparse
import os
import sys
from datetime import datetime
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
os.chdir(ROOT)
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "config.settings")

import django

django.setup()

from application.gonenkukumi.infrastructure.oracle.client import (  # noqa: E402
    OracleNotConfiguredError,
    OracleQueryError,
    oracle_connection,
    use_mock,
)
from application.inventory_order_alert.interfaces.wiring import ListQuery, build_list_rows  # noqa: E402
from application.inventory_order_alert.domain.value_objects.dates import parse_optional_ymd  # noqa: E402
from application.inventory_order_alert.domain.value_objects.export_csv import render_export_csv  # noqa: E402
from application.inventory_order_alert.domain.value_objects.slims_stock import read_csv_text  # noqa: E402


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
    parser.add_argument(
        "--slims-csv",
        default="",
        help="SLIMS 在庫 CSV パス（任意）",
    )
    parser.add_argument(
        "--attention-only",
        action=argparse.BooleanOptionalAction,
        default=True,
        help="対応が要る流動区分の行のみ出力（通常流動品を除く。既定: true）",
    )
    return parser.parse_args()


def write_summary_csv(path: Path, rows: list[dict[str, object]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes(render_export_csv(rows))


def main() -> int:
    args = parse_args()
    if use_mock():
        print("ERROR: ORACLE_USE_MOCK=false と Oracle 接続情報を設定してください。", file=sys.stderr)
        return 1

    as_of_date = parse_optional_ymd(args.as_of_date)
    output_dir = Path(args.output_dir)
    timestamp = datetime.now().strftime("%Y%m%d%H%M%S")
    summary_path = output_dir / f"{timestamp}_inventory_order_alert.csv"

    slims_text = read_csv_text(Path(args.slims_csv)) if args.slims_csv else None
    query = ListQuery(as_of_date=as_of_date, attention_only=args.attention_only)

    try:
        with oracle_connection() as connection:
            summary_rows = build_list_rows(
                connection,
                query,
                slims_csv_text=slims_text,
                stock_as_of_date=as_of_date if slims_text else None,
            )
    except OracleNotConfiguredError as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        return 1
    except OracleQueryError as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        return 1
    except ValueError as exc:
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

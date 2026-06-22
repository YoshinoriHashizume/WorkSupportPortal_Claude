from __future__ import annotations

from pathlib import Path

from django.core.management.base import BaseCommand, CommandError

from apps.inventory_order_alert.application.stock_storage import (
    decode_slims_csv_bytes,
    import_slims_csv_text,
)


class Command(BaseCommand):
    help = "SLIMS 在庫 CSV をファイルから取り込み、Oracle 集計を実行する"

    def add_arguments(self, parser):
        parser.add_argument("csv_path", help="取り込む SLIMS 在庫 CSV のパス")
        parser.add_argument(
            "--file-name",
            default="",
            help="取込履歴に記録するファイル名（省略時は csv_path のファイル名）",
        )

    def handle(self, *args, **options):
        csv_path = Path(str(options["csv_path"]))
        if not csv_path.is_file():
            raise CommandError(f"CSV ファイルが見つかりません: {csv_path}")

        file_name = str(options["file_name"] or csv_path.name)
        text = decode_slims_csv_bytes(csv_path.read_bytes())
        info = import_slims_csv_text(text, user=None, file_name=file_name)

        if info.aggregation_error:
            raise CommandError(f"集計に失敗しました: {info.aggregation_error}")

        self.stdout.write(
            self.style.SUCCESS(
                f"SLIMS 在庫 CSV を取り込みました: {file_name} "
                f"({info.row_count} 行 / 集計 {info.summary_row_count} 件 / {info.stock_as_of_label})"
            )
        )
        if info.confirmation_reset_count:
            self.stdout.write(
                f"確認状態を未確認に戻した件数: {info.confirmation_reset_count}"
            )

from __future__ import annotations

import os

from django.conf import settings
from django.core.management.base import BaseCommand, CommandError
from django.utils import timezone

from application.inventory_order_alert.interfaces.wiring import patch_snapshot_row_usecase
from application.inventory_order_alert.domain.value_objects.snapshot_patch import parse_patch_date


class Command(BaseCommand):
    help = "開発用: 最新集計スナップショットの行をパッチしてアラート判定を確認する"

    def add_arguments(self, parser):
        parser.add_argument("--cust-code", required=True, help="得意先コード")
        parser.add_argument("--item-cd", required=True, help="得意先品番")
        parser.add_argument(
            "--last-ship-date",
            help="最終出荷日（YYYY/MM/DD, YYYYMMDD, today）",
        )
        parser.add_argument(
            "--last-incoming-date",
            help="最終入荷日（YYYY/MM/DD, YYYYMMDD, today）",
        )
        parser.add_argument(
            "--post-shipment-count",
            type=int,
            help="最終入荷日以降の出荷回数",
        )
        parser.add_argument(
            "--reconcile",
            action="store_true",
            help="パッチ後に確認状態の整合（アラート悪化時の未確認復帰）を実行",
        )

    def handle(self, *args, **options):
        if not settings.DEBUG and os.environ.get("IOA_ALLOW_SNAPSHOT_PATCH") != "1":
            raise CommandError(
                "本コマンドは DEBUG=true または IOA_ALLOW_SNAPSHOT_PATCH=1 のときのみ実行できます。"
            )

        today = timezone.localdate()
        last_ship_date = None
        if options.get("last_ship_date"):
            last_ship_date = parse_patch_date(options["last_ship_date"], today=today)

        last_incoming_date = None
        if options.get("last_incoming_date"):
            last_incoming_date = parse_patch_date(options["last_incoming_date"], today=today)

        try:
            result = patch_snapshot_row_usecase().execute(
                cust_code=str(options["cust_code"]).strip(),
                item_cd=str(options["item_cd"]).strip(),
                last_ship_date=last_ship_date,
                last_incoming_date=last_incoming_date,
                post_shipment_count=options.get("post_shipment_count"),
                run_reconcile=bool(options.get("reconcile")),
            )
        except ValueError as exc:
            raise CommandError(str(exc)) from exc

        self.stdout.write(
            self.style.SUCCESS(
                "パッチ完了: "
                f"cust_code={result.cust_code}, item_cd={result.item_cd}\n"
                f"  最終出荷日: {result.previous_last_ship_date or '(空)'} -> {result.new_last_ship_date or '(空)'}\n"
                f"  流動区分: {result.previous_flow_quadrant} -> {result.new_flow_quadrant}\n"
                f"  確認状態復帰: {result.confirmation_reset_count} 件"
            )
        )

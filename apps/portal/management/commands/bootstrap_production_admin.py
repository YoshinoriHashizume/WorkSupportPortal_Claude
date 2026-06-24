from __future__ import annotations

from django.core.management.base import BaseCommand

from apps.portal.composition import bootstrap_production_admin_usecase
from apps.portal.domain.bootstrap import BootstrapProductionAdminConfig


class Command(BaseCommand):
    help = "本番初回用: desknet ログインする管理者を1名作成し、利用承認済み・全メニュー権限を付与する。"

    def add_arguments(self, parser):
        parser.add_argument("--username", required=True, help="社員番号（desknet と同じ）")
        parser.add_argument("--last-name", required=True, help="姓")
        parser.add_argument("--first-name", required=True, help="名")

    def handle(self, *args, **options):
        config = BootstrapProductionAdminConfig(
            username=options["username"].strip(),
            last_name=options["last_name"].strip(),
            first_name=options["first_name"].strip(),
        )
        result = bootstrap_production_admin_usecase().execute(config)
        action = "作成" if result.created else "更新"
        self.stdout.write(
            self.style.SUCCESS(
                f"管理者 {result.username} を{action}しました。"
                f" 新規メニュー権限: {result.menu_groups_granted} 件"
            )
        )
        self.stdout.write("このユーザーは desknet's NEO の社員番号・パスワードでログインしてください。")

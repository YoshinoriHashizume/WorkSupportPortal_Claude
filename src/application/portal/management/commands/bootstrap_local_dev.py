from __future__ import annotations

from django.conf import settings
from django.core.management.base import BaseCommand, CommandError

from application.portal.interfaces.wiring import bootstrap_local_dev_usecase
from application.portal.domain.value_objects.bootstrap import BootstrapLocalDevConfig


class Command(BaseCommand):
    help = "ローカル開発用の初期ユーザーを作成し、全メニュー権限と利用承認を付与する。"

    def add_arguments(self, parser):
        parser.add_argument(
            "--force",
            action="store_true",
            help="AUTH_DEV_MODE=false でも実行する（DEBUG=true のときのみ）",
        )

    def handle(self, *args, **options):
        if not settings.AUTH_DEV_MODE and not options["force"]:
            self.stdout.write("AUTH_DEV_MODE=false のためスキップしました。")
            return

        if not settings.DEBUG and not options["force"]:
            raise CommandError("DEBUG=false の環境では bootstrap_local_dev を実行できません。")

        config = BootstrapLocalDevConfig(
            username=settings.AUTH_DEV_USERNAME,
            password=settings.AUTH_DEV_PASSWORD,
            last_name=settings.AUTH_DEV_LAST_NAME,
            first_name=settings.AUTH_DEV_FIRST_NAME,
        )
        result = bootstrap_local_dev_usecase().execute(config)
        action = "作成" if result.created else "更新"
        self.stdout.write(
            self.style.SUCCESS(
                f"開発ユーザー {result.username} を{action}しました。"
                f" 新規メニュー権限: {result.menu_groups_granted} 件"
            )
        )
        self.stdout.write(f"ログイン: 社員番号={config.username} / パスワード={config.password}")

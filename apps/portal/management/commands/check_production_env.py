from __future__ import annotations

import os
import re
from pathlib import Path
from urllib.parse import urlparse

from django.conf import settings
from django.core.management.base import BaseCommand, CommandError


def mask_database_url(database_url: str) -> str:
    parsed = urlparse(database_url)
    if not parsed.password:
        return database_url
    return re.sub(
        rf":{re.escape(parsed.password)}@",
        ":***@",
        database_url,
        count=1,
    )


class Command(BaseCommand):
    help = "本番デプロイ用: .env.production の存在と PostgreSQL 接続設定を確認する。"

    def handle(self, *args, **options):
        base_dir = Path(settings.BASE_DIR)
        env_path = base_dir / ".env.production"
        env_txt_path = base_dir / ".env.production.txt"
        failed = False

        self.stdout.write(f"BASE_DIR: {base_dir}")
        self.stdout.write(f".env.production: {'あり' if env_path.is_file() else 'なし'}")

        if not env_path.is_file():
            failed = True

        if env_txt_path.is_file():
            failed = True
            self.stdout.write(
                self.style.ERROR(
                    "`.env.production.txt` があります。"
                    " メモ帳の「名前を .env.production にして種類 TXT」で保存していないか確認してください。"
                )
            )

        database_url = os.environ.get("DATABASE_URL", "").strip()
        if database_url:
            self.stdout.write(f"DATABASE_URL: {mask_database_url(database_url)}")
        else:
            failed = True
            self.stdout.write(self.style.ERROR("DATABASE_URL: 未設定（SQLite にフォールバックします）"))

        engine = settings.DATABASES["default"]["ENGINE"]
        self.stdout.write(f"DB ENGINE: {engine}")

        sqlite_path = base_dir / "db.sqlite3"
        if sqlite_path.is_file():
            self.stdout.write(self.style.WARNING(f"db.sqlite3 あり: {sqlite_path}（PostgreSQL 利用時は削除可）"))

        settings_path = base_dir / "config" / "settings.py"
        if settings_path.is_file():
            source = settings_path.read_text(encoding="utf-8")
            if 'load_dotenv(BASE_DIR / ".env.production"' not in source:
                failed = True
                self.stdout.write(
                    self.style.ERROR(
                        "config/settings.py が古い可能性があります。"
                        " git pull するか、開発 PC から最新版をコピーしてください。"
                    )
                )

        if "postgresql" in engine:
            if failed:
                raise CommandError("PostgreSQL 設定は読めていますが、上記の警告を解消してください。")
            self.stdout.write(self.style.SUCCESS("PostgreSQL 設定 OK"))
            return

        raise CommandError(
            "SQLite が使われています。"
            " `.env.production` の場所・ファイル名・DATABASE_URL を確認するか、"
            " migrate 前に `set DATABASE_URL=postgresql://...` を実行してください。"
        )

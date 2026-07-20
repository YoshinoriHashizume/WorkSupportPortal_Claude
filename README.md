# WorkSupportPortal（業務支援ポータル）

基幹周辺業務を支援する社内 Web ポータル（Python + Django）。

## ドキュメント

仕様・手順はすべて **`Document/`** にあります。

| 文書 | 内容 |
|------|------|
| [Document/アプリケーション仕様書.md](Document/アプリケーション仕様書.md) | 目的・技術スタック・画面・認証 |
| [Document/ドメイン駆動設計.md](Document/ドメイン駆動設計.md) | DDD・Clean Architecture（§5.0） |
| [CLAUDE.md](CLAUDE.md) | **Claude Code 向け常時規約**（レイヤー・SDD・開発要点） |
| [Document/ローカル開発環境構築手順.md](Document/ローカル開発環境構築手順.md) | **DevContainer によるローカル起動** |
| [Document/プログラム作成実行書.md](Document/プログラム作成実行書.md) | 実装の進め方 |
| [Document/社内標準移行メモ.md](Document/社内標準移行メモ.md) | Docker 分離・レイヤー改称の記録 |
| [Document/本番環境デプロイ手順.md](Document/本番環境デプロイ手順.md) | 本番デプロイ |

## ディレクトリ構成（社内標準）

```text
.
├── .devcontainer/                 # DevContainer 定義
├── docker/                        # Django / PostgreSQL / nginx イメージ
├── docker-compose.devcontainer.yaml
├── docker-compose.production.yaml
├── .env.example                   # 環境変数テンプレート（実体は .env）
├── Document/                      # 仕様書（ルートに維持）
└── src/                           # Django ソース
    ├── manage.py
    ├── config/
    ├── application/<app>/         # domain / use_cases / infrastructure / interfaces
    ├── templates/
    └── static/
```

依存の向き: **interfaces → use_cases → domain ← infrastructure**  
DI: `interfaces/wiring.py` で手動組み立て（DI コンテナ不使用）。  
ランタイム依存の正: **`requirements-prod.txt`**（Docker は `requirements-docker.txt`、Windows 直実行は `requirements-windows-prod.txt`）。

## クイックスタート

1. `.env.example` を `.env` にコピーして編集する。
2. Docker Desktop を起動する。
3. 次のいずれか:
   - Cursor / VS Code で **Reopen in Container**
   - またはホストで `docker compose -f docker-compose.devcontainer.yaml up --build -d`
4. ブラウザで `http://localhost:8990` を開く（PostgreSQL はホスト `5440`）。

詳細は [ローカル開発環境構築手順.md](Document/ローカル開発環境構築手順.md)。

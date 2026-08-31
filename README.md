# WorkSupportPortal（業務支援ポータル）

基幹周辺業務を支援する社内 Web ポータル（Python + Django）。

## ドキュメント

文書は 3 か所に分かれています。**アプリ固有はコードと同じ場所**（`src/application/<app>/docs/`）、
**横断設計**は `src/docs/`、**全体の手順書**は `Document/`（ルート）です。

### 全体（`Document/` ＋ ルート）

| 文書 | 内容 |
|------|------|
| [Document/アプリケーション仕様書.md](Document/アプリケーション仕様書.md) | 目的・技術スタック・画面・認証・要件一覧 |
| [Document/ドメイン駆動設計.md](Document/ドメイン駆動設計.md) | DDD・Clean Architecture（§5.0） |
| [CLAUDE.md](CLAUDE.md) | **Claude Code 向け常時規約**（レイヤー・SDD・開発要点） |
| [Document/ローカル開発環境構築手順.md](Document/ローカル開発環境構築手順.md) | **DevContainer によるローカル起動** |
| [Document/プログラム作成実行書.md](Document/プログラム作成実行書.md) | 実装の進め方 |
| [Document/社内標準移行メモ.md](Document/社内標準移行メモ.md) | Docker 分離・レイヤー改称・文書配置移行の記録 |
| [Document/本番環境デプロイ手順.md](Document/本番環境デプロイ手順.md) | 本番デプロイ |
| [Document/Microsoft認証（Entra ID）構築手順.md](Document/Microsoft認証（Entra%20ID）構築手順.md) | Entra ID のアプリ登録・環境変数 |

### 横断設計（`src/docs/`）

| 文書 | 内容 |
|------|------|
| [src/docs/ubiquitous_language_core.md](src/docs/ubiquitous_language_core.md) | ユビキタス言語集（core） |
| [src/docs/テスト配置_共通仕様.md](src/docs/テスト配置_共通仕様.md) | 各 app 配下へのテスト配置ルール |

### アプリ別（`src/application/<app>/docs/`）

| アプリ | app | 文書 |
|------|-----|------|
| 5年9組 | `gonenkukumi` | [機能仕様書](src/application/gonenkukumi/docs/5年9組_機能仕様書.md) / [テスト仕様書](src/application/gonenkukumi/docs/5年9組_テスト仕様書.md) / [MARI_Oracle_テーブル定義](src/application/gonenkukumi/docs/MARI_Oracle_テーブル定義.md) |
| 検収書比較 | `receipt_comparison` | [機能仕様書](src/application/receipt_comparison/docs/検収書比較_機能仕様書.md) / [テスト仕様書](src/application/receipt_comparison/docs/検収書比較_テスト仕様書.md) |
| 在庫発注アラート | `inventory_order_alert` | [機能仕様書](src/application/inventory_order_alert/docs/在庫発注アラート_機能仕様書.md) / [テスト仕様書](src/application/inventory_order_alert/docs/在庫発注アラート_テスト仕様書.md) |
| 資産棚卸結果 | `asset_inventory` | [機能仕様書](src/application/asset_inventory/docs/資産棚卸結果_機能仕様書.md) / [テスト仕様書](src/application/asset_inventory/docs/資産棚卸結果_テスト仕様書.md) |
| 出荷トレンド一覧 | `shipment_trend` | [機能仕様書](src/application/shipment_trend/docs/出荷トレンド一覧_機能仕様書.md) / [テスト仕様書](src/application/shipment_trend/docs/出荷トレンド一覧_テスト仕様書.md) |
| ポータル共通 | `portal` | [ポータル一覧表_共通仕様](src/application/portal/docs/ポータル一覧表_共通仕様.md) |

## ディレクトリ構成（社内標準）

```text
.
├── .devcontainer/                 # DevContainer 定義
├── docker/                        # Django / PostgreSQL / nginx イメージ
├── docker-compose.devcontainer.yaml
├── docker-compose.production.yaml
├── .env.example                   # 環境変数テンプレート（実体は .env）
├── Document/                      # アプリケーション仕様書・全体の手順書（ルート）
└── src/                           # Django ソース
    ├── manage.py
    ├── config/
    ├── docs/                      # 横断設計文書（ubiquitous_language_core.md 等）
    ├── application/<app>/         # domain / use_cases / infrastructure / interfaces
    │   └── docs/                  #   アプリ固有の仕様書・spec/{feature}/・issues/
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

# 在庫発注アラート 設定画面・未実装 API 実装 タスク分解

| 項目 | 内容 |
|---|---|
| 文書ID | TASK-INVENTORY-ORDER-ALERT-2026-002 |
| 作成日 | 2026/08/25 |
| 更新日 | 2026/08/25 |
| 対応文書 | [在庫発注アラート_機能仕様書.md](../../在庫発注アラート_機能仕様書.md)（§4.2 / §8.1 / §8.4 / §8.9 / §8.10 / §8.11 / §9 / §13 Q5 / REQ-F-015 / REQ-F-016） |
| 契機 | L3レビュー（3巡目）2026/08/25 の指摘 **L3T-1**（仕様が実装より広い）・**L3T-2**（L3-11 の緩和策が成立しない）。ユーザー決定: **全て実装する** |
| ユビキタス言語 | [ubiquitous_language.md](../../ubiquitous_language.md) |

---

## 1. 背景と方針

L3レビュー（3巡目）で、機能仕様書に規定済みでありながら実装が存在しない範囲が確定した。

| 仕様 | 内容 | 現況 |
|---|---|---|
| §8.1 | `GET /api/inventory-order-alert/summary` | ルートなし。判定・絞り込みの部品（`domain/value_objects/list_query.py` / `list_rows.py`）のみ実装済み |
| §8.4 | `GET /api/inventory-order-alert/stock-locations` | ルートなし。在庫内訳は `load_latest_stock_lines()` で取得可能 |
| §8.9 | `GET /api/inventory-order-alert/vendors` | ルートなし |
| §8.10 | `GET` / `PUT /api/inventory-order-alert/settings` | ルートなし。`stockStaleDays` / `criticalEnabled` に保存経路が存在しない |
| §8.11 | `GET /api/inventory-order-alert/dashboard-summary` | ルートなし。帯は `portal/interfaces/wiring.py` からプロセス内呼び出しで描画 |
| §4.2・REQ-F-016 | 設定画面 SCR-02（`/app/production/inventory-order-alert/settings`、管理者のみ） | ルート・テンプレートとも存在しない |

**方針**:

- 既存の一覧画面（SCR-01）の描画経路は**変更しない**。追加する API は読み取り専用の並行経路とし、既存の振る舞いに影響を与えない。
- **Oracle へは問い合わせない**（§4.1.1）。すべて PostgreSQL の集計スナップショット／SLIMS 在庫スナップショットから応答する。§8.9 の仕入先候補も、§4.1.4 の「候補値は直近スナップショットから生成する」原則に合わせスナップショット由来とする（**要 仕様追記**: TASK-08）。
- Clean Architecture を維持する。`domain/` `use_cases/` に `import django` を持ち込まない。組み立ては `interfaces/wiring.py` のみ。
- **仕様書が SSOT**。実装にあたり仕様の記述不足が判明した箇所は、**コードより先に仕様書を修正する**（TASK-08）。

---

## 2. 変更対象ファイル一覧

### 2.1 新規作成

| # | ファイル | 内容 |
|---|---|---|
| N-1 | `use_cases/app_settings.py` | 設定の取得／更新ユースケース（§8.10・§4.2） |
| N-2 | `use_cases/summary_api.py` | §8.1 summary / §8.4 stock-locations / §8.9 vendors / §8.11 dashboard-summary の読み取りユースケース |
| N-3 | `templates/inventory_order_alert/settings.html` | 設定画面 SCR-02（§4.2） |
| N-4 | `tests/test_app_settings_usecase.py` | 設定値のパース・保存のテスト |
| N-5 | `tests/test_summary_api.py` | 4 つの読み取り API のユースケーステスト |
| N-6 | `tests/test_settings_page_views.py` | 設定画面・設定 API の認可（管理者可 / 一般 403）と画面表示のテスト |

### 2.2 変更

| # | ファイル | 変更概要 |
|---|---|---|
| M-1 | `domain/value_objects/app_settings.py` | `SettingsInput` と `parse_settings_payload()` を**追加**（`warningDays` / `criticalEnabled` / `stockStaleDays` の検証）。既存の `AppSettings` / `AlertSettingsInput` / `parse_alert_settings_payload` は**変更しない** |
| M-2 | `domain/repositories/ports.py` | `SaveAppSettings` / `LoadStockLines` の型エイリアスを**追加**（既存行は変更しない） |
| M-3 | `infrastructure/persistence/settings_repository.py` | `save_app_settings()` を**追加**（既存 `load_app_settings` / `save_warning_month_settings` は変更しない） |
| M-4 | `interfaces/wiring.py` | 新ユースケースの組み立て関数を**追加**（既存の関数は変更しない） |
| M-5 | `interfaces/views.py` | ビューを**追加**: `settings_page` / `api_settings` / `api_summary` / `api_stock_locations` / `api_vendors` / `api_dashboard_summary`。既存ビューは変更しない |
| M-6 | `interfaces/urls.py` | 上記 6 経路を `urlpatterns` に**追加**。既存の 7 経路は変更しない |
| M-7 | `docs/在庫発注アラート_機能仕様書.md` | §4.2・§8.1・§8.3・§8.9・§13 Q5 の記述を実装に合わせて是正（TASK-08）。レビュー履歴の「対応」列を更新 |

### 2.3 削除

**削除は行わない。** 既存コード・既存仕様の削除を伴う変更は本タスクに含まれない。

---

## 3. 影響範囲

| 対象 | 影響 |
|---|---|
| 一覧画面 SCR-01 | **なし**（描画経路・テンプレート・クエリともに変更しない） |
| メニュー画面アラート帯 | **なし**（`portal/interfaces/wiring.py` 経由のプロセス内呼び出しを維持し、§8.11 は並行経路として追加する） |
| PostgreSQL スキーマ | **なし**（`InventoryOrderAlertSettings` の既存列 `warning_days` / `critical_enabled` / `stock_stale_days` に保存するのみ。マイグレーション追加なし） |
| Oracle（MARI） | **なし**（参照専用の原則を維持し、新規クエリを追加しない） |
| 他アプリ | **なし**（`application/portal/interfaces/favorites.py` の `is_portal_admin` を参照するのみ。portal 側は変更しない） |
| 既存テスト | 追加のみ。既存 978 件は変更しない |

---

## 4. タスク

### TASK-01 設定値の検証（domain）

- `domain/value_objects/app_settings.py` に `SettingsInput`（`warning_days` / `critical_enabled` / `stock_stale_days`）と `parse_settings_payload()` を追加する。
- 範囲: `warningDays` 1〜3650 / `stockStaleDays` 1〜365 / `criticalEnabled` は真偽値。範囲外・型不一致は `ValueError`（日本語メッセージ）。
- **前提**: TASK-08 で §4.2 に許容範囲を明記してから実装する（仕様が先）。
- テスト: N-4（正常値・下限／上限・範囲外・型不正・キー欠落）。

### TASK-02 設定の保存（infrastructure / ports）

- `settings_repository.save_app_settings(*, warning_days, critical_enabled, stock_stale_days, updated_by=None) -> AppSettings` を追加する。
- `ports.py` に `SaveAppSettings` を追加する。
- テスト: N-4（保存後に `load_app_settings()` が反映値を返すこと）。

### TASK-03 設定ユースケース（use_cases）

- `use_cases/app_settings.py` に `AppSettingsUseCase`（`load()` / `save(payload, updated_by)`）を実装する。`import django` を持たない。
- テスト: N-4。

### TASK-04 設定 API（§8.10）

- `GET /api/inventory-order-alert/settings` → `{ "ok": true, "settings": {...} }`
- `PUT /api/inventory-order-alert/settings` → 検証後に保存し `{ "ok": true, "settings": {...} }`。不正時 400。
- **管理者のみ**（§9）。一般ユーザーは 403（JSON）。
- テスト: N-6。

### TASK-05 設定画面 SCR-02（§4.2 / REQ-F-016）

- `GET /app/production/inventory-order-alert/settings`（管理者のみ・一般は 403 プレーンテキスト「権限がありません。」＝ `receipt_comparison` の設定画面と同じ振る舞い）。
- テンプレート `settings.html` は既存 `list.html` のレイアウト規約に従い、`warningShipmentMonths` / `warningIncomingMonths` / `criticalEnabled` / `stockStaleDays` を編集できるフォームを表示する。保存は §8.10 の `PUT` を呼ぶ。
- 非推奨キー（`recentIncomingDays` 等）は画面に出さない（DB 保持のみ）。
- テスト: N-6。

### TASK-06 読み取り API 3 種（§8.1 / §8.4 / §8.9）

- `use_cases/summary_api.py` に集約する。いずれも Oracle へ問い合わせない。
- §8.1: 集計スナップショット読込 → 最新設定でアラート再判定（`merge_query_with_settings` → `enrich_summary_rows`）→ 確認状態を反映 → `filter_summary_rows` / `sort_summary_rows` → `rows` / `counts` / `stockImport` を返す。入力不正は 400。
- §8.4: `itemCd` 必須。最新 SLIMS スナップショットから当該品番の内訳を返す。`itemCd` 未指定は 400。
- §8.9: 集計スナップショットの `level1_vend_cd` / `level1_vend_name` から重複除去して `items` を返す。
- テスト: N-5。

### TASK-07 ダッシュボード集計 API（§8.11）

- 既存 `PortalDashboard` ユースケースの結果を JSON 化して返す（`counts` / `stockImport`）。
- 認可は既存ミドルウェア（`/api/inventory-order-alert/` は生産管理メニューグループ必須）で担保される。
- テスト: N-5・N-6。

### TASK-08 仕様書の是正（コードより先に実施）

| # | 対象 | 内容 |
|---|---|---|
| 8-a | §4.2 | 各キーの**許容範囲**（`warningDays` 1〜3650 / `stockStaleDays` 1〜365 / 月数 1〜36）を追記する。画面に表示するのは月数 2 種・`criticalEnabled`・`stockStaleDays` の 4 項目であることを明記する |
| 8-b | §8.1 | クエリの記述を実装の語彙に合わせる（`warningShipmentMonths` / `warningIncomingMonths` / `criticalEnabled` を追記。**一覧画面のフィルタ（§4.1.4）とは別系統**である旨を注記） |
| 8-c | §8.9 | 取得元を「Oracle `M_VEND_CTRL` 等」から「**直近の集計スナップショット**（`level1_vend_cd` / `level1_vend_name`）」に是正する（§4.1.1 の Oracle 非問い合わせ原則と整合） |
| 8-d | §8.3 | 画面側 CSV 出力 URL（`/app/production/inventory-order-alert/export.csv`）を併記する（**L3T-5**） |
| 8-e | §13 Q5 | 設定画面の実装完了に合わせ、「設定画面から調整する」が実行可能になった旨に更新する（**L3T-2** の解消） |
| 8-f | レビュー履歴 | L3T-1・L3T-2・L3T-5 の「対応」列を更新する |

### TASK-09 検証

- `python manage.py test`（既存 978 件 + 追加分がすべて green であること）。
- `src/config/tests/test_clean_architecture.py` が green であること（domain / use_cases に Django 依存がないこと）。

---

## 5. 実行順序

TASK-08（8-a〜8-c の仕様先行分）→ TASK-01 → TASK-02 → TASK-03 → TASK-04 → TASK-05 → TASK-06 → TASK-07 → TASK-08（8-d〜8-f）→ TASK-09

---

## 6. 実行レポート

| 日時 | タスク | 結果 | 備考 |
|---|---|---|---|
| 2026/08/25 | TASK-08（8-a〜8-c） | 完了 | §4.2 に許容範囲と画面表示 4 項目、§8.1 にクエリ語彙（一覧フィルタとは別系統である旨の注記を含む）、§8.9 に取得元＝集計スナップショットを追記。§8.10 に認可・応答の詳細を追記 |
| 2026/08/25 | TASK-01 | 完了 | `domain/value_objects/app_settings.py` に `SettingsInput` / `parse_settings_payload()` / `settings_payload()` と範囲定数を追加。既存の `AppSettings` / `AlertSettingsInput` / `parse_alert_settings_payload` は無変更 |
| 2026/08/25 | TASK-02 | 完了 | `settings_repository.save_app_settings()` を追加。`ports.py` に `SaveAppSettings` / `LoadStockLines` 等の型エイリアスを追加 |
| 2026/08/25 | TASK-03 | 完了 | `use_cases/app_settings.py`（`AppSettingsUseCase`）を新規作成。Django 非依存 |
| 2026/08/25 | TASK-04 | 完了 | `GET` / `PUT /api/inventory-order-alert/settings` を追加。管理者以外は 403（JSON）、不正入力は 400、`POST` は 405 |
| 2026/08/25 | TASK-05 | 完了 | `templates/inventory_order_alert/settings.html` と `settings_page` ビューを追加。管理者以外はプレーンテキスト 403。月数は §8.10 の `alert-settings`、`criticalEnabled` / `stockStaleDays` は §8.10 の `settings` へ `PUT` する |
| 2026/08/25 | TASK-06 | 完了 | `use_cases/summary_api.py` に `SummaryApi` / `StockLocations` / `Vendors` を実装。Oracle へは問い合わせない |
| 2026/08/25 | TASK-07 | 完了 | `DashboardSummary` を追加。`PortalDashboard` は変更せず、`importedAt` のみ集計スナップショットから補う |
| 2026/08/25 | TASK-08（8-d〜8-f） | 完了 | §8.3 に画面側 CSV URL を併記（L3T-5）。§13 Q5 を設定画面実装済みの実態に更新（L3T-2）。レビュー履歴の「対応」列・未解決件数・次のアクションを更新（L3T-1・L3T-2・L3T-5 を解消済みに） |
| 2026/08/25 | TASK-09 | 完了 | `pytest -q` → **1036 passed**（既存 978 件 + 追加 58 件）。`config/tests/test_clean_architecture.py` → 58 passed |

### 追加テスト内訳

| ファイル | 件数 |
|---|---|
| `tests/test_app_settings_usecase.py`（N-4） | 22 |
| `tests/test_summary_api.py`（N-5、ユースケース 17 + API 経路 9） | 26 |
| `tests/test_settings_page_views.py`（N-6） | 10 |

### 残メモ

- 設定画面 SCR-02 への**導線（一覧画面からのリンク）を 2026/08/25 に追加した**（`templates/inventory_order_alert/list.html` に管理者のみ表示の「設定」リンク、`interfaces/views.py` の `list_page` に `is_admin` を追加、`tests/test_settings_page_views.py` に表示／非表示テスト 2 件）。仕様は §4.2 に「導線」として明記済み。
- `parse_settings_payload()` は数値文字列（`"14"` 等）を受け付ける。画面のフォーム送信が文字列で届くための意図的な仕様（N-4 に明記）。

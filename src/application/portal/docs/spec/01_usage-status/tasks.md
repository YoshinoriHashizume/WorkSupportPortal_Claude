文書ID: TASK-USAGE-STATUS-2026-001
作成日: 2026/08/27
更新日: 2026/08/28
対応文書: ./design.md（DESIGN-USAGE-STATUS-2026-001） / ./test-design.md（TEST-USAGE-STATUS-2026-001） / ./requirements.md（REQ-USAGE-STATUS-2026-001）

# 利用状況 タスクリスト

## 0. 前提

- 実装は **TDD（Red → Green → Refactor）** で進める（CLAUDE.md §2）。各実装タスクの直前にテスト作成タスクを置く。
- 実装順は test-design.md §5.3 の 7 段に従う。段の区切り（記録側が先・画面側が後）は requirements.md §6.3 制約 4 による。
- 1 タスク = 原則 1 ファイル（CLAUDE.md §3）。`ports.py` / `wiring.py` / `test_usage_status_repository.py` は記録側と画面側で 2 回触るが、段が異なるため別タスクとする。
- テストは `application/portal/tests/` 直下のフラット構成・モジュールレベル関数・英語スネークケース＋日本語 docstring 1 行（test-design.md §1.5）。
- 他の 5 つの業務コンテキスト（`asset_inventory` / `gonenkukumi` / `inventory_order_alert` / `receipt_comparison` / `shipment_trend`）のファイルは 1 つも変更しない（REQ-NF-006）。

**中間状態についての注意**:

| 事象 | 発生する期間 | 扱い |
|---|---|---|
| 管理メニューに「利用状況」が現れるがリンク先が未実装 | タスク 1 完了 〜 タスク 29 完了 | 開発ブランチ内の一時的な状態として許容する。タスク 29（URL 登録）で解消する |
| TC-DOM-015（出力エンドポイント一覧と `urlpatterns` の一致）が赤のまま | タスク 4 完了 〜 タスク 29 完了 | `EXPORT_ENDPOINTS` #9 が本機能自身の CSV 出力 URL のため、URL 登録まで一致しない。タスク 32 で緑を確認する |

---

## 状況チェックシート

**凡例**: `[ ]` 未着手 / `[~]` 進行中 / `[✅YYYY/MM/DD HH:MM]` 完了 / `[- YYYY/MM/DD HH:MM]` スキップ

### 段 1: 記録側 Domain（完了条件: TC-DOM-001〜039 が緑。TC-DOM-015 を除く）

| # | タスク | レイヤー | 状態 |
|---|--------|---------|------|
| 1 | メニュー項目 `usage-status` を `MENU_ITEMS` に追加 | domain | [✅2026/08/27 18:00] |
| 2 | `MenuUsageLog` のテスト作成（TC-DOM-001〜005） | domain / test | [✅2026/08/27 18:03] |
| 3 | `MenuUsageLog` エンティティの実装 | domain | [✅2026/08/27 18:05] |
| 4 | 記録対象の判別のテスト作成（TC-DOM-010〜014・020〜039） | domain / test | [✅2026/08/27 18:08] |
| 5 | `usage_record.py`（`EXPORT_ENDPOINTS`・判別の純関数）の実装 | domain | [✅2026/08/27 18:13] |

### 段 2: 記録側 Application / Infrastructure（完了条件: TC-APP-001〜003・TC-INF-001〜006 が緑）

| # | タスク | レイヤー | 状態 |
|---|--------|---------|------|
| 6 | `MenuUsageLogRepository` ポートの追記 | domain | [✅2026/08/27 18:14] |
| 7 | `RecordUsage` のテスト作成（TC-APP-001〜003） | use_cases / test | [✅2026/08/27 18:15] |
| 8 | `RecordUsage` ユースケースの実装 | use_cases | [✅2026/08/27 18:15] |
| 9 | `MenuUsageLog` ORM モデルの追加 | infrastructure | [✅2026/08/27 18:16] |
| 10 | マイグレーション `0007_menu_usage_log.py` の作成 | infrastructure | [✅2026/08/27 18:17] |
| 11 | 記録リポジトリのテスト作成（TC-INF-001〜006） | infrastructure / test | [✅2026/08/27 18:18] |
| 12 | `DjangoMenuUsageLogRepository` の実装 | infrastructure | [✅2026/08/27 18:19] |

### 段 3: 記録側 Interfaces（完了条件: TC-UI-001〜011 が緑。**この段でメニュー利用ログの蓄積が始まる**）

| # | タスク | レイヤー | 状態 |
|---|--------|---------|------|
| 13 | `wiring.py` に記録側ファクトリ 2 件を追記 | interfaces | [✅2026/08/27 18:22] |
| 14 | `UsageLoggingMiddleware` のテスト作成（TC-UI-001〜011） | interfaces / test | [✅2026/08/27 18:28] |
| 15 | `UsageLoggingMiddleware` の実装 | interfaces | [✅2026/08/27 18:30] |
| 16 | `MIDDLEWARE` への登録 | config | [✅2026/08/27 18:31] |

### 段 4: 画面側 Domain（完了条件: TC-DOM-050〜104 が緑）

| # | タスク | レイヤー | 状態 |
|---|--------|---------|------|
| 17 | `AggregationPeriod` のテスト作成（TC-DOM-050〜066） | domain / test | [✅2026/08/27 18:32] |
| 18 | `usage_period.py` の実装 | domain | [✅2026/08/27 18:33] |
| 19 | 行 VO・集計関数のテスト作成（TC-DOM-070〜104） | domain / test | [✅2026/08/27 18:41] |
| 20 | `usage_status_display.py` の実装 | domain | [✅2026/08/27 18:46] |

### 段 5: 画面側 Application / Infrastructure（完了条件: TC-APP-010〜025・TC-INF-010〜028 が緑）

| # | タスク | レイヤー | 状態 |
|---|--------|---------|------|
| 21 | `UsageStatusRepository` ポートの追記 | domain | [✅2026/08/27 18:47] |
| 22 | `UsageStatus` のテスト作成（TC-APP-010〜025） | use_cases / test | [✅2026/08/27 18:57] |
| 23 | `UsageStatus` ユースケースの実装 | use_cases | [✅2026/08/27 19:02] |
| 24 | 集計リポジトリのテスト追記（TC-INF-010〜028） | infrastructure / test | [✅2026/08/27 19:11] |
| 25 | `DjangoUsageStatusRepository` の実装 | infrastructure | [✅2026/08/27 19:14] |

### 段 6: 画面側 Interfaces（完了条件: TC-UI-020〜041 が緑）

| # | タスク | レイヤー | 状態 |
|---|--------|---------|------|
| 26 | `wiring.py` に集計側ファクトリ 2 件を追記 | interfaces | [✅2026/08/27 19:17] |
| 27 | 画面・CSV 出力のテスト作成（TC-UI-020〜041） | interfaces / test | [✅2026/08/27 19:32] |
| 28 | `views.py` に view 2 件を追加 | interfaces | [✅2026/08/27 19:37] |
| 29 | `urls.py` にルート 2 件を追加 | interfaces | [✅2026/08/27 19:39] |
| 30 | テンプレート `usage_status.html` の作成 | interfaces | [✅2026/08/27 19:55] |
| 31 | `usage-status-list-client.js` の作成 | interfaces | [✅2026/08/27 20:01] |

### 段 7: 仕上げ

| # | タスク | レイヤー | 状態 |
|---|--------|---------|------|
| 32 | TC-DOM-015（出力エンドポイント一覧と `urlpatterns` の一致）の確認 | domain / test | [✅2026/08/27 20:02] |
| 33 | 全体テストとアーキテクチャ検証（TC-UI-050） | 全体 | [✅2026/08/27 20:08] |
| 34 | 手動確認（test-design.md §4.4 #1〜#6） | 全体 | [✅2026/08/28 08:57] |
| 35 | 容量監視の運用手順を `Document/` に追記 | docs | [✅2026/08/27 20:25] |

---

## タスク詳細

### 段 1: 記録側 Domain

#### タスク 1: メニュー項目 `usage-status` を `MENU_ITEMS` に追加

- **対象ファイル**: `application/portal/domain/value_objects/menu.py`（変更）
- **内容**: design.md §6.1 のとおり `PortalMenuItem(key="usage-status", title="利用状況", href="/app/management/usage-status", group_key="management")` を `MENU_ITEMS` に 1 件追加する。既存の管理メニュー項目の並びに合わせて配置する。削除・改名は行わない。
- **なぜ最初か**: TC-DOM-026・037・038（`resolve_menu_key` が `usage-status` を返す）が `MENU_ITEMS` の定義に依存するため。
- **完了条件**: `pytest application/portal/tests/` の既存テストがすべて緑。管理者のポータル画面に「利用状況」が表示される（リンク先はタスク 29 まで未実装）。
- **対応要件**: REQ-F-005・REQ-NF-001

#### タスク 2: `MenuUsageLog` のテスト作成（Red）

- **対象ファイル**: `application/portal/tests/test_menu_usage_log.py`（新規）
- **内容**: test-design.md §2.1「エンティティ: `MenuUsageLog`」の TC-DOM-001〜005 を実装する。`@pytest.mark.django_db` は付けない（DB 不要）。
  - TC-DOM-001 属性の保持 / TC-DOM-002 `EXPORT` の受理 / TC-DOM-003 未知の利用種別（`"DOWNLOAD"` / `""` / `"view"` / `None`）で `ValueError` / TC-DOM-004 `user_id=None` の許容 / TC-DOM-005 状態変更メソッドを持たないこと
- **完了条件**: 5 件が **`ImportError` または失敗で赤**（Red）。
- **対応要件**: REQ-F-001・REQ-F-018・REQ-NF-004

#### タスク 3: `MenuUsageLog` エンティティの実装（Green）

- **対象ファイル**: `application/portal/domain/entities/menu_usage_log.py`（新規）
- **内容**: design.md §4.1 のとおり `log_id` / `user_id` / `menu_key` / `usage_type` / `used_at` を持つ追記専用のエンティティを実装する。生成時に `usage_type` が `VIEW` / `EXPORT` のいずれかであることを検証し、外れる場合は `ValueError` を送出する。状態を変更するメソッドは作らない。`import django` を書かない。
- **完了条件**: TC-DOM-001〜005 が緑。
- **対応要件**: REQ-F-001・REQ-F-017・REQ-F-018

#### タスク 4: 記録対象の判別のテスト作成（Red）

- **対象ファイル**: `application/portal/tests/test_usage_record_target.py`（新規）
- **内容**: test-design.md §2.1 の TC-DOM-010〜015・020〜027・030〜039 を実装する。
  - `EXPORT_ENDPOINTS`（TC-DOM-010〜015）／`resolve_menu_key`（TC-DOM-020〜027）／`resolve_usage_record_target` の判定順 1〜5（TC-DOM-030〜039）
  - TC-DOM-015 は全アプリの `urlpatterns` を走査して `export` を含むルートを列挙し、`EXPORT_ENDPOINTS` の 9 件と一致することを検証する（REQ-NF-008）。**このテストはタスク 29 で本機能の CSV 出力 URL を登録するまで赤のままとする**（前提 §0 の中間状態を参照）。
- **完了条件**: TC-DOM-015 を除く 21 件が赤（Red）。TC-DOM-015 は赤のまま残し、タスク 32 で緑にする。
- **対応要件**: REQ-F-001〜004・REQ-F-015・REQ-NF-008

#### タスク 5: `usage_record.py` の実装（Green）

- **対象ファイル**: `application/portal/domain/value_objects/usage_record.py`（新規）
- **内容**: design.md §4.2・§4.4(a)(b) のとおり実装する。
  - `UsageType`（`VIEW` / `EXPORT`）と `USAGE_TYPE_LABELS`
  - `ExportEndpoint`（frozen dataclass）と ファーストクラスコレクション `ExportEndpoints`（`menu_key_for(path, comparison_type)`）、公開インスタンス `EXPORT_ENDPOINTS`（design.md §4.4(b) の 9 件）
  - `UsageRecordTarget`（frozen dataclass）
  - `resolve_menu_key(path, comparison_type)`: `menu_access.is_menu_path_active` と同一の一致規則。パス正規化は `menu_access.py` から再利用する（domain 内 import）
  - `resolve_usage_record_target(...)`: 判定順 1〜5 をこの順で評価する
  - あわせて `application/portal/domain/entities/menu_usage_log.py` の暫定定数 `_USAGE_TYPES` を削除し、`UsageType` を import して値域検証に使う（タスク3 の懸念事項の解消。design.md §4.2 が利用種別の SSOT）
- **完了条件**: TC-DOM-010〜014・020〜027・030〜039 が緑（TC-DOM-015 を除く）。TC-DOM-001〜005 も緑のまま。`import django` を書かない。
- **対応要件**: REQ-F-001〜004・REQ-F-015

### 段 2: 記録側 Application / Infrastructure

#### タスク 6: `MenuUsageLogRepository` ポートの追記

- **対象ファイル**: `application/portal/domain/repositories/ports.py`（変更）
- **内容**: design.md §6.7 のとおり `typing.Protocol` で `MenuUsageLogRepository`（`record(*, user, menu_key, usage_type) -> None`）を追記する。既存のポートは変更しない。更新・削除のメソッドは定義しない（REQ-NF-004）。
- **完了条件**: `pytest config/tests/test_clean_architecture.py` が緑。既存の portal テストが緑。
- **対応要件**: REQ-F-001・REQ-NF-004

#### タスク 7: `RecordUsage` のテスト作成（Red）

- **対象ファイル**: `application/portal/tests/test_usecase_record_usage.py`（新規）
- **内容**: TC-APP-001〜003 を実装する。リポジトリは `Protocol` を満たす小さなフェイククラスに差し替える（DB を使わない・`@pytest.mark.django_db` を付けない）。ドメインモデルはモック化しない。
- **完了条件**: 3 件が赤（Red）。
- **対応要件**: REQ-F-001・REQ-F-002・REQ-F-004

#### タスク 8: `RecordUsage` ユースケースの実装（Green）

- **対象ファイル**: `application/portal/use_cases/record_usage.py`（新規）
- **内容**: design.md §6.7 のとおり `record(*, user, target: UsageRecordTarget) -> None` を実装する。リポジトリの `record()` を呼ぶだけの薄い層とし、判別ロジックを持たない。`import django` および infrastructure / models の import を書かない。
- **完了条件**: TC-APP-001〜003 が緑。`pytest config/tests/test_clean_architecture.py` が緑。
- **対応要件**: REQ-F-001・REQ-F-002

#### タスク 9: `MenuUsageLog` ORM モデルの追加

- **対象ファイル**: `application/portal/models.py`（変更）
- **内容**: design.md §5.1 のコードのとおり `MenuUsageLog` を追加する。`user`（`SET_NULL` / `null=True`）・`menu_key`（`max_length=80`）・`usage_type`（`TextChoices`・`max_length=10`）・`used_at` の 4 列と、`Meta.ordering` と索引 4 本（`menu_usage_used_at_idx` / `menu_usage_menu_key_idx` / `menu_usage_user_idx` / `menu_usage_type_idx`）を定義する。`db_table` は指定しない。IP アドレス・ユーザーエージェント・操作対象データの列は作らない（REQ-NF-005）。既存モデルは変更しない。
- **完了条件**: `python manage.py makemigrations --check --dry-run` が「変更あり」を検出する（次タスクで生成）。既存テストが緑。
- **対応要件**: REQ-F-001・REQ-F-018・REQ-NF-002・REQ-NF-004・REQ-NF-005

#### タスク 10: マイグレーション `0007_menu_usage_log.py` の作成

- **対象ファイル**: `application/portal/migrations/0007_menu_usage_log.py`（新規）
- **内容**: `python manage.py makemigrations portal --name menu_usage_log` で生成する。生成物がテーブル作成と索引 4 本の作成のみであること（既存データの変換を含まないこと）を目視で確認する。依存は `0006_normalize_menu_group_access_keys`。
- **完了条件**: `python manage.py migrate` が成功し、`python manage.py makemigrations --check --dry-run` が差分なしを報告する。
- **対応要件**: REQ-NF-002・REQ-NF-004

#### タスク 11: 記録リポジトリのテスト作成（Red）

- **対象ファイル**: `application/portal/tests/test_usage_status_repository.py`（新規）
- **内容**: TC-INF-001〜006 を実装する。`@pytest.mark.django_db` を付け、実際に `MenuUsageLog` を INSERT して検証する。
  - TC-INF-001 1 行保存 / TC-INF-002 保存項目が 4 つに限られること / TC-INF-003 ユーザー削除後も `user=None` でログが残ること / TC-INF-004 同一ユーザーの繰り返し記録 / TC-INF-005 更新・削除のメソッドを公開しないこと / TC-INF-006 `menu_key` の長さ境界（80 / 81 / 空文字）
  - fixture はこのファイル内に閉じる（`conftest.py` を新設しない）。
- **完了条件**: 6 件が赤（Red）。
- **対応要件**: REQ-F-001・REQ-F-018・REQ-NF-002・REQ-NF-004

#### タスク 12: `DjangoMenuUsageLogRepository` の実装（Green）

- **対象ファイル**: `application/portal/infrastructure/persistence/menu_usage_log_repository.py`（新規）
- **内容**: `MenuUsageLogRepository` ポートを実装する。`record()` は `used_at` に `django.utils.timezone.now()` を設定して 1 行 INSERT する。更新・削除のメソッドは公開しない（REQ-NF-004）。
- **完了条件**: TC-INF-001〜006 が緑。
- **対応要件**: REQ-F-001・REQ-NF-003・REQ-NF-004

### 段 3: 記録側 Interfaces

#### タスク 13: `wiring.py` に記録側ファクトリを追記

- **対象ファイル**: `application/portal/interfaces/wiring.py`（変更）
- **内容**: design.md §6.7 のとおり `get_menu_usage_log_repository()` と `record_usage_usecase()` を追記する。`composition.py` および `services/` は新設しない。既存の関数は変更しない。
- **完了条件**: `pytest config/tests/test_clean_architecture.py` が緑。
- **対応要件**: REQ-F-001

#### タスク 14: `UsageLoggingMiddleware` のテスト作成（Red）

- **対象ファイル**: `application/portal/tests/test_usage_logging_middleware.py`（新規）
- **内容**: TC-UI-001〜011 を実装する。`@pytest.mark.django_db` を付け、`django_test_client` で実リクエストを流して `MenuUsageLog` の行を検証する。
  - 記録される（001 画面表示・006 CSV 出力・009 1 リクエスト 1 件・011 旧 URL リダイレクト後 1 件のみ）
  - 記録されない（002 匿名・003 403・004 302・005 JSON）
  - 失敗時の非中断（007 応答が返ること・008 失敗をユーザーに見せないこと）
  - 010 `settings.MIDDLEWARE` 上で `AccessApprovalMiddleware` の直後にあること
- **完了条件**: 11 件が赤（Red）。
- **対応要件**: REQ-F-001〜004

#### タスク 15: `UsageLoggingMiddleware` の実装（Green）

- **対象ファイル**: `application/portal/interfaces/usage_logging.py`（新規）
- **内容**: design.md §6.6 のとおり実装する。応答生成後に `_record` を呼び、例外は握りつぶして `logger.warning` に落とす（ユーザーには表示しない）。未認証なら何もしない。`resolve_usage_record_target(...)` に `path` / `comparison_type` / `status_code` / `content_type` / `is_attachment` を渡し、`None` でなければ `wiring.record_usage_usecase()` に委譲する。view / infrastructure / models を直 import しない。
- **完了条件**: TC-UI-001〜009・011 が緑（TC-UI-010 はタスク 16 で緑）。
- **対応要件**: REQ-F-001〜004・REQ-NF-003

#### タスク 16: `MIDDLEWARE` への登録

- **対象ファイル**: `config/settings/base.py`（変更）
- **内容**: `MIDDLEWARE` の `application.portal.interfaces.middleware.AccessApprovalMiddleware` の **直後** に `application.portal.interfaces.usage_logging.UsageLoggingMiddleware` を 1 行追加する。既存の行は削除・並べ替えしない。
- **完了条件**: TC-UI-010 を含む TC-UI-001〜011 が緑。`make test-all` が緑（この時点でメニュー利用ログの蓄積が始まる）。
- **対応要件**: REQ-F-001・REQ-F-003

### 段 4: 画面側 Domain

#### タスク 17: `AggregationPeriod` のテスト作成（Red）

- **対象ファイル**: `application/portal/tests/test_usage_period.py`（新規）
- **内容**: TC-DOM-050〜058（`AggregationPeriod`：1 日・逆順・365/366/367 日・未来日・不変性・等価性・既定 30 日）と TC-DOM-060〜066（`parse_aggregation_period`：両方空・片方空・書式不正・正常・順序違反の伝播・前後の空白除去）を実装する。基準日は `today = date(2026, 8, 27)` を引数で与え、`date.today()` を呼ばない。
- **完了条件**: 16 件が赤（Red）。
- **対応要件**: REQ-F-006

#### タスク 18: `usage_period.py` の実装（Green）

- **対象ファイル**: `application/portal/domain/value_objects/usage_period.py`（新規）
- **内容**: design.md §4.2 のとおり `AggregationPeriod`（frozen dataclass。`__post_init__` で検証規則 3・4）・`AggregationPeriodError`（`message` を持つ）・`DEFAULT_AGGREGATION_DAYS=30`・`MAX_AGGREGATION_DAYS=366`・`default_aggregation_period(today)`・`parse_aggregation_period(start, end, *, today)`（検証規則 1・2）を実装する。日付境界（`Asia/Tokyo` の 00:00:00〜翌日 00:00:00）の解釈は持たない。
- **完了条件**: TC-DOM-050〜058・060〜066 が緑。`import django` を書かない。
- **対応要件**: REQ-F-006

#### タスク 19: 行 VO・集計関数のテスト作成（Red）

- **対象ファイル**: `application/portal/tests/test_usage_status_display.py`（新規）
- **内容**: TC-DOM-070〜082（`UsageSummary` / `MenuUsageRows` / `UserUsageRows` / `ExportLogRows` / `UnusedMenuGroupGrantRows` の不変性・`is_empty`・`sorted_by`・`filtered_by_group`・`csv_rows`）と TC-DOM-090〜104（`most_used_menu_key` の最多・同数時のメニューキー昇順・0 件、`build_daily_trend` の欠落日 0 埋め・期間外除外、`unused_user_count`、`dormant_user_count`（未ログインを含む）、`menu_display_title` の廃止表記、`aggregation_target_menu_keys`、`USAGE_STATUS_CSV_ROW_LIMIT`、`USAGE_STATUS_PURPOSE_NOTE`）を実装する。
- **完了条件**: 28 件が赤（Red）。
- **対応要件**: REQ-F-007〜014・REQ-F-016〜018・REQ-NF-005・REQ-NF-007

#### タスク 20: `usage_status_display.py` の実装（Green）

- **対象ファイル**: `application/portal/domain/value_objects/usage_status_display.py`（新規）
- **内容**: design.md §4.2「画面側」の行 VO 6 種（`UsageSummary` / `MenuUsageRow` / `UserUsageRow` / `UnusedMenuGroupGrantRow` / `ExportLogRow` / `DailyUsagePoint`）と、そのファーストクラスコレクション 5 種（`sorted_by` / `filtered_by_group` / `csv_rows` / `is_empty`）、定数（`USAGE_STATUS_CSV_ROW_LIMIT` / `RETIRED_MENU_SUFFIX` / `UNKNOWN_USER_LABEL` / `USAGE_STATUS_SECTIONS` / `*_SORT_LABELS` / `USAGE_STATUS_PURPOSE_NOTE`）、集計関数（`most_used_menu_key` / `build_daily_trend` / `unused_user_count` / `dormant_user_count` / `menu_display_title` / `aggregation_target_menu_keys` / `unused_menu_group_grant_rows`）を実装する。並び替えは共有カーネル `application/shared/domain/value_objects/list_table.py` の `SortSpec` を用いる。すべて frozen とし、絞り込み・並び替えは新しいインスタンスを返す。
- **完了条件**: TC-DOM-070〜082・090〜104 が緑。`import django` を書かない。
- **対応要件**: REQ-F-007〜014・REQ-F-016〜018・REQ-NF-005・REQ-NF-007

### 段 5: 画面側 Application / Infrastructure

#### タスク 21: `UsageStatusRepository` ポートの追記

- **対象ファイル**: `application/portal/domain/repositories/ports.py`（変更）
- **内容**: design.md §6.7 の 11 メソッド（`overall_counts` / `menu_counts` / `last_used_at_by_menu_key` / `user_counts` / `last_used_at_by_user` / `menu_counts_by_user` / `used_menu_keys_by_user` / `daily_counts` / `export_entries` / `approved_user_entries` / `menu_group_grants`）を `Protocol` として追記する。集計期間は aware な `datetime`（`start_at` / `end_at`）で受け取る。タスク 6 で追記した `MenuUsageLogRepository` と既存ポートは変更しない。
- **完了条件**: `pytest config/tests/test_clean_architecture.py` が緑。
- **対応要件**: REQ-F-007〜014

#### タスク 22: `UsageStatus` のテスト作成（Red）

- **対象ファイル**: `application/portal/tests/test_usecase_usage_status.py`（新規）
- **内容**: TC-APP-010〜025 を実装する。リポジトリは test-design.md §3.1 のデータを返すフェイク（`Protocol` を満たす小さなクラス）に差し替え、DB を使わない。
  - `page_context`（010 全区画の組み立て / 011 aware な datetime の受け渡し / 012 不正期間で `error_message`・一覧空 / 013 ログ 0 件 / 014 メニューグループ絞り込み / 015 並び替え / 016 `today` の受け取り / 022 利用目的の注記 / 023〜025 ページング）
  - `csv_payload`（017 区分ごとの行 / 018 未知の区分 / 019 上限ちょうど / 020 上限超過 / 021 不正期間）
- **完了条件**: 16 件が赤（Red）。
- **対応要件**: REQ-F-006〜016・REQ-NF-005・REQ-NF-007

#### タスク 23: `UsageStatus` ユースケースの実装（Green）

- **対象ファイル**: `application/portal/use_cases/usage_status.py`（新規）
- **内容**: design.md §6.7 のとおり `page_context(*, start, end, group_key, sort_key, sort_direction, page, page_size, today)` と `csv_payload(*, section, ...)` を実装する。`AggregationPeriodError` は捕捉して `error_message` に載せ、一覧は空にする。CSV は上限超過時に `(rows=None, error_message=...)` を返す。ページングは共有カーネルの `paginate_rows` を用いる。`import django` および infrastructure / models の import を書かない（`date` → aware な `datetime` の変換は infrastructure に委ねる）。
- **完了条件**: TC-APP-010〜025 が緑。`pytest config/tests/test_clean_architecture.py` が緑。
- **対応要件**: REQ-F-006〜016・REQ-NF-007

#### タスク 24: 集計リポジトリのテスト追記（Red）

- **対象ファイル**: `application/portal/tests/test_usage_status_repository.py`（変更・追記）
- **内容**: TC-INF-010〜028 を追記する（タスク 11 で作成したファイルの末尾に足す。既存のテストは変更しない）。
  - 期間の境界（011 開始日 00:00:00 を含む / 012 終了日 23:59:59.999 を含む / 013 開始前を除く / 014 翌日 00:00:00 を除く / 015 UTC 保存行の `Asia/Tokyo` 解釈）
  - 集計（010 全体 / 016 `VIEW` と `EXPORT` の分離 / 017・018 全期間の最終利用日時 / 019 ユーザー × メニュー / 020 日別 / 021 出力のみ / 022・023 許可済みユーザー / 024 付与日）
  - 異常・エッジ（025 `user=None` を含む / 026 現行定義にないメニューキー / 027 ログ 0 件 / 028 索引 4 本の定義）
- **完了条件**: 19 件が赤（Red）。
- **対応要件**: REQ-F-006〜012・REQ-F-017・REQ-F-018

#### タスク 25: `DjangoUsageStatusRepository` の実装（Green）

- **対象ファイル**: `application/portal/infrastructure/persistence/usage_status_repository.py`（新規）
- **内容**: `UsageStatusRepository` ポートを実装する。design.md §5.3 のとおり `used_at__gte=開始日 00:00:00` / `used_at__lt=終了日の翌日 00:00:00`（`Asia/Tokyo`）で絞り込み、日別は `TruncDate("used_at")` で求める。最終利用日時はキーごとに `ORDER BY used_at DESC LIMIT 1` で取得する（全期間の GROUP BY を行わない）。最多利用メニューの判定は domain に委ねる（`menu_counts_by_user` は `user_id` / `menu_key` / `count` を返すだけ）。集計は DB 側で圧縮する。
- **完了条件**: TC-INF-010〜028 が緑。
- **対応要件**: REQ-F-006〜012・REQ-NF-002

### 段 6: 画面側 Interfaces

#### タスク 26: `wiring.py` に集計側ファクトリを追記

- **対象ファイル**: `application/portal/interfaces/wiring.py`（変更）
- **内容**: `get_usage_status_repository()` と `usage_status_usecase()` を追記する。タスク 13 で追記した関数と既存の関数は変更しない。
- **完了条件**: `pytest config/tests/test_clean_architecture.py` が緑。
- **対応要件**: REQ-F-007〜014

#### タスク 27: 画面・CSV 出力のテスト作成（Red）

- **対象ファイル**: `application/portal/tests/test_usage_status_page.py`（新規）
- **内容**: TC-UI-020〜041 を実装する。`@pytest.mark.django_db` を付け、`django_test_client` で検証する。
  - 認可（020 管理者 200 / 021・022 一般ユーザーは 403 / 023 匿名はログインへ / 024 管理者のメニューにのみ表示）
  - 表示（025 利用目的の注記 / 026 既定 30 日 / 027 不正期間のエラー / 028 該当なし / 029 廃止メニュー / 030 ユーザー不明 / 031 無効ユーザー / 032 メニューグループ絞り込み / 040・041 ページング）
  - CSV（033 区分ごとの出力 / 034 期間・絞り込みの反映 / 035 上限超過時の案内）
  - 自己記録（036 画面表示の `VIEW` / 037 CSV 出力の `EXPORT`）
  - ルーティングと画面設定（038 `slug` プレースホルダより前に解決されること / 039 一覧の画面別設定の必須キー）
- **完了条件**: 22 件が赤（Red）。
- **対応要件**: REQ-F-005〜018・REQ-NF-001・REQ-NF-005・REQ-NF-007

#### タスク 28: `views.py` に view 2 件を追加

- **対象ファイル**: `application/portal/interfaces/views.py`（変更）
- **内容**: `usage_status_page` と `usage_status_export_csv` を追加する。`wiring` のファクトリのみを呼び、`use_cases` / `infrastructure` / `models` を直 import しない。「今日」は `django.utils.timezone.localdate()` で求めて `today` として渡す。認可は既存の `can_access_menu_group`（`management`）に委ね、新たな仕組みを作らない。CSV の文字コード・改行・ファイル名は既存の出力に揃え、上限超過時は画面へ戻して案内を表示する。既存の view は変更しない。
- **完了条件**: TC-UI-021〜023（認可）と TC-UI-033〜035（CSV）が緑。テンプレートを要する TC-UI-020・025〜032・040・041 はタスク 30 で緑にする。
- **対応要件**: REQ-F-006・REQ-F-013〜016・REQ-NF-001

#### タスク 29: `urls.py` にルート 2 件を追加

- **対象ファイル**: `application/portal/interfaces/urls.py`（変更）
- **内容**: design.md §6.2 のとおり `/app/management/usage-status`（`usage_status`）と `/app/management/usage-status/export.csv`（`usage_status_export_csv`）を、`app/management/<str:slug>` のプレースホルダより **前** に追加する。既存のルートは削除・並べ替えしない。
- **完了条件**: TC-UI-038 が緑。TC-DOM-015 が緑になる（タスク 32 で確認する）。
- **対応要件**: REQ-F-005・REQ-F-014

#### タスク 30: テンプレート `usage_status.html` の作成

- **対象ファイル**: `templates/portal/usage_status.html`（新規）
- **内容**: design.md §6.4 の区画 0〜7 を上から順に配置する。利用目的の注記を常時表示し、絞り込みパネル（開始日・終了日・メニューグループ）、全体集計、日別推移（外部ライブラリを使わず CSS の `width` で比率を表現）、4 つの一覧を置く。0 件は「該当なし」を表示し、集計期間が不正なときはエラー文言を絞り込みパネル直下に表示して一覧を描画しない。並び替え・ページングは既存の `portal-list-core.js` / `portal-list-sort-dialog.js` を用いる。
- **完了条件**: TC-UI-020・025〜032・040・041 が緑。
- **対応要件**: REQ-F-006〜013・REQ-F-016〜018・REQ-NF-005・REQ-NF-007

#### タスク 31: `usage-status-list-client.js` の作成

- **対象ファイル**: `static/js/usage-status-list-client.js`（新規）
- **内容**: 既存の `shipment-trend-list-client.js` と同じ役割で、4 つの一覧の画面別設定（列定義・既定の並び替え・CSV 出力の区分）だけを定義する。共通エンジンの実装は複製しない（`ポータル一覧表_共通仕様.md` に準拠）。
- **完了条件**: TC-UI-039 が緑。段 6 の TC-UI-020〜041 がすべて緑。
- **対応要件**: REQ-NF-007

### 段 7: 仕上げ

#### タスク 32: TC-DOM-015 の確認

- **対象ファイル**: `application/portal/tests/test_usage_record_target.py`（確認のみ。必要なら修正）
- **内容**: タスク 29 で URL を登録したことにより、全アプリの `urlpatterns` 走査結果と `EXPORT_ENDPOINTS` の 9 件が一致することを確認する。一致しない場合は、出力エンドポイントの実態に合わせて `EXPORT_ENDPOINTS`（design.md §4.4(b)）を先に修正する（仕様が Single Source of Truth のため、design.md → 実装の順で直す）。
- **完了条件**: `pytest application/portal/tests/test_usage_record_target.py` が全件緑。
- **対応要件**: REQ-NF-008

#### タスク 33: 全体テストとアーキテクチャ検証

- **対象ファイル**: なし（検証のみ）
- **内容**: `make test-all` と `pytest config/tests/test_clean_architecture.py` を実行する。本機能ではアーキテクチャ検証に新規テスト関数を足さない（TC-UI-050）。`git diff --name-only` で `asset_inventory` / `gonenkukumi` / `inventory_order_alert` / `receipt_comparison` / `shipment_trend` の変更が 0 件であることを確認する（test-design.md §4.4 #6）。
- **完了条件**: 両方が緑。対象外コンテキストの変更が 0 件。
- **対応要件**: REQ-NF-006

#### タスク 34: 手動確認

- **対象ファイル**: なし（検証のみ）
- **内容**: test-design.md §4.4 の手動確認 #1〜#5 を実施する（#1 画面表示 3 秒以内・50 万件 / #2 記録遅延 50ms 以内 / #3 同時 50 ユーザー / #4 年間容量の見積り（design.md §5.6） / #5 見た目）。#6 はタスク 33 で実施済み。
- **完了条件**: 各項目の実測値を「タスク実行レポート」に記録する。基準を満たさない項目があれば、Issue として起票する（`manage-issue`）。
- **対応要件**: REQ-NF-002・REQ-NF-003・REQ-NF-004

#### タスク 35: 容量監視の運用手順を追記

- **対象ファイル**: `Document/本番環境デプロイ手順.md`（変更）
- **内容**: design.md §5.6 のとおり、`portal_menuusagelog` を PostgreSQL の容量監視の対象に加える手順を追記する（実測で 50 万件あたり 97.4MB・年間およそ 100MB の増加見込み・保持期間は無期限・削除しない）。追記先の節が見当たらない場合は、どの手順書に書くかをユーザーに確認してから追記する。
- **完了条件**: 手順書に追記され、監視対象の一覧に本テーブルが載っていること。
- **対応要件**: REQ-NF-004

---

## タスク実行レポート

（各タスク完了時にここへ追記する。形式は下記のとおり、`--------------------` で前後を囲む）

--------------------
タスク 1: メニュー項目 `usage-status` を `MENU_ITEMS` に追加（完了 2026/08/27 18:00）

- 懸念事項: タスク 29（URL 登録）までの間、管理メニューに「利用状況」が表示されるがリンク先が 404 になる。開発ブランチ内に限った一時的な状態として許容する。
- 改善事項: なし。design.md §6.1 のとおり 1 項目を管理グループ末尾に追加しただけで、既存項目の変更・削除はない。
- 設計のGoodポイント: メニュー定義が `MENU_ITEMS` の 1 箇所に集約されているため、メニュー追加・グループ所属・アクセス制御が同時に効く。`MENU_BY_KEY` も自動で追随する。
- チーム共有ポイント: 既存 109 テストが緑のまま（`pytest application/portal/tests/`）。メニューグループ「管理」に属するため、アクセス制御は既存の承認済みグループ判定にそのまま乗る。
--------------------

```
--------------------
タスク N: {タスク名}（完了 YYYY/MM/DD HH:MM）

- 懸念事項:
- 改善事項:
- 設計のGoodポイント:
- チーム共有ポイント:
--------------------
```

--------------------

### タスク2: `MenuUsageLog` のテスト作成（✅2026/08/27 18:03）

- **懸念事項**: TC-DOM-003 の入力4種（`"DOWNLOAD"` / `""` / `"view"` / `None`）を `pytest.mark.parametrize` で1関数にまとめた。テスト関数数は1、テストケース数は4となり、レポート上の件数と test-design.md の件数の見え方がずれる。テスト設計の意図（4入力すべてを検証）は満たしている。
- **改善事項**: なし。
- **設計のGoodポイント**: TC-DOM-005（状態変化メソッドを持たない）を `dir()` 走査で表現したことで、将来 `set_*` / `update_*` 系のメソッドが追加されたら自動で赤になる。追記のみという設計判断（REQ-F-017・REQ-NF-004）がテストで守られる。
- **チーム共有ポイント**: 現時点で `ModuleNotFoundError: No module named 'application.portal.domain.entities.menu_usage_log'` により収集エラーで赤（想定どおりの Red）。タスク3 で `menu_usage_log.py` を実装して緑にする。

--------------------

--------------------

### タスク3: `MenuUsageLog` エンティティの実装（✅2026/08/27 18:05）

- **懸念事項**: 利用種別（S-601）の値域を、暫定的にエンティティ内の `_USAGE_TYPES` として持たせた。正式な定義は design.md §4.2 のとおり `value_objects/usage_record.py` の `UsageType` であり、タスク5 で `usage_record.py` を作成した際に、エンティティ側を `UsageType` の import に切り替えて重複を解消する（タスク5 の内容に追記済み）。
- **改善事項**: なし。
- **設計のGoodポイント**: `@dataclass(frozen=True)` ＋ `__post_init__` 検証により、「追記のみ・不正な利用種別のインスタンスを作れない」という設計意図（REQ-F-017・REQ-F-018）がコードの構造そのもので表現できた。既存 `menu.py` の frozen dataclass と書き方も揃っている。
- **チーム共有ポイント**: TC-DOM-001〜005 が緑（8 passed。TC-DOM-003 は parametrize で 4 ケース）。`application/portal/tests/` 全体＋`config/tests/test_clean_architecture.py` で **186 passed**、依存方向の違反なし。

--------------------

--------------------

### タスク4: 記録対象の判別のテスト作成（✅2026/08/27 18:08）

- **懸念事項**: test-design.md の TC-DOM-022 が `/app/production/receipt-comparison` の期待結果を `None` としていたが、このパスは `href` 空の親 `receipt-comparison` のパスであると同時に子「完成品」のリンク先（`?type=finished-product`）でもあるため、TC-DOM-023・024（既定は完成品）と矛盾していた。**仕様が SSOT** の原則に従い test-design.md 側を先に修正（期待結果を「親のキーは返さず子の既定 `receipt-comparison-finished-product` を返す」に変更・テストケース名も `test_resolve_menu_key_never_returns_parent_without_href` に改称）してからテストを書いた。
- **改善事項**: TC-DOM-015 の走査で `/app/production/receipt-comparison/<slug:comparison_slug>/export`（旧 URL のリダイレクト）が引っかかるため、テスト内に `EXCLUDED_EXPORT_ROUTES` として明示した。302 を返すルートであり判定順 1 で除外される。
- **設計のGoodポイント**: TC-DOM-027（`resolve_menu_key` と `is_menu_path_active` の一致）を `MENU_ITEMS` 全走査で書いたため、一致規則を二重に持った瞬間に赤になる。design.md §4.4(a) の「判定規則を二重に持たない」という方針がテストで守られる。
- **チーム共有ポイント**: 現時点で `ModuleNotFoundError: No module named 'application.portal.domain.value_objects.usage_record'` により収集エラーで赤（想定どおりの Red）。TC-DOM-015 はタスク29（URL 登録）まで赤のままである点も想定どおり。

--------------------

--------------------

### タスク5 実行レポート（2026/08/27 18:13）

**懸念事項**

- TC-DOM-015 は意図的に赤のまま残している。原因は `/app/management/usage-status/export.csv` が未登録であることのみ（タスク29 で登録して緑になる）。タスク32 で確認する。
- `resolve_menu_key` はメニュー定義（`MENU_ITEMS`）を先頭から線形探索する。現在14件なので問題ないが、メニューが増えた場合は前方一致の優先順位（より具体的な href を先に評価する）を意識する必要がある。

**改善事項**

- タスク3 で暫定に置いた `_USAGE_TYPES` を削除し、`usage_record.USAGE_TYPES` を import する形に統一した。利用種別（S-601）の SSOT が `usage_record.py` 一箇所になった。
- TC-DOM-015 のテスト設計に欠陥（パスに "export" を含むかどうかで出力ルートを判定していたため `/api/asset-inventory/asp-import.csv` を検出できない）があったため、test-design.md を先に修正し、二段構えの検証（① "export" を含む全ルートが一覧と一致 ② `EXPORT_ENDPOINTS` の全パスが実在のルートに存在）に変更した。

**設計のGoodポイント**

- 出力エンドポイント一覧を `ExportEndpoints`（ファーストクラスコレクション）にしたことで、パス→メニューキーの解決と受入比較（TC-DOM-015）の双方が同じ定義を参照する。
- 記録対象の判別を `resolve_usage_record_target` の純関数に閉じ込めたため、ミドルウェア（タスク15）は Django のリクエスト／レスポンスから5つの値を取り出して渡すだけになる。domain に `import django` は不要のまま。
- 受入判定（`is_attachment` / `content_type` / `status_code`）を先に評価してから解決に進む順序にしたため、対象外リクエストは早期に `None` を返す。

**チーム共有ポイント**

- 出力エンドポイントを新設・改名した場合、`usage_record.EXPORT_ENDPOINTS` への追加を忘れると TC-DOM-015 が赤くなる。テストが仕様の変更検知として機能する。
- 親メニュー（`href` が空の `receipt-comparison`）は利用ログに出てこない。子（完成品／支給品）のキーで記録される。

--------------------

### タスク6: `MenuUsageLogRepository` ポートの追記（✅2026/08/27 18:14）

**懸念事項**

- なし。既存ポートの定義には手を触れていない。

**改善事項**

- ポートの並びは既存の登場順（機能単位）に合わせ、`DatabaseBrowser` の前に挿入した。

**設計のGoodポイント**

- `record()` のみを公開し、更新・削除のメソッドを型レベルで存在させないことで REQ-NF-004（追記のみ）をポートの形で表現した。実装者がうっかり削除メソッドを追加しても、ポートを満たすためではないと分かる。

**チーム共有ポイント**

- ポータルのリポジトリポートは 1 ファイル（`ports.py`）に集約されている。新しい永続化の窓口を作るときはここに追記する。

--------------------

### タスク7: `RecordUsage` のテスト作成（✅2026/08/27 18:15）

**懸念事項**

- なし。DB を使わないため `@pytest.mark.django_db` は付けていない。

**改善事項**

- フェイクは `unittest.mock` ではなく素のクラスにし、呼び出し内容を `calls` に貯める形にした。ポートの引数名（キーワード専用）が変わればテストが壊れるため、契約の変更検知になる。

**設計のGoodポイント**

- TC-APP-003 で「例外を握りつぶさない」ことをユースケース層の契約として固定した。記録失敗を画面に波及させない責務はミドルウェア（タスク15）側にあり、層の分担がテストとして表現されている。

**チーム共有ポイント**

- ユースケースのテストはリポジトリをフェイクに差し替えれば DB 不要で書ける。ドメインモデル（`UsageRecordTarget`）はモック化しない。

--------------------

### タスク8: `RecordUsage` ユースケースの実装（✅2026/08/27 18:15）

**懸念事項**

- なし。TC-APP-001〜003 が緑（全体 231 passed / 1 failed は TC-DOM-015 のみ）。

**改善事項**

- ポートを型注釈として import するだけにとどめ、`import django` も infrastructure / models の import も書いていない。`config/tests/test_clean_architecture.py` は緑。

**設計のGoodポイント**

- ユースケースが 1 メソッド・分岐なしの薄い層に収まった。判別は domain（`resolve_usage_record_target`）、時刻の付与と INSERT は infrastructure に分かれており、どこを直せばよいかが一意に決まる。

**チーム共有ポイント**

- 記録の流れは「ミドルウェア → `RecordUsage.record()` → リポジトリ」の 3 段。ミドルウェアは判別結果（`UsageRecordTarget`）を作って渡すだけになる。

--------------------

### タスク9: `MenuUsageLog` ORM モデルの追加（✅2026/08/27 18:16）

**懸念事項**

- `python manage.py makemigrations --check --dry-run` を全アプリで実行すると、**本機能と無関係の `receipt_comparison` に未生成のマイグレーション差分がある**ことが分かった（`unique_sp_receipt_supplier_vendor_code` の削除と `customer_code` の変更）。本タスクでは触らず、タスク10 の確認は `portal` に限定して行う。別途チームで扱う必要がある。

**改善事項**

- `UsageType` の表示ラベルを design.md のリテラルではなく `usage_record.USAGE_TYPE_LABELS` から引く形にした。既存の `UserAccessRequest` が `access_status` の定数を import している流儀と揃い、利用種別（S-601）の値とラベルの SSOT が domain 側の 1 箇所に保たれる（値は design.md と同一）。

**設計のGoodポイント**

- メニューへの外部キーを持たないため、メニュー定義の改称・削除がログに影響しない（REQ-F-017）。
- `on_delete=SET_NULL` により、ユーザー削除後も利用実績が残る（REQ-F-018）。

**チーム共有ポイント**

- 記録する列は 4 つのみ。IP アドレス・ユーザーエージェント・操作対象データは意図的に持たない（REQ-NF-005）。列を足したくなったら要件から見直す。

--------------------

### タスク10: マイグレーション `0007_menu_usage_log.py` の作成（✅2026/08/27 18:17）

**懸念事項**

- 完了条件の「`makemigrations --check --dry-run` が差分なし」は、タスク9 で判明した `receipt_comparison` の既存差分があるため **`portal` に限定して確認**した（`No changes detected in app 'portal'`）。`receipt_comparison` の差分は本機能とは無関係で、別途対応が必要。

**改善事項**

- なし。生成物を目視確認し、`CreateModel` と索引 4 本のみでデータ変換を含まないことを確認した。依存は `0006_normalize_menu_group_access_keys`（設計どおり）。

**設計のGoodポイント**

- 既存テーブルへの変更を一切伴わないため、リリース時のロールバックはテーブル削除のみで完結する。

**チーム共有ポイント**

- `python manage.py migrate` を適用済み（ローカル）。本番反映はタスク35 の手順書追記とあわせて案内する。

--------------------

### タスク11: 記録リポジトリのテスト作成（✅2026/08/27 18:18）

**懸念事項**

- TC-INF-006 の「メニューキーが空文字なら保存しない」は design.md に明記が無く、test-design.md のみの規定。実装ではリポジトリ側で早期 return する方針とする（例外にすると画面が落ちるため）。タスク12 で実装したうえで design.md に追記するか、次のレビューで判断する。

**改善事項**

- 81 文字の `DataError` はトランザクションを壊すため、`transaction.atomic()` で囲んで後続の検証を実行できるようにした。

**設計のGoodポイント**

- TC-INF-002 をモデルのフィールド名の集合と完全一致で検証したことで、将来 IP アドレス等の列を足すとテストが落ちる。REQ-NF-005（記録項目を増やさない）が仕組みとして守られる。
- TC-INF-005 は公開メソッドが `record` だけであることを完全一致で確認するため、読み取り以外の窓口が増えたら気づける。

**チーム共有ポイント**

- リポジトリのテストは実 DB（PostgreSQL）に INSERT する。`varchar(80)` 超過が `DataError` になるのは PostgreSQL の挙動に依存する。

--------------------

### タスク12: `DjangoMenuUsageLogRepository` の実装（✅2026/08/27 18:19）

**懸念事項**

- なし。TC-INF-001〜006 が緑（全体 237 passed / 1 failed は TC-DOM-015 のみ）。

**改善事項**

- タスク11 の懸念（空文字のメニューキーの扱いが design.md に無い）を解消するため、design.md §5.1 に「メニューキーが空文字の場合は記録しない（リポジトリで早期 return）」を追記した（2026/08/27 追記と明記）。仕様を先に直してから実装を確定させた。

**設計のGoodポイント**

- `used_at` を `timezone.now()` でリポジトリが設定するため、domain / use_cases は現在時刻を知らずに済み、テストで時刻を固定する必要がない。

**チーム共有ポイント**

- 記録は `objects.create()` の 1 回だけで、ロックもトランザクション制御も持たない。同時アクセスで待ちが発生しない構造になっている（REQ-NF-003）。

--------------------

--------------------

### タスク13 実行レポート（2026/08/27 18:22 完了）

**懸念事項**
- `wiring.py` の import が 3 ブロック（use_cases / domain.ports / infrastructure）で肥大化してきている。今後 画面側（タスク26）でさらに 2 件増えるため、可読性の観点では現状が上限に近い。ただし DI コンテナ不使用・組み立ては wiring のみという CLAUDE.md のルール上、分割はしない。

**改善事項**
- `record_usage_usecase()` はキーワード引数（`repository=`）で組み立てた。既存のユースケースは位置引数だが、`RecordUsage.__init__` がキーワード専用（`*`）のため意図的にこの形にしている。今後追加するユースケースもキーワード専用に揃えると読み違えが起きにくい。

**設計のGoodポイント**
- ファクトリの戻り値型を具象（`DjangoMenuUsageLogRepository`）ではなくポート（`MenuUsageLogRepository`）にしたことで、呼び出し側（middleware）が infrastructure を知らずに済む。Clean Architecture テストが緑のまま通ったのはこの型付けの効果。

**チーム共有ポイント**
- 記録側の組み立ては `wiring.record_usage_usecase()` の 1 か所に閉じた。middleware は `wiring` だけを import すればよく、views/infrastructure/models を直接触らない（タスク15 の前提）。
- テスト結果: 237 passed / 1 failed（失敗は TC-DOM-015 のみ。タスク29 で `/app/management/usage-status/export.csv` を登録するまで意図的に赤）。

--------------------

--------------------

### タスク14 実行レポート（2026/08/27 18:28）

**対象ファイル**: `application/portal/tests/test_usage_logging_middleware.py`（新規）

**結果**: TC-UI-001〜011 の 11 件すべてが赤。うち 10 件は `ModuleNotFoundError: No module named 'application.portal.interfaces.usage_logging'`（タスク15 で解消）、TC-UI-010 のみ `settings.MIDDLEWARE` に未登録であることのアサーション失敗（タスク16 で解消）。想定どおりの Red。

**懸念事項**

- TC-UI-005/006 はスタブ用の `ROOT_URLCONF`（テストモジュール内 `urlpatterns`）で JSON 応答と CSV 添付応答を作っている。実際の出荷トレンド／資産棚卸の出力ビューは Oracle・取引先マスタに依存するため、ミドルウェア単体の検証にはスタブが妥当と判断した。実エンドポイントとの結線は各機能の既存テストとタスク34（手動確認）で担保する。
- TC-UI-007 の warning 検証は `logging` のロガー名 `application.portal.interfaces.usage_logging` を前提にしている。タスク15 で `logging.getLogger(__name__)` 以外を使うとテストが落ちるので、実装時に合わせること。
- TC-UI-010 だけが `override_settings` を掛けずに素の `settings.MIDDLEWARE` を見る。他の 10 件は「登録前でもミドルウェアの振る舞いを検証できる」よう `_middleware_with_usage_logging()` で差し込む二段構えにした。タスク16 完了後は両方が同じ並びを見ることになる。

**改善事項**

- `_middleware_with_usage_logging()` は登録済みなら差し込まないため、タスク16 の後もテストは無変更で通る。テストの寿命を伸ばすための工夫として他の feature でも流用できる。
- 記録失敗の注入は `DjangoMenuUsageLogRepository.record` を monkeypatch する方式にした。wiring 側の関数名や組み立て方が変わっても壊れない。

**設計のGoodポイント**

- 記録可否の判定ロジックは `resolve_usage_record_target()`（domain）に閉じているため、ミドルウェアのテストは「HTTP の実際の応答（200／302／403／JSON／attachment）でも同じ結論になるか」の確認に集中できた。ドメイン側の網羅テスト（TC-DOM 系）と役割が重複していない。
- 旧 URL リダイレクト（TC-UI-011）を `follow=True` で通すことで、302 は記録せず遷移先だけ 1 件記録するという要件が結合レベルで検証できている。

**チーム共有ポイント**

- ミドルウェアのテストは「認証済みか」「200 か」「HTML か添付か」の 3 条件でしか記録しない、という判断基準をテスト名がそのまま説明している。仕様変更時はまずこのファイルを読めばよい。
- 記録の失敗は業務操作を止めない（REQ-F-004）ことを TC-UI-007／008 の 2 本で担保している。「応答が返ること」と「利用者に失敗を見せないこと」は別要件なので分けてある。

--------------------

--------------------

### タスク15 実行レポート（2026/08/27 18:30）

**対象ファイル**: `application/portal/interfaces/usage_logging.py`（新規）

**結果**: TC-UI-001〜009・011 の 10 件が緑。TC-UI-010 は `settings.MIDDLEWARE` 未登録のため引き続き赤（タスク16 で解消）。`application/portal/tests/` ＋ Clean Architecture 検証は **247 passed / 2 failed**（残る 2 件は TC-UI-010 と、タスク29 まで意図的に赤の TC-DOM-015 のみ）。

**懸念事項**

- `except Exception` で握りつぶす範囲が `_record()` 全体なので、ドメイン判定の不具合も warning に埋もれる。運用では warning ログの発生件数を監視対象にしておきたい（タスク35 の容量監視と併せて `Document/本番環境デプロイ手順.md` に書く候補）。
- `response.headers` は `StreamingHttpResponse` でも参照できるが、大きな CSV をストリーミングで返す実装に将来変えた場合、`Content-Disposition` の付与タイミングに注意が必要。

**改善事項**

- ログに `exc_info=True` を付け、`path` を添えた。利用者には見せず（TC-UI-008）、開発者には原因が追える形にしている。

**設計のGoodポイント**

- 記録可否の判断は `resolve_usage_record_target()`（domain）に全面委譲し、ミドルウェアは「認証確認 → 判定呼び出し → ユースケース呼び出し」の 3 行だけ。Interfaces 層にビジネスルールが漏れていない。
- `wiring` をモジュールとして import し `wiring.record_usage_usecase()` を都度呼ぶ形にしたため、Interfaces から use_cases / infrastructure を直 import せずに済み、Clean Architecture 検証も緑のまま。

**チーム共有ポイント**

- ミドルウェアは `get_response` の**後**に記録するため、業務ビューの処理時間には影響しない（記録は追記 1 件のみ）。
- 記録対象の増減はミドルウェアではなく `domain/value_objects/usage_record.py`（`EXPORT_ENDPOINTS` と `resolve_menu_key`）を直せばよい。新メニュー追加時の変更点はそこ 1 箇所。

--------------------

--------------------

### タスク16 実行レポート（2026/08/27 18:31）

**対象ファイル**: `config/settings/base.py`（`MIDDLEWARE` に 1 行追加のみ。既存行の削除・並べ替えなし）

**追加内容**: `"application.portal.interfaces.usage_logging.UsageLoggingMiddleware"` を `AccessApprovalMiddleware` の直後、`MessageMiddleware` の前に挿入。

**結果**: TC-UI-001〜011 の 11 件すべて緑。プロジェクト全体のテストは **1255 passed / 1 failed**。残る 1 件は TC-DOM-015（`test_export_endpoints_match_all_export_urlpatterns`）で、タスク29 で `/app/management/usage-status/export.csv` を URL 登録するまで意図的に赤のまま。他アプリ（資産棚卸・5年9組・検収書比較・在庫発注アラート・出荷トレンド）のテストはすべて緑で、ミドルウェア追加による回帰はない。

**懸念事項**

- 挿入位置は `AccessApprovalMiddleware` の直後で固定。将来ここに別のミドルウェアを割り込ませると TC-UI-010 が落ちる。落ちたときは「順序を戻す」か「テストの期待順序を更新する」かを設計判断として明示的に決めること。
- `DEBUG=False` のとき `WhiteNoiseMiddleware` が index 1 に挿入されるが、これは記録対象より前段なので影響しない（静的ファイルは 200 でも `text/html` ではないため記録されない）。

**改善事項**

- 段3（記録側 Interfaces）はこれで完了。以降のリクエストからメニュー利用ログが実際に蓄積され始めるため、段6（画面側）の実装中も実データで確認できる。

**設計のGoodポイント**

- アクセス承認ゲート（`AccessApprovalMiddleware`）より後段に置いたことで、未承認ユーザーの 302／403 が記録側に到達する前に確定しており、「許可された利用のみ記録する」という要件が順序で自然に担保されている。

**チーム共有ポイント**

- 記録は本日この時点から開始される。段6 の画面ができるまでの間も `portal_menu_usage_log` にデータは溜まり続けるので、動作確認時は件数の増加で記録が効いていることを確認できる。
- 記録側（段1〜3）と画面側（段4〜6）を分けた requirements.md §6.3 制約4 の 2 段階区切りは、ここが第 1 段階の完了点にあたる。

--------------------

--------------------

### タスク17 実行レポート（2026/08/27 18:32）

**対象ファイル**: `application/portal/tests/test_usage_period.py`（新規）

**結果**: 16 件（TC-DOM-050〜058・060〜066）を作成し、`ModuleNotFoundError: application.portal.domain.value_objects.usage_period` により収集段階で赤。想定どおりの Red。

**懸念事項**

- TC-DOM-063 は 4 パターン（`2026/08/01` / `2026-13-01` / `abc` / `2026-02-30`）を 1 関数内のループで検証している。`pytest.mark.parametrize` を使うと収集件数が 19 件になり test-design.md の「16 件」とずれるため、テストケース ID と件数を一致させる方を優先した。失敗時にどのパターンかわかるよう `assert` にメッセージを添えてある。

**改善事項**

- 基準日は `TODAY = date(2026, 8, 27)` をモジュール定数にし、`date.today()` を一切呼ばない。テストが実行日に依存せず、365/366/367 日の境界も固定値で検証できる。

**設計のGoodポイント**

- 検証規則 1・2（文字列解釈）を `parse_aggregation_period` の、規則 3・4（値の制約）を `AggregationPeriod.__post_init__` のテストに分けて書けている。VO のコンストラクタで不正値を弾く設計が、そのままテストの分割線になっている。
- TC-DOM-065 で「`parse_` 経由でもコンストラクタの文言がそのまま伝わる」ことを固定したので、規則 3 の検査を parse 側へ重複実装する誤りを防げる。

**チーム共有ポイント**

- エラー文言は画面表示にそのまま使うため、テストで完全一致を固定している。文言を変えるときは requirements.md／design.md §4.2 の検証規則表とセットで直すこと。

--------------------

--------------------

### タスク18 実行レポート（2026/08/27 18:33）

**対象ファイル**: `application/portal/domain/value_objects/usage_period.py`（新規）

**結果**: TC-DOM-050〜058・060〜066 の 16 件すべて緑。Clean Architecture 検証も緑（`import django` なし）。

**懸念事項**

- 日付解釈に `date.fromisoformat()` を使っている。Python 3.11 以降は `20260801` のような区切り無し表記も受け付けるため、`yyyy-mm-dd` 以外がすり抜ける余地がある。画面側は `<input type="date">` で送るため実害は小さいと判断したが、厳密化が必要になったら `datetime.strptime(text, "%Y-%m-%d")` に替える（テストは変更不要）。
- エラー文言を定数（`MESSAGE_*`）に出したので、テストは文言のリテラルを直接持つ形のままにしてある。文言を変えるとテストが落ちる＝仕様変更に気づける、という意図。

**改善事項**

- `MESSAGE_TOO_LONG` は `MAX_AGGREGATION_DAYS` を f-string で埋め込み、上限値と文言が乖離しないようにした。

**設計のGoodポイント**

- `days` を property にしたことで、検証規則 4（366 日上限）とテストの期待値が同じ計算式を共有せず済んでいる（テスト側は具体的な日付ペアで検証）。
- 現在日は `today` 引数で受け取り、domain 内で `date.today()` を呼ばない。テストが実行日に依存しない。
- 規則 1・2 を `parse_aggregation_period`、規則 3・4 を `__post_init__` に配置。どの経路で `AggregationPeriod` を作っても不正な期間のインスタンスは存在しえない。

**チーム共有ポイント**

- 集計期間は「両端を含む」。`days` は `(end - start).days + 1`。SQL 側の絞り込みは終了日の翌日 00:00 未満（design.md §5.3）で、この VO は日付境界の解釈を持たない — 役割分担を混ぜないこと。

--------------------

### タスク 19 実行レポート（2026/08/27 18:41）

--------------------

**懸念事項**
- `usage_status_display.py` が未作成のため Red はモジュール未検出（collection error）で、28 件が個別に赤と数えられる状態ではない。タスク 20 の Green 時に 28 件が緑になることをもって網羅を確認する。
- テストを書く過程で、design.md §4.2 に**引数の型が未定義の関数**（`unused_user_count` / `dormant_user_count` / `unused_menu_group_grant_rows` の `entries`・`grants`）があることが判明した。仕様が SSOT のため、先に design.md §4.2 へ `UserAggregationEntry`・`MenuGroupGrantEntry`（いずれも frozen VO）と関数シグネチャを追記してからテストを確定させた。

**改善事項**
- TC-DOM-101（廃止メニュー）の期待結果にメニューグループ `"—"` が含まれていたが、design.md には対応する関数が無かった。`is_retired_menu(menu_key)` / `menu_group_title(menu_key)` / `UNKNOWN_GROUP_LABEL` を design.md §4.2 に追記し、テストから参照できるようにした。
- 行 VO の生成が長くなるため、テスト内に `_menu_usage_row` / `_user_usage_row` / `_approved_active_entry` のヘルパーを置き、各テストが検証対象の値だけを明示するようにした。

**設計のGoodポイント**
- 並び替えを共有カーネルの `SortSpec` に寄せているため、TC-DOM-074 は「新しいコレクションを返す・元は不変」というコレクション側の契約だけを検証すればよく、並び替え仕様の二重定義が起きない。
- `csv_rows()` のヘッダを `*_SORT_LABELS` の値から作る規約にしたことで、TC-DOM-077 が列ラベルの重複定義を検出できるテストになった。

**チーム共有ポイント**
- 集計関数の入力は Django の ORM オブジェクトではなく `UserAggregationEntry` / `MenuGroupGrantEntry`（domain の frozen VO）で受け渡す。ORM → VO の変換は infrastructure（段5）の責務であり、domain は Django 非依存を保つ。
- 変更ファイル: `application/portal/tests/test_usage_status_display.py`（新規・28 テスト）、`application/portal/docs/spec/01_usage-status/design.md`（§4.2 に VO 2 件・関数 2 件・定数 1 件を追記）。

--------------------

--------------------

### タスク 20 実行レポート（2026/08/27 18:46）

**結果**: `application/portal/domain/value_objects/usage_status_display.py` を新規作成し、TC-DOM-070〜082・090〜104（28 件）が緑。
`python -m pytest config/tests/test_clean_architecture.py application/portal/tests -q` → 292 passed / 1 failed（既知の TC-DOM-015 のみ。タスク 29 で URL 登録後に解消）。

**懸念事項**

- `filtered_by_group` はメニューグループ「キー」を受け取り、行が持つメニューグループ「名」と突き合わせる。
  ユーザー別一覧は 1 行に複数のメニューグループ名を持つため、区切り文字 `GROUP_TITLE_SEPARATOR = "、"` で分割して一致判定している。
  段 5 でユーザー別行を組み立てる際は、必ずこの区切り文字で連結すること（連結側と分割側の取り決めが暗黙になっている）。
- 並び替えキー `_sort_key` は未設定（None）を空文字に寄せている。日付列・文字列列では問題ないが、
  数値列に None が混ざると比較エラーになる。数値列（回数）は必ず 0 埋めで渡す前提。

**改善事項**

- 4 つのコレクションに共通の `is_empty` / `sorted_by` / `filtered_by_group` / `csv_rows` を `_RowCollection` に集約し、
  差分（並び替えの既定・グループ一致の判定）だけを各コレクションで上書きする形にした。
  行が増えても CSV ヘッダは `*_SORT_LABELS` の定義 1 か所を直せば追随する。
- メニューグループキー → メニューグループ名の解決を `menu_group_title_by_key` として切り出し、
  絞り込みと未利用のメニューグループ付与の行組み立てで共用した。

**設計のGoodポイント**

- 並び替えは共有カーネル `application/shared/domain/value_objects/list_table.py` の `SortSpec` をそのまま使い、
  `LABELS` に無い列は黙って無視する。画面からの不正なクエリで例外にならない。
- 集計関数の入力を `UserAggregationEntry` / `MenuGroupGrantEntry` という frozen な VO に限定したため、
  domain は Django に一切依存しない（`import django` なし）。clean architecture テストも緑。
- 行 VO・コレクションはすべて frozen。絞り込み・並び替えは新しいインスタンスを返し、元のコレクションを壊さない。

**チーム共有ポイント**

- 出力ログ一覧（`ExportLogRows`）は**構築時に日時の降順へ整列**する。呼び出し側で並べ直す必要はない。
- 廃止メニュー（現行定義に無いメニューキー）は表示名に `（廃止）`、メニューグループ名は `—`（`UNKNOWN_GROUP_LABEL`）になる。
- 集計対象メニューキーは `aggregation_target_menu_keys()`。遷移先を持たない親メニュー（検収書比較）は除外される。

**変更ファイル**

- `application/portal/domain/value_objects/usage_status_display.py`（新規）
- `application/portal/docs/spec/01_usage-status/tasks.md`（本レポート・チェックシート更新）

--------------------

--------------------

### タスク 21 実行レポート（2026/08/27 18:47）

**結果**: `application/portal/domain/repositories/ports.py` に `UsageStatusRepository`（11 メソッド）を追記。
`python -m pytest config/tests/test_clean_architecture.py -q` → 69 passed。既存ポートと `MenuUsageLogRepository` は変更していない。

**懸念事項**

- 集計期間を `start_at` / `end_at`（aware な `datetime`）で受け取る取り決めのため、`date` → `datetime` の変換責務は infrastructure 側にある。
  ユースケース（タスク 23）は `AggregationPeriod`（`date`）を持ち、境界の解釈（`Asia/Tokyo` の 00:00:00 〜 翌日 00:00:00 未満）はリポジトリ実装（タスク 25）が担う。この分担を実装時に取り違えないこと。
- 戻り値の多くが `list[dict[str, object]]` で、キー名の取り決めがポートの型では表現できない。
  キー名は design.md §6.7 と test-design.md §3.1 が唯一の根拠になるため、タスク 22 のフェイクとタスク 25 の実装で必ず一致させる。

**改善事項**

- design.md §6.7 のポート定義のうち、ユーザー ID をキーとする 2 メソッド（`last_used_at_by_user` / `used_menu_keys_by_user`）の
  キー型が `str` になっていたため、実体（`user_id` は `int`）に合わせて `dict[int, ...]` へ修正した（仕様が SSOT のため design.md を先に修正）。

**設計のGoodポイント**

- 記録側（`MenuUsageLogRepository`）と集計側（`UsageStatusRepository`）をポートとして分離した。
  記録側は `record` 1 メソッドのみを公開し、更新・削除の手段を持たない（追記専用を型で表現）。
- 集計を 11 個の細かい問い合わせに分けたことで、DB 側で圧縮した結果だけを domain に渡せる（REQ-NF-002）。

**チーム共有ポイント**

- `menu_counts_by_user` は最多利用メニューを判定しない。`(user_id, menu_key, count)` を返すだけで、判定は domain の `most_used_menu_key` が担う。
- `last_used_at_by_menu_key` / `last_used_at_by_user` は**全期間**が対象（集計期間の引数を取らない）。

**変更ファイル**

- `application/portal/domain/repositories/ports.py`（変更）
- `application/portal/docs/spec/01_usage-status/design.md`（§6.7 のキー型を修正）
- `application/portal/docs/spec/01_usage-status/tasks.md`（本レポート・チェックシート更新）

--------------------

--------------------

### タスク22 実行レポート (2026/08/27 18:57)

**結果**: `application/portal/tests/test_usecase_usage_status.py` を新規作成。TC-APP-010〜025（テスト関数 20 件、うち TC-APP-017 は区分 4 つのパラメタライズ）を実装。`UsageStatus` が未実装のため収集時点で `ModuleNotFoundError` となり Red を確認。

**変更ファイル**:
- `application/portal/tests/test_usecase_usage_status.py`（新規）
- `application/portal/docs/spec/01_usage-status/design.md`（§6.7 に戻り値のキーを追記・仕様先行修正）
- `application/portal/docs/spec/01_usage-status/test-design.md`（TC-APP-025 の期待結果を共有カーネルの規約に合わせて修正）

**懸念事項**:
- タイムゾーンの扱い。TC-APP-011 が「リポジトリに aware な datetime を渡す」ことを求める一方、`use_cases` は Django 非依存でなければならない。`UsageStatus(repository, tzinfo=...)` として `wiring` が `timezone.get_current_timezone()` を渡す形に design.md を修正した。タスク26（wiring）で渡し漏れると本番だけ naive になるため、TC-UI 側で確認する。
- CSV 上限のテスト（TC-APP-019/020）は 10 万行の行 VO を生成するため、単体テストとしては重い（実行時間が延びる場合はタスク33で計測する）。

**改善事項**:
- design.md §6.7 にリポジトリ 11 メソッドの戻り値キー・`page_context()` のコンテキストキー・`csv_payload()` の戻り値（`CsvPayload`）を表と dataclass で明文化した。テストとタスク23の実装が同じ契約を見られるようになった。
- test-design.md TC-APP-025 が「最終ページ超過で空になる」と書かれていたが、共有カーネル `paginate_rows` は最終ページに丸める仕様（`test_list_table.py` で既定）。TC-APP-023 の「共有カーネルの戻り値をそのまま使う」と矛盾するため、期待結果を「最終ページに丸める」へ修正した（テスト名も `test_page_context_clamps_page_beyond_last_page`）。

**設計のGoodポイント**:
- 期間不正のときリポジトリを 1 度も呼ばない契約（TC-APP-012）をフェイクの呼び出し記録で直接検証できる。無駄な集計クエリが走らないことをテストで固定できた。
- 行 VO・ファーストクラスコレクション（タスク20）に絞り込み・並び替え・CSV 化が入っているため、ユースケース側のテストは「組み立てた結果」だけを見ればよく、アサーションが短い。

**チーム共有ポイント**:
- 集計期間は半開区間（`start_at` = 開始日 00:00、`end_at` = 終了日翌日 00:00）で受け渡す。タスク25 の `used_at__gte` / `used_at__lt` と対になる。
- ユーザー別一覧は「利用ログのあるユーザー」ではなく「利用申請が許可済みかつ有効なユーザー」を母集団とし、ログが 0 件のユーザーも 0 回として並べる（§8.2 の無効化ユーザー除外と対応）。

--------------------

--------------------

### タスク23 実行レポート (2026/08/27 19:02)

**結果**: `application/portal/use_cases/usage_status.py` を新規作成し、TC-APP-010〜025（20 テスト）が Green。
`config/tests/test_clean_architecture.py` + `application/portal/tests` は 312 passed / 1 failed で、
唯一の失敗は TC-DOM-015（`test_export_endpoints_match_all_export_urlpatterns`）＝タスク29 で URL を登録するまで意図的に赤のまま。

**変更ファイル**:
- `application/portal/use_cases/usage_status.py`（新規）

**懸念事項**:
- `page_context()` は 4 つの一覧すべてに同じ `page` / `page_size` を適用する仕様のため、
  一覧ごとに件数差が大きいと片方だけ最終ページに丸められる。仕様どおりだが、画面側（タスク30）で
  各一覧のページ番号が同期して見えることをユーザーに分かる形で示す必要がある。
- ユーザー別一覧・未利用付与一覧の母集団は「承認済みかつ有効なユーザー」に限定した。
  無効化ユーザーの付与は表示されないため、退職者の権限棚卸しは別の観点（ユーザー管理画面）で行う想定。
- 未利用メニューグループの判定は、利用したメニューキー → メニューグループキーへの変換に
  `MENU_BY_KEY` を用いる。廃止メニューのログはグループに紐付かないため未利用判定に寄与しない
  （廃止済みメニューを使っていた付与は「未利用」として残る）。

**改善事項**:
- 期間の datetime 変換（`_range`）をユースケースに閉じ込め、`tzinfo` を注入する形にしたことで、
  `use_cases` から Django のタイムゾーン API を完全に排除できた。タスク26 の wiring で
  `timezone.get_current_timezone()` を渡し忘れないこと。
- 絞り込み → 並び替え → ページングの順序を `_filtered_and_sorted` に集約し、
  `page_context()` と `csv_payload()` が同じ経路を通るようにした（画面と CSV の内容が必ず一致する）。

**設計のGoodポイント**:
- 一覧の絞り込み・並び替え・CSV 行化はすべて domain のファーストクラスコレクション側にあり、
  ユースケースは「リポジトリの生データ → 行 VO への組み立て」と「順番の適用」だけを担う薄い層に収まった。
- 集計期間が不正なときはリポジトリを 1 度も呼ばずに空の表示を返すため、
  不正入力で DB に無駄なクエリが飛ばない。テストはフェイクの `calls` で検証できる。

**チーム共有ポイント**:
- リポジトリに渡す期間は半開区間 `[開始日 00:00, 終了日翌日 00:00)`。
  タスク25 の実装は `used_at__gte` / `used_at__lt` で受けること（`__lte` は不可）。
- CSV 上限超過時は例外ではなく `CsvPayload(rows=None, error_message=...)` を返す。
  Interfaces 側（タスク27）はこの `error_message` を画面に戻す責務を持つ。
- `sort_key` が空のときは並び替えを行わず、リポジトリ／domain が組み立てた順のまま返す。

--------------------

### タスク24: 集計リポジトリのテスト追記（TC-INF-010〜028）

**完了日時**: 2026/08/27 19:11

**結果**: 19 件を `application/portal/tests/test_usage_status_repository.py` の末尾に追記した。
`DjangoUsageStatusRepository` が未実装のため、モジュールの import で
`ModuleNotFoundError: No module named 'application.portal.infrastructure.persistence.usage_status_repository'`
となり、テストは赤（Red）。既存の TC-INF-001〜006 は変更していない。

**変更ファイル**:

- `application/portal/tests/test_usage_status_repository.py`（追記。テスト関数は 6 件 → 25 件）
- `application/portal/docs/spec/01_usage-status/test-design.md`（TC-INF-025 の期待結果 1 セルを修正）

--------------------

**懸念事項**

- TC-INF-025 の期待結果が design.md §6.7 と食い違っていた（test-design.md は「ユーザー別には
  `user_id=None` として現れる」、design.md は「ユーザー別集計には含めない」）。SDD ルール
  （仕様が Single Source of Truth・実装中の仕様変更は仕様書を先に直す）に従い、
  design.md を正として test-design.md の当該セルを修正してからテストを書いた。
- TC-INF-016 / 019 / 020 は、test-design.md §3.1 の共通データセットでは期待値
  （表示 2 回・出力 1 回、メニュー別 3 件と 1 件、日別 3 件と 1 件）が成立しないため、
  各テスト内で専用のデータを組み立てている。共通 fixture との二重管理になる点は
  タスク25 の緑化後に必要なら整理する。

**改善事項**

- `PortalMenuGroupAccess.created_at` は `auto_now_add` のため、付与日を制御するテストでは
  作成後に `.filter(pk=...).update(created_at=...)` で上書きする必要がある。
  ヘルパー `_grant()` に閉じ込めて、以降のテストが意識しなくて済むようにした。
- 期間の指定は半開区間（`start_at` 以上・`end_at` 未満）に統一し、
  `PERIOD_END_AT = 2026-08-06 00:00 JST` という形で定数化した。
  「終了日の 23:59:59.999 を含む／翌日 00:00 を含まない」という境界の意図が読み取りやすくなる。

**設計のGoodポイント**

- design.md §6.7 が「infrastructure は `menu_key` を返すだけ。メニュー名・グループ名の解決と
  最多利用メニューの判定は domain」と切っているため、テストも
  「回数を返すか」だけを検証すればよく、ドメインのルール変更に引きずられない。
- 最終利用日時（`last_used_at_by_menu_key()` / `last_used_at_by_user()`）だけ全期間を見る
  という仕様が明文化されていたので、期間内の集計テストと分けて素直に書けた。

**チーム共有ポイント**

- 利用ユーザー数（V-604）は「ログを持つユーザーの実数。無効なユーザーも含む」。
  一方で物理削除により `user_id` が NULL になったログは実数に数えない。
  §3.1 のデータでは `active_user_count == 2` になる。
- タイムゾーン境界のテストでは `timezone.now()` を使わず、
  必ず `ZoneInfo("Asia/Tokyo")` を明示した `datetime` を組み立てる（test-design.md §3.3）。
  UTC で保存された行が JST の日付で集計されることは TC-INF-015 で担保している。

--------------------

### タスク25: `DjangoUsageStatusRepository` の実装

**完了日時**: 2026/08/27 19:14

**結果**: `application/portal/infrastructure/persistence/usage_status_repository.py` を新規作成し、
design.md §6.7 の 11 メソッドを実装した。TC-INF-010〜028 は緑（19 件）。
同ファイルの既存 TC-INF-001〜006 と合わせて 25 件が通る。
`config/tests/test_clean_architecture.py` ＋ `application/portal/tests` は 331 passed / 1 failed。
唯一の失敗は TC-DOM-015（`test_export_endpoints_match_all_export_urlpatterns`）で、
タスク29 で `/app/management/usage-status/export.csv` を登録するまで意図的に赤のまま。

**変更ファイル**:

- `application/portal/infrastructure/persistence/usage_status_repository.py`（新規）

--------------------

**懸念事項**

- `menu_group_grants()` と `approved_user_entries()` は集計期間を受け取らないため、
  許可済みユーザーが増えるほど行数が線形に増える。現在の想定規模（数十〜数百ユーザー）では
  問題ないが、母集団が大きくなった場合は use_case 側の突き合わせごと見直しが要る。
- `export_entries()` は出力操作の記録をすべて返す。REQ-NF-003 の CSV 上限は use_case 側
  （`CsvPayload`）で見ているので、期間を広く取ると一時的に大きなリストを持つ。

**改善事項**

- 最終利用日時は design.md §5.3 の「キーごとに `ORDER BY used_at DESC LIMIT 1`」ではなく
  `values(...).annotate(Max("used_at"))` の 1 クエリにした。結果は同じで、
  メニュー数・ユーザー数ぶんのクエリ発行を避けられる。索引 `menu_usage_menu_key_idx` /
  `menu_usage_user_idx` がそのまま効く。
- 「利用ユーザー数」「メニュー別の利用ユーザー数」は `Count("user", distinct=True)` で数えている。
  SQL の `COUNT(DISTINCT ...)` は NULL を数えないため、物理削除されたユーザーの行が
  自動的に母集団から外れる（V-604・design.md §6.7 と一致）。

**設計のGoodポイント**

- 期間の絞り込みを `_logs_in_period()` 1 箇所に閉じ込めたので、半開区間（`gte` / `lt`）の
  ルールがメソッドごとにぶれない。日付境界の仕様変更があってもここだけ直せばよい。
- メニュー名・グループ名の解決と最多利用メニューの判定を domain に残したことで、
  infrastructure が `menu_key` と回数だけを返す薄い層になった。
  メニュー定義が変わってもこのファイルは影響を受けない。

**チーム共有ポイント**

- 日別推移の日付は `TruncDate("used_at")`。DB 側で現在のタイムゾーン（`Asia/Tokyo`）に
  変換されるため、UTC で保存された行も JST の日付で集計される（TC-INF-015 で担保）。
- 付与日（V-613）は `created_at` を `timezone.localtime()` してから `.date()` を取る。
  UTC のまま日付を取ると、深夜に付与された分が前日にずれる。

--------------------

--------------------

### タスク 26 実行レポート（2026/08/27 19:17）

**結果**: 完了。`pytest config/tests/test_clean_architecture.py` → 69 passed。

**変更ファイル**: `application/portal/interfaces/wiring.py`（変更のみ。既存関数・タスク 13 で追記した `get_menu_usage_log_repository()` / `record_usage_usecase()` は無変更）

- 追記した関数: `get_usage_status_repository()`（`DjangoUsageStatusRepository` を返す）、`usage_status_usecase()`（`UsageStatus(get_usage_status_repository(), tzinfo=timezone.get_current_timezone())`）
- 追記した import: `django.utils.timezone` / `UsageStatus` / `UsageStatusRepository` / `DjangoUsageStatusRepository`

**懸念事項**

- `timezone.get_current_timezone()` はモジュール読み込み時ではなく `usage_status_usecase()` 呼び出し時に評価される。ここを定数化すると `settings.TIME_ZONE` 変更やテストの `override_settings` が効かなくなるため、呼び出しごとの評価を維持すること。
- `wiring.py` に初めて `django.utils` の直接 import が入った。interfaces 層なので依存方向の違反ではない（`config/tests/test_clean_architecture.py` が緑で確認済み）が、今後 wiring に Django 依存を増やす場合はレイヤー越境が起きていないか都度確認したい。

**改善事項**

- `usage_status_usecase()` は毎回リポジトリを生成する。既存の他ファクトリ（`menu_access_usecase()` 等）と同じ方針で統一しており、状態を持たないため問題はない。キャッシュ化する場合は全ファクトリを一括で見直す。

**設計のGoodポイント**

- タイムゾーンの決定を use case ではなく wiring に置いたことで、`UsageStatus` が Django 非依存のまま保たれた。テストでは任意の `tzinfo` を注入して検証できる。
- 記録側（タスク 13）と画面側（本タスク）でファクトリを分けたため、views が必要な側だけを取得できる。

**チーム共有ポイント**

- 利用状況画面の view からは `wiring.usage_status_usecase()` のみを呼ぶ。`DjangoUsageStatusRepository` や `UsageStatus` を views から直接 import しないこと。
- `tzinfo` の受け渡しは wiring の責務。新しく `UsageStatus` を生成する箇所を作る場合は必ず `timezone.get_current_timezone()` を渡す（渡し忘れると naive datetime で集計期間がずれる）。

--------------------

### タスク27: 画面・CSV 出力のテスト作成（TC-UI-020〜041）[✅2026/08/27 19:32]

**結果**: 21 failed / 4 passed（Red を確認）。

**変更ファイル**:
- `application/portal/tests/test_usage_status_page.py`（新規・22 テスト関数／`export_returns_csv_per_section` は 4 区分の parametrize）
- `application/portal/docs/spec/01_usage-status/test-design.md`（TC-UI-028 の期待結果と §4.2「対象 0 件」行を実装可能な内容へ修正）

**失敗の内訳（想定どおりの Red）**: URL 未登録による 404（8 件）、`reverse("portal:usage_status")` の NoReverseMatch（1 件）、`static/js/usage-status-list-client.js` 未作成による FileNotFoundError（1 件）、それらに起因する context/CSV/ログ記録の assert 失敗。

**先に通った 4 件**: 一般ユーザーの 403（画面・CSV）、未ログイン時の `/login` リダイレクト、管理者メニューのみへの表示。いずれも既存の `AccessApprovalMiddleware` と `MENU_ITEMS` で満たされており、view 側に認可コードを書く必要がないことを裏づけている。

**懸念事項**:
- TC-UI-028 の元の期待結果「4 つの一覧すべてに『該当なし』」は design.md §6.4 および実装済みの `UsageStatus` と矛盾していた（メニュー別は集計対象メニューを常に全件、ユーザー別は承認済み有効ユーザーを常に全件並べる）。CLAUDE.md「仕様が SSOT・仕様を先に直す」に従い test-design.md を先に修正してからテストを書いた。TC-INF-025 に続き 2 件目の仕様先行修正。
- TC-UI-041（`?page=abc&size=-1`）は `paginate_rows` が page しかクランプしないため、view 側で size のサニタイズが必要。タスク28 の実装時に落とさないこと。
- TC-UI-035 は `UsageStatus.csv_payload` を monkeypatch している。タスク28 で view が `csv_payload` 以外の経路で CSV を組み立てると、このテストが意味を失う。

**改善事項**:
- CSV の契約（`text/csv; charset=utf-8` / `attachment; filename="usage_status_{section}.csv"` / BOM + CRLF / 先頭行は各 SORT_LABELS の値）をテスト側で先に固定した。タスク28 はこれに合わせるだけでよい。
- TC-UI-039 の JS 静的検証で `menu-usage-rows` 等 4 つの `json_script` 要素 ID を先に決めたため、タスク30（テンプレート）とタスク31（JS）の ID がぶれない。

**設計のGoodポイント**:
- 認可（ミドルウェア）と利用ログ記録（`UsageLoggingMiddleware`）が横断関心として切り出されているため、画面テスト 22 件のうち 4 件が view 実装前に green になった。責務分離が効いている証拠。
- グループ絞り込み・並び替え・ページングがすべて Domain 層の VO（`filtered_by_group` / `sorted_by` / `paginate_rows`）に載っているため、Interfaces 層のテストはクエリパラメータの受け渡しだけを検証すればよく、テストが薄く保てた。

**チーム共有ポイント**:
- 画面テストの HTML 直接 assert はサイドバーのメニュー名と衝突しうる（例:「資産棚卸結果」）。絞り込み系は `response.context` を見る、HTML を見るのは画面固有の文言（「（廃止）」「（ユーザー不明）」「利用目的の注記」）に限る、という使い分けにした。
- `MenuUsageLog.used_at` は `auto_now_add` を持たないため、テストから任意日時のログを作れる。集計期間のテストはこの前提に依存している。

--------------------

--------------------

### タスク28: `views.py` に view 2 件を追加 [✅2026/08/27 19:37]

**結果**: `usage_status_page` / `usage_status_export_csv` を追加。`pytest config/tests/test_clean_architecture.py` 69 件緑。
`application/portal/tests/` 全体は 22 failed / 266 passed（内訳: 利用状況画面テスト 21 件＋TC-DOM-015 の 1 件。
**いずれもタスク 29〜31 未着手が原因**で、既存テストの退行は 0 件）。

**変更ファイル**: `application/portal/interfaces/views.py`（追加のみ・既存 view は無変更）

**完了条件の達成状況（正直な報告）**:

| 完了条件 | 状態 | 補足 |
|---------|------|------|
| TC-UI-021〜023（認可） | ✅ 緑 | ただしタスク 27 の時点から緑。ミドルウェアが 403／`/login` を返すため view 追加の有無に依存しない |
| TC-UI-033・034（CSV 出力） | ⏳ 未緑 | URL 未登録（404）。**タスク 29 で緑になる** |
| TC-UI-035（上限超過の案内） | ⏳ 未緑 | URL に加えテンプレートも必要。**タスク 30 で緑になる** |

--------------------

**懸念事項**

- タスク 28 の完了条件に挙がっていた TC-UI-033〜035 は、**この 1 ファイルだけでは緑にできない**（ルート登録＝タスク 29、テンプレート＝タスク 30 が前提）。
  tasks.md の完了条件の書き方が「1 タスク＝1 ファイル」の原則とやや噛み合っていない。実装は仕様どおりだが、緑化の判定はタスク 29・30 で行う。
- `_positive_int` を view 側に置いた。`paginate_rows` は `page` の上限クランプのみで `page_size` を検証しないため、
  不正な `size`（`-1`・`abc`）のサニタイズは Interfaces 層の責務として実装した（TC-UI-041 対応）。
  同じ処理が他の一覧画面（出荷トレンド等）にも散在しているなら、将来 `shared` へ寄せる余地がある。
- CSV 上限超過時に `page_context` を再計算するため、集計クエリが 2 度走る（`csv_payload` と `page_context`）。
  上限超過は例外的な経路であり、通常時は 1 回のみ。現状は素直さを優先した。

**改善事項**

- CSV 出力の実体（BOM＋CRLF＋`Content-Disposition`）を `_csv_response` に切り出したので、
  今後 portal に CSV 出力が増えても同じヘルパーを再利用できる。
- クエリ読み取りを `_usage_status_query` に集約したことで、画面と CSV で期間・絞り込み・並び順の解釈が必ず一致する（TC-UI-034 の要求）。

**設計のGoodポイント**

- view は `wiring.usage_status_usecase()` だけを呼び、`use_cases` / `infrastructure` / `models` を一切 import していない。
  `test_clean_architecture.py` 69 件が緑のまま通ったことで依存方向が機械的に担保された。
- 認可を新規に書かず既存の `AccessApprovalMiddleware`（`/app/management/*`）へ委ねたため、view 側に権限判定コードが 1 行も無い。
- 「今日」を `timezone.localdate()` で view が決め、use_case には `today` として渡す構造になっているため、
  use_case 層は Django に依存せずテストで任意の日付を注入できる。

**チーム共有ポイント**

- 利用状況の CSV 契約: `text/csv; charset=utf-8` / `attachment; filename="usage_status_{section}.csv"` / BOM 付き UTF-8 / CRLF。
- `page` は `paginate_rows` が丸めるが `size` は丸めない。**一覧画面を追加するときは view 側で `size` を検証すること**。
- 上限超過時は CSV を返さず画面へ戻す。したがって `Content-Disposition` が付かないレスポンスが正常系として存在する。

--------------------

--------------------

### タスク29: `urls.py` にルート 2 件を追加 [✅2026/08/27 19:39]

**結果**: `app/management/usage-status`（`usage_status`）と `app/management/usage-status/export.csv`（`usage_status_export_csv`）を
`app/management/<str:slug>` プレースホルダの**直前**に追加。既存ルートは削除・並べ替えなし。

- TC-UI-038（プレースホルダより先に解決される）✅ 緑
- TC-DOM-015（`EXPORT_ENDPOINTS` 9 件と urlpatterns の一致）✅ 緑 — `test_usage_record_target.py` 43 件すべて緑
- TC-UI-033・034（CSV 出力）✅ 緑
- 画面テストは 15 failed / 10 passed。内訳は **TemplateDoesNotExist 14 件（タスク 30）＋ JS ファイル未作成 1 件（タスク 31）** のみ

**変更ファイル**: `application/portal/interfaces/urls.py`（2 ルート追加のみ）

--------------------

**懸念事項**

- `app/management/<str:slug>` が総取りするプレースホルダのため、**新規ルートを必ずその前に置く**という暗黙のルールがある。
  TC-UI-038 がこの順序を守る番人になっているが、`urls.py` 自体にはコメントが無く、順序を崩す変更が起きうる。

**改善事項**

- 追加を 2 行だけに留め、既存 4 ルートの並びに手を入れなかったため差分が読みやすい。

**設計のGoodポイント**

- CSV の URL を `.../export.csv` と拡張子付きにしたことで、画面 URL とプレースホルダの双方と衝突しない。
- `EXPORT_ENDPOINTS`（domain）と `urlpatterns`（interfaces）の突き合わせテスト（TC-DOM-015）があるため、
  出力系ルートの追加漏れ・記録漏れがテストで自動検知される。実際、今回のルート追加でこのテストが自然に緑へ戻った。

**チーム共有ポイント**

- **portal に新しい `/app/management/...` を足すときは、必ず `<str:slug>` より前に書く。**
- **CSV 出力を新設したら `EXPORT_ENDPOINTS` にも追加する。**忘れると TC-DOM-015 が落ちる。

--------------------

### タスク30 実行レポート (2026/08/27 19:55)

**結果**: `templates/portal/usage_status.html` を新規作成し、TC-UI-020・025〜032・040・041 を含む
`test_usage_status_page.py` は **24 passed / 1 failed**。残る 1 件は
`test_usage_status_list_client_js_defines_required_keys`（タスク31 で作成する JS が未存在）のみ。

**変更ファイル**:
- `templates/portal/usage_status.html`（新規）— design.md §6.4 区画 0〜7
- `templates/portal/includes/usage_status_footer.html`（新規）— 4 一覧で共通のページ送りフッタ
- `application/portal/tests/test_usage_status_page.py`（1 アサーション修正）

--------------------

**懸念事項**

- `sort` / `dir` / `page` / `size` が 4 一覧で共通のため、ある一覧を 2 ページ目にすると他の 3 一覧も 2 ページ目になる。
  design.md §6.4 の合意どおりだが、運用で「一覧ごとに独立したページ送り」を求められたらクエリキーの分割（`menus_page` 等）が必要になる。
- テストのアサーション 1 件（`user_usage_rows.rows == []`）が test-design.md TC-UI-028
  （ユーザー別は承認済み有効ユーザーを 0 回でも全件並べる）と矛盾していた。仕様を SSOT として
  テスト側を TC-UI-030 の記述（「（ユーザー不明）はユーザー別一覧に現れない」）に合わせて修正した。
  **プロダクションコードは変更していない。**

**改善事項**

- ページ送りフッタは 4 一覧で同一のため、`templates/portal/includes/usage_status_footer.html` に切り出した。
  1 タスク 1 ファイル原則から 1 ファイル増えるが、同じマークアップの 4 重複を避けるほうが保守しやすいと判断した。
- 画面固有のスタイルは `{% block extra_head %}` 内の `<style>` に閉じ込め、`static/css/app.css` を変更しなかった。
  既存の `.card` / `.db-table*` / `.muted` / `.error` / `.button-link` を再利用している。

**設計のGoodポイント**

- ヘッダのラベルを `sort_labels`（＝ドメインの `*_SORT_LABELS`）から生成しているため、
  画面ヘッダと CSV ヘッダが必ず一致する。ラベル変更時の直し漏れが構造的に起きない。
- 絞り込み・並び替え・ページ送りをすべて素の GET フォームで組んだため、JS なしでも全機能が動く。
  `usage-status-list-client.js`（タスク31）は操作性の上乗せに徹する。
- 日別推移は `{% widthratio %}` とインライン `width` の横棒のみで実装し、外部ライブラリ依存を作らなかった。

**チーム共有ポイント**

- **集計期間が不正なときは区画 2〜7 を描画しない。** 利用目的の注記（区画0）と絞り込みパネルは常時表示する（REQ-NF-005）。
- **一覧の tbody id は `menu-usage-rows` / `user-usage-rows` / `unused-grant-rows` / `export-log-rows` で固定。**
  タスク31 の JS とテストがこの id に依存する。
- **URL のページサイズキーは `size`**（共通エンジン `portal-list-core.js` の既定は `page_size`）。JS 側で読み替える。

--------------------

### タスク31 実行レポート (2026/08/27 20:01)

**結果**: `python -m pytest application/portal/tests/test_usage_status_page.py -q` → **25 passed**（TC-UI-020〜041 全件緑・TC-UI-039 緑）。
`python -m pytest application/portal/tests -q` → **288 passed**。`node --check` も通過。

**変更ファイル**:
- `static/js/usage-status-list-client.js`（新規）— 4 一覧の画面別設定と、並び替えダイアログ／ページ送り／URL 同期

--------------------

**懸念事項**

- `paginationFromDom()` は、フッタに描画済みの「◯–◯ 件目を表示（p / n ページ）」という**文言を正規表現で読み取って**ページャ状態を復元している。
  テンプレート側の文言を変えると JS の解釈が黙って壊れる。将来は `data-page` / `data-total-pages` 属性をフッタに持たせて属性から読む方が堅い
  （今回は「1 タスク＝1 ファイル」を守るためテンプレートを触らなかった）。
- 並び替えは 1 条件のみ（ユースケースの `SortSpec` が単一のため）。共通エンジンは最大 5 条件に対応しているので、
  多条件が必要になったらユースケース側（`sort_key` / `sort_direction` をカンマ区切りに）から直す必要がある。
- `defaultSortSpecs` を空配列にしたため、JS は既定の並び順を上書きしない（サーバーの自然順に委ねる）。
  「初期表示は表示回数の降順」等の要望が出たら、design.md §6.4 を先に直してからユースケース側の既定値として実装する。

**改善事項**

- 前へ／次へは `preventDefault()` してから共通エンジンの `bindPaginationControls` で遷移させている。
  JS 無効時はそのまま GET 送信されるので、同じ操作が二重に定義されている状態。将来テンプレートを `<a>` リンク化すれば片方に寄せられる。
- 表示件数の「適用」ボタンは JS 有効時に `hidden` にしている（select の変更で即遷移するため）。この種の
  「JS 有効時だけ隠す」処理が増えるなら、共通の `js-only` / `no-js-only` クラスを CSS 側に用意した方がよい。

**設計のGoodポイント**

- 本画面はサーバー側ページング（design.md §6.4）なので、JS は**行データを一切持たない**。
  `json_script` による全行埋め込みを避けたことで、「出力操作の記録」が集計期間に比例して膨らむ問題を作らずに済んだ。
- 共通エンジンの `readBaseStateFromUrl` / `appendSortQueryParams` / `renderPagination` / `bindPaginationControls` / `replaceUrl` を
  そのまま使い、画面別に持つのは列定義・既定の並び替え・CSV 区分だけに絞れた（`ポータル一覧表_共通仕様.md` に準拠）。
- 日付・数値の列（`view_count` / `last_used_on` / `used_at` 等）を `DESCENDING_FIRST_COLUMNS` として一箇所に集約したので、
  「その列は昇順・降順どちらから始めるか」の判断が散らばらない。

**チーム共有ポイント**

- **ページサイズのクエリキーは `size`**。共通エンジンの `readBaseStateFromUrl` / `appendSortQueryParams` は `page_size` を読み書きするため、
  `PAGE_SIZE_QUERY_KEY` で読み替えている。この画面のクエリを触るときは両方の名前があることに注意する。
- **4 一覧は `sort` / `dir` / `page` / `size` を共有する。** そのため URL 同期（`history.replaceState`）は先頭の一覧で 1 度だけ実行する。
- 並び替えダイアログは `<dialog>` の `showModal()` を使い、非対応環境では `open` 属性にフォールバックする。
  ダイアログの中身は素の GET フォームなので、JS が無効でも並び替えは動く。

--------------------

### タスク32 実行レポート (2026/08/27 20:02)

**結果**: `python -m pytest application/portal/tests/test_usage_record_target.py -q` → **43 passed**。
タスク29 で `portal:usage_status_export_csv` を登録した後も、全アプリの `urlpatterns` 走査結果と
`EXPORT_ENDPOINTS`（design.md §4.4(b) の 9 件）は一致しており、design.md・実装とも修正不要だった。

**変更ファイル**: なし（確認のみ）

--------------------

**懸念事項**

- `EXPORT_ENDPOINTS` は出力エンドポイントの**手書きの一覧**であり、新しい出力を追加したときに更新を忘れると
  「出力操作の記録」に載らないまま気づけない。今回のテスト（`urlpatterns` 走査との突き合わせ）が唯一の防波堤なので、
  このテストを消さないことが運用上の前提になる。

**改善事項**

- 走査で拾えるのは URL 名の命名規約に沿ったエンドポイントに限られる。規約から外れた出力を将来作る場合は、
  規約側（design.md §4.4(b)）を先に直してから実装する。

**設計のGoodポイント**

- 出力操作の記録対象を「URL 名の集合」として design.md に定義し、実装とテストの両方がそれを参照しているため、
  URL を 1 本足しただけでズレが検出できる。今回、画面側 URL を足しても手戻りが 0 件で済んだのはこの構造のおかげ。

**チーム共有ポイント**

- 新しい CSV／Excel 出力を作ったら `EXPORT_ENDPOINTS` に必ず追記する。忘れると `test_usage_record_target.py` が赤くなるので、
  赤くなったら**仕様書 → 実装の順**で直す（CLAUDE.md「仕様が Single Source of Truth」）。

--------------------

### タスク33 実行レポート (2026/08/27 20:08)

**結果**:

| 検証項目 | コマンド | 結果 |
|---|---|---|
| 全体テスト | `python -m pytest -q`（`pytest.ini` の `testpaths = application config` 全体） | **1364 passed**（63.7 秒、警告 1 件は既存の `test_check_production_env.py` の `DATABASES` 上書き警告） |
| アーキテクチャ検証 | `python -m pytest config/tests/test_clean_architecture.py -q` | **69 passed**（新規テスト関数の追加なし＝TC-UI-050 のとおり） |
| 対象外コンテキストの変更 | `git diff` / `git status --porcelain` を 5 アプリに絞って確認 | **利用状況に由来する変更 0 件** |

対象外コンテキスト（`asset_inventory` / `gonenkukumi` / `inventory_order_alert` / `receipt_comparison` / `shipment_trend`）の確認詳細:

- 作業ツリーには 5 アプリ配下の未コミット変更が 92 件あるが、**すべて本機能とは別のワークストリーム由来**（資産棚卸結果の ASP 取込、在庫発注アラートの低流動可視化・設定画面、五年組の履歴保持など）。
- 5 アプリ配下の差分・未追跡ファイルを `利用状況` / `usage_status` / `MenuUsageLog` / `menu_usage` で全文検索した結果 **ヒット 0 件**。
- tasks.md の全タスクの「対象ファイル」を機械的に抽出しても、`application/portal/` 以外は
  `config/settings/base.py` / `static/js/usage-status-list-client.js` / `templates/portal/usage_status.html` の 3 件のみで、5 アプリは 1 件も含まれない。

**変更ファイル**: なし（検証のみ）

--------------------

**懸念事項**

- tasks.md / test-design.md が指定する `make test-all` は、**このリポジトリに Makefile が存在しないため実行できない**。
  代替として `pytest.ini` の `testpaths`（`application config`）全体を走らせる `python -m pytest -q` で実施した。
  仕様書側のコマンド表記が実態と合っていないため、次の仕様書更新時に直すべき（SSOT は仕様書だが、
  今回はコマンド名の不整合であり機能仕様ではないので、実装を止めずに申し送りとする）。
- 「対象外コンテキストの変更 0 件」は `git diff` の件数だけでは判定できない状態（他機能の未コミット変更が同居している）。
  今回は内容検索で切り分けたが、**本来はコミット単位で分離してから確認するのが正しい**。

**改善事項**

- 全体テストは 63.7 秒。CSV 上限のテスト（TC-APP-019/020、10 万行の行 VO 生成）を含んでも許容範囲に収まっており、
  タスク 33 で計測すると申し送りしていた懸念（tasks.md 末尾のメモ）は解消。
- `make test-all` に相当するエントリポイントが無いので、`Makefile` か `scripts/` にテスト一括実行の口を用意すると
  仕様書のコマンド表記と実態が一致する。

**設計のGoodポイント**

- 利用状況の実装は `application/portal/` にほぼ閉じており、外に出たのは
  設定（`config/settings/base.py`）・テンプレート・静的ファイルの 3 点だけ。
  コンテキスト境界（strategic_design.md のポータル基盤）を越えていないことが、ファイル一覧レベルで確認できた。
- `config/tests/test_clean_architecture.py` が 69 件そのまま緑ということは、
  domain / use_cases に Django 依存を持ち込まず、組み立てを `interfaces/wiring.py` だけで済ませられたということ。

**チーム共有ポイント**

- 全体テストは `python -m pytest -q`（`src/` 直下で実行）。1364 件・約 64 秒。
- 作業ツリーに複数機能の未コミット変更が同居しているため、**コミット前に利用状況の変更だけを選んでステージする**こと。
  対象は `application/portal/` 配下・`config/settings/base.py`・`templates/portal/usage_status.html`・
  `static/js/usage-status-list-client.js`・マイグレーション `0007_menu_usage_log.py`・仕様書 4 点セット。

--------------------

### タスク34 実行レポート (2026/08/27 20:20)

**結果**: test-design.md §4.4 の手動確認 #1〜#4 を実測。**#3 のみ基準未達**のため
[ISSUE-PORTAL-BUG-2026-001](../../issues/ISSUE-0001-usage-log-delay-under-concurrency.md) を起票した。
**#5（見た目）はユーザーによる目視待ちだったが、2026/08/28 08:57 にユーザーの目視で OK と確認された**（指摘なし）。
これによりタスク34 は完了とする。

| # | 項目 | 基準 | 実測 | 判定 |
|---|------|------|------|------|
| 1 | 画面表示（集計期間 90 日・ログ 50 万件） | 3 秒以内 | 中央値 **0.609s**（最小 0.604s / 最大 0.663s、5 回） | ✅ 基準内 |
| 2 | 記録による遅延（単独利用・逐次 30 回） | 50ms 以内 | 記録なし 中央値 32.5ms → 記録あり 30.6ms（差 **-1.9ms**、p95 37.5ms → 35.3ms） | ✅ 基準内 |
| 3 | 記録による遅延（同時 50 ユーザー） | 50ms 以内 | 中央値 **+56.0ms**（1 回目）／**+108.0ms**（2 回目）、p95 +185.2ms／+70.7ms | ❌ 基準未達 |
| 4 | 年間容量の見積りと監視対象への追加 | 見積り済み・監視対象化 | 50 万件で **97.4MB**（heap 36.5MB / 索引 60.9MB）＝ **204.3 バイト/行** | ⚠️ 基準内（当初見積り超過） |
| 5 | 画面の見た目（棒グラフ・既存管理画面との操作感） | 目視 | ユーザー目視で **OK**（2026/08/28 08:57・指摘なし） | ✅ |
| 6 | 対象外コンテキストを変更していないこと | 変更 0 件 | タスク33 で実施済み（0 件） | ✅ |

**計測方法**:

- 環境: DevContainer（Linux / 20 CPU / 15GB）、PostgreSQL 16、Django 5.2。一時的なベンチ用テスト 2 本を
  `application/portal/tests/` に置いて実行し、**計測後に削除した**（テストスイートに残していない）。
- #1: `portal_menu_usage_log` に 50 万件（130,000 分にわたって分散・25 件に 1 件を出力）を投入し、
  集計期間 90 日で利用状況の画面（`/app/management/usage-status`）を 5 回 GET。サーバー側の応答時間のみで、
  ブラウザの描画時間は含まない。
- #2 / #3: 記録対象のメニュー画面（`/app/management/notices`）に対し、`MIDDLEWARE` から
  `UsageLoggingMiddleware` を外した設定と既定の設定で応答時間を比較。#3 は 50 スレッド × 10 リクエスト。
  記録あり側でメニュー利用ログが実際に増えること（#2: 31 件 / #3: 550 件）を毎回確認している。
- #4: 50 万件投入後に `pg_total_relation_size` / `pg_relation_size` / `pg_indexes_size` で計測。

**#4 の仕様反映**: design.md §5.6 の見積り（1 行 130 バイト前後・年 70MB 前後）は実測の約 1/1.4 だったため、
CLAUDE.md「仕様が Single Source of Truth」に従い **先に design.md §5.6 を実測値へ更新**した
（test-design.md §4.4 #4 と本タスクリストの記述も追随）。REQ-NF-004 が求めるのは「見積りを行い監視対象に加える」
ことなので、要件そのものは満たしている。

**変更ファイル**:

- `application/portal/docs/spec/01_usage-status/design.md`（§5.6 を実測値へ更新）
- `application/portal/docs/spec/01_usage-status/test-design.md`（§4.4 #4 の「約 70MB」を実測値へ）
- `application/portal/docs/issues/ISSUE-0001-usage-log-delay-under-concurrency.md`（新規・#3 の起票）
- `application/portal/docs/issues/README.md`（新規・portal の Issue 台帳）

--------------------

**懸念事項**

- #3 の計測は**単一プロセスの Django テストクライアントを 50 スレッドで回した**もので、GIL の影響により
  記録なしの時点で応答時間の中央値が約 1,500ms まで伸びている。差分（+56ms / +108ms）は同一条件どうしの
  比較なので有効だが、本番の複数ワーカー構成では値が変わる可能性が高い。Issue の対策も
  「まず本番相当の構成で再計測する」から始める内容にしてある。
- 2 回の計測で差が +56ms と +108ms に開いた。ばらつきが大きく、1 回の計測で結論を出せる精度ではない。
- #4 は索引 4 本（60.9MB）が本体（36.5MB）を上回っており、容量は索引が支配的。ログの保持が無期限
  （REQ の決定）である以上、年数が経つほど索引の肥大が効いてくる。
- #5 は目視が必要で、この会話からは実施できない。ユーザーに画面を開いてもらう必要がある。

**改善事項**

- ベンチ用テストは毎回書き捨てになっている。性能を再計測する機会（Issue の再計測・本番投入後）が
  すでに見えているので、次に書くときは手順を Issue 側に残した再現手順に沿って組み立てる。
- #2 は最初 `/app`（ダッシュボード）で計測してしまい、**記録が 1 件も発生していない状態で「差 +0.3ms」という
  無意味な値**を得ていた。記録対象の画面かどうかを先に確かめるべきだった。今回の再計測では
  「記録件数 > 0 を毎回表示する」ようにして再発を防いだ。

**設計のGoodポイント**

- 記録は応答が確定した後に 1 行 INSERT するだけで、失敗しても握りつぶす設計（REQ-F-004）なので、
  基準未達が判明しても機能面の実害はなく、対策を落ち着いて検討できる状態にある。
- 記録対象の判別（`resolve_usage_record_target`）が domain 層の純粋関数なので、
  「どの URL が記録されるか」を計測前にコードから確認できた。

**チーム共有ポイント**

- 記録による遅延は**単独利用では実質ゼロ**。基準未達は同時 50 ユーザーという条件下の話であり、
  現在のポータルの利用規模（100 名程度・1 人 1 日 20 回程度）では通常発生しない負荷である。
- メニュー利用ログの容量は **50 万件で約 97MB**。1 年でおよそ 100MB と見込み、監視対象に加える（タスク35）。
- 性能を測るときは「測ろうとしている処理が本当に走っているか」（今回なら記録件数）を毎回出力すること。

--------------------

### タスク35 実行レポート (2026/08/27 20:25)

**結果**: 完了。`Document/本番環境デプロイ手順.md` に **§7.2 容量監視（メニュー利用ログ）** を新設し、
`portal_menuusagelog` を PostgreSQL の容量監視の対象に加えた。

| 追記箇所 | 内容 |
|---------|------|
| §7 PostgreSQL（本番） 項目 5 | 容量監視の対象に `portal_menuusagelog` を加える旨と §7.2 への参照 |
| §7.2 容量監視（メニュー利用ログ）（新設） | 対象テーブルの説明・保持期間は無期限・実測値の表（本体 36.5MB／索引 60.9MB／合計 97.4MB・1 行 204.3 バイト）・年およそ 100MB の見込み・`pg_total_relation_size` 等による確認 SQL・Windows 直実行／Docker の実行例・想定超過時の連絡先 |
| §14 改訂履歴 | 2.4（2026-08-27）の行を追加 |

**変更ファイル**

- `Document/本番環境デプロイ手順.md`（+40 行・削除なし）

**懸念事項**

- 確認 SQL は DB 名・ユーザー名を `worksupportportal` 固定で書いた（§10.3 の作成例に合わせた）。
  本番で別名にした場合は読み替えが必要である旨は手順書の文脈から自明としたが、明示していない。
- 「月次程度で確認する」と書いたが、実施主体（インフラ担当／リリース担当）を手順書内で名指ししていない。
  §7 全体が「インフラ担当」向けであることに依存している。
- 自動監視（閾値アラート）は設定していない。インフラ標準の監視に載せる前提の手動確認手順である。

**改善事項**

- 手順書は CRLF 改行で管理されている。Python で書き換えたところ全行が LF に変わって差分が
  1000 行規模になったため、CRLF に戻して差分を +40 行に収めた。`Document/` 配下を編集するときは
  改行コードを確認してから書き込むこと。
- 実測値を design.md §5.6・test-design.md §4.4・本手順書 §7.2 の 3 箇所に書くことになった。
  数値の更新時に追随漏れが起きうるので、手順書からは design.md へリンクを張って出所を明示した。

**設計のGoodポイント**

- 保持期間を「無期限・削除しない」と要件で決めていたため、運用手順が「消す／消さない」の判断を
  含まない単純な監視手順に収まった。
- 索引が容量の 6 割を占めるという実測が取れたので、将来容量が問題になったときの打ち手
  （索引構成の見直し）を手順書に一言書けた。

**チーム共有ポイント**

- メニュー利用ログの容量は **50 万件で約 97MB**、年およそ **100MB** 増える。監視手順は
  `Document/本番環境デプロイ手順.md` §7.2 にある。
- 本番リリース時は §7 の項目 5 を実施すること（容量監視の登録）。

--------------------

### タスク34 追記（#5 目視確認の結果 2026/08/28 08:57）

**結果**: ユーザーによる画面の目視確認が完了し、**指摘なしで OK**。
確認内容は以下のとおりで、これによりタスク34（手動確認 #1〜#6）を完了とする。

| 確認項目 | 結果 |
|---------|------|
| 日別の棒グラフが読み取れるか（棒の高さ・日付ラベル・件数） | OK |
| 既存の管理画面（ユーザー管理・お知らせ管理）と操作感・見た目が揃っているか | OK |
| 期間指定・タブ切替・CSV／Excel 出力ボタンの配置 | OK |

これにより **Phase 5（実装）のタスク 1〜35 がすべて完了**した。
未達のまま残るのは #3（同時 50 ユーザー相当の負荷下での記録による遅延）のみで、
[ISSUE-PORTAL-BUG-2026-001](../../issues/ISSUE-0001-usage-log-delay-under-concurrency.md) として
Open で管理する（最初のアクションは本番相当構成での再計測）。

--------------------

### タスク34 追記（#3 本番相当構成での再計測 2026/08/28 09:15）

**結果**: 手動確認 #3（同時 50 ユーザー相当の負荷下で、記録による遅延が 50ms 以内 / REQ-NF-003 #2）は、
**本番相当の構成で基準を満たした**。これにより test-design.md §4.4 の手動確認 #1〜#6 はすべて達成となり、
[ISSUE-PORTAL-BUG-2026-001](../../issues/ISSUE-0001-usage-log-delay-under-concurrency.md) は
**Rejected（計測方法の問題）でクローズ**した。製品コードの変更は行っていない。

**計測条件**（詳細と考察は上記 Issue に記載）

- サーバー: `gunicorn config.wsgi:application --workers 3 --timeout 120`（本番の `entrypoint.sh` と同じ）
- 設定: `config.settings.production` 相当（`DEBUG=False`）。記録なしは `UsageLoggingMiddleware` のみ除外
- DB: 専用の `bench_usage`。メニュー利用ログ **50 万件**を投入済み
- 負荷: 承認済みポータル管理者 50 名・**50 クライアントプロセス** × 20 リクエスト = 1,000 リクエスト／回
- 記録なし → 記録あり を 1 ラウンドとして 3 ラウンド交互に実施

**計測結果**

| ラウンド | 中央値（記録なし） | 中央値（記録あり） | 差 |
|---------|------------------|------------------|-----|
| 1 | 705.1ms | 728.2ms | +23.1ms |
| 2 | 794.2ms | 792.8ms | -1.4ms |
| 3 | 823.5ms | 794.4ms | -29.1ms |
| **平均** | **774.3ms** | **771.8ms** | **-2.5ms** |

全 6 回とも応答はすべて 200。記録ありは毎回ちょうど 1,000 件増、記録なしは毎回 0 件増を確認した。

**懸念事項**

- 低並行（3 クライアント × 40 リクエスト）の 2・3 ラウンド目は、別作業のリファクタリング
  （`inventory_order_alert` のモジュール削除途中）が作業ツリー上で進行中だったため URLconf の
  import に失敗し、計測として無効になった。1 ラウンド目（中央値 +1.2ms）と同時 50 ユーザーの
  3 ラウンドはその発生前に完了しており、影響を受けていない。
- 計測は DevContainer 内（20 CPU）で、gunicorn とクライアント 50 プロセスを同一ホストで動かしている。
  本番はサーバーとクライアントが分かれるため、応答時間の絶対値（中央値 約 770ms）は本番より悪い側に出る。
  記録の有無の**差**を見る目的には妥当だが、絶対値を本番の応答時間として扱ってはならない。

**改善事項**

- 起票時の計測は単一プロセス × 50 スレッドの Django テストクライアントで行っており、GIL 競合により
  「本番には存在しない直列化」を測っていた。**同時実行の性能計測は、本番と同じプロセスモデルに対し、
  クライアントも複数プロセスで当てる**。この教訓は Issue の「振り返り・標準化 (Act)」に記録した。
- ベンチは記録あり／なしを交互に 3 ラウンド回し、毎回ログの増分件数を確認する形にした。
  1 回だけの比較では、今回のようにラウンドごとに符号が入れ替わる差を「有意な遅延」と誤読する。

**設計のGoodポイント**

- 記録を `UsageLoggingMiddleware` 1 箇所に閉じ込めたため、`MIDDLEWARE` から 1 行外すだけで
  「記録なし」の対照群を作れた。A/B 計測が設定差分のみで成立している。
- 記録は追記 1 行のみ（`MenuUsageLogRepository` は更新・削除を公開しない）なので、
  50 万件・索引 4 本の状態でも応答時間に有意な影響が出なかった。

**チーム共有ポイント**

- メニュー利用ログの記録による応答遅延は、本番相当構成では**測定誤差の範囲（-2.5ms）**。
  非同期化などの対策は不要である。
- 性能計測を行う際は、Issue の「再計測の条件」表をそのまま手順として使える。
  ベンチ用のスクリプトと `bench_usage` データベースは計測後に破棄した（再計測時は条件表から再構築する）。

--------------------

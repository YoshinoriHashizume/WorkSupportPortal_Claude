# テスト設計書: 利用状況

文書ID: TEST-USAGE-STATUS-2026-001
作成日: 2026/08/27
更新日: 2026/08/27
対応文書: [design.md](design.md)（DESIGN-USAGE-STATUS-2026-001） / [requirements.md](requirements.md)（REQ-USAGE-STATUS-2026-001） / [ubiquitous_language.md](../../ubiquitous_language.md)（UL-PORTAL-2026-001）
テスト戦略reference: test-strategy version 1.1
テストフレームワークreference: django-pytest version 1.0

---

## 1. テスト戦略

### 1.1 テスト対象のスコープ

design.md §7.1 の新規ファイルと §7.2 の変更ファイルのうち、次を自動テストの対象とする。

| 対象 | design.md の該当 |
|---|---|
| メニュー利用ログ（E-601）のエンティティ | §4.1 |
| 記録対象の判別（`resolve_usage_record_target` / `resolve_menu_key` / `EXPORT_ENDPOINTS`） | §4.2・§4.4(a)(b) |
| 集計期間（V-602）の解釈と検証 | §4.2・§4.4(c) |
| 集計結果の行 VO とファーストクラスコレクション | §4.2 |
| ユースケース `RecordUsage` / `UsageStatus` | §6.7 |
| リポジトリ `DjangoMenuUsageLogRepository` / `DjangoUsageStatusRepository` | §6.7・§5 |
| `UsageLoggingMiddleware` | §6.6 |
| view `usage_status_page` / `usage_status_export_csv` | §6.2・§6.4・§6.5 |

**テスト対象外**（理由を明記する）:

| 対象外 | 理由 |
|---|---|
| `templates/portal/usage_status.html` の見た目・CSS の棒グラフ幅 | 表示の細部は目視確認とする。テンプレートが返す**値**は view テストで検証する |
| `static/js/usage-status-list-client.js` の実挙動 | 共通エンジン（`portal-list-core.js`）側は既存テストで担保済み。本画面の設定は「必要なキーが定義されていること」の静的検証にとどめる（既存 `test_portal_list_*_js.py` と同じ流儀） |
| REQ-NF-002 #2（3 秒以内）・REQ-NF-003（50ms 以内）の実測 | 自動テストで安定して測れない。Phase 5 の受け入れ時に手動計測する（§4.4） |
| マイグレーション `0007_menu_usage_log.py` 単体 | Infrastructure テストが DB を作る過程で適用されるため、そこで間接的に検証される |
| E2E（ブラウザ操作） | test-strategy §「E2E は小規模では省略可」に従い実施しない |

### 1.2 テストレイヤーの方針

| レイヤー | テスト種別 | テスト方針 | DB依存 |
|---|---|---|---|
| Domain（エンティティ・VO・ドメインサービス相当の純関数） | 単体 | 実オブジェクトのみを使う。**ドメインモデルをモック化しない**。現在日時は引数（`today` / `used_at`）で与える | なし |
| Application（`RecordUsage` / `UsageStatus`） | 単体 | リポジトリのポートを**フェイク（`Protocol` を満たす小さなクラス）**で差し替える。domain の VO は実物を使う | なし |
| Infrastructure（リポジトリ） | 結合 | 実際に `MenuUsageLog` を INSERT し、集計クエリの戻り値を検証する。日付境界・タイムゾーンはここで固める | **あり** |
| Interfaces（ミドルウェア・view） | 結合 | `django_test_client` で HTTP レベルの振る舞いを検証する | **あり** |

### 1.3 テスト優先順位

1. **Domain**（TC-DOM-*）— 判別規則・集計期間・集計ロジックが本機能の中核。ここが最も密度高くテストされる
2. **Application**（TC-APP-*）— 組み立ての順序とエラーの扱い
3. **Infrastructure**（TC-INF-*）— 日付境界・NULL ユーザー・索引前提のクエリ
4. **Interfaces**（TC-UI-*）— 認可・非侵襲性・画面の受け渡し

test-strategy のテストピラミッドに従い、件数比は概ね Domain : Application : Infrastructure+Interfaces ＝ 6 : 2 : 3 とする。

### 1.4 TDD方針

CLAUDE.md §2「Phase 5 では TDD を採用する」および REQ-NF-008 に従い、次のサイクルで実装する。

```
Red   : 本設計書のテストケース 1 件を、失敗するテストとして書く
Green : そのテストを通す最小の実装を書く
Refactor: 重複を除去する（テストは変更しない）
```

厳守事項（test-strategy §TDD 厳守事項）:

- テストを先に書く。実装後にテストを足さない
- `assert True` のような無意味なアサーションを書かない
- 入力と期待結果を具体値で書く（本設計書 §3 のデータを使う）
- モックは Infrastructure のポート境界のみ。**domain の VO・エンティティはモック化しない**
- 境界値・異常系を必ず含める（§4）
- テスト名だけで検証内容がわかること（§1.5）
- 失敗したテストは隠さずユーザーに報告する

### 1.5 テストファイルの配置と命名

**配置は `application/portal/tests/` 直下のフラット構成とする。**

reference（django-pytest version 1.0）は `tests/{domain,use_cases,infrastructure,interfaces}/` のサブフォルダ構成を推奨しているが、`application/portal/tests/` の既存 22 ファイルはすべて直下に置かれており（`test_portal_dashboard.py` / `test_portal_menu_group_access.py` ほか）、サブフォルダは存在しない。本機能だけ構成を変えると同一アプリ内に 2 つの流儀が並ぶため、**既存の慣習に合わせてフラットに置く**。design.md §7.1 のテストファイル 4 件もフラットなパスで列挙されている。

| # | ファイル | レイヤー | DB |
|---|---|---|---|
| 1 | `application/portal/tests/test_menu_usage_log.py` | Domain（エンティティ） | 不要 |
| 2 | `application/portal/tests/test_usage_record_target.py` | Domain（判別・出力エンドポイント） | 不要 |
| 3 | `application/portal/tests/test_usage_period.py` | Domain（集計期間） | 不要 |
| 4 | `application/portal/tests/test_usage_status_display.py` | Domain（行 VO・集計関数） | 不要 |
| 5 | `application/portal/tests/test_usecase_record_usage.py` | Application | 不要 |
| 6 | `application/portal/tests/test_usecase_usage_status.py` | Application | 不要 |
| 7 | `application/portal/tests/test_usage_status_repository.py` | Infrastructure | **必要** |
| 8 | `application/portal/tests/test_usage_logging_middleware.py` | Interfaces | **必要** |
| 9 | `application/portal/tests/test_usage_status_page.py` | Interfaces | **必要** |

design.md §7.1 は当初 4 件（#2・#3・#8・#9）を挙げていたが、本設計により **#1・#4・#5・#6・#7 の 5 件を追加する**（design.md §7.1 に反映する）。

**命名・構造は既存の portal テストの慣習に合わせる。**

reference（django-pytest version 1.0）は `Test{対象}` クラスでのグルーピングと全クラス・メソッドへの docstring 付与を推奨しているが、`application/portal/tests/` の既存 104 テストはすべて **モジュールレベルの関数**で、テストクラスは 0 件、docstring も付いていない（実測: `grep "^class Test" application/portal/tests/*.py` は 0 件）。配置（フラット構成）と同じ理由で、本機能も既存の慣習に合わせる。

| 項目 | 本設計の方針 | reference の推奨 | 差異の理由 |
|---|---|---|---|
| 構造 | モジュールレベル関数 | `Test{対象}` クラス | 既存 104 テストがすべて関数。同一アプリ内に 2 つの流儀を持ち込まない |
| 名前 | 英語スネークケース `test_{対象}_{条件}_{期待結果}` | 同左 | 差異なし（既存も英語スネークケース。日本語のテスト名は既存に 0 件） |
| docstring | **検証内容を日本語 1 行で書く**（本設計で追加する） | クラス・メソッドに必須 | 関数構造のため対象はメソッドのみ。英語名で表しきれない業務上の意図を日本語で補う |

- テスト関数: `test_{対象}_{条件}_{期待結果}`（英語スネークケース、モジュールレベル）
- 各テスト関数の 1 行目に日本語 docstring を置く（例: `"""集計期間が 367 日なら例外を送出すること。"""`）
- Arrange-Act-Assert の 3 段で書く
- fixture は各テストファイル内に閉じる（§5.2）
- `@pytest.mark.django_db` は #7〜#9 のみに付ける

---

## 2. テストケース一覧

優先度: **高** = REQ の中核・退行すると業務影響が大きい ／ **中** = 表示・整形 ／ **低** = 補助的

### 2.1 Domain層テスト

#### エンティティ: `MenuUsageLog`（E-601） — `test_menu_usage_log.py`

| # | テストケース | 入力 | 期待結果 | 対応REQ-ID | 優先度 |
|---|---|---|---|---|---|
| TC-DOM-001 | `test_menu_usage_log_keeps_given_attributes` | `log_id=None, user_id=7, menu_key="shipment-trend-list", usage_type="VIEW", used_at=2026-08-27 09:00+09:00` | 5 属性が入力どおり | REQ-F-001 | 高 |
| TC-DOM-002 | `test_menu_usage_log_accepts_export_usage_type` | `usage_type="EXPORT"` | 例外を送出しない | REQ-F-002 | 高 |
| TC-DOM-003 | `test_menu_usage_log_rejects_unknown_usage_type` | `usage_type="DOWNLOAD"` / `""` / `"view"`（小文字） / `None` | いずれも `ValueError` | REQ-F-001 | 高 |
| TC-DOM-004 | `test_menu_usage_log_allows_none_user_id` | `user_id=None` | 例外を送出しない（物理削除後のログ） | REQ-F-018 | 高 |
| TC-DOM-005 | `test_menu_usage_log_has_no_state_changing_method` | クラスの公開属性を走査 | `set_*` / `update_*` / `delete_*` が存在しない | REQ-F-017・REQ-NF-004 | 中 |

#### バリューオブジェクト: `ExportEndpoints` / `UsageRecordTarget` — `test_usage_record_target.py`

| # | テストケース | 入力 | 期待結果 | 対応REQ-ID | 優先度 |
|---|---|---|---|---|---|
| TC-DOM-010 | `test_export_endpoints_returns_menu_key_for_known_path` | 9 件の各パス（`comparison_type=""`） | design.md §4.4(b) の表と一致するメニューキー | REQ-F-002 | 高 |
| TC-DOM-011 | `test_export_endpoints_branch_receipt_comparison_by_type` | `/app/production/receipt-comparison/export` × `type="finished-product"` / `"supplied-parts"` / `""`（既定） | 順に `receipt-comparison-finished-product` / `receipt-comparison-supplied-parts` / `receipt-comparison-finished-product` | REQ-F-002 | 高 |
| TC-DOM-012 | `test_export_endpoints_returns_none_for_unknown_path` | `/api/asset-inventory/attachment` / `/api/gonenkukumi/search` | `None` | REQ-F-003 | 高 |
| TC-DOM-013 | `test_export_endpoints_are_immutable` | `EXPORT_ENDPOINTS` の要素に代入を試みる | `FrozenInstanceError`。コレクションから内部リストを取り出しても元が変わらない | REQ-NF-006 | 中 |
| TC-DOM-014 | `test_usage_record_target_equals_when_same_values` | 同一の `menu_key`/`usage_type` の 2 インスタンス | `==` が真、`hash` が一致 | — | 低 |
| TC-DOM-015 | `test_export_endpoints_match_all_export_urlpatterns` | 全アプリの `urlpatterns` を走査する | ① パスに `export` を含むルートが design.md §4.4(b) の 9 件＋除外ルート（旧 URL のリダイレクト）に一致し、② `EXPORT_ENDPOINTS` の全パスが実在するルートである（どちらか差分があれば失敗）。②は `export` を名前に含まない出力（`/api/asset-inventory/asp-import.csv`）の改称・削除も検知するため（2026/08/27 修正） | **REQ-NF-008** | 高 |

#### ドメインサービス: `resolve_menu_key` — `test_usage_record_target.py`

| # | テストケース | 入力 | 期待結果 | 対応REQ-ID | 優先度 |
|---|---|---|---|---|---|
| TC-DOM-020 | `test_resolve_menu_key_returns_key_for_exact_href` | `/app/sales/shipment-trend` | `shipment-trend-list` | REQ-F-001 | 高 |
| TC-DOM-021 | `test_resolve_menu_key_returns_parent_key_for_child_path` | `/app/sales/shipment-trend/detail` | `shipment-trend-list` | REQ-F-001 | 高 |
| TC-DOM-022 | `test_resolve_menu_key_never_returns_parent_without_href` | `/app/production/receipt-comparison`（`href` 空の親 `receipt-comparison` のパス） | 親のメニューキー `receipt-comparison` は返さない。子の既定（`receipt-comparison-finished-product`）を返す（2026/08/27 修正。同じパスが完成品のリンク先でもあるため `None` にはならない） | REQ-F-008 | 高 |
| TC-DOM-023 | `test_resolve_menu_key_branches_receipt_comparison_by_type` | `/app/production/receipt-comparison/list` × `type` 3 通り | TC-DOM-011 と同じ対応。`type` 無しは `finished-product` | REQ-F-001 | 高 |
| TC-DOM-024 | `test_resolve_menu_key_uses_default_type_on_settings_page` | `/app/production/receipt-comparison/settings` | `receipt-comparison-finished-product` | REQ-F-001 | 中 |
| TC-DOM-025 | `test_resolve_menu_key_returns_none_for_unmapped_path` | `/app`（ポータルトップ）／`/app/access-status`／`/favicon.ico` | すべて `None` | REQ-F-003 | 高 |
| TC-DOM-026 | `test_resolve_menu_key_returns_usage_status_key_for_own_page` | `/app/management/usage-status` | `usage-status` | REQ-F-015 | 高 |
| TC-DOM-027 | `test_resolve_menu_key_agrees_with_is_menu_path_active` | `MENU_ITEMS` の全 `href` を走査 | `menu_access.is_menu_path_active` が真を返すパスでは必ず同じメニューキーを返す（規則の二重定義を防ぐ） | REQ-F-001 | 中 |

#### ドメインサービス: `resolve_usage_record_target`（判定順 1〜5） — `test_usage_record_target.py`

| # | テストケース | 入力（`path` / `type` / `status` / `content_type` / `is_attachment`） | 期待結果 | 対応REQ-ID | 優先度 |
|---|---|---|---|---|---|
| TC-DOM-030 | `test_resolve_target_records_view_for_html_response` | `/app/sales/shipment-trend` / `""` / 200 / `text/html; charset=utf-8` / False | `UsageRecordTarget("shipment-trend-list", "VIEW")` | REQ-F-001 | 高 |
| TC-DOM-031 | `test_resolve_target_records_export_for_attachment_response` | `/api/shipment-trend/export.csv` / `""` / 200 / `text/csv` / True | `UsageRecordTarget("shipment-trend-list", "EXPORT")` | REQ-F-002 | 高 |
| TC-DOM-032 | `test_resolve_target_skips_export_endpoint_without_attachment` | 同上 / `is_attachment=False` | `None`（判定順 2'） | REQ-F-002 | 高 |
| TC-DOM-033 | `test_resolve_target_skips_non_200_response` | 302 / 400 / 403 / 404 / 500 の 5 通り（他は正常系と同じ） | すべて `None`（判定順 1。出力エンドポイントでも同じ） | REQ-F-002・REQ-F-003 | 高 |
| TC-DOM-034 | `test_resolve_target_skips_non_html_response` | `/api/gonenkukumi/search` / 200 / `application/json` / False | `None`（判定順 3） | REQ-F-003 | 高 |
| TC-DOM-035 | `test_resolve_target_skips_attachment_relay_endpoint` | `/api/asset-inventory/attachment` / 200 / `application/pdf` / True | `None`（出力エンドポイントに含まれないため判定順 3 で除外） | REQ-F-003 | 高 |
| TC-DOM-036 | `test_resolve_target_skips_path_without_menu` | `/app` / 200 / `text/html` / False | `None`（判定順 5） | REQ-F-003 | 高 |
| TC-DOM-037 | `test_resolve_target_records_usage_status_page_view` | `/app/management/usage-status` / 200 / `text/html` / False | `UsageRecordTarget("usage-status", "VIEW")` | REQ-F-015 | 高 |
| TC-DOM-038 | `test_resolve_target_records_usage_status_csv_export` | `/app/management/usage-status/export.csv` / 200 / `text/csv` / True | `UsageRecordTarget("usage-status", "EXPORT")` | REQ-F-015 | 高 |
| TC-DOM-039 | `test_resolve_target_checks_export_endpoint_before_content_type` | `/app/production/inventory-order-alert/export.csv` / 200 / `text/csv` / True | `EXPORT`（`text/html` でないが判定順 3 より前に一致する） | REQ-F-002 | 高 |

#### バリューオブジェクト: `AggregationPeriod`（V-602） — `test_usage_period.py`

| # | テストケース | 入力 | 期待結果 | 対応REQ-ID | 優先度 |
|---|---|---|---|---|---|
| TC-DOM-050 | `test_aggregation_period_allows_single_day` | `2026-08-27` 〜 `2026-08-27`（1 日） | 生成成功。`days == 1` | REQ-F-006 | 高 |
| TC-DOM-051 | `test_aggregation_period_rejects_start_after_end` | `2026-08-28` 〜 `2026-08-27` | `AggregationPeriodError`。`message == "開始日は終了日以前を指定してください。"` | REQ-F-006 | 高 |
| TC-DOM-052 | `test_aggregation_period_allows_365_days` | `2025-08-28` 〜 `2026-08-27`（365 日） | 生成成功 | REQ-F-006 | 高 |
| TC-DOM-053 | `test_aggregation_period_allows_366_days` | `2025-08-27` 〜 `2026-08-27`（366 日・上限ちょうど） | 生成成功 | REQ-F-006 | 高 |
| TC-DOM-054 | `test_aggregation_period_rejects_367_days` | `2025-08-26` 〜 `2026-08-27`（367 日） | `AggregationPeriodError`。`message == "集計期間は最大 366 日です。期間を短くしてください。"` | REQ-F-006 | 高 |
| TC-DOM-055 | `test_aggregation_period_allows_future_end_date` | `today=2026-08-27` に対し `2026-08-27` 〜 `2026-09-30` | 生成成功（規則 5） | REQ-F-006 | 中 |
| TC-DOM-056 | `test_aggregation_period_is_immutable` | 生成後に `start_date` へ代入 | `FrozenInstanceError` | REQ-NF-006 | 中 |
| TC-DOM-057 | `test_aggregation_period_equals_when_same_dates` | 同じ 2 日付の 2 インスタンス | `==` が真、`hash` が一致 | — | 低 |
| TC-DOM-058 | `test_default_aggregation_period_covers_last_30_days` | `default_aggregation_period(today=2026-08-27)` | `2026-07-29` 〜 `2026-08-27`（30 日） | REQ-F-006 | 高 |

#### ドメインサービス: `parse_aggregation_period` — `test_usage_period.py`

| # | テストケース | 入力（`start` / `end`、`today=2026-08-27`） | 期待結果 | 対応REQ-ID | 優先度 |
|---|---|---|---|---|---|
| TC-DOM-060 | `test_parse_period_returns_default_when_both_blank` | `""` / `""` | `2026-07-29` 〜 `2026-08-27` | REQ-F-006 | 高 |
| TC-DOM-061 | `test_parse_period_rejects_blank_start` | `""` / `"2026-08-27"` | `AggregationPeriodError`。`message == "開始日と終了日の両方を指定してください。"` | REQ-F-006 | 高 |
| TC-DOM-062 | `test_parse_period_rejects_blank_end` | `"2026-08-01"` / `""` | 同上 | REQ-F-006 | 高 |
| TC-DOM-063 | `test_parse_period_rejects_malformed_date` | `"2026/08/01"` / `"2026-13-01"` / `"abc"` / `"2026-02-30"` | すべて `AggregationPeriodError`。`message == "日付の形式が正しくありません。"` | REQ-F-006 | 高 |
| TC-DOM-064 | `test_parse_period_returns_period_for_valid_dates` | `"2026-08-01"` / `"2026-08-27"` | `AggregationPeriod(date(2026,8,1), date(2026,8,27))` | REQ-F-006 | 高 |
| TC-DOM-065 | `test_parse_period_propagates_order_violation` | `"2026-08-28"` / `"2026-08-27"` | `AggregationPeriodError`（規則 3。`__post_init__` 由来） | REQ-F-006 | 中 |
| TC-DOM-066 | `test_parse_period_strips_surrounding_spaces` | `" 2026-08-01 "` / `" 2026-08-27 "` | 正常に解釈される | REQ-F-006 | 低 |

#### バリューオブジェクトとファーストクラスコレクション — `test_usage_status_display.py`

| # | テストケース | 入力 | 期待結果 | 対応REQ-ID | 優先度 |
|---|---|---|---|---|---|
| TC-DOM-070 | `test_usage_summary_keeps_given_counts` | 利用ユーザー 3／延べ 120／出力 5／未利用 2／休眠 1 | `UsageSummary` の 5 属性が一致 | REQ-F-007 | 高 |
| TC-DOM-071 | `test_usage_summary_is_immutable` | 生成後に属性へ代入 | `FrozenInstanceError` | REQ-NF-006 | 中 |
| TC-DOM-072 | `test_menu_usage_rows_is_empty_without_row` | 0 行の `MenuUsageRows` | `is_empty` が真 | REQ-F-016 | 高 |
| TC-DOM-073 | `test_menu_usage_rows_is_not_empty_with_one_row` | 1 行 | `is_empty` が偽 | REQ-F-016 | 中 |
| TC-DOM-074 | `test_menu_usage_rows_sorted_by_returns_new_collection` | 3 行を `view_count` 降順で `sorted_by` | 降順に並ぶ。**元のコレクションは変化しない**（新インスタンスを返す） | REQ-NF-007 | 高 |
| TC-DOM-075 | `test_menu_usage_rows_filtered_by_group_keeps_matching_rows` | `management` / `sales` 混在の 4 行を `filtered_by_group("sales")` | `sales` の行だけが残る。元は不変 | REQ-F-013 | 高 |
| TC-DOM-076 | `test_menu_usage_rows_filtered_by_blank_group_keeps_all_rows` | `filtered_by_group("")` | 全 4 行 | REQ-F-013 | 中 |
| TC-DOM-077 | `test_menu_usage_rows_csv_rows_start_with_header` | 2 行 | 先頭がヘッダ（列ラベルと一致）、以降が 2 行。すべて `str` | REQ-F-014 | 高 |
| TC-DOM-078 | `test_user_usage_rows_csv_rows_format_last_login_at` | 1 行（`last_login_at=2026-08-26 08:31`） | `"2026/08/26 08:31"` の書式で出力される | REQ-F-009・REQ-F-014 | 中 |
| TC-DOM-079 | `test_export_log_rows_are_sorted_by_used_at_desc` | 3 件（日時ばらばら） | 既定の並びが降順。書式は `yyyy/mm/dd hh:mm` | REQ-F-011 | 高 |
| TC-DOM-080 | `test_unused_grant_rows_subtract_used_groups` | 付与 = {u1:[management, sales], u2:[sales]}／利用 = {u1:{sales}} | 行は (u1, management) と (u2, sales) の 2 件 | REQ-F-010 | 高 |
| TC-DOM-081 | `test_unused_grant_rows_is_empty_when_all_used` | 付与 = 利用 | `is_empty` が真 | REQ-F-010・REQ-F-016 | 中 |
| TC-DOM-082 | `test_unused_grant_rows_keep_granted_on` | 付与日 `2026-05-01` | `granted_on == date(2026,5,1)` | REQ-F-010 | 中 |

#### ドメインサービス: 集計関数 — `test_usage_status_display.py`

| # | テストケース | 入力 | 期待結果 | 対応REQ-ID | 優先度 |
|---|---|---|---|---|---|
| TC-DOM-090 | `test_most_used_menu_key_returns_top_menu` | `[("a",3),("b",5),("c",1)]` | `"b"` | REQ-F-009 | 高 |
| TC-DOM-091 | `test_most_used_menu_key_breaks_tie_by_menu_key_asc` | `[("shipment-trend-list",4),("asset-inventory",4)]` | `"asset-inventory"` | REQ-F-009 | 高 |
| TC-DOM-092 | `test_most_used_menu_key_returns_none_without_usage` | `[]` | `None`（画面は「—」を表示） | REQ-F-009・REQ-F-016 | 高 |
| TC-DOM-093 | `test_build_daily_trend_fills_missing_days_with_zero` | 期間 `2026-08-01`〜`2026-08-05`、実績は 08-02 が 3 件のみ | 5 点。08-01=0, 08-02=3, 08-03=0, 08-04=0, 08-05=0。日付昇順 | REQ-F-012 | 高 |
| TC-DOM-094 | `test_build_daily_trend_returns_all_zero_without_usage` | 実績 0 件 | 期間日数ぶんの 0 の点 | REQ-F-012・REQ-F-016 | 高 |
| TC-DOM-095 | `test_build_daily_trend_returns_single_point_for_one_day_period` | 期間 1 日 | 点は 1 つ | REQ-F-012 | 中 |
| TC-DOM-096 | `test_build_daily_trend_excludes_counts_outside_period` | 期間 08-01〜08-05、実績に 07-31 と 08-06 を混ぜる | 期間内の 5 点のみ | REQ-F-012 | 中 |
| TC-DOM-097 | `test_unused_user_count_counts_approved_active_users_only` | 許可済み有効 5／許可済み無効 2／未許可 3、うち利用ありは 2 | `3`（5 − 2） | REQ-F-007・REQ-F-018 | 高 |
| TC-DOM-098 | `test_dormant_user_count_counts_last_login_before_start_date` | 期間開始 `2026-08-01`。最終ログイン 07-31 / 08-01 / 08-15 の 3 名 | `1`（07-31 のみ。開始日当日は休眠に含めない） | REQ-F-007 | 高 |
| TC-DOM-099 | `test_dormant_user_count_includes_never_logged_in_user` | `last_login=None` の有効ユーザー 1 名 | `1`（S-603 を含める） | REQ-F-007 | 高 |
| TC-DOM-100 | `test_menu_display_title_returns_title_for_known_key` | `"shipment-trend-list"` | メニュー定義の `title` | REQ-F-008 | 高 |
| TC-DOM-101 | `test_menu_display_title_marks_retired_for_unknown_key` | `"legacy-report"` | `"legacy-report（廃止）"`。`is_retired` が真、メニューグループは `"—"` | REQ-F-017 | 高 |
| TC-DOM-102 | `test_aggregation_target_menu_keys_exclude_parent_without_href` | `MENU_ITEMS` 全件 | `receipt-comparison`（`href` 空）が含まれない。`usage-status` は含まれる | REQ-F-008・REQ-F-015 | 高 |
| TC-DOM-103 | `test_usage_status_csv_row_limit_is_100000` | `USAGE_STATUS_CSV_ROW_LIMIT` | `100_000` | REQ-F-014 | 低 |
| TC-DOM-104 | `test_usage_status_purpose_note_denies_performance_review` | `USAGE_STATUS_PURPOSE_NOTE` | 「勤務評価には用いません」を含む | REQ-NF-005 | 中 |

### 2.2 Application層テスト

リポジトリは `Protocol` を満たすフェイク（戻り値を固定した小さなクラス）に差し替える。DB は使わない。

#### `RecordUsage` — `test_usecase_record_usage.py`

| # | テストケース | 入力 | 期待結果 | 対応REQ-ID | 優先度 |
|---|---|---|---|---|---|
| TC-APP-001 | `test_record_usage_passes_target_to_repository` | `target=UsageRecordTarget("shipment-trend-list","VIEW")`, `user=<ユーザー>` | フェイクの `record()` が 1 回、`menu_key`/`usage_type`/`user` が一致 | REQ-F-001 | 高 |
| TC-APP-002 | `test_record_usage_passes_export_usage_type` | `usage_type="EXPORT"` | フェイクに `"EXPORT"` が渡る | REQ-F-002 | 高 |
| TC-APP-003 | `test_record_usage_propagates_repository_error` | フェイクが `RuntimeError` | 例外がそのまま伝播する（握りつぶすのは Interfaces 層の責務） | REQ-F-004 | 高 |

#### `UsageStatus` — `test_usecase_usage_status.py`

| # | テストケース | 入力 | 期待結果 | 対応REQ-ID | 優先度 |
|---|---|---|---|---|---|
| TC-APP-010 | `test_page_context_builds_all_sections` | フェイクが §3.1 のデータを返す | 戻り値に全体集計・メニュー別・ユーザー別・未利用付与・出力記録・日別推移の 6 つが揃う | REQ-F-007〜012 | 高 |
| TC-APP-011 | `test_page_context_passes_aware_datetime_range` | `start="2026-08-01", end="2026-08-27"` | フェイクが受け取った `start_at`/`end_at` が `tzinfo` を持つ | REQ-F-006 | 高 |
| TC-APP-012 | `test_page_context_returns_error_message_for_invalid_period` | `start="2026-08-28", end="2026-08-27"` | `error_message` が規則 3 の文言。各一覧が空。**リポジトリを 1 度も呼ばない** | REQ-F-006 | 高 |
| TC-APP-013 | `test_page_context_returns_zero_summary_without_logs` | フェイクがすべて空を返す | 例外なし。`UsageSummary` の 5 値が 0。各一覧の `is_empty` が真 | REQ-F-016 | 高 |
| TC-APP-014 | `test_page_context_filters_rows_by_menu_group` | `group_key="sales"` | メニュー別・ユーザー別・未利用付与が `sales` の行のみ | REQ-F-013 | 高 |
| TC-APP-015 | `test_page_context_applies_sort_specs` | `sort_key="usage_count", sort_direction="desc"` | 対象一覧が降順 | REQ-NF-007 | 中 |
| TC-APP-016 | `test_page_context_uses_given_today` | `today=date(2026,1,15)` を明示 | 既定期間が `2025-12-17`〜`2026-01-15` になる（実行日に依存しない） | REQ-F-006 | 高 |
| TC-APP-017 | `test_csv_payload_returns_rows_for_each_section` | `section` = `menus`/`users`/`unused-grants`/`exports` | 各区分のヘッダ行が一致。`error_message` は `None` | REQ-F-014 | 高 |
| TC-APP-018 | `test_csv_payload_rejects_unknown_section` | `section="unknown"` | `rows is None` かつ `error_message` あり | REQ-F-014 | 中 |
| TC-APP-019 | `test_csv_payload_allows_row_limit_exactly` | 100,000 行 | `rows` の長さがヘッダ ＋ 100,000 | REQ-F-014 | 高 |
| TC-APP-020 | `test_csv_payload_rejects_rows_over_limit` | 100,001 行 | `rows is None`。`error_message` に「10 万行」を含む | REQ-F-014 | 高 |
| TC-APP-021 | `test_csv_payload_rejects_invalid_period` | `start > end` | `rows is None`。`error_message` は規則 3 の文言 | REQ-F-006・REQ-F-014 | 中 |
| TC-APP-022 | `test_page_context_always_includes_purpose_note` | 任意 | `USAGE_STATUS_PURPOSE_NOTE` がコンテキストに載る（エラー時も） | REQ-NF-005 | 中 |
| TC-APP-023 | `test_page_context_paginates_rows_with_shared_kernel` | 全 25 行・`page=2, page_size=10` | 対象一覧の行が 11〜20 行目。共有カーネル `paginate_rows` の戻り値をそのまま使う | REQ-NF-007 | 中 |
| TC-APP-024 | `test_page_context_returns_first_page_by_default` | `page`/`page_size` を渡さない | 1 ページ目が返り、総ページ数がコンテキストに載る | REQ-NF-007 | 中 |
| TC-APP-025 | `test_page_context_clamps_page_beyond_last_page` | 全 5 行・`page=99` | 例外を送出せず、共有カーネル `paginate_rows` の規約どおり最終ページに丸めて返る | REQ-NF-007 | 中 |

### 2.3 Infrastructure層テスト

`@pytest.mark.django_db` を付ける。`MenuUsageLog` を直接 INSERT して集計結果を検証する。

#### `DjangoMenuUsageLogRepository` — `test_usage_status_repository.py`

| # | テストケース | 入力 | 期待結果 | 対応REQ-ID | 優先度 |
|---|---|---|---|---|---|
| TC-INF-001 | `test_record_saves_single_row` | `record(user=u1, menu_key="shipment-trend-list", usage_type="VIEW")` | 行数 1。`used_at` が現在時刻に近い aware datetime | REQ-F-001 | 高 |
| TC-INF-002 | `test_record_stores_only_four_columns` | 保存後のモデルのフィールド名 | `id`/`user`/`menu_key`/`usage_type`/`used_at` のみ（IP・UA 等が無い） | REQ-NF-005 | 高 |
| TC-INF-003 | `test_record_keeps_log_with_null_user_after_user_delete` | 記録後に `User.delete()` | ログ行は残り `user_id is None` | REQ-F-018・REQ-NF-004 | 高 |
| TC-INF-004 | `test_record_allows_repeated_rows_for_same_user` | 同一ユーザーで 3 回 | 3 行。ユニーク制約で失敗しない | REQ-NF-003 | 中 |
| TC-INF-005 | `test_menu_usage_log_repository_has_no_update_or_delete` | リポジトリの公開メソッド | `record` と読み取りのみ。`update_*`/`delete_*` が無い | REQ-NF-004 | 中 |
| TC-INF-006 | `test_record_stores_menu_key_up_to_max_length` | `menu_key` が 80 文字ちょうど / 81 文字 / 空文字 | 80 文字は保存できる。81 文字は `DataError`（切り捨てて保存しない）。空文字は保存しない | REQ-F-001・REQ-NF-004 | 低 |

#### `DjangoUsageStatusRepository` — `test_usage_status_repository.py`

| # | テストケース | 入力 | 期待結果 | 対応REQ-ID | 優先度 |
|---|---|---|---|---|---|
| TC-INF-010 | `test_overall_counts_include_logs_in_period_only` | §3.1 のログ（期間内 6 件・期間外 2 件） | `usage_count=6`、`export_count` は `EXPORT` の件数、`active_user_count` は重複を除いたユーザー数 | REQ-F-007 | 高 |
| TC-INF-011 | `test_period_includes_start_date_midnight` | `2026-08-01 00:00:00+09:00` のログ、期間 08-01〜08-05 | 含まれる | REQ-F-006 | 高 |
| TC-INF-012 | `test_period_includes_end_date_last_moment` | `2026-08-05 23:59:59.999+09:00` | 含まれる（`__lt 翌日00:00` のため秒未満も取りこぼさない） | REQ-F-006 | 高 |
| TC-INF-013 | `test_period_excludes_moment_before_start_date` | `2026-07-31 23:59:59+09:00` | 含まれない | REQ-F-006 | 高 |
| TC-INF-014 | `test_period_excludes_next_day_midnight` | `2026-08-06 00:00:00+09:00` | 含まれない | REQ-F-006 | 高 |
| TC-INF-015 | `test_period_uses_asia_tokyo_date_for_utc_rows` | UTC `2026-08-04 16:00`（JST 08-05 01:00）のログ、期間 08-05〜08-05 | 含まれる | REQ-F-006 | 高 |
| TC-INF-016 | `test_menu_counts_split_view_and_export` | 同一メニューに `VIEW` 2 件・`EXPORT` 1 件 | `view_count=2`, `export_count=1`, `user_count` は重複除去 | REQ-F-008 | 高 |
| TC-INF-017 | `test_last_used_at_by_menu_key_returns_latest_of_all_time` | 期間外（過去）にのみ利用があるメニュー | 集計期間外でも最終利用日が返る | REQ-F-008 | 高 |
| TC-INF-018 | `test_last_used_at_by_user_returns_latest_of_all_time` | 同上 | 同上 | REQ-F-009 | 高 |
| TC-INF-019 | `test_menu_counts_by_user_returns_counts_per_pair` | u1 が a を 3 回・b を 1 回 | `[{user_id:u1, menu_key:"a", count:3}, {…"b",1}]`。**最多の判定はしない** | REQ-F-009 | 高 |
| TC-INF-020 | `test_daily_counts_return_count_per_date` | 08-02 に 3 件・08-04 に 1 件 | 2 レコード（0 件の日は返さない。埋めるのは domain） | REQ-F-012 | 高 |
| TC-INF-021 | `test_export_entries_return_export_rows_only` | `VIEW` 5 件・`EXPORT` 2 件 | 2 件。利用日時降順 | REQ-F-011 | 高 |
| TC-INF-022 | `test_approved_user_entries_return_six_fields` | 許可・未許可・却下のユーザー | 許可済みのみ。各行に `user_id`/`username`/`display_name`/`role`/`is_active`/`last_login` | REQ-F-009 | 高 |
| TC-INF-023 | `test_approved_user_entries_include_inactive_user` | `is_active=False` の許可済みユーザー | 行に含まれ `is_active=False`（除外の判断は domain） | REQ-F-018 | 高 |
| TC-INF-024 | `test_menu_group_grants_include_granted_on` | `MenuGroupAccess` 2 件 | `user_id`/`group_key`/`granted_on`（`created_at` の日付） | REQ-F-010 | 高 |
| TC-INF-025 | `test_counts_include_logs_with_null_user` | `user=None` のログ 2 件 | 全体集計・メニュー別・日別・出力記録に含まれる。ユーザー別（`user_counts()` / `menu_counts_by_user()` / `used_menu_keys_by_user()`）には含めない（design.md §6.7） | REQ-F-018 | 高 |
| TC-INF-026 | `test_menu_counts_include_unknown_menu_key` | `menu_key="legacy-report"` のログ | メニュー別集計に現れる（表示名の解決は domain） | REQ-F-017 | 高 |
| TC-INF-027 | `test_counts_return_empty_without_logs` | ログ 0 件 | 例外なし。件数は 0、一覧は空 | REQ-F-016 | 高 |
| TC-INF-028 | `test_menu_usage_log_defines_four_indexes` | `MenuUsageLog._meta.indexes` | design.md §5.2 の 4 本（フィールドと名前が一致） | REQ-NF-002 | 中 |

### 2.4 Interfaces層テスト

#### `UsageLoggingMiddleware` — `test_usage_logging_middleware.py`

| # | テストケース | 入力 | 期待結果 | 対応REQ-ID | 優先度 |
|---|---|---|---|---|---|
| TC-UI-001 | `test_middleware_records_view_for_authenticated_page_request` | 許可済みユーザーでメニュー画面に GET | ログ 1 件（`VIEW`、該当メニューキー、当該ユーザー） | REQ-F-001 | 高 |
| TC-UI-002 | `test_middleware_skips_anonymous_request` | 匿名で GET（ログイン画面へリダイレクト） | ログ 0 件 | REQ-F-003 | 高 |
| TC-UI-003 | `test_middleware_skips_forbidden_response` | 一般ユーザーで管理メニューに GET | 403 が返り、ログ 0 件 | REQ-F-003・REQ-NF-001 | 高 |
| TC-UI-004 | `test_middleware_skips_redirect_response` | 未許可ユーザーで `/app/...` に GET（利用申請状況へ 302） | ログ 0 件 | REQ-F-003 | 高 |
| TC-UI-005 | `test_middleware_skips_api_json_response` | `/api/...` の JSON 応答 | ログ 0 件 | REQ-F-003 | 高 |
| TC-UI-006 | `test_middleware_records_export_for_csv_download` | 出力エンドポイントに GET（200 ＋ attachment） | ログ 1 件（`EXPORT`） | REQ-F-002 | 高 |
| TC-UI-007 | `test_middleware_returns_response_when_recording_fails` | リポジトリが例外を送出するようパッチ | HTTP 200。本文が変わらない。ログ 0 件。`logging` に warning が 1 件 | REQ-F-004 | 高 |
| TC-UI-008 | `test_middleware_hides_recording_failure_from_user` | 同上 | 応答本文にエラー文言・トレースバックを含まない | REQ-F-004 | 高 |
| TC-UI-009 | `test_middleware_records_once_per_request` | 画面を 1 回 GET | ログ 1 件（重複記録なし） | REQ-NF-003 | 高 |
| TC-UI-010 | `test_middleware_is_registered_after_access_approval` | `settings.MIDDLEWARE` | `AccessApprovalMiddleware` の直後に位置する | REQ-F-003 | 中 |
| TC-UI-011 | `test_middleware_records_once_for_legacy_url_redirect` | 検収書比較の旧 URL に GET（302 → 遷移先を GET） | ログは遷移先の 1 件のみ | REQ-F-002 | 中 |

#### view `usage_status_page` / `usage_status_export_csv` — `test_usage_status_page.py`

| # | テストケース | 入力 | 期待結果 | 対応REQ-ID | 優先度 |
|---|---|---|---|---|---|
| TC-UI-020 | `test_usage_status_page_returns_200_for_admin` | 管理者で `/app/management/usage-status` に GET | 200。テンプレート `portal/usage_status.html` | REQ-F-005 | 高 |
| TC-UI-021 | `test_usage_status_page_forbids_general_user` | 一般ユーザーで同 URL に GET | 403 | REQ-NF-001 | 高 |
| TC-UI-022 | `test_usage_status_export_forbids_general_user` | 一般ユーザーで `export.csv` に GET | 403 | REQ-NF-001 | 高 |
| TC-UI-023 | `test_usage_status_page_redirects_anonymous_to_login` | 匿名で GET | ログイン画面へリダイレクト | REQ-NF-001 | 中 |
| TC-UI-024 | `test_usage_status_appears_in_admin_menu_only` | 管理者でポータルトップを GET | 管理メニューに「利用状況」が含まれる。一般ユーザーには含まれない | REQ-F-005 | 高 |
| TC-UI-025 | `test_usage_status_page_always_shows_purpose_note` | 管理者で GET（正常時・エラー時の両方） | 本文に注記が含まれる | REQ-NF-005 | 高 |
| TC-UI-026 | `test_usage_status_page_defaults_to_last_30_days` | クエリなしで GET | 画面の開始日が当日の 29 日前、終了日が当日 | REQ-F-006 | 高 |
| TC-UI-027 | `test_usage_status_page_shows_error_for_invalid_period` | `?start=2026-08-28&end=2026-08-27` | 200。エラー文言あり。一覧の行が 0 | REQ-F-006 | 高 |
| TC-UI-028 | `test_usage_status_page_shows_no_rows_message_without_logs` | ログを作らずに GET | 全体集計（利用回数・出力回数・利用ユーザー数）が 0。未利用付与・出力操作の記録の 2 一覧が 0 件で「該当なし」を表示。メニュー別は集計対象メニューが全件 0 回で並び、ユーザー別は承認済み有効ユーザーが全件 0 回で並ぶ（利活用把握のため 0 回の行も表示する） | REQ-F-016 | 高 |
| TC-UI-029 | `test_usage_status_page_marks_retired_menu` | `menu_key="legacy-report"` のログ | 本文に「legacy-report（廃止）」 | REQ-F-017 | 高 |
| TC-UI-030 | `test_usage_status_page_shows_unknown_user_label` | `user=None` のログ | 出力操作の記録に `UNKNOWN_USER_LABEL`。ユーザー別一覧には現れない | REQ-F-018 | 高 |
| TC-UI-031 | `test_usage_status_page_excludes_inactive_user_from_user_rows` | `is_active=False` のユーザーのログ | ユーザー別・未利用付与に現れない。全体集計・メニュー別には含まれる | REQ-F-018 | 高 |
| TC-UI-032 | `test_usage_status_page_filters_by_menu_group` | `?group=sales` | `sales` の行のみ | REQ-F-013 | 高 |
| TC-UI-033 | `test_usage_status_export_returns_csv_per_section` | `?section=menus` ほか 4 区分 | 200。`Content-Disposition: attachment`。ヘッダ行が区分ごとに一致 | REQ-F-014 | 高 |
| TC-UI-034 | `test_usage_status_export_applies_same_period_and_filter` | `?section=users&start=…&end=…&group=sales` | 画面と同じ行数・同じ並び | REQ-F-014 | 高 |
| TC-UI-035 | `test_usage_status_export_shows_message_over_row_limit` | 上限超過となるよう `csv_payload` をパッチ | `Content-Disposition` を返さず、画面に文言を表示 | REQ-F-014 | 中 |
| TC-UI-036 | `test_usage_status_page_records_its_own_view` | 管理者で画面を GET | `usage-status` の `VIEW` が 1 件 | REQ-F-015 | 高 |
| TC-UI-037 | `test_usage_status_export_records_its_own_export` | 管理者で `export.csv` を GET | `usage-status` の `EXPORT` が 1 件 | REQ-F-015 | 高 |
| TC-UI-038 | `test_usage_status_url_resolves_before_slug_placeholder` | `reverse("portal:usage_status")` と `resolve()` | `/app/management/usage-status` が `usage_status_page` に解決される（`<str:slug>` に吸われない） | REQ-F-005 | 高 |
| TC-UI-039 | `test_usage_status_list_client_js_defines_required_keys` | `static/js/usage-status-list-client.js` を読み取る | 4 つの一覧ぶんの設定キーが定義されている（既存 `test_portal_list_*_js.py` と同じ静的検証） | REQ-NF-007 | 低 |
| TC-UI-040 | `test_usage_status_page_applies_page_query_parameters` | `?page=2&size=10` | 2 ページ目の行が描画され、ページャの現在ページが 2 になる | REQ-NF-007 | 中 |
| TC-UI-041 | `test_usage_status_page_ignores_invalid_page_query_parameters` | `?page=abc&size=-1` | 500 にならず既定（1 ページ目・既定件数）で描画される | REQ-NF-007 | 中 |

#### アーキテクチャ検証（既存テストの拡張・`config/tests/test_clean_architecture.py`）

| # | テストケース | 入力 | 期待結果 | 対応REQ-ID | 優先度 |
|---|---|---|---|---|---|
| TC-UI-050 | `config/tests/test_clean_architecture.py` の既存テスト全件（本機能では新規テスト関数を足さない） | 新規ファイル追加後に `config/tests/test_clean_architecture.py` を実行 | 全件 PASS（`domain`/`use_cases` に `import django` が無い、views が wiring 経由、`composition.py`・`services/` を作っていない） | REQ-NF-006 | 高 |

---

## 3. テストデータ

### 3.1 正常系テストデータ

**基準日**: `today = date(2026, 8, 27)`。既定の集計期間は `2026-07-29` 〜 `2026-08-27`。
Domain / Application のテストでは基準日を必ず引数で与え、実行日に依存させない。

**ユーザー（Infrastructure / Interfaces）**:

| 変数 | `username`（core V-001） | 役割（core R-003） | 利用申請 | `is_active`（S-604） | `last_login`（V-606） |
|---|---|---|---|---|---|
| `admin_user` | `10001` | 管理者（core R-001） | 許可（core S-001） | True | `2026-08-27 08:30+09:00` |
| `general_user` | `10002` | 一般ユーザー（core R-002） | 許可 | True | `2026-08-26 08:31+09:00` |
| `dormant_user` | `10003` | 一般ユーザー | 許可 | True | `2026-07-01 08:00+09:00`（休眠・S-605） |
| `never_login_user` | `10004` | 一般ユーザー | 許可 | True | `None`（未ログイン・S-603） |
| `inactive_user` | `10005` | 一般ユーザー | 許可 | **False** | `2026-08-20 08:00+09:00` |
| `pending_user` | `10006` | 一般ユーザー | 申請中 | True | `None` |

**メニューグループ付与（core V-002）**: `general_user` に `sales` と `management`、`dormant_user` に `sales`。付与日はいずれも `2026-05-01`。

**メニュー利用ログ（期間 `2026-08-01` 〜 `2026-08-05` のテスト用）**:

| # | ユーザー | `menu_key` | `usage_type` | `used_at`（JST） | 用途 |
|---|---|---|---|---|---|
| 1 | `general_user` | `shipment-trend-list` | `VIEW` | 2026-08-01 00:00:00 | 開始日の下限境界 |
| 2 | `general_user` | `shipment-trend-list` | `VIEW` | 2026-08-02 10:15:00 | 通常 |
| 3 | `general_user` | `shipment-trend-list` | `EXPORT` | 2026-08-02 10:16:00 | 出力操作（A-602） |
| 4 | `general_user` | `asset-inventory` | `VIEW` | 2026-08-02 11:00:00 | 最多同数のタイブレーク検証用 |
| 5 | `dormant_user` | `asset-inventory` | `VIEW` | 2026-08-04 09:00:00 | 日別推移の欠落日検証用 |
| 6 | `None`（削除済み） | `shipment-trend-list` | `EXPORT` | 2026-08-05 23:59:59.999 | 終了日の上限境界 ＋ REQ-F-018 |
| 7 | `general_user` | `shipment-trend-list` | `VIEW` | 2026-07-31 23:59:59 | 期間外（下限の外） |
| 8 | `general_user` | `shipment-trend-list` | `VIEW` | 2026-08-06 00:00:00 | 期間外（上限の外） |

この 8 件により、期間内 6 件 / 期間外 2 件、`VIEW` 4 件 / `EXPORT` 2 件、利用ユーザー 2 名（＋ 削除済み 1）、08-03 が空白日、という前提が 1 セットで揃う。

**判別テスト用の応答パターン**（Domain）:

| 名前 | `path` | `type` | `status_code` | `content_type` | `is_attachment` |
|---|---|---|---|---|---|
| HTML 正常 | `/app/sales/shipment-trend` | `""` | 200 | `text/html; charset=utf-8` | False |
| 出力成功 | `/api/shipment-trend/export.csv` | `""` | 200 | `text/csv` | True |
| 出力失敗 | `/api/shipment-trend/export.csv` | `""` | 502 | `text/html` | False |
| 非同期問い合わせ | `/api/gonenkukumi/search` | `""` | 200 | `application/json` | False |
| 添付中継 | `/api/asset-inventory/attachment` | `""` | 200 | `application/pdf` | True |
| リダイレクト | `/app/production/receipt-comparison/xxx` | `""` | 302 | `text/html` | False |

### 3.2 異常系テストデータ

| 分類 | データ |
|---|---|
| 集計期間（文字列） | `""` / `" "` / `"2026/08/01"` / `"2026-13-01"` / `"2026-02-30"` / `"abc"` / `"20260801"` |
| 集計期間（日付） | 開始 > 終了（`2026-08-28`〜`2026-08-27`）／365 日／366 日／367 日／未来日終了（`2026-09-30`） |
| 利用種別 | `"DOWNLOAD"` / `"view"` / `""` / `None` |
| メニューキー | 現行定義に無い `"legacy-report"`／空文字／80 文字ちょうど／81 文字 |
| ユーザー | `user_id=None`（物理削除）／`is_active=False`／申請中（未許可） |
| CSV | 0 行／1 行／100,000 行／100,001 行／未知の `section` |
| リポジトリ | `record()` が `OperationalError` を送出／集計メソッドが空リストを返す |

### 3.3 テストデータの作り方

- **Domain / Application**: リテラルでその場に組み立てる。fixture もフェイクもテストファイル内に閉じる
- **Infrastructure / Interfaces**: `django.contrib.auth.get_user_model()` と `application/portal/models.py` の ORM モデルを直接使う。factory ライブラリは導入しない（既存の portal テストと同じ流儀）
- `used_at` は `django.utils.timezone.make_aware(datetime(...), ZoneInfo("Asia/Tokyo"))` で明示的に作る。`timezone.now()` を境界テストに使わない
- 既存の portal テストが用意しているユーザー作成ヘルパーがあれば再利用する。無ければ本機能のテストファイル内に `_create_approved_user(...)` を置く

---

## 4. 境界値・異常系のカバレッジ

### 4.1 境界値テスト

| 対象 | 最小-1 | 最小 | 典型 | 最大 | 最大+1 | テストケース |
|---|---|---|---|---|---|---|
| 集計期間の日数 | — | 1 日（開始＝終了） | 30 日（既定） | 366 日 | 367 日 | TC-DOM-050・052・053・054・058 |
| 集計期間の下限日時 | 開始日前日 23:59:59 | 開始日 00:00:00 | — | — | — | TC-INF-011・013 |
| 集計期間の上限日時 | — | — | — | 終了日 23:59:59.999 | 翌日 00:00:00 | TC-INF-012・014 |
| CSV 行数 | — | 0 行 | 1 行 | 100,000 行 | 100,001 行 | TC-APP-017・019・020 |
| 一覧の行数 | — | 0 行 | 1 行／多数 | — | — | TC-DOM-072・073・TC-UI-028 |
| 日別推移の点数 | — | 1 点（1 日期間） | 5 点（欠落あり） | 366 点 | — | TC-DOM-093・095 |
| 最多利用メニューの候補 | — | 0 件（`None`） | 単独最多 | 同数（タイブレーク） | — | TC-DOM-090・091・092 |
| 休眠の判定日 | 開始日前日 | 開始日当日 | — | — | — | TC-DOM-098 |
| `menu_key` の長さ | — | 空文字 | 通常 | 80 文字 | 81 文字 | TC-INF-006 |
| ページ番号 | 0・非数値 | 1（既定） | 2 | 最終ページ | 最終ページ+1 | TC-APP-023・024・025、TC-UI-040・041 |

### 4.2 異常系テスト

| 対象 | 異常ケース | 期待される振る舞い | テストケース |
|---|---|---|---|
| 利用種別 | 値域外の文字列 | エンティティ生成時に `ValueError` | TC-DOM-003 |
| 集計期間 | 片方だけ空 | `AggregationPeriodError`（規則 1 の文言） | TC-DOM-061・062 |
| 集計期間 | 形式不正・存在しない日付 | `AggregationPeriodError`（規則 2 の文言） | TC-DOM-063 |
| 集計期間 | 開始 > 終了 | `AggregationPeriodError`（規則 3 の文言）。画面は 200 でエラー表示 | TC-DOM-051・TC-UI-027 |
| 集計期間 | 366 日超過 | `AggregationPeriodError`（規則 4 の文言） | TC-DOM-054 |
| 利用記録 | DB 書き込み失敗 | 応答はそのまま返る。warning ログのみ | TC-UI-007・008 |
| 利用記録 | 未認証・匿名 | 記録しない | TC-UI-002 |
| 利用記録 | 403 / 302 / 5xx | 記録しない | TC-UI-003・004・TC-DOM-033 |
| 認可 | 一般ユーザーが URL 直接指定 | 403 | TC-UI-021・022 |
| 表示 | 対象 0 件 | 未利用付与・出力操作の記録は「該当なし」。メニュー別・ユーザー別は 0 回の行を表示する。例外にしない | TC-UI-028・TC-APP-013 |
| 表示 | 現行定義に無いメニューキー | 「（廃止）」付きで表示。グループは「—」 | TC-DOM-101・TC-UI-029 |
| 表示 | 物理削除されたユーザー | `UNKNOWN_USER_LABEL`。ユーザー別一覧からは除外 | TC-DOM-097・TC-INF-025・TC-UI-030 |
| 表示 | 無効化されたユーザー | ユーザー別・未利用付与から除外。集計には含める | TC-INF-023・TC-UI-031 |
| CSV | 上限超過 | 出力せず文言を表示 | TC-APP-020・TC-UI-035 |
| CSV | 未知の区分 | エラーを返す（500 にしない） | TC-APP-018 |

### 4.3 エッジケース

| # | ケース | 検証方法 | テストケース |
|---|---|---|---|
| 1 | 同時実行（50 ユーザーの一斉アクセス） | 排他制御を持たない構造であることを設計で担保する。テストでは「1 リクエスト 1 INSERT のみ・トランザクションを跨いだロックを取らない」ことを TC-UI-009 と TC-INF-004 で間接的に固定する。並列負荷の実測は §4.4 で手動確認 | TC-UI-009・TC-INF-004 |
| 2 | 大量データ（50 万件） | 自動テストでは作らない。§4.4 の手動確認で計測する。代わりに索引定義を TC-INF-028 で固定する | TC-INF-028 |
| 3 | データ不整合（現行定義に無いメニューキー） | 廃止扱いで表示し、例外にしない | TC-DOM-101・TC-INF-026 |
| 4 | データ不整合（ログはあるがユーザーが存在しない） | `user_id=None` として集計に含める | TC-INF-025 |
| 5 | 旧 URL のリダイレクト経由アクセス | 二重記録しない | TC-UI-011 |
| 6 | 出力エンドポイントの追加漏れ | 全アプリの `urlpatterns` を走査し、`EXPORT_ENDPOINTS` との差分で失敗させる | TC-DOM-015 |
| 7 | 利用状況画面自身の再帰的な記録 | 記録される（仕様）。1 表示につき 1 件を超えない | TC-UI-036・037・TC-UI-009 |
| 8 | 集計期間の全日が未来 | エラーにせず 0 件表示 | TC-DOM-055・TC-UI-028 |

### 4.4 自動テスト対象外の確認項目（Phase 5 の手動確認）

| # | 項目 | 確認方法 | 対応REQ-ID |
|---|---|---|---|
| 1 | 画面表示 3 秒以内（集計期間 3 か月・ログ 50 万件） | 検証環境にログを投入し、ブラウザの計測で確認 | REQ-NF-002 #2 |
| 2 | 記録による遅延が 50ms 以内 | ミドルウェア有無での応答時間を比較計測 | REQ-NF-003 |
| 3 | 同時 50 ユーザーで #2 を満たす | 負荷をかけて計測 | REQ-NF-003 #2 |
| 4 | 年間容量の見積り（実測 97.4MB / 50 万件・design.md §5.6）と監視対象への追加 | 実測して `Document/` の運用手順に反映 | REQ-NF-004 |
| 5 | 画面の見た目（棒グラフ・既存管理画面との操作感） | 目視 | REQ-NF-007 |
| 6 | 対象外コンテキストを変更していないこと | `git diff --name-only` で `asset_inventory` / `gonenkukumi` / `inventory_order_alert` / `receipt_comparison` / `shipment_trend` の変更が 0 件であることを確認 | REQ-NF-006 |

### 4.5 要件カバレッジ表

| REQ-ID | 対応テストケース |
|---|---|
| REQ-F-001 | TC-DOM-001・003・020・021・023・024・027・030、TC-APP-001、TC-INF-001・006、TC-UI-001 |
| REQ-F-002 | TC-DOM-002・010・011・031・032・033・039、TC-APP-002、TC-UI-006・011 |
| REQ-F-003 | TC-DOM-012・025・033・034・035・036、TC-UI-002・003・004・005・010 |
| REQ-F-004 | TC-APP-003、TC-UI-007・008 |
| REQ-F-005 | TC-UI-020・024・038 |
| REQ-F-006 | TC-DOM-050〜066、TC-APP-011・012・016、TC-INF-011〜015、TC-UI-026・027 |
| REQ-F-007 | TC-DOM-070・071・097・098・099、TC-APP-010、TC-INF-010 |
| REQ-F-008 | TC-DOM-022・072〜077・100・102、TC-INF-016・017 |
| REQ-F-009 | TC-DOM-078・090・091・092、TC-INF-018・019・022 |
| REQ-F-010 | TC-DOM-080・081・082、TC-INF-024 |
| REQ-F-011 | TC-DOM-079、TC-INF-021 |
| REQ-F-012 | TC-DOM-093〜096、TC-INF-020 |
| REQ-F-013 | TC-DOM-075・076、TC-APP-014、TC-UI-032 |
| REQ-F-014 | TC-DOM-077・078・103、TC-APP-017〜021、TC-UI-033・034・035 |
| REQ-F-015 | TC-DOM-026・037・038・102、TC-UI-036・037 |
| REQ-F-016 | TC-DOM-072・073・081・092・094、TC-APP-013、TC-INF-027、TC-UI-028 |
| REQ-F-017 | TC-DOM-005・101、TC-INF-026、TC-UI-029 |
| REQ-F-018 | TC-DOM-004・097、TC-INF-003・023・025、TC-UI-030・031 |
| REQ-NF-001 | TC-UI-003・021・022・023 |
| REQ-NF-002 | TC-INF-028、§4.4 #1 |
| REQ-NF-003 | TC-INF-004、TC-UI-009、§4.4 #2・#3 |
| REQ-NF-004 | TC-DOM-005、TC-INF-003・005・006、§4.4 #4 |
| REQ-NF-005 | TC-DOM-104、TC-INF-002、TC-APP-022、TC-UI-025 |
| REQ-NF-006 | TC-DOM-013・056・071、TC-UI-050、§4.4 #6 |
| REQ-NF-007 | TC-DOM-074、TC-APP-015・023〜025、TC-UI-039〜041、§4.4 #5 |
| REQ-NF-008 | TC-DOM-015、および本設計書の全テストケース（TDD で実装する） |

**未カバーの REQ-ID: 0 件**（REQ-NF-002 #2・REQ-NF-003 の実測のみ §4.4 の手動確認に委ねる）。

---

## 5. テスト環境

### 5.1 テスト実行コマンド

pytest + pytest-django。設定は `config/settings/test.py`。

| 目的 | コマンド |
|---|---|
| DB 不要のテストだけを高速に回す（TDD の内側のループ） | `make test-fast` |
| 本機能の Domain / Application だけを回す | `pytest application/portal/tests/test_menu_usage_log.py application/portal/tests/test_usage_record_target.py application/portal/tests/test_usage_period.py application/portal/tests/test_usage_status_display.py application/portal/tests/test_usecase_record_usage.py application/portal/tests/test_usecase_usage_status.py` |
| portal 全体 | `pytest application/portal/tests/` |
| 1 件だけ | `pytest application/portal/tests/test_usage_period.py::test_aggregation_period_rejects_367_days` |
| 全テスト（DB あり） | `make test-all` |
| カバレッジ | `make test-cov` |
| アーキテクチャ検証 | `pytest config/tests/test_clean_architecture.py` |

TDD のサイクルでは `make test-fast` を主に回し、Infrastructure / Interfaces に着手した段階で `pytest application/portal/tests/` に切り替える。

### 5.2 テストデータの準備方法

- **fixture**: 本機能のテストファイル内に閉じた pytest fixture として書く（`conftest.py` に共有 fixture を新設しない。既存 portal テストに合わせる）
- **factory ライブラリ**: 導入しない
- **DB**: `@pytest.mark.django_db` を付けたテストのみ。マイグレーション `0007_menu_usage_log.py` が適用された状態で実行される
- **タイムゾーン**: `settings.TIME_ZONE = "Asia/Tokyo"` / `USE_TZ = True` を前提とする。境界テストでは JST の aware datetime を明示的に組み立てる
- **時刻の固定**: `freezegun` 等は導入しない。現在日時は `today` 引数・`used_at` 引数で外から与える設計（design.md §6.7）のため、ライブラリを使わずに固定できる。ミドルウェアの記録時刻だけは `timezone.now()` に依存するが、値そのものを検証せず「記録されたこと」を検証する

### 5.3 実装順（TDD の進め方）

requirements.md §6.3 の制約 4（記録が先・画面が後）に従い、次の順で Red-Green-Refactor を回す。

| 段 | 対象 | テストファイル | 完了条件 |
|---|---|---|---|
| 1 | 記録側 Domain | #1・#2 | TC-DOM-001〜039 が緑（**TC-DOM-015 を除く**） |
| 2 | 記録側 Application / Infrastructure | #5・#7（記録部分） | TC-APP-001〜003・TC-INF-001〜006 が緑 |
| 3 | 記録側 Interfaces | #8 | TC-UI-001〜011 が緑。**この段でメニュー利用ログの蓄積が始められる** |
| 4 | 画面側 Domain | #3・#4 | TC-DOM-050〜104 が緑 |
| 5 | 画面側 Application / Infrastructure | #6・#7（集計部分） | TC-APP-010〜025・TC-INF-010〜028 が緑 |
| 6 | 画面側 Interfaces | #9 | TC-UI-020〜041 が緑。あわせて **TC-DOM-015 が緑**（本段で `/app/management/usage-status/export.csv` を `urlpatterns` に登録するため） |
| 7 | 仕上げ | — | `make test-all` と `pytest config/tests/test_clean_architecture.py` が緑（TC-UI-050）。§4.4 #6 を確認 |

> **TC-DOM-015 の緑になる時期について（2026/08/27 追記）**
> TC-DOM-015 は `EXPORT_ENDPOINTS`（design.md §4.4(b)）と全アプリの `urlpatterns` の一致を検証する。
> 同表の 9 件目は本機能自身の CSV 出力 URL であり、段 6 で URL を登録するまで一致しない。
> したがって段 1 では TC-DOM-015 を赤のまま残し、段 6 で緑になることを確認する。
> また TC-DOM-026・037・038（`resolve_menu_key` が `usage-status` を返す）は `MENU_ITEMS` への
> メニュー項目追加（design.md §6.1）を前提とするため、この 1 件の変更は段 1 の最初に行う。

---

## レビュー履歴

### テスト設計レビュー (2026/08/27 17:42)

**テスト戦略reference**: test-strategy version 1.1（updated 2026-04-25、make-test-design 側と ✅ 一致）
**テストフレームワークreference**: django-pytest version 1.0

**観点別サマリー**:

| 観点 | OK | 警告 | NG |
|------|-----|------|-----|
| 1. テスト戦略の妥当性 | 6件 | 0件 | 1件 |
| 2. テストケースの網羅性 | 7件 | 1件 | 0件 |
| 3. 境界値・異常系のカバレッジ | 5件 | 2件 | 0件 |
| 4. テストケースの品質 | 6件 | 2件 | 0件 |
| **合計** | **24件** | **5件** | **1件** |

**総合判定**: CONDITIONAL PASS（NG 1件）→ 指摘 6 件すべて修正済みのため、実質 PASS

**指摘事項**:

| # | 観点 | 重要度 | 該当箇所 | 指摘内容 | 対応 |
|---|------|--------|---------|---------|------|
| 1 | 観点1 | **NG** | §5.1 | 「1 件だけ」実行コマンドが `TestAggregationPeriod::test_集計期間_367日_例外を送出する` のままで、§1.5 で定めた「クラスを作らない・英語スネークケース」と矛盾。そのままでは実行できない | 修正済み（`test_usage_period.py::test_aggregation_period_rejects_367_days` に修正） |
| 2 | 観点2 | 警告 | §5.3 | 段2・段5・段6 の完了条件が TC-APP-023〜025 / TC-UI-040・041（ページング）と TC-INF-006 を含んでいない | 修正済み（`TC-APP-010〜025` / `TC-UI-020〜041` / `TC-INF-001〜006` に更新） |
| 3 | 観点3 | 警告 | §4.1 | `menu_key` の長さの境界（80 / 81 文字）に対応する TC-ID が無く、§3.2 への参照だけで終わっていた | 修正済み（TC-INF-006 を新設し、§4.1・§4.5 から参照） |
| 4 | 観点3 | 警告 | §2.1 TC-DOM-003 | §3.2 の異常系データには利用種別 `None` があるのに、テストケースの入力に含まれていなかった | 修正済み（TC-DOM-003 の入力に `None` を追加） |
| 5 | 観点4 | 警告 | §2.4 TC-UI-050 | テストケース欄が「既存の検証がそのまま通ること」という説明文で、何を実行するのかが名前から読めない | 修正済み（`config/tests/test_clean_architecture.py` の既存テスト全件と明記） |
| 6 | 観点4 | 警告 | §2.4 TC-UI-051 | 「Phase 5 の手動確認」と書かれた項目が自動テストの一覧（§2.4）に置かれており、§4.4（手動確認）に載っていなかった | 修正済み（§2.4 から §4.4 #6 へ移設。§4.5 REQ-NF-006・§5.3 段7 の参照も更新） |

**主な OK 判定の根拠**:

- テストピラミッド: Domain 104 件 / Application 25 件 / Infrastructure 29 件 / Interfaces 22 件。Domain 層が最多で、E2E は明示的にスコープ外（§1.1）
- レイヤー別方針（§1.2）で DB 依存の有無を明示。`@pytest.mark.django_db` は Infrastructure / Interfaces のみ
- モック方針: ドメインモデルはモック化せず実物を使う。Application はポートのフェイクのみ差し替える
- 要件カバレッジ（§4.5）: REQ-F-001〜018・REQ-NF-001〜008 の全 26 ID がいずれかのテストケースに対応。未カバー 0 件
- 境界値: 集計期間の日数（1 / 366 / 367）・日時境界（開始日 00:00:00 / 終了日 23:59:59.999 / 翌日 00:00:00）・CSV 行数（0 / 1 / 100,000 / 100,001）・0 件・タイブレークを網羅
- テストケースはすべて具体的な入力と期待結果を持ち、`assert True` 相当の形だけのアサーションは無い

**不足しているテストケースの提案**: 上記 #3・#4 で追加済み。他に不足なし

**未解決の指摘**: 0 件 (NG: 0 件 / 警告: 0 件)

**次のアクション**: Phase 4（タスク分解 / make-tasks）へ進む。テスト設計 L2（Codex クロスレビュー）は Codex CLI 未導入のため保留。

<!-- 次のレビューはこの下に追記する -->

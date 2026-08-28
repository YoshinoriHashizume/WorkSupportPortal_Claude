文書ID: TASK-LOW-FLOW-VISIBILITY-2026-001
作成日: 2026/08/27
更新日:
対応文書: ./design.md (DESIGN-LOW-FLOW-VISIBILITY-2026-001), ./test-design.md (TEST-LOW-FLOW-VISIBILITY-2026-001), ./requirements.md (REQ-LOW-FLOW-VISIBILITY-2026-001)

# low-flow-visibility タスクリスト

## 0. 実装方針

- **TDD（Red → Green → Refactor）** を採用する（CLAUDE.md §2）。各実装タスクの直前にテスト作成タスクを置く。
- **1タスク = 原則1ファイル**（CLAUDE.md 絶対ルール3）。テスト作成タスクと実装タスクを分けることでこれを守る。
- Clean Architecture のレイヤー順（domain → use_cases → infrastructure → interfaces）で進める。
- 本機能は**置換**である。ステージ2で旧ドメインVOを先に削除し、以降は `ImportError` / `TypeError` を
  「まだ直していない箇所」の検知手段として使う（test-design.md §1.4）。
  **ステージ2〜6の途中はテストスイート全体が Red のままになる。** 全体 Green はステージ7で回復させる。
- 各タスクの完了条件に書いた pytest コマンドが通ることを、そのタスクの Done の定義とする。
- テストケースID（D-xxx / A-xxx / I-xxx / X-xxx / E-xxx）は test-design.md §2〜§4 を指す。

### ブランチと成果物の扱い

- 作業ブランチ: `feature/ioa-low-flow-visibility`（`develop` から分岐）
- `staticfiles/` は手編集しない。JS/CSS 変更後にステージ7で `collectstatic` を実行する。

---

## 1. 状況チェックシート

**凡例**: `[ ]` 未着手 / `[~]` 進行中 / `[✅YYYY/MM/DD HH:MM]` 完了 / `[- YYYY/MM/DD HH:MM]` スキップ

### ステージ1: 流動区分ドメインの新設

| # | タスク | レイヤー | 状態 |
|---|--------|---------|------|
| 1 | 流動区分ドメインのテスト作成（D-001〜D-083） | domain | [✅2026/08/28 09:07] |
| 2 | `flow_quadrant.py` の実装 | domain | [✅2026/08/28 09:09] |
| 3 | 判定ルール凡例のテスト作成（D-084〜D-087） | domain | [✅2026/08/28 09:11] |
| 4 | `flow_quadrant_rules.py` の実装 | domain | [✅2026/08/28 09:12] |

### ステージ2: 旧アラートレベルドメインの撤去

| # | タスク | レイヤー | 状態 |
|---|--------|---------|------|
| 5 | 旧ドメインVOと対応テストの削除 | domain | [✅2026/08/28 09:14] |

### ステージ3: 既存ドメインVOの置換

| # | タスク | レイヤー | 状態 |
|---|--------|---------|------|
| 6 | `test_list_summary.py` の改修（D-088〜D-099） | domain | [✅2026/08/28 09:15] |
| 7 | `list_rows.py` の置換 | domain | [ ] |
| 8 | `test_list_query.py` の改修（D-124〜D-134） | domain | [ ] |
| 9 | `list_query.py` の置換 | domain | [ ] |
| 10 | `test_row_counts.py` の改修（D-109〜D-116） | domain | [ ] |
| 11 | `row_counts.py` の置換 | domain | [ ] |
| 12 | `test_row_display.py` の改修（D-117〜D-123） | domain | [ ] |
| 13 | `row_display.py` の置換 | domain | [ ] |
| 14 | `test_table_display.py` の改修（D-100〜D-108） | domain | [ ] |
| 15 | `table_display.py` の置換 | domain | [ ] |
| 16 | `test_list_filter.py` の改修（D-135〜D-138） | domain | [ ] |
| 17 | `list_filter.py` の置換 | domain | [ ] |
| 18 | `test_export_csv.py` の列定義テスト改修（D-139〜D-142） | domain | [ ] |
| 19 | `export_csv.py`（VO）の列定義置換 | domain | [ ] |
| 20 | `test_list_client_data.py` の改修（D-143〜D-149） | domain | [ ] |
| 21 | `list_client_data.py` の置換 | domain | [ ] |
| 22 | 設定VO撤去のテスト改修（D-150〜D-154） | domain | [ ] |
| 23 | `app_settings.py`（VO）の項目削除 | domain | [ ] |
| 24 | `test_domain_confirmation.py` の改修（D-155） | domain | [ ] |
| 25 | `confirmation.py`（VO）のフィールド名変更 | domain | [ ] |
| 26 | `ports.py` から警告条件保存ポートを削除 | domain | [ ] |

### ステージ4: ユースケースの置換

| # | タスク | レイヤー | 状態 |
|---|--------|---------|------|
| 27 | `use_cases/save_alert_settings.py` の削除 | use_cases | [ ] |
| 28 | ListPage のテスト改修（A-001〜A-009） | use_cases | [ ] |
| 29 | `use_cases/list_page.py` の置換 | use_cases | [ ] |
| 30 | ExportCsv のテスト改修（A-012〜A-020） | use_cases | [ ] |
| 31 | `use_cases/export_csv.py` の置換 | use_cases | [ ] |
| 32 | PortalDashboard のテスト改修（A-021〜A-030） | use_cases | [ ] |
| 33 | `use_cases/portal_dashboard.py` の置換 | use_cases | [ ] |
| 34 | SummaryApi のテスト改修（A-031〜A-034） | use_cases | [ ] |
| 35 | `use_cases/summary_api.py` の置換 | use_cases | [ ] |
| 36 | SaveConfirmation のテスト改修（A-035 / A-036） | use_cases | [ ] |
| 37 | `test_save_confirmation.py` の改修（A-035 / A-036 の入力側） | use_cases | [ ] |
| 38 | `use_cases/save_confirmation.py` の置換 | use_cases | [ ] |
| 39 | PatchSnapshotRow のテスト改修（A-037） | use_cases | [ ] |
| 40 | `use_cases/patch_snapshot_row.py` の置換 | use_cases | [ ] |

### ステージ5: インフラストラクチャの置換

| # | タスク | レイヤー | 状態 |
|---|--------|---------|------|
| 41 | マイグレーション検証テストの作成（I-021 / I-022） | infrastructure | [ ] |
| 42 | `models.py` のフィールド名変更と残置カラムのコメント付与 | infrastructure | [ ] |
| 43 | `migrations/0011_rename_confirmed_alert_level.py` の作成 | infrastructure | [ ] |
| 44 | `test_summary_storage.py` の改修（I-001〜I-008 / I-019 / I-020） | infrastructure | [ ] |
| 45 | `summary_repository.py` の置換 | infrastructure | [ ] |
| 46 | `test_reconcile_confirmations.py` の改修（I-009〜I-016） | infrastructure | [ ] |
| 47 | `confirmation_repository.py` の置換 | infrastructure | [ ] |
| 48 | `test_settings_service.py` の改修（I-017 / I-018） | infrastructure | [ ] |
| 49 | `settings_repository.py` の警告条件保存削除 | infrastructure | [ ] |
| 50 | `summary_snapshot_repository.py` の詰め替え規則変更 | infrastructure | [ ] |
| 51 | `test_build_summary_rows.py` の改修（I-023 / I-024） | infrastructure | [ ] |
| 52 | `summary_aggregation.py` の `ListQuery` 生成置換 | infrastructure | [ ] |

### ステージ6: インターフェースの置換

| # | タスク | レイヤー | 状態 |
|---|--------|---------|------|
| 53 | templatetag のテスト改修（X-024） | interfaces | [ ] |
| 54 | `templatetags/inventory_order_alert_format.py` の置換 | interfaces | [ ] |
| 55 | views のテスト改修（X-001〜X-016） | interfaces | [ ] |
| 56 | `interfaces/views.py` の置換 | interfaces | [ ] |
| 57 | `interfaces/urls.py` から `alert-settings` を削除 | interfaces | [ ] |
| 58 | `interfaces/wiring.py` から `save_alert_settings_usecase` を削除 | interfaces | [ ] |
| 59 | 一覧テンプレートのテスト改修（X-019〜X-023） | interfaces | [ ] |
| 60 | `templates/inventory_order_alert/list.html` の置換 | interfaces | [ ] |
| 61 | 設定画面テストの改修（X-017 / X-018） | interfaces | [ ] |
| 62 | `templates/inventory_order_alert/settings.html` の月数入力削除 | interfaces | [ ] |
| 63 | `templates/portal/dashboard.html` のアラート帯文言変更 | interfaces | [ ] |
| 64 | 一覧 JS のテスト改修（X-029〜X-035） | interfaces | [ ] |
| 65 | `inventory-order-alert-list-client.js` の置換 | interfaces | [ ] |
| 66 | `inventory-order-alert-list.js` の保存処理削除 | interfaces | [ ] |
| 67 | CSS のテスト作成（X-025〜X-028） | interfaces | [ ] |
| 68 | `static/css/app.css` のセレクタ ASCII 化 | interfaces | [ ] |
| 69 | `scripts/verify_post_receipt_shipment_count.py` の追随（X-037） | interfaces | [ ] |

### ステージ7: 全体検証と仕上げ

| # | タスク | レイヤー | 状態 |
|---|--------|---------|------|
| 70 | 旧識別子の残存0件テストの作成（A-038 / A-039 / X-036 / X-037） | 横断 | [ ] |
| 71 | エッジケース・性能テストの作成（E-001〜E-010） | 横断 | [ ] |
| 72 | アプリ全体テストとアーキテクチャテストの Green 化（X-038） | 横断 | [ ] |
| 73 | `collectstatic` の実行 | 横断 | [ ] |
| 74 | 機能仕様書の改訂 | docs | [ ] |
| 75 | 本番相当環境でのマイグレーション適用確認 | 運用 | [ ] |

---

## 2. タスク詳細

### ステージ1: 流動区分ドメインの新設

#### タスク1: 流動区分ドメインのテスト作成（D-001〜D-083）

- **対象ファイル**: `application/inventory_order_alert/tests/test_flow_quadrant.py`（新規）
- **内容**:
  - test-design.md §2.1 の D-001〜D-083 を実装する（83件）。
  - 検証対象: `EvaluationPeriod` / `EvaluationPeriods`（D-001〜D-017）、`FlowAxis`（D-018 / D-019）、
    `FlowSelection` と `REFERENCE_FLOW_SELECTION`（D-020〜D-022）、`FlowQuadrant`（D-023〜D-028）、
    `is_within_evaluation_period`（D-029〜D-040）、`resolve_flow_quadrant`（D-041〜D-053）、
    `resolve_flow_quadrant_matrix`（D-054〜D-057）、`is_no_incoming_record`（D-058〜D-061）、
    `responsible_departments`（D-062〜D-066）、`normalize_flow_quadrant`（D-067〜D-076）、
    `is_flow_escalated`（D-077〜D-083）。
  - test-design.md §3.1 の判定条件6値（`SELECTION_L1` / `L3` / `L6` / `D1` / `D2` / `D5`）と
    代表6行をモジュール定数として本ファイル先頭に定義する。
  - 基準日は **2026/8/27 固定リテラル**。`date.today()` は使わない（test-design.md §5.2）。
  - モジュールレベル関数・docstring なし・AAA 構造（test-design.md §1.2）。
- **完了条件**:
  `pytest application/inventory_order_alert/tests/test_flow_quadrant.py` が
  **83件すべて `ImportError` または失敗で Red** になること（Red の確認）。

#### タスク2: `flow_quadrant.py` の実装

- **対象ファイル**: `application/inventory_order_alert/domain/value_objects/flow_quadrant.py`（新規）
- **内容**:
  - design.md §4.2.1〜§4.2.5 / §4.4 に従って実装する。
  - VO: `FlowAxis`（低流動判定軸 / 死蔵判定軸）、`EvaluationPeriod`（months / key / label）、
    `EvaluationPeriods`（ファーストクラスコレクション。6要素・`for_axis` / `default_for_axis` / `find`）、
    `FlowQuadrant`（供給リスク品 / 在庫死蔵品 / 在庫過剰リスク品 / 通常流動品。key・ランク0〜3）、
    `FlowSelection`（判定軸 × 判定期間）、`REFERENCE_FLOW_SELECTION`（低流動判定軸・3か月）。
  - 判定関数: `is_within_evaluation_period` / `resolve_flow_quadrant` /
    `resolve_flow_quadrant_matrix` / `is_no_incoming_record` / `responsible_departments` /
    `normalize_flow_quadrant`（design.md §5.2 の互換写像）/ `is_flow_escalated`。
  - 暦月計算は既存の `domain/value_objects/dates.py` の `add_calendar_months` を使う。
    `is_within_calendar_months` は境界日と未来日を落とすため**使わない**（test-design.md §4.1）。
  - `import django` を書かない。すべて `@dataclass(frozen=True)` または純関数。
  - **判定関数は例外を投げない**（D-053 で横断検証される）。
- **完了条件**:
  `pytest application/inventory_order_alert/tests/test_flow_quadrant.py` が **83件すべて Green**。

#### タスク3: 判定ルール凡例のテスト作成（D-084〜D-087）

- **対象ファイル**: `application/inventory_order_alert/tests/test_flow_quadrant_rules.py`（新規）
- **内容**: test-design.md §2.1 の D-084〜D-087。`build_flow_quadrant_rule_rows` が
  判定軸・判定期間に応じた凡例4行を返し、ラベル文言がユビキタス言語と一致することを検証する。
- **完了条件**: 4件すべて Red（`ImportError`）。

#### タスク4: `flow_quadrant_rules.py` の実装

- **対象ファイル**: `application/inventory_order_alert/domain/value_objects/flow_quadrant_rules.py`（新規）
- **内容**: design.md §6.6.5 の判定ルールダイアログ用の凡例行を構築する。
  `alert_rules.py` の `build_alert_rule_rows` の置き換え。`flow_quadrant.py` にのみ依存する。
- **完了条件**: `pytest application/inventory_order_alert/tests/test_flow_quadrant_rules.py` が Green。

---

### ステージ2: 旧アラートレベルドメインの撤去

#### タスク5: 旧ドメインVOと対応テストの削除

- **対象ファイル（削除）**:
  - `application/inventory_order_alert/domain/value_objects/alert_level.py`
  - `application/inventory_order_alert/domain/value_objects/alert_rules.py`
  - `application/inventory_order_alert/tests/test_alert_level.py`
  - `application/inventory_order_alert/tests/test_alert_rules.py`
  - `application/inventory_order_alert/tests/test_save_alert_settings.py`
- **内容**: design.md §7.3 の削除。**削除対象は上記5ファイルのみ**（CLAUDE.md 絶対ルール4に基づき明示）。
  `use_cases/save_alert_settings.py` の削除はタスク27で行う（レイヤー順を守るため）。
- **完了条件**:
  - 上記5ファイルが存在しない。
  - `grep -rn "alert_level\|alert_rules" application/inventory_order_alert --include=*.py` の
    残存箇所を一覧化し、ステージ3〜6で潰す対象リストとして記録する。
  - この時点で `pytest application/inventory_order_alert/` は **大量に Red**（想定どおり）。

---

### ステージ3: 既存ドメインVOの置換

> 以降のテスト改修タスクは共通で「旧アラートレベル前提のアサーションを流動区分前提へ書き換える」。
> 各タスクの完了条件は **そのテストファイル単体が Red（実装前）→ 次タスクで Green（実装後）**。

#### タスク6: `test_list_summary.py` の改修（D-088〜D-099）

- **対象ファイル**: `application/inventory_order_alert/tests/test_list_summary.py`
- **内容**: `apply_alert_levels_to_rows` 前提のテストを `apply_flow_quadrants_to_rows` 前提へ。
  行への `flow_quadrant` / `flow_quadrant_key` / `flow_quadrants`（6通り）/ `no_incoming_record` /
  `responsible_department` の付与（D-088〜D-093）、解析不能日付・0件・行数不変（D-094〜D-096）、
  `filter_summary_rows` の流動区分フィルタ（D-097 / D-098）、
  `alert_only` を渡すと `TypeError`（D-099）。
- **完了条件**: 該当テストが Red。

#### タスク7: `list_rows.py` の置換

- **対象ファイル**: `application/inventory_order_alert/domain/value_objects/list_rows.py`
- **内容**: design.md §7.2。`apply_alert_levels_to_rows` → `apply_flow_quadrants_to_rows` に改名し、
  6通りの流動区分（`resolve_flow_quadrant_matrix`）を行に持たせる。
  `filter_summary_rows` / `sort_summary_rows` を流動区分基準へ。
- **完了条件**: `pytest application/inventory_order_alert/tests/test_list_summary.py` が Green。

#### タスク8: `test_list_query.py` の改修（D-124〜D-134）

- **対象ファイル**: `application/inventory_order_alert/tests/test_list_query.py`
- **内容**: `parse_list_query` が `axis` / `period` / `flow_quadrant` / `attention_only` を解釈すること、
  不正値・欠落時のフォールバック（判定軸の既定＝低流動判定軸、判定期間の既定＝`default_for_axis`、
  未知の流動区分キー→絞り込みなし）を検証する。
- **完了条件**: 該当テストが Red。

#### タスク9: `list_query.py` の置換

- **対象ファイル**: `application/inventory_order_alert/domain/value_objects/list_query.py`
- **内容**: design.md §7.2 / §6.1。`ListQuery` から
  `alert_only` / `warning_shipment_months` / `warning_incoming_months` / `critical_enabled` を削除し、
  `flow_selection: FlowSelection` / `flow_quadrant: str` / `attention_only: bool` を追加。
  `parse_list_query` / `merge_query_with_settings` を追随させる。
- **完了条件**: `pytest application/inventory_order_alert/tests/test_list_query.py` が Green。

#### タスク10: `test_row_counts.py` の改修（D-109〜D-116）

- **対象ファイル**: `application/inventory_order_alert/tests/test_row_counts.py`
- **内容**: `RowCounts` が `supply_risk` / `dormant_stock` / `excess_stock_risk` / `normal_flow` /
  `attention`（前3者の和）を持つこと、確認状態の3件数が維持されること、0件・全件同一区分の境界を検証。
- **完了条件**: 該当テストが Red。

#### タスク11: `row_counts.py` の置換

- **対象ファイル**: `application/inventory_order_alert/domain/value_objects/row_counts.py`
- **内容**: design.md §7.2 / §6.6.3。
- **完了条件**: `pytest application/inventory_order_alert/tests/test_row_counts.py` が Green。

#### タスク12: `test_row_display.py` の改修（D-117〜D-123）

- **対象ファイル**: `application/inventory_order_alert/tests/test_row_display.py`
- **内容**: `display_flow_quadrant` の表示、行クラスが流動区分キー（ASCII）を返すこと、
  確認済／確認中の優先が維持されること、`counts_toward_alert_summary` が**存在しないこと**を検証。
- **完了条件**: 該当テストが Red。

#### タスク13: `row_display.py` の置換

- **対象ファイル**: `application/inventory_order_alert/domain/value_objects/row_display.py`
- **内容**: design.md §7.2 / §6.6.7。`display_alert_level` → `display_flow_quadrant`、
  `row_alert_class` → 流動区分キーを返す関数へ。
  **`counts_toward_alert_summary()` を削除する**（design.md §7.3 の明示的削除対象）。
- **完了条件**: `pytest application/inventory_order_alert/tests/test_row_display.py` が Green。

#### タスク14: `test_table_display.py` の改修（D-100〜D-108）

- **対象ファイル**: `application/inventory_order_alert/tests/test_table_display.py`
- **内容**: `SORTABLE_COLUMNS` の置換・追加、`DEFAULT_SORT`、流動区分ランク（0〜3）による
  ソート順、5条件のソート境界（test-design.md §4.1）を検証。
- **完了条件**: 該当テストが Red。

#### タスク15: `table_display.py` の置換

- **対象ファイル**: `application/inventory_order_alert/domain/value_objects/table_display.py`
- **内容**: design.md §7.2 / §6.6.2。`_sort_value()` の分岐を `flow_quadrant_sort_rank` へ。
- **完了条件**: `pytest application/inventory_order_alert/tests/test_table_display.py` が Green。

#### タスク16: `test_list_filter.py` の改修（D-135〜D-138）

- **対象ファイル**: `application/inventory_order_alert/tests/test_list_filter.py`
- **内容**: `build_display_query_string` が `axis` / `period` / `flow_quadrant` を含むこと、
  既定値のときに冗長なパラメータを出さないことを検証。
- **完了条件**: 該当テストが Red。

#### タスク17: `list_filter.py` の置換

- **対象ファイル**: `application/inventory_order_alert/domain/value_objects/list_filter.py`
- **内容**: design.md §7.2 / §6.1。
- **完了条件**: `pytest application/inventory_order_alert/tests/test_list_filter.py` が Green。

#### タスク18: `test_export_csv.py` の列定義テスト改修（D-139〜D-142）

- **対象ファイル**: `application/inventory_order_alert/tests/test_export_csv.py`
- **内容**: `EXPORT_COLUMNS` から旧アラートレベル列が消え、流動区分・判定軸・判定期間・
  責任部署の各列が design.md §6.3 の順で並ぶことを検証する。
  ※ 同ファイル内のユースケース側テスト（A-012〜A-020）はタスク30で改修する。
- **完了条件**: D-139〜D-142 が Red。

#### タスク19: `export_csv.py`（VO）の列定義置換

- **対象ファイル**: `application/inventory_order_alert/domain/value_objects/export_csv.py`
- **内容**: design.md §6.3 の `EXPORT_COLUMNS` 置換・追加。
- **完了条件**: D-139〜D-142 が Green。

#### タスク20: `test_list_client_data.py` の改修（D-143〜D-149）

- **対象ファイル**: `application/inventory_order_alert/tests/test_list_client_data.py`
- **内容**: クライアント配信ペイロード（design.md §6.2）に `flowQuadrants`（6通り）・
  `flowQuadrantKey`・`noIncomingRecord`・`responsibleDepartment` が含まれ、
  `alertLevel` 系のキーが**含まれないこと**を検証。
- **完了条件**: 該当テストが Red。

#### タスク21: `list_client_data.py` の置換

- **対象ファイル**: `application/inventory_order_alert/domain/value_objects/list_client_data.py`
- **内容**: design.md §6.2。
- **完了条件**: `pytest application/inventory_order_alert/tests/test_list_client_data.py` が Green。

#### タスク22: 設定VO撤去のテスト改修（D-150〜D-154）

- **対象ファイル**: `application/inventory_order_alert/tests/test_app_settings_usecase.py`
- **内容**: `AppSettings` に残るのが `warning_days` / `stock_stale_days` と監査項目のみであること、
  `warning_shipment_months` / `warning_incoming_months` / `critical_enabled` が
  **属性として存在しないこと**を検証。
- **完了条件**: 該当テストが Red。

#### タスク23: `app_settings.py`（VO）の項目削除

- **対象ファイル**: `application/inventory_order_alert/domain/value_objects/app_settings.py`
- **内容**: design.md §6.5 / §7.2。**削除対象**: `warning_shipment_months` /
  `warning_incoming_months` / `critical_enabled` の3属性。
  DBカラムは残置する（design.md §5.3。カラム削除のマイグレーションは作らない）。
- **完了条件**: `pytest application/inventory_order_alert/tests/test_app_settings_usecase.py` が Green。

#### タスク24: `test_domain_confirmation.py` の改修（D-155）

- **対象ファイル**: `application/inventory_order_alert/tests/test_domain_confirmation.py`
- **内容**: `ConfirmationRecord.confirmed_flow_quadrant` を検証し、
  `confirmed_alert_level` が存在しないことを確認。
- **完了条件**: 該当テストが Red。

#### タスク25: `confirmation.py`（VO）のフィールド名変更

- **対象ファイル**: `application/inventory_order_alert/domain/value_objects/confirmation.py`
- **内容**: `ConfirmationRecord.confirmed_alert_level` → `confirmed_flow_quadrant`。
- **完了条件**: `pytest application/inventory_order_alert/tests/test_domain_confirmation.py` が Green。

#### タスク26: `ports.py` から警告条件保存ポートを削除

- **対象ファイル**: `application/inventory_order_alert/domain/repositories/ports.py`
- **内容**: design.md §7.2。**削除対象**: 警告条件保存ポート（`SaveWarningMonthSettings` 相当）の型定義。
- **完了条件**:
  - `grep -n "warning_month\|WarningMonth" application/inventory_order_alert/domain/repositories/ports.py` が0件。
  - `pytest config/tests/test_clean_architecture.py` が Green（X-038）。

---

### ステージ4: ユースケースの置換

#### タスク27: `use_cases/save_alert_settings.py` の削除

- **対象ファイル（削除）**: `application/inventory_order_alert/use_cases/save_alert_settings.py`
- **内容**: design.md §7.3 / §6.5。警告条件の設定を廃止する。
  対応テスト `tests/test_save_alert_settings.py` はタスク5で削除済み。
- **完了条件**: ファイルが存在しない。`grep -rn "save_alert_settings" application/inventory_order_alert`
  の残存箇所（`wiring.py` / `views.py` / `urls.py`）をタスク56〜58で潰す対象として記録する。

#### タスク28: ListPage のテスト改修（A-001〜A-009）

- **対象ファイル**: `application/inventory_order_alert/tests/test_inventory_order_alert_views.py`
- **内容**: `ListPageContext` から警告条件3項目が消え、`flow_selection` / `flow_axis_options` /
  `flow_period_options` / `flow_quadrant_filter` / `flow_quadrant_rule_rows` が入ることを検証。
  ※ 同ファイルの Interfaces 側テスト（X-001〜X-016）はタスク55で改修する。
- **完了条件**: A-001〜A-009 が Red。

#### タスク29: `use_cases/list_page.py` の置換

- **対象ファイル**: `application/inventory_order_alert/use_cases/list_page.py`
- **内容**: design.md §7.2。**削除対象**: `ListPageContext` の
  `warning_shipment_months` / `warning_incoming_months` / `critical_enabled` と `alert_rule_rows`。
- **完了条件**: A-001〜A-009 が Green。

#### タスク30: ExportCsv のテスト改修（A-012〜A-020）

- **対象ファイル**: `application/inventory_order_alert/tests/test_export_csv.py`
- **内容**: `execute(*, query_params)` シグネチャ、判定条件が CSV の内容に反映されること、
  ファイル名・ヘッダ行を検証（design.md §6.3）。
- **完了条件**: A-012〜A-020 が Red。

#### タスク31: `use_cases/export_csv.py` の置換

- **対象ファイル**: `application/inventory_order_alert/use_cases/export_csv.py`
- **内容**: design.md §6.3 / §7.2。
- **完了条件**: `pytest application/inventory_order_alert/tests/test_export_csv.py` が Green（D-139〜D-142 含む）。

#### タスク32: PortalDashboard のテスト改修（A-021〜A-030）

- **対象ファイル**: `application/inventory_order_alert/tests/test_inventory_order_alert_views.py`
- **内容**: `DashboardBannerContext` が流動区分ベースになること、tone の4分岐（design.md §6.4）を検証。
- **完了条件**: A-021〜A-030 が Red。

#### タスク33: `use_cases/portal_dashboard.py` の置換

- **対象ファイル**: `application/inventory_order_alert/use_cases/portal_dashboard.py`
- **内容**: design.md §6.4 / §7.2。
- **完了条件**: A-021〜A-030 が Green。

#### タスク34: SummaryApi のテスト改修（A-031〜A-034）

- **対象ファイル**: `application/inventory_order_alert/tests/test_summary_api.py`
- **内容**: `merge_query_with_settings` の警告条件上書きが消えること、
  `_counts_payload` / `dashboard_summary_payload` が流動区分ベースであることを検証。
- **完了条件**: 該当テストが Red。

#### タスク35: `use_cases/summary_api.py` の置換

- **対象ファイル**: `application/inventory_order_alert/use_cases/summary_api.py`
- **内容**: design.md §7.2。
- **完了条件**: `pytest application/inventory_order_alert/tests/test_summary_api.py` が Green。

#### タスク36: SaveConfirmation のテスト改修（A-035 / A-036）

- **対象ファイル**: `application/inventory_order_alert/tests/test_confirmation_save_result.py`
- **内容**: 一覧で死蔵5年を選択中に確認保存しても、保存される流動区分は
  **`REFERENCE_FLOW_SELECTION`（低流動判定軸・3か月）基準**であること（A-035）、
  レスポンスの `counts` が流動区分ベースであること（A-036）を検証。
- **完了条件**: 該当テストが Red。

#### タスク37: `test_save_confirmation.py` の改修（A-035 / A-036 の入力側）

- **対象ファイル**: `application/inventory_order_alert/tests/test_save_confirmation.py`
- **内容**: 確認保存の入力側テスト（7件）。`alert_level=` キーワード引数を
  流動区分ベースへ、`ConfirmationRecord.confirmed_alert_level` の参照を
  `confirmed_flow_quadrant` へ書き換える。空文字（未判定）のケースは
  `normalize_flow_quadrant("")` が通常流動品を返す前提に合わせる。
- **完了条件**: 該当7件が Red。

#### タスク38: `use_cases/save_confirmation.py` の置換

- **対象ファイル**: `application/inventory_order_alert/use_cases/save_confirmation.py`
- **内容**: design.md §7.2。`lookup_alert_level_for_row` → `lookup_flow_quadrant_for_row`。
- **完了条件**: `pytest application/inventory_order_alert/tests/test_confirmation_save_result.py` が Green。

#### タスク39: PatchSnapshotRow のテスト改修（A-037）

- **対象ファイル**: `application/inventory_order_alert/tests/test_snapshot_patch.py`
- **内容**: `_apply_flow_quadrants` が `REFERENCE_FLOW_SELECTION` で適用されることを検証。
- **完了条件**: 該当テストが Red。

#### タスク40: `use_cases/patch_snapshot_row.py` の置換

- **対象ファイル**: `application/inventory_order_alert/use_cases/patch_snapshot_row.py`
- **内容**: design.md §7.2。
- **完了条件**: `pytest application/inventory_order_alert/tests/test_snapshot_patch.py` が Green。

---

### ステージ5: インフラストラクチャの置換

> **重要**: `conftest.py` の `django_db_use_migrations` fixture が `False` を返すため、
> テストDBはモデル定義から生成され、**マイグレーションはテストで実行されない**（test-design.md §2.3 補足）。
> そのためタスク41は「マイグレーションファイルの内容検査」と「`makemigrations --check`」で代替し、
> 実DBへの適用はタスク75（本番相当環境での手動確認）で担保する。

#### タスク41: マイグレーション検証テストの作成（I-021 / I-022）

- **対象ファイル**: `application/inventory_order_alert/tests/test_flow_quadrant_migration.py`（新規）
- **内容**:
  - I-021: `migrations/0011_rename_confirmed_alert_level.py` を import し、
    `Migration.operations` が `RenameField` 1件のみで、
    `old_name='confirmed_alert_level'` / `new_name='confirmed_flow_quadrant'` であることを検査（DB非依存）。
  - I-022: `call_command('makemigrations', '--check', '--dry-run')` が
    未作成のマイグレーションを検出しないことを検証。
- **完了条件**: 2件とも Red。

#### タスク42: `models.py` のフィールド名変更と残置カラムのコメント付与

- **対象ファイル**: `application/inventory_order_alert/models.py`
- **内容**:
  - `InventoryOrderAlertConfirmation.confirmed_alert_level` → `confirmed_flow_quadrant`（`max_length=40` 据え置き）。
  - `InventoryOrderAlertSettings` の `warning_shipment_months` / `warning_incoming_months` /
    `critical_enabled` に「旧アラートレベル方式の残置カラム（未使用）」のコメントを付与（design.md §5.3）。
    **カラムは削除しない。**
- **完了条件**: `python manage.py makemigrations --check --dry-run` が
  「未作成のマイグレーションがある」と報告すること（タスク43の Red 状態）。

#### タスク43: `migrations/0011_rename_confirmed_alert_level.py` の作成

- **対象ファイル**: `application/inventory_order_alert/migrations/0011_rename_confirmed_alert_level.py`（新規）
- **内容**: `RenameField` 1件のみ（design.md §5.2）。
  `python manage.py makemigrations inventory_order_alert --name rename_confirmed_alert_level` で生成し、
  **`RenameField` になっているか（RemoveField + AddField になっていないか）を目視確認する**。
  なっていない場合は手で `RenameField` に書き直す（データ消失を避けるため）。
  依存は `0010_memo_entry_newest_first_ordering`。
- **完了条件**: `pytest application/inventory_order_alert/tests/test_flow_quadrant_migration.py` が Green。

#### タスク44: `test_summary_storage.py` の改修（I-001〜I-008 / I-019 / I-020）

- **対象ファイル**: `application/inventory_order_alert/tests/test_summary_storage.py`
- **内容**: スナップショット読込時に**毎回再判定**されること（I-001〜I-004）、
  スナップショットの `rows` スキーマが不変であること（I-005）、
  `load_app_settings()` に依存しなくなること（I-019 / I-020）を検証。
- **完了条件**: 該当テストが Red。

#### タスク45: `summary_repository.py` の置換

- **対象ファイル**: `application/inventory_order_alert/infrastructure/persistence/summary_repository.py`
- **内容**: design.md §7.2。`apply_alert_levels_to_rows` の呼び出しを
  `apply_flow_quadrants_to_rows` に差し替え、**`load_app_settings()` への依存を削除**する。
- **完了条件**: `pytest application/inventory_order_alert/tests/test_summary_storage.py` が Green。

#### タスク46: `test_reconcile_confirmations.py` の改修（I-009〜I-016）

- **対象ファイル**: `application/inventory_order_alert/tests/test_reconcile_confirmations.py`
- **内容**: 旧ラベルが入った確認記録の読込（I-009〜I-011）、
  `is_flow_escalated` による差し戻し（I-012〜I-016）を検証。
  移行直後の深刻化判定（E-008 / design.md §9 R-2）を含む。
- **完了条件**: 該当テストが Red。

#### タスク47: `confirmation_repository.py` の置換

- **対象ファイル**: `application/inventory_order_alert/infrastructure/persistence/confirmation_repository.py`
- **内容**: design.md §7.2 / §5.2。フィールド名の追随、
  `normalize_alert_level` → `normalize_flow_quadrant`、深刻化判定を `is_flow_escalated` へ。
  判定基準は **`REFERENCE_FLOW_SELECTION` 固定**（利用者の画面選択に影響されない）。
- **完了条件**: `pytest application/inventory_order_alert/tests/test_reconcile_confirmations.py` が Green。

#### タスク48: `test_settings_service.py` の改修（I-017 / I-018）

- **対象ファイル**: `application/inventory_order_alert/tests/test_settings_service.py`
- **内容**: `save_warning_month_settings` が存在しないこと、
  `load_app_settings` が残置カラムを読まないことを検証。D-150〜D-154 の残りもここで扱う。
- **完了条件**: 該当テストが Red。

#### タスク49: `settings_repository.py` の警告条件保存削除

- **対象ファイル**: `application/inventory_order_alert/infrastructure/persistence/settings_repository.py`
- **内容**: design.md §7.2。**削除対象**: `save_warning_month_settings` 関数、
  `load_app_settings` 内の `warning_shipment_months` / `warning_incoming_months` / `critical_enabled` の読み取り。
- **完了条件**: `pytest application/inventory_order_alert/tests/test_settings_service.py` が Green。

#### タスク50: `summary_snapshot_repository.py` の詰め替え規則変更

- **対象ファイル**: `application/inventory_order_alert/infrastructure/persistence/summary_snapshot_repository.py`
- **内容**: design.md §5.1。`critical_count` / `warning_count` カラムへの詰め替えを流動区分ベースへ
  （カラム名は据え置き。`critical_count` ← 供給リスク品、`warning_count` ← 在庫死蔵品＋在庫過剰リスク品）。
- **完了条件**: `pytest application/inventory_order_alert/tests/test_summary_storage.py` が Green（I-006〜I-008）。

#### タスク51: `test_build_summary_rows.py` の改修（I-023 / I-024）

- **対象ファイル**: `application/inventory_order_alert/tests/test_build_summary_rows.py`
- **内容**: `ListQuery` の生成が流動区分ベースになること（I-023）、
  **Oracle 集計 SQL 本体が変わっていないこと**（I-024）を検証。
- **完了条件**: 該当テストが Red。

#### タスク52: `summary_aggregation.py` の `ListQuery` 生成置換

- **対象ファイル**: `application/inventory_order_alert/infrastructure/oracle/summary_aggregation.py`
- **内容**: design.md §7.2。`ListQuery` の生成を `REFERENCE_FLOW_SELECTION` ベースへ。
  **Oracle への発行 SQL は変更しない**（基幹 MARI は読み取り専用）。
- **完了条件**: `pytest application/inventory_order_alert/tests/test_build_summary_rows.py` が Green。

---

### ステージ6: インターフェースの置換

#### タスク53: templatetag のテスト改修（X-024）

- **対象ファイル**: `application/inventory_order_alert/tests/test_format_display.py`
- **内容**: `ioa_display` / `ioa_row_alert_class` が流動区分を扱うことを検証。
- **完了条件**: X-024 が Red。

#### タスク54: `templatetags/inventory_order_alert_format.py` の置換

- **対象ファイル**: `application/inventory_order_alert/templatetags/inventory_order_alert_format.py`
- **内容**: design.md §7.2。`row_display.py` の新関数へ委譲する。
- **完了条件**: X-024 が Green。

#### タスク55: views のテスト改修（X-001〜X-016）

- **対象ファイル**: `application/inventory_order_alert/tests/test_inventory_order_alert_views.py`
- **内容**: 一覧ページのコンテキスト（X-001〜X-008）、クエリパラメータのフォールバック（X-009〜X-011）、
  認可（X-012）、**撤去した警告条件保存 API が 404 を返すこと**（X-013）、
  **`shipment_trend` の同名 API が 404 にならないこと**（X-014 / design.md §9 R-8）、
  CSV ダウンロード（X-015 / X-016）を検証。
- **完了条件**: 該当テストが Red。

#### タスク56: `interfaces/views.py` の置換

- **対象ファイル**: `application/inventory_order_alert/interfaces/views.py`
- **内容**: design.md §7.2 / §6.5。**削除対象**: `api_save_alert_settings` ビュー。
  `list_page` / `settings_page` / `export_csv` のコンテキストを追随させる。
  views は use_cases / infrastructure / models を直 import しない（wiring 経由。CLAUDE.md §2）。
- **完了条件**: `pytest application/inventory_order_alert/tests/test_inventory_order_alert_views.py` が Green。

#### タスク57: `interfaces/urls.py` から `alert-settings` を削除

- **対象ファイル**: `application/inventory_order_alert/interfaces/urls.py`
- **内容**: design.md §6.5。**削除対象**: `alert-settings` パス1件のみ。
- **完了条件**: X-013 / X-014 が Green。

#### タスク58: `interfaces/wiring.py` から `save_alert_settings_usecase` を削除

- **対象ファイル**: `application/inventory_order_alert/interfaces/wiring.py`
- **内容**: design.md §7.2。**削除対象**: `save_alert_settings_usecase` の組み立てと `__all__` からの登録。
- **完了条件**: A-038 / A-039 の対象（タスク70で検証）。
  `pytest config/tests/test_clean_architecture.py` が Green。

#### タスク59: 一覧テンプレートのテスト改修（X-019〜X-023）

- **対象ファイル**: `application/inventory_order_alert/tests/test_inventory_order_alert_row_template.py`
- **内容**: 判定条件セレクタ・件数サマリ・列・判定ルールダイアログ（design.md §6.6）の描画、
  行の強調クラスが ASCII キーであること（§6.6.7）を検証。A-010 / A-011 もここに含む。
- **完了条件**: 該当テストが Red。

#### タスク60: `templates/inventory_order_alert/list.html` の置換

- **対象ファイル**: `templates/inventory_order_alert/list.html`
- **内容**: design.md §6.6.1〜§6.6.7。判定条件セレクタ（判定軸 × 判定期間）、
  件数サマリ、一覧列、判定ルールダイアログ（旧「警告条件ダイアログ」の置換先）、呼称の使い分け（§6.6.6）。
- **完了条件**: `pytest application/inventory_order_alert/tests/test_inventory_order_alert_row_template.py` が Green。

#### タスク61: 設定画面テストの改修（X-017 / X-018）

- **対象ファイル**: `application/inventory_order_alert/tests/test_settings_page_views.py`
- **内容**: 設定画面から月数入力と保存処理が消え、`warning_days` / `stock_stale_days` は残ることを検証。
- **完了条件**: 該当テストが Red。

#### タスク62: `templates/inventory_order_alert/settings.html` の月数入力削除

- **対象ファイル**: `templates/inventory_order_alert/settings.html`
- **内容**: design.md §6.5。**削除対象**: 警告条件（出荷月数・入荷月数・重点有効化）の入力欄と保存フォーム。
- **完了条件**: `pytest application/inventory_order_alert/tests/test_settings_page_views.py` が Green。

#### タスク63: `templates/portal/dashboard.html` のアラート帯文言変更

- **対象ファイル**: `templates/portal/dashboard.html`
- **内容**: design.md §6.4。流動区分ベースの文言・tone へ。
- **完了条件**: A-021〜A-030 が Green のまま、ポータル画面のテストが Green。

#### タスク64: 一覧 JS のテスト改修（X-029〜X-035）

- **対象ファイル**: `application/inventory_order_alert/tests/test_inventory_order_alert_list_js.py`
- **内容**: ソース文字列アサーション方式（test-design.md §1.2）。
  `flowQuadrants` からの引き直し、流動区分ランク、`countRows` / `renderCounts` / `updateUrl` の追随、
  **JS 側が暦月計算を持たないこと**（X-031。判定はサーバ側で6通り事前計算済み）、
  `alertLevel` / `alertOnly` 等の旧識別子が残っていないことを検証。
- **完了条件**: 該当テストが Red。

#### タスク65: `inventory-order-alert-list-client.js` の置換

- **対象ファイル**: `static/js/inventory-order-alert-list-client.js`
- **内容**: design.md §7.2 / §3.2。判定条件セレクタの制御、`ALERT_RANK` → 流動区分ランク、
  行の再描画・件数集計・URL 更新の追随。**判定ロジックは持たず、`flowQuadrants` から引くだけにする**。
- **完了条件**: `pytest application/inventory_order_alert/tests/test_inventory_order_alert_list_js.py` が Green。

#### タスク66: `inventory-order-alert-list.js` の保存処理削除

- **対象ファイル**: `static/js/inventory-order-alert-list.js`
- **内容**: design.md §7.2。**削除対象**: 警告条件ダイアログの保存処理（`fetch` 呼び出しとハンドラ）。
  ダイアログの開閉処理は判定ルールダイアログ用に残す。行クラス更新を流動区分キーへ追随。
- **完了条件**: X-029〜X-035 が Green。

#### タスク67: CSS のテスト作成（X-025〜X-028）

- **対象ファイル**: `application/inventory_order_alert/tests/test_flow_quadrant_css.py`（新規）
- **内容**: `static/css/app.css` を読み込み、流動区分4値の ASCII セレクタが存在すること、
  日本語セレクタ（`.alert-row--重点` 等）が**存在しないこと**、
  判定条件セレクタのスタイルがあることを検証。
  他アプリの前例 `portal/tests/test_portal_list_filter_css.py` の方式に倣う。
- **完了条件**: 4件とも Red。

#### タスク68: `static/css/app.css` のセレクタ ASCII 化

- **対象ファイル**: `static/css/app.css`
- **内容**: design.md §6.6.7 / §7.4。**削除対象**: 旧アラートレベルの日本語セレクタ4種。
  確認状態のクラス（`確認済` / `確認中`）は**対象外・据え置き**。
  `application/shipment_trend/` と同一ブロックを共有しているため、
  **shipment_trend 側のセレクタを壊していないことを差分で確認する**。
- **完了条件**: `pytest application/inventory_order_alert/tests/test_flow_quadrant_css.py` が Green、
  かつ `pytest application/shipment_trend/` が Green。

#### タスク69: `scripts/verify_post_receipt_shipment_count.py` の追随（X-037）

- **対象ファイル**: `scripts/verify_post_receipt_shipment_count.py`
- **内容**: design.md §7.2。`ListQuery(alert_only=...)` → `ListQuery(attention_only=...)`、
  CLI オプション `--alert-only` → `--attention-only`。
- **完了条件**: `pytest application/inventory_order_alert/tests/test_verify_post_receipt_shipment_count.py` が Green。

---

### ステージ7: 全体検証と仕上げ

#### タスク70: 旧識別子の残存0件テストの作成（A-038 / A-039 / X-036 / X-037）

- **対象ファイル**: `application/inventory_order_alert/tests/test_legacy_alert_identifiers_removed.py`（新規）
- **内容**: リポジトリ内を走査し、`alert_level` / `alertLevel` / `alert_only` / `alertOnly` /
  `save_alert_settings` の残存が0件であることを検証する（test-design.md §1.4 の完了条件）。
  走査対象: `application/inventory_order_alert` / `static/js` / `templates/inventory_order_alert` / `scripts`。
  `docs/` 配下（仕様書）と `migrations/0008_*.py` / `0011_*.py`（旧名を含むのが正当）は除外する。
- **完了条件**:
  - `pytest application/inventory_order_alert/tests/test_legacy_alert_identifiers_removed.py` が Green。
  - 手動確認: `grep -rn "alert_level\|alertLevel\|alert_only\|alertOnly" application/inventory_order_alert static/js templates/inventory_order_alert scripts --include=*.py --include=*.js --include=*.html`
    の結果がマイグレーション2件のみ。

#### タスク71: エッジケース・性能テストの作成（E-001〜E-010）

- **対象ファイル**: `application/inventory_order_alert/tests/test_flow_quadrant.py`（追記）
- **内容**: test-design.md §4.3。
  E-001 ペイロード増分が1行あたり**100バイト以下**（design.md §9 R-3 への応答）、
  E-002 5,000行での生成、E-003 30,000回判定、E-004 判定軸切替で行集合が不変、
  E-005 件数の左右一致、E-006 アラート帯と一覧の件数差が固定、E-007 同時実行、
  E-008 移行直後の深刻化判定、E-009 呼称の使い分け、E-010 24通りのパラメトライズド判定。
- **完了条件**: 10件すべて Green。NF-001 の性能要件が数値で確認できること。

#### タスク72: アプリ全体テストとアーキテクチャテストの Green 化（X-038）

- **対象ファイル**: なし（検証のみ。失敗があれば該当タスクへ戻る）
- **内容**: 全体テストを実行し、ステージ2以降 Red だったスイートを Green に戻す。
- **完了条件**:
  - `pytest application/inventory_order_alert/` が全件 Green（266件の設計テストを含む）。
  - `pytest config/tests/test_clean_architecture.py` が Green。
  - `pytest` （リポジトリ全体）が Green。
  - `pytest --cov=application/inventory_order_alert --cov-report=term-missing application/inventory_order_alert/`
    で `flow_quadrant.py` のカバレッジが確認できること。

#### タスク73: `collectstatic` の実行

- **対象ファイル**: `staticfiles/`（生成物。手編集しない）
- **内容**: `python manage.py collectstatic --noinput`。
- **完了条件**: `staticfiles/js/inventory-order-alert-list-client.js` と
  `staticfiles/css/app.css` が更新され、旧識別子が残っていないこと。

#### タスク74: 機能仕様書の改訂

- **対象ファイル**: `application/inventory_order_alert/docs/在庫発注アラート_機能仕様書.md`
- **内容**: design.md §7.5 / requirements.md §6.3。
  §2.3（REQ-F-004 / 011 / 012 / 013 / 014）・§4.1.3〜4.1.5・§5・§6・§8 を
  流動区分ベースへ改訂する。仕様書が Single Source of Truth であるため、
  **コードと食い違ったまま残さない**（CLAUDE.md §3 仕様の原則）。
- **完了条件**: 改訂後の機能仕様書に旧アラートレベル（重点／警告（出荷なし）／警告（出荷あり））の
  記述が残っていないこと。更新日を `date '+%Y/%m/%d'` で記録すること。

#### タスク75: 本番相当環境でのマイグレーション適用確認

- **対象ファイル**: なし（運用確認）
- **内容**: test-design.md §2.3 の補足のとおり、`django_db_use_migrations=False` により
  `RenameField` の実行はテストで検証できない。**本番相当の PostgreSQL 16 に対して手動で確認する**。
  - `python manage.py migrate inventory_order_alert 0011` を実行し、エラーなく完了すること。
  - 適用前後で `InventoryOrderAlertConfirmation` の行数が一致すること（データ保持の確認）。
  - `confirmed_flow_quadrant` に旧アラートレベルのラベルがそのまま入っていること（書き換えない。NF-007）。
  - 画面を開き、旧ラベルが `normalize_flow_quadrant` で流動区分に正規化されて表示されること。
  - ロールバック手順（`migrate inventory_order_alert 0010`）が機能することを確認する。
- **完了条件**: 上記5点の確認結果を「タスク実行レポート」に記録すること。

---

## 3. タスク実行レポート

（各タスク完了時にここへ追記する。`--------------------` で前後を囲み、
`date '+%Y/%m/%d %H:%M'` で取得した実際の時刻を記録する。）

<!--
--------------------
### タスクN: {タスク名}（完了 YYYY/MM/DD HH:MM）

- 懸念事項:
- 改善事項:
- 設計のGoodポイント:
- チーム共有ポイント:
--------------------
-->

--------------------
### タスク1: 流動区分ドメインのテスト作成（完了 2026/08/28 09:07）

- 懸念事項: テストケース設計中に test-design.md §3.1 判定条件マトリクスの誤りを1件発見した（`ROW_SUPPLY_RISK` × 低流動6か月 を「通常流動品」と記載）。基準日 2026/8/27 から6か月遡ると境界日は 2026/2/27 であり、最終入荷日 2026/1/10 は期間外のため正しくは「供給リスク品」。test-design.md を修正済み（design.md §4.4 の規則自体は正しいため未変更）。
- 改善事項: マトリクスの全15セルを手計算で再検証した。他14セルに誤りはなかった。
- 設計のGoodポイント: 代表6行と判定条件6値をモジュール定数に固定したことで、境界日の暦月丸め（月末→2/28、うるう年→2/29）を実データで検証でき、仕様の誤りを実装前に検出できた。
- チーム共有ポイント: 暦月の遡り計算は `add_calendar_months(as_of, -months)` に一本化しており、「N か月前の同日」であって「30×N 日前」ではない。仕様書に期待値を手書きする際はこの規則で必ず検算すること。
--------------------

--------------------
### タスク2: `flow_quadrant.py` の実装（完了 2026/08/28 09:09）

- 懸念事項: `normalize_flow_quadrant` が未知の値を通常流動品へ寄せる安全側設計のため、データ不整合が表面化しにくい。将来ログ出力の要否を検討する余地がある。
- 改善事項: 責任部署と旧ラベル互換写像をモジュール定数（`RESPONSIBLE_DEPARTMENTS` / `LEGACY_QUADRANT_ALIASES`）に切り出し、関数本体を写像の参照のみにした。
- 設計のGoodポイント: 判定期間を `EvaluationPeriod.months` に集約したため、低流動（か月）と死蔵（年）の単位差が判定ロジックへ漏れていない。判定関数が例外を投げず、必ず4値のいずれかを返す点も呼び出し側を単純にしている。
- チーム共有ポイント: `is_within_evaluation_period` は境界日ちょうどと未来日を「期間内」とみなす。既存の `is_within_calendar_months` は境界日を除外するため用途が異なる。混用しないこと。
--------------------

--------------------
### タスク3: 判定ルール凡例のテスト作成（完了 2026/08/28 09:11）

- 懸念事項: なし。
- 改善事項: D-087（月数を引数に取らない）を `inspect.signature` によるシグネチャ検査で表現し、「引数が無いこと」を実行時に固定した。
- 設計のGoodポイント: 凡例の責任部署を `responsible_departments()` と突き合わせて検証するため、S-203 の表と凡例が二重定義でずれることを防げる。
- チーム共有ポイント: 判定ルールダイアログは読み取り専用の凡例に変わり、月数設定は持たない。
--------------------

--------------------
### タスク4: `flow_quadrant_rules.py` の実装（完了 2026/08/28 09:12）

- 懸念事項: なし。
- 改善事項: 凡例の並びを `FLOW_QUADRANTS`（緊急度順）と一致させ、テストで同一性を検証した。
- 設計のGoodポイント: 責任部署をハードコードせず `responsible_departments()` から取得しているため、R-201 の変更が凡例へ自動的に波及する。
- チーム共有ポイント: `build_flow_quadrant_rule_rows()` は引数を取らない。`ListPageContext` の月数関連フィールド撤去（タスク群ステージ4）と対になる。
--------------------

--------------------
### タスク5: 旧ドメインVOと対応テストの削除（完了 2026/08/28 09:14）

- 懸念事項: 想定どおり `pytest application/inventory_order_alert/` は Red になった。全体 Green の回復はステージ7まで持ち越す。
- 改善事項: 削除は tasks.md 記載の5ファイルのみに限定し、`use_cases/save_alert_settings.py` はレイヤー順を守るためタスク27へ残した。
- 設計のGoodポイント: 旧VOを先に削除したことで、`alert_level` / `alert_rules` への依存が import エラーとして機械的に洗い出せる。
- チーム共有ポイント: 削除後に残った依存元（ステージ3〜6で潰す対象）は以下のとおり。
  - domain: `row_counts.py` / `table_display.py` / `row_display.py` / `list_rows.py`
  - use_cases: `list_page.py` / `patch_snapshot_row.py` / `save_confirmation.py` / `summary_api.py`
  - infrastructure: `persistence/confirmation_repository.py`
  - interfaces相当: `templatetags/inventory_order_alert_format.py`
  - tests: `test_reconcile_confirmations.py` / `test_snapshot_patch.py` / `test_row_display.py`
  - なお `models.py` の `confirmed_alert_level` 列と既存マイグレーション（0008/0009）は名称変更の対象であり、ステージ5・7で扱う。
--------------------

--------------------

### タスク6: `test_list_summary.py` の改修（完了 2026/08/28 09:15）

- 懸念事項: **タスク7（`list_rows.py` の置換）はタスク9（`list_query.py` の置換）に依存する。**
  `filter_summary_rows` が `query.flow_quadrant` / `query.attention_only`、`apply_flow_quadrants_to_rows` が
  `query.flow_selection` を参照するため、`ListQuery` に新フィールドが入るまでタスク7の完了条件（Green）を満たせない。
  そのため実行順を **タスク6 → 8 → 9 → 7** に入れ替える（タスク自体の内容・完了条件は変更しない）。
- 改善事項: 旧 `test_list_summary.py` にあった `parse_list_query` のテストはタスク8（`test_list_query.py`）へ、
  `sort_summary_rows` のテストはタスク14（`test_table_display.py`）へ移す設計になっているため、本ファイルからは削除した。
  現時点で `sort_summary_rows` を検証するテストが一時的に存在しない状態になる（タスク14で回復する）。
- 設計のGoodポイント: 行への付与（`apply_flow_quadrants_to_rows`）と絞り込み（`filter_summary_rows`）でテスト用の
  行ビルダーを分けた（`_source_row` / `_filter_row`）。付与前の行と付与後の行を取り違えないため。
- チーム共有ポイント: Red の内容は `list_rows.py` が削除済み `alert_level` を import している ModuleNotFoundError。
  期待どおりの Red であり、タスク7で解消する。
--------------------

---

## レビュー履歴

<!-- 実装レビュー（implement-review-l1）がこのセクションに追記する。作成時点では見出しのみ残す。 -->

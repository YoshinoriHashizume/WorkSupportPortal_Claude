文書ID: TASK-SINGLE-FLOW-VIEW-2026-001
作成日: 2026/09/16
更新日: 2026/09/17
対応文書: ./design.md（DESIGN-SINGLE-FLOW-VIEW-2026-001）, ./test-design.md（TEST-SINGLE-FLOW-VIEW-2026-001）, ./requirements.md（REQ-SINGLE-FLOW-VIEW-2026-001）

# 05_single-flow-view タスクリスト

## 状況チェックシート

**凡例**: [ ] 未着手 / [~] 進行中 / [✅YYYY/MM/DD HH:MM] 完了 / [- YYYY/MM/DD HH:MM] スキップ

方針:
- 1 タスク = 原則 1 ファイル。TDD のため「テスト作成（Red）→ 実装（Green）」を対で並べる
- レイヤー順: domain → use_cases → infrastructure → interfaces → docs
- **第 1 段階（タスク 1〜40）を完了・検証してから第 2 段階（41〜68）に着手する**（requirements §6.3）
- 各タスク完了時に `date '+%Y/%m/%d %H:%M'` で時刻を取得して記録する

### 第 1 段階: 判定期間の一本化・セル表示・移行措置

| # | タスク | レイヤー | 状態 |
|---|--------|---------|------|
| 1 | 判定期間・流動区分のテスト改修（TC-SFV-D-001〜025） | domain/test | [✅2026/09/16 11:32] |
| 2 | `flow_quadrant.py` の実装（判定軸廃止・年数 VO・区分改称・旧称写像） | domain | [✅2026/09/16 17:40] 本体は 11:34 実装済み。起動hotfix を先行し、暫定の責任部署表はタスク 4 で撤去 |
| 3 | 推奨アクションのテスト作成（TC-SFV-D-030〜038） | domain/test | [✅2026/09/16 17:32] |
| 4 | `recommended_action.py` の実装 | domain | [✅2026/09/16 17:40] |
| 5 | 判定ルール表のテスト改修（TC-SFV-D-040〜041） | domain/test | [✅2026/09/16 17:53] |
| 6 | `flow_quadrant_rules.py` の実装 | domain | [✅2026/09/16 17:55] |
| 7 | 一覧クエリのテスト改修（TC-SFV-D-050〜053） | domain/test | [✅2026/09/16 17:58] |
| 8 | `list_query.py` の実装 | domain | [✅2026/09/16 17:58] |
| 9 | 一覧フィルタのテスト改修（新キー・旧キー写像） | domain/test | [✅2026/09/16 17:59] |
| 10 | `list_filter.py` の実装 | domain | [✅2026/09/16 17:59] 起動hotfix で実装済み（変更なし） |
| 11 | 行への状況・推奨アクション付与のテスト作成（TC-SFV-D-063） | domain/test | [✅2026/09/16 18:01] |
| 12 | `list_rows.py` の実装（行列キー Y1/Y3/Y5、状況・推奨アクション） | domain | [✅2026/09/16 18:02] |
| 13 | 件数サマリのテスト改修（TC-SFV-D-057） | domain/test | [✅2026/09/16 18:05] |
| 14 | `row_counts.py` / `row_display.py` の実装 | domain | [✅2026/09/16 18:06] |
| 15 | クライアント配信ペイロードのテスト改修（TC-SFV-D-054〜056） | domain/test | [✅2026/09/16 18:07] |
| 16 | `list_client_data.py` の実装 | domain | [✅2026/09/16 18:07] |
| 17 | CSV 出力のテスト改修（TC-SFV-D-060、062） | domain/test | [✅2026/09/16 18:08] |
| 18 | `export_csv.py` の実装 | domain | [✅2026/09/16 18:09] |
| 19 | 旧識別子撤去テストの改修（`test_legacy_alert_identifiers_removed.py`） | domain/test | [✅2026/09/16 18:30] 18:10 テスト改修、templates / static / use_cases の撤去完了で Green |
| 20 | 一覧ユースケースのテスト改修（TC-SFV-A-003） | use_cases/test | [✅2026/09/16 18:14] |
| 21 | `list_page.py` の実装 | use_cases | [✅2026/09/16 18:15] |
| 22 | ダッシュボードのテスト改修（TC-SFV-A-004） | use_cases/test | [✅2026/09/16 18:13] |
| 23 | `portal_dashboard.py` の実装 | use_cases | [✅2026/09/16 18:13] |
| 24 | 深刻化による未確認化のテスト改修（TC-SFV-A-006、I-010） | use_cases/test | [✅2026/09/16 18:19] コード変更なしで Green |
| 25 | 推奨アクション定義ファイル読み込みのテスト作成（TC-SFV-I-007〜009） | infrastructure/test | [✅2026/09/16 18:19] |
| 26 | `infrastructure/config/recommended_actions.py` の実装 | infrastructure | [✅2026/09/16 18:20] |
| 27 | `wiring.py` の実装（推奨アクションの組み立て、TC-SFV-A-007） | interfaces | [✅2026/09/16 18:21] |
| 28 | `views.py` の実装（判定軸コンテキストの撤去） | interfaces | [✅2026/09/16 18:15] タスク 21 と同時（`evaluation_periods` / `recommended_actions` をコンテキストへ） |
| 29 | 一覧テンプレート `list.html` の実装 | interfaces | [✅2026/09/16 18:24] |
| 30 | `inventory-order-alert-list-client.js` の実装 | interfaces | [✅2026/09/16 18:26] |
| 31 | `inventory-order-alert-list.js` の実装（詳細ダイアログ） | interfaces | [✅2026/09/16 18:26] |
| 32 | `app.css` の実装 | interfaces | [✅2026/09/16 18:27] |
| 33 | ダッシュボードテンプレート `dashboard.html` の実装 | interfaces | [✅2026/09/16 18:29] |
| 34 | 一覧ビューのテスト改修（TC-SFV-X-001〜013、021） | interfaces/test | [✅2026/09/16 18:40] |
| 35 | JS ソース断言テストの改修（TC-SFV-X-017〜019） | interfaces/test | [✅2026/09/16 18:43] |
| 36 | ダッシュボードビューのテスト改修（TC-SFV-X-012） | interfaces/test | [✅2026/09/16 18:40] タスク 34 と同じファイル（`test_dashboard_shows_inventory_order_alert_banner`） |
| 37 | 機能仕様書の改訂（§4.1.5・§4.1.6・§5.2・§6.2・改訂履歴） | docs | [✅2026/09/16 18:52] |
| 38 | 02_low-flow-visibility/requirements.md への置換注記 | docs | [✅2026/09/16 18:53] |
| 39 | 本番デプロイ手順への「確認状態リセット」追記（REQ-SFV-F-020） | docs | [✅2026/09/16 18:54] |
| 40 | 第 1 段階の検証（全テスト・`manage.py check`・実データでメニュー帯の件数変化を測定・DECISIONS 記録） | 検証 | [✅2026/09/16 19:00] ブラウザ目視は未実施（ユーザー確認待ち） |

### 第 2 段階: 内示受注に基づく需要予測・緊急度

| # | タスク | レイヤー | 状態 |
|---|--------|---------|------|
| 41 | 内示推移のテスト作成（TC-SFV-D-070〜075） | domain/test | [✅2026/09/17 08:17] |
| 42 | `unconfirmed_order_trend.py` の実装 | domain | [✅2026/09/17 08:17] |
| 43 | 照合単位のテスト作成（TC-SFV-D-080〜087） | domain/test | [✅2026/09/17 08:19] |
| 44 | `reconciliation_unit.py` の実装 | domain | [✅2026/09/17 08:19] |
| 45 | 需要予測のテスト作成（TC-SFV-D-090〜109） | domain/test | [✅2026/09/17 08:20] |
| 46 | `demand_forecast.py` の実装 | domain | [✅2026/09/17 08:21] |
| 47 | 在庫月数ソートのテスト追加（TC-SFV-D-059） | domain/test | [✅2026/09/17 08:23] 対象は `test_table_display.py`（ソートの実装場所） |
| 48 | `list_filter.py` の実装（在庫月数ソート） | domain | [✅2026/09/17 08:24] 対象は `table_display.py` |
| 49 | ペイロード第 2 段階キーのテスト追加 | domain/test | [✅2026/09/17 08:24] |
| 50 | `list_client_data.py` の実装（第 2 段階キー） | domain | [✅2026/09/17 08:26] |
| 51 | CSV 追加列のテスト追加（TC-SFV-D-061） | domain/test | [✅2026/09/17 08:24] |
| 52 | `export_csv.py` の実装（末尾 4 列） | domain | [✅2026/09/17 08:26] |
| 53 | 取込ポートのテスト作成（TC-SFV-A-001〜002） | use_cases/test | [✅2026/09/17 08:28] |
| 54 | `domain/repositories/ports.py` の `StockImporter` に行の後処理（`enrich_rows`）を追加 | domain | [✅2026/09/17 08:29] |
| 55 | `import_stock.py` の実装（`attach_demand_forecast` を後処理として渡す） | use_cases | [✅2026/09/17 08:31] |
| 56 | 内示受注クエリのテスト作成（TC-SFV-I-001〜003、006） | infrastructure/test | [✅2026/09/17 08:33] |
| 57 | `summary_queries.py` の実装（`fetch_unconfirmed_orders`） | infrastructure | [✅2026/09/17 08:35] |
| 58 | 集計行への内示推移付与のテスト追加（TC-SFV-I-004〜005） | infrastructure/test | [✅2026/09/17 08:33] |
| 59 | `summary_queries.build_summary_rows` / `summary_aggregation.py` の実装 | infrastructure | [✅2026/09/17 08:35] |
| 60 | `list.html` の実装（緊急度・需要予測区分） | interfaces | [✅2026/09/17 08:38] |
| 61 | `inventory-order-alert-list-client.js` の実装（緊急度セル・在庫月数ソート） | interfaces | [✅2026/09/17 08:39] |
| 62 | `inventory-order-alert-list.js` の実装（詳細の需要予測区分） | interfaces | [✅2026/09/17 08:39] |
| 63 | `app.css` の実装（緊急度・需要予測区分） | interfaces | [✅2026/09/17 08:39] |
| 64 | 一覧ビューのテスト追加（TC-SFV-X-013 第 2 段階、014〜016） | interfaces/test | [✅2026/09/17 08:42] |
| 65 | JS ソース断言テストの追加（TC-SFV-X-020） | interfaces/test | [✅2026/09/17 08:42] |
| 66 | 機能仕様書の改訂（§4.1.6 需要予測・§7.1 内示受注・改訂履歴） | docs | [✅2026/09/17 08:54] |
| 67 | 実データでの数値検証（test-design §3.3）と DECISIONS 記録 | 検証 | [✅2026/09/17 08:56] |
| 68 | 第 2 段階の検証（全テスト・`manage.py check`・取込時間の実測） | 検証 | [✅2026/09/17 08:57] ブラウザ目視は未実施（ユーザー確認待ち） |

---

## タスク詳細

### 第 1 段階

#### タスク1: 判定期間・流動区分のテスト改修
- 対象ファイル: `application/inventory_order_alert/tests/test_flow_quadrant.py`（`test_flow_quadrant_edge_cases.py` の判定軸依存の断言も同時に整理）
- 内容: TC-SFV-D-001〜025 を実装。判定軸（`FLOW_AXIS_*` / `for_axis` / `default_for_axis`）に依存する既存テストを削除し、年数 VO・Y キー行列・新区分名・ランク・旧称/旧キー写像・深刻化判定・責任部署の断言に置き換える
- 完了条件: 新テストが Red（`ImportError` / `AttributeError` / 断言失敗）で失敗する

#### タスク2: `flow_quadrant.py` の実装
- 対象ファイル: `application/inventory_order_alert/domain/value_objects/flow_quadrant.py`
- 内容: design §4.1〜4.2。`EVALUATION_PERIOD_YEARS`、`EvaluationPeriod(years)`＋`__post_init__`、`EvaluationPeriods`（`find` / `find_by_years` / `default`）、`DEFAULT_EVALUATION_PERIOD`、`FlowSelection`（axis 削除）、`REFERENCE_FLOW_SELECTION`。区分定数を `QUADRANT_LOW_FLOW_NO_INCOMING` / `QUADRANT_LOW_FLOW_NO_SHIPMENT` に改称、`FLOW_QUADRANT_KEYS` を新キーに、`LEGACY_QUADRANT_ALIASES` に旧称ラベル・旧キーを追加。`resolve_flow_quadrant_matrix` は 3 キー。責任部署はタスク 4 の `RecommendedActions` から引く（タスク 4 完了まで暫定で既存表を残す）。design §7.3 の定数・メソッドを削除
- 完了条件: タスク 1 のテストが Green。`import django` なし

#### タスク3: 推奨アクションのテスト作成
- 対象ファイル: `application/inventory_order_alert/tests/test_recommended_action.py`（新規）
- 内容: TC-SFV-D-030〜038
- 完了条件: Red

#### タスク4: `recommended_action.py` の実装
- 対象ファイル: `application/inventory_order_alert/domain/value_objects/recommended_action.py`（新規）
- 内容: design §4.3。`RecommendedAction`（`__post_init__` で区分を検証）、`RecommendedActions`（4 区分必須、`for_quadrant` / `with_action_texts`）、`DEFAULT_RECOMMENDED_ACTIONS`（S-203 の表の文言・状況テンプレート・責任部署）、`render_status()`。`flow_quadrant.responsible_departments()` をこのコレクション参照に差し替え、`RESPONSIBLE_DEPARTMENTS` を撤去
- 完了条件: タスク 3 のテスト Green、タスク 1 のテストも Green のまま

#### タスク5: 判定ルール表のテスト改修
- 対象ファイル: `application/inventory_order_alert/tests/test_flow_quadrant_rules.py`
- 内容: TC-SFV-D-040〜041
- 完了条件: Red

#### タスク6: `flow_quadrant_rules.py` の実装
- 対象ファイル: `application/inventory_order_alert/domain/value_objects/flow_quadrant_rules.py`
- 内容: `FlowQuadrantRuleRow` に `status_template` / `action` を追加し、`RecommendedActions` から引く。判定軸の説明を削除。ランク順に並べる
- 完了条件: タスク 5 Green

#### タスク7: 一覧クエリのテスト改修
- 対象ファイル: `application/inventory_order_alert/tests/test_list_query.py`
- 内容: TC-SFV-D-050〜053
- 完了条件: Red

#### タスク8: `list_query.py` の実装
- 対象ファイル: `application/inventory_order_alert/domain/value_objects/list_query.py`
- 内容: `parse_flow_selection` を `period` の年数解釈のみに（`axis` 無視、不正は既定）。`parse_flow_quadrant` は `normalize_flow_quadrant` で旧キーを写像
- 完了条件: タスク 7 Green

#### タスク9: 一覧フィルタのテスト改修
- 対象ファイル: `application/inventory_order_alert/tests/test_list_filter.py`
- 内容: 流動区分フィルタとランクソートの断言を新キー・新区分名に。旧キー指定でも絞れること（TC-SFV-D-058 の既定ソート含む）
- 完了条件: Red

#### タスク10: `list_filter.py` の実装
- 対象ファイル: `application/inventory_order_alert/domain/value_objects/list_filter.py`
- 内容: 新キーでの絞り込み・ランクソート。`REFERENCE_FLOW_SELECTION` 参照は変更不要
- 完了条件: タスク 9 Green

#### タスク11: 行への状況・推奨アクション付与のテスト作成
- 対象ファイル: `application/inventory_order_alert/tests/test_list_rows.py`（新規。既存の `test_row_display.py` に行付与の断言があれば移す）
- 内容: TC-SFV-D-063。`apply_flow_quadrants_to_rows` が `flow_status` / `recommended_action` / `responsible_department` を付与し、`flow_quadrants` が Y キーであること
- 完了条件: Red

#### タスク12: `list_rows.py` の実装
- 対象ファイル: `application/inventory_order_alert/domain/value_objects/list_rows.py`
- 内容: design §3.1・§4.3。行列を Y1/Y3/Y5 で付与、選択中の判定期間で `render_status()` を呼び `flow_status` を、`RecommendedActions` から `recommended_action` を付与。通常流動品は空文字
- 完了条件: タスク 11 Green

#### タスク13: 件数サマリのテスト改修
- 対象ファイル: `application/inventory_order_alert/tests/test_row_counts.py`（`test_row_display.py` の区分名断言も併せて）
- 内容: TC-SFV-D-057
- 完了条件: Red

#### タスク14: `row_counts.py` / `row_display.py` の実装
- 対象ファイル: `application/inventory_order_alert/domain/value_objects/row_counts.py`、`row_display.py`（2 ファイル。区分名の定数参照差し替えのみで密結合のため同時に扱う）
- 内容: 新区分定数への追随
- 完了条件: タスク 13 Green

#### タスク15: クライアント配信ペイロードのテスト改修
- 対象ファイル: `application/inventory_order_alert/tests/test_list_client_data.py`
- 内容: TC-SFV-D-054〜056
- 完了条件: Red

#### タスク16: `list_client_data.py` の実装
- 対象ファイル: `application/inventory_order_alert/domain/value_objects/list_client_data.py`
- 内容: design §6.2。`flowAxes` / `flowPeriods` を削除し `evaluationPeriods` / `defaultPeriodKey` / `recommendedActions` を追加。区分ラベル・順序・責任部署を新区分に
- 完了条件: タスク 15 Green

#### タスク17: CSV 出力のテスト改修
- 対象ファイル: `application/inventory_order_alert/tests/test_export_csv.py`
- 内容: TC-SFV-D-060、062。既存 24 列の順序が不変であることの断言を追加（第 2 段階の D-061 の土台）
- 完了条件: Red

#### タスク18: `export_csv.py` の実装
- 対象ファイル: `application/inventory_order_alert/domain/value_objects/export_csv.py`
- 内容: 流動区分の値を新区分名、`判定軸` 列は空文字、`判定期間` は `1年` 等
- 完了条件: タスク 17 Green

#### タスク19: 旧識別子撤去テストの改修
- 対象ファイル: `application/inventory_order_alert/tests/test_legacy_alert_identifiers_removed.py`
- 内容: 旧称（供給リスク品・在庫過剰リスク品）・旧キー（supply-risk・excess-stock-risk）・判定軸（low_flow・dormant・FLOW_AXIS）が domain / templates / static に定数・表示として残っていないことを断言（`LEGACY_QUADRANT_ALIASES` と CSS の互換記述は除外）
- 完了条件: Green（実装タスク 2〜18 の完了後に通る）

#### タスク20: 一覧ユースケースのテスト改修
- 対象ファイル: `application/inventory_order_alert/tests/test_inventory_order_alert_application.py`
- 内容: TC-SFV-A-003
- 完了条件: Red

#### タスク21: `list_page.py` の実装
- 対象ファイル: `application/inventory_order_alert/use_cases/list_page.py`
- 内容: 判定軸関連のコンテキスト（`flow_axis_options` 等）を撤去し、`evaluation_periods` と選択中の判定期間を出す。`RecommendedActions` を受け取りペイロードに渡す
- 完了条件: タスク 20 Green

#### タスク22: ダッシュボードのテスト改修
- 対象ファイル: `application/portal/tests/test_portal_dashboard.py`（在庫発注アラート帯の断言部分）
- 内容: TC-SFV-A-004
- 完了条件: Red

#### タスク23: `portal_dashboard.py` の実装
- 対象ファイル: `application/inventory_order_alert/use_cases/portal_dashboard.py`
- 内容: `BANNER_FLOW_CONDITION_LABEL` を「判定期間 1年」に。区分名を新区分に
- 完了条件: タスク 22 Green

#### タスク24: 深刻化による未確認化のテスト改修
- 対象ファイル: `application/inventory_order_alert/tests/test_reconcile_confirmations.py`（`test_save_confirmation.py` の区分名断言も併せて）
- 内容: TC-SFV-A-006、I-010。新区分名・旧称保存値の正規化・固定基準 1 年
- 完了条件: Green（コード変更なしで通ること。通らなければ `confirmation_repository.py` を最小修正し、その旨を実行レポートに記録）

#### タスク25: 推奨アクション定義ファイル読み込みのテスト作成
- 対象ファイル: `application/inventory_order_alert/tests/test_recommended_actions_config.py`（新規）
- 内容: TC-SFV-I-007〜009（`tmp_path`・`caplog`）
- 完了条件: Red

#### タスク26: `infrastructure/config/recommended_actions.py` の実装
- 対象ファイル: `application/inventory_order_alert/infrastructure/config/__init__.py`、`recommended_actions.py`（新規）
- 内容: design §4.3。`load_recommended_actions(path=None)`。既定パスは同ディレクトリの `recommended_actions.json`。なければ既定、不正 JSON は WARNING ログで既定
- 完了条件: タスク 25 Green

#### タスク27: `wiring.py` の実装
- 対象ファイル: `application/inventory_order_alert/interfaces/wiring.py`
- 内容: `list_page_usecase()` / `export_csv_usecase()` に `load_recommended_actions()` の結果を注入。TC-SFV-A-007 を `test_inventory_order_alert_application.py` に追加
- 完了条件: A-007 Green、`test_clean_architecture` Green

#### タスク28: `views.py` の実装
- 対象ファイル: `application/inventory_order_alert/interfaces/views.py`
- 内容: 判定軸関連のコンテキストキーを撤去し、`evaluation_periods` / `flow_selection` を渡す
- 完了条件: `manage.py check` 問題なし。既存の views テストがタスク 34 で更新されるまでは失敗してよい

#### タスク29: 一覧テンプレート `list.html` の実装
- 対象ファイル: `templates/inventory_order_alert/list.html`
- 内容: design §6.3〜6.4。判定軸セレクタと「判定条件」パネルを撤去、判定期間セレクタ `#ioa-evaluation-period` をアクション行の先頭に、流動区分フィルタの選択肢を新区分に、セルを `ioa-flow-cell` 構成に、判定ルールダイアログの列、詳細ダイアログの流動区分区分（状況・推奨アクション・判定期間）。JS キャッシュバスター更新
- 完了条件: テンプレートがレンダリングされる（タスク 34 で断言）

#### タスク30: `inventory-order-alert-list-client.js` の実装
- 対象ファイル: `static/js/inventory-order-alert-list-client.js`
- 内容: `flowAxis` 状態と `resolveFlowPeriod(flowPeriods, axis, …)` を撤去し `evaluationPeriods` / `periodKey` に。セル描画で `recommendedActions[key].statusTemplate` に `{period}` / `{last_incoming}` / `{last_ship}` を置換。URL 同期は `period` のみ。`FLOW_QUADRANT_RANK` を新キーに
- 完了条件: `node --check` 通過、タスク 35 の断言 Green

#### タスク31: `inventory-order-alert-list.js` の実装
- 対象ファイル: `static/js/inventory-order-alert-list.js`
- 内容: 詳細ダイアログの流動区分区分に状況・推奨アクション・判定期間を表示。`getFlowConditionLabel` 相当を判定期間ラベルに
- 完了条件: `node --check` 通過

#### タスク32: `app.css` の実装
- 対象ファイル: `static/css/app.css`
- 内容: `.ioa-flow-cell*` のレイアウト（`min-width: 22em`、狭幅で状況・責任部署を隠す）、`alert-row--low-flow-no-incoming` / `--low-flow-no-shipment` へのクラス名追随（色は旧区分を引き継ぐ）、判定期間セレクタの配置。CSS キャッシュバスター（`base.html`）更新
- 完了条件: 旧キーのセレクタが CSS に残っていない

#### タスク33: ダッシュボードテンプレート `dashboard.html` の実装
- 対象ファイル: `templates/portal/dashboard.html`
- 内容: 在庫発注アラート帯の区分名・条件ラベル
- 完了条件: タスク 36 Green

#### タスク34: 一覧ビューのテスト改修
- 対象ファイル: `application/inventory_order_alert/tests/test_inventory_order_alert_views.py`
- 内容: TC-SFV-X-001〜013（013 は第 1 段階分）、021。旧称・判定軸の断言を置き換え
- 完了条件: Green

#### タスク35: JS ソース断言テストの改修
- 対象ファイル: `application/inventory_order_alert/tests/test_inventory_order_alert_list_js.py`
- 内容: TC-SFV-X-017〜019。`flowAxis` 関連の既存断言を削除。V-218 の断言は維持
- 完了条件: Green

#### タスク36: ダッシュボードビューのテスト改修
- 対象ファイル: `application/portal/tests/test_portal_dashboard.py`
- 内容: TC-SFV-X-012
- 完了条件: Green

#### タスク37: 機能仕様書の改訂
- 対象ファイル: `application/inventory_order_alert/docs/在庫発注アラート_機能仕様書.md`
- 内容: §4.1.5（判定期間セレクタの位置・判定軸の廃止）、§4.1.6（セル構成・詳細ダイアログ）、§5.2（メニュー帯の固定基準 1 年）、§6.2（判定期間 1/3/5 年・新区分・ランク・状況・推奨アクション）、§8.3（CSV）、改訂履歴 5.0（区分改称は大改訂）
- 完了条件: 旧称・判定軸が「改訂前」注記以外に残っていない

#### タスク38: 02_low-flow-visibility/requirements.md への置換注記
- 対象ファイル: `application/inventory_order_alert/docs/spec/02_low-flow-visibility/requirements.md`
- 内容: REQ-LFV-F-002・F-003・F-018 と UC-03 に「05_single-flow-view で置き換え」の注記（本文は削除しない）
- 完了条件: 注記が入っている

#### タスク39: 本番デプロイ手順への「確認状態リセット」追記
- 対象ファイル: `Document/` 配下の本番デプロイ手順（該当ファイルを Glob で特定）
- 内容: REQ-SFV-F-020。リリース時に管理者が設定画面の「確認状態リセット」を実行する手順と、利用者への周知文（メニュー帯の件数基準変更・確認記録のリセット）
- 完了条件: 手順書に追記されている

#### タスク40: 第 1 段階の検証
- 対象: リポジトリ全体
- 内容: `pytest -q` 全件 Green、`python manage.py check`、`node --check` 両 JS。実データ（2026/09/07 取込スナップショット）で新基準（1 年）の 4 区分件数と旧基準（3 か月）の件数を比較し、DECISIONS.md に「ステージ17（05 第 1 段階）」として記録（R-3）。`git status` で意図しない変更がないことを確認
- 完了条件: 上記すべて。ユーザーへ報告し第 2 段階の着手可否を確認

### 第 2 段階

#### タスク41: 内示推移のテスト作成
- 対象ファイル: `application/inventory_order_alert/tests/test_unconfirmed_order_trend.py`（新規）
- 内容: TC-SFV-D-070〜075
- 完了条件: Red

#### タスク42: `unconfirmed_order_trend.py` の実装
- 対象ファイル: `application/inventory_order_alert/domain/value_objects/unconfirmed_order_trend.py`（新規）
- 内容: design §4.4。`build_unconfirmed_order_trend(orders, *, as_of_date)` → 固定 4 件、負は 0
- 完了条件: タスク 41 Green

#### タスク43: 照合単位のテスト作成
- 対象ファイル: `application/inventory_order_alert/tests/test_reconciliation_unit.py`（新規）
- 内容: TC-SFV-D-080〜087
- 完了条件: Red

#### タスク44: `reconciliation_unit.py` の実装
- 対象ファイル: `application/inventory_order_alert/domain/value_objects/reconciliation_unit.py`（新規）
- 内容: design §4.5。`ReconciliationUnit`（`row_keys`）、`ReconciliationUnits.build` / `unit_of`。level1 が空の行は連結しない
- 完了条件: タスク 43 Green

#### タスク45: 需要予測のテスト作成
- 対象ファイル: `application/inventory_order_alert/tests/test_demand_forecast.py`（新規）
- 内容: TC-SFV-D-090〜109。test-design §3.1 の ROW_100 / ROW_104 / ROW_137_A / ROW_137_B を使う
- 完了条件: Red

#### タスク46: `demand_forecast.py` の実装
- 対象ファイル: `application/inventory_order_alert/domain/value_objects/demand_forecast.py`（新規）
- 内容: design §4.6。`DemandForecast`（`Literal` basis、`__post_init__`）、`build_demand_forecast`、`stock_total_of`、`stockout_forecast_month`（上限 120 か月）、`months_of_stock`、`attach_demand_forecast(rows, *, as_of_date)`（コピーを返す）
- 完了条件: タスク 45 Green

#### タスク47: 在庫月数ソートのテスト追加
- 対象ファイル: `application/inventory_order_alert/tests/test_list_filter.py`
- 内容: TC-SFV-D-059
- 完了条件: Red

#### タスク48: `list_filter.py` の実装（在庫月数ソート）
- 対象ファイル: `application/inventory_order_alert/domain/value_objects/list_filter.py`
- 内容: `months_of_stock` を昇順・降順でソート、空は末尾
- 完了条件: タスク 47 Green

#### タスク49: ペイロード第 2 段階キーのテスト追加
- 対象ファイル: `application/inventory_order_alert/tests/test_list_client_data.py`
- 内容: 行に `internalItemCd` / `unconfirmedOrderTrend` / `reconciliationUnitKey` / `demandForecast{basis, monthly, monthsOfStock, stockoutForecastMonth}` が出ること。キーがない旧行は `basis == "なし"`
- 完了条件: Red

#### タスク50: `list_client_data.py` の実装（第 2 段階キー）
- 対象ファイル: `application/inventory_order_alert/domain/value_objects/list_client_data.py`
- 内容: design §6.2 の第 2 段階キー
- 完了条件: タスク 49 Green

#### タスク51: CSV 追加列のテスト追加
- 対象ファイル: `application/inventory_order_alert/tests/test_export_csv.py`
- 内容: TC-SFV-D-061
- 完了条件: Red

#### タスク52: `export_csv.py` の実装（末尾 4 列）
- 対象ファイル: `application/inventory_order_alert/domain/value_objects/export_csv.py`
- 内容: `在庫月数` / `在庫切れ予測月` / `需要予測の算出根拠` / `推奨アクション` を末尾に追加
- 完了条件: タスク 51 Green

#### タスク53: 取込ポートのテスト作成
- 対象ファイル: `application/inventory_order_alert/tests/test_import_stock_usecase.py`（新規）
- 内容: TC-SFV-A-001〜002。`StockImporter` のスタブに渡された `enrich_rows` が `attach_demand_forecast` であること、集計 → 付与 → 保存の順序、内示取得失敗時のメッセージ
- 完了条件: Red

#### タスク54: `ports.py` の `StockImporter` に行の後処理を追加
- 対象ファイル: `application/inventory_order_alert/domain/repositories/ports.py`
- 内容: `StockImporter.__call__(..., enrich_rows: Callable[[list[dict], date], list[dict]] | None = None)`。design §6.7 の「ユースケースが domain を呼ぶ」を、既存ポートの構造（集計と保存を infrastructure が一括で行う）を壊さずに実現するための最小変更。判断理由を実行レポートに記録
- 完了条件: 型が通る（`import django` なし）

#### タスク55: `import_stock.py` の実装
- 対象ファイル: `application/inventory_order_alert/use_cases/import_stock.py`
- 内容: `ImportStock.execute` が `enrich_rows=attach_demand_forecast` を渡す
- 完了条件: タスク 53 Green

#### タスク56: 内示受注クエリのテスト作成
- 対象ファイル: `application/inventory_order_alert/tests/test_unconfirmed_order_query.py`（新規。`test_incoming_trend_query.py` の方式）
- 内容: TC-SFV-I-001〜003、006
- 完了条件: Red

#### タスク57: `summary_queries.py` の実装（`fetch_unconfirmed_orders`）
- 対象ファイル: `application/inventory_order_alert/infrastructure/oracle/summary_queries.py`
- 内容: design §6.6 の SQL と行変換。`OracleQueryError` を捕捉して空＋エラーメッセージを返す経路
- 完了条件: タスク 56 の I-001〜002、006 Green

#### タスク58: 集計行への内示推移付与のテスト追加
- 対象ファイル: `application/inventory_order_alert/tests/test_build_summary_rows.py`
- 内容: TC-SFV-I-004〜005、I-003
- 完了条件: Red

#### タスク59: `build_summary_rows` / `summary_aggregation.py` の実装
- 対象ファイル: `application/inventory_order_alert/infrastructure/oracle/summary_queries.py`（`build_summary_rows`）、`summary_aggregation.py`（`enrich_rows` の適用と `aggregation_error` への追記）
- 内容: 行に `internal_item_cd` / `unconfirmed_order_trend` を付与。`enrich_rows` があれば保存前に適用。内示取得失敗を `aggregation_error` に追記して続行
- 完了条件: タスク 58 Green、タスク 53 Green

#### タスク60: `list.html` の実装（緊急度・需要予測区分）
- 対象ファイル: `templates/inventory_order_alert/list.html`
- 内容: セルの `ioa-flow-urgency`、詳細ダイアログの `ioa-detail-demand-forecast-section`（推定在庫推移とメモの間）。キャッシュバスター更新
- 完了条件: タスク 64 で断言

#### タスク61: `inventory-order-alert-list-client.js` の実装（緊急度セル・在庫月数ソート）
- 対象ファイル: `static/js/inventory-order-alert-list-client.js`
- 内容: `demandForecast` を緊急度行に描画（算出できない行は非表示、120 か月超は「十分」）、`months_of_stock` ソート
- 完了条件: `node --check`、タスク 65 Green

#### タスク62: `inventory-order-alert-list.js` の実装（詳細の需要予測区分）
- 対象ファイル: `static/js/inventory-order-alert-list.js`
- 内容: 算出根拠・月別内示受注数量・在庫月数・在庫切れ予測月・照合単位の在庫内訳（既存 `renderAnchorBreakdown` 流用）
- 完了条件: `node --check`

#### タスク63: `app.css` の実装（緊急度・需要予測区分）
- 対象ファイル: `static/css/app.css`
- 内容: `.ioa-flow-urgency`、需要予測区分のスタイル。キャッシュバスター更新
- 完了条件: 表示崩れなし（目視）

#### タスク64: 一覧ビューのテスト追加
- 対象ファイル: `application/inventory_order_alert/tests/test_inventory_order_alert_views.py`
- 内容: TC-SFV-X-013（第 2 段階）、014〜016
- 完了条件: Green

#### タスク65: JS ソース断言テストの追加
- 対象ファイル: `application/inventory_order_alert/tests/test_inventory_order_alert_list_js.py`
- 内容: TC-SFV-X-020
- 完了条件: Green

#### タスク66: 機能仕様書の改訂（第 2 段階）
- 対象ファイル: `application/inventory_order_alert/docs/在庫発注アラート_機能仕様書.md`
- 内容: §4.1.6 に需要予測・緊急度、§7.1 に内示受注の取得、§8.3 に CSV 追加列、§10.5 スナップショット項目、改訂履歴
- 完了条件: 用語集と整合

#### タスク67: 実データでの数値検証と DECISIONS 記録
- 対象ファイル: `application/inventory_order_alert/docs/spec/04_shipment-history-chart/DECISIONS.md`（既存の判断ログに「ステージ18（05 第 2 段階）」として追記。05 専用の DECISIONS.md は作らない）
- 内容: test-design §3.3（照合単位 1,994・96160-00500 の需要 224/在庫月数・実績ベース比率・単位の妥当性 R-5・取込時間 R-6）
- 完了条件: 記録済み

#### タスク68: 第 2 段階の検証
- 対象: リポジトリ全体
- 内容: `pytest -q` 全件 Green、`manage.py check`、`node --check`、取込時間の実測（+5 秒以内）、`git status`
- 完了条件: 上記すべて。ユーザーへ報告

---

### 起動hotfix（2026/09/16）

タスク2で `DEFAULT_FLOW_AXIS` 等を削除した直後、後続タスク（8・14・16・21・23）未着手のままコンテナが `migrate` で落ちた。
判定軸定数は戻さず、起動経路の参照だけ新 API に付け替えた。05 の本実装はタスク3から再開する。

| ファイル | 内容 |
|---------|------|
| `domain/value_objects/list_query.py` | `period` の年数 / Yキーのみ解釈。`axis` は無視 |
| `domain/value_objects/list_client_data.py` | `flowAxes` / `flowPeriods` をやめ `evaluationPeriods` / `defaultPeriodKey` |
| `domain/value_objects/list_filter.py` | クエリから `axis` を外し `period` は年数 |
| `domain/value_objects/row_counts.py` | 新区分定数で件数を数える（項目名 `supply_risk` 等は暫定維持） |
| `domain/value_objects/flow_quadrant_rules.py` | 凡例を新区分名へ |
| `use_cases/list_page.py` | 判定軸オプションを空、期間は Y1/Y3/Y5 |
| `use_cases/portal_dashboard.py` | 帯ラベルを判定期間のみ |
| `use_cases/export_csv.py` | `判定軸` 列は空文字（design §7.3） |
| `tests/test_ioa_startup.py` | 起動 import と上記の回帰 |

---

## タスク実行レポート

（各タスク完了時にここへ追記する。`--------------------` で前後を囲み、日時・懸念事項・改善事項・設計の Good ポイント・チーム共有ポイントを書く）

--------------------
### タスク1 実行レポート（2026/09/16 11:32）
- 対象: `tests/test_flow_quadrant.py`（全面書き換え、TC-SFV-D-001〜025）、`tests/test_flow_quadrant_edge_cases.py`（判定軸依存の断言を年数選択に置換、e009 を削除）
- 結果: Red（`ImportError: cannot import name 'DEFAULT_EVALUATION_PERIOD'`）
- 懸念事項: edge_cases は `count_rows` の項目名（`low_flow_no_incoming` / `low_flow_no_shipment`）と `list_rows` / `list_client_data` に依存するため、タスク 12・14・16 完了まで Red のまま
- 改善事項: 02 で書かれていた月末丸め・うるう日・5 年境界の判定規則テストは年数化しても有効なので残した（判定規則は変えないという設計 §4.1 の担保）
- 設計の Good ポイント: `EvaluationPeriod` の値域検証（D-002）を先にテストで固定したことで、URL 由来の不正値が VO まで届かない構造を強制できる
- チーム共有ポイント: 96160-00500 の実データ（入荷 2025/04/02・出荷 2023/07/27）を D-014 に固定した。1/3/5 年で区分が変わる典型例として今後の説明にも使える
--------------------
### タスク3 実行レポート（2026/09/16 17:32）
- 対象: `tests/test_recommended_action.py`（新規、TC-SFV-D-030〜038、18 件）
- 結果: Red（`ModuleNotFoundError: recommended_action`）
- 懸念事項: `RecommendedActions` に `__len__` / `__iter__` を要求した（D-030 の「4 件」を数えるため）。design §4.3 のシグネチャには明記がないが、既存 `EvaluationPeriods` と同じファーストクラスコレクションの作法に合わせた。D-033 に「同じ区分の重複」の拒否も加えた（欠けと同じく 4 区分が揃わないため）
- 改善事項: 上書きキーは `FLOW_QUADRANT_KEYS` の値（`low-flow-no-incoming` 等）で受ける。旧キー `supply-risk` は写像せず未知キーとして無視する（D-035）——定義ファイルは新規に作るものであり互換の必要がないため
- 設計の Good ポイント: `render_status()` を純関数にしたことで、判定期間ラベル・入荷実績なしの置換をセル描画（JS）と CSV/詳細で共有できる
- チーム共有ポイント: 状況テンプレートの断言は「最終入荷 2025/04/02」「1年」の包含のみで、文言全体は固定していない。T-207 の文言は暫定（業務側で確定前）なので、文言変更でテストが割れないようにしている
--------------------
### タスク4 実行レポート（2026/09/16 17:40）
- 対象: `domain/value_objects/recommended_action.py`（新規）、`domain/value_objects/flow_quadrant.py`（暫定 `_RESPONSIBLE_DEPARTMENTS` を削除し `responsible_departments()` を `DEFAULT_RECOMMENDED_ACTIONS` 参照に差し替え）
- 結果: Green（`test_recommended_action.py` 18 件、`test_flow_quadrant.py`・`test_ioa_startup.py`・`test_clean_architecture.py` 含め 179 件）。全体は 12 failed / 15 errors で再開前と同数（後続タスクの改修対象のみ）
- 懸念事項: `flow_quadrant.py` → `recommended_action.py` は相互参照になるため、`responsible_departments()` 内で遅延 import した。定義表を 1 か所にする（design §4.3）ための最小構成だが、将来 `responsible_departments()` の呼び出し元を `RecommendedActions` 直接参照に寄せれば遅延 import は不要になる
- 改善事項: `RecommendedActions.__post_init__` でランク順に並べ替えて保持する（構築時の並びに依存せず `==` 比較と `__iter__` の順序が安定する）。`render_status()` は `str.format` でなく `replace` で置換し、文言中の `{}` で `KeyError` が出ない
- 設計の Good ポイント: 状況テンプレートの既定文言は用語集 S-203 表の「状況」列をそのままプレースホルダ化した。入荷実績なし（V-214）は `{last_incoming}` を「入荷実績なし」に置換するだけで表現でき、テンプレートを区分ごとに分岐させていない
- チーム共有ポイント: 上書きキーは `FLOW_QUADRANT_KEYS` の値（`low-flow-no-incoming` 等）。タスク 26 の `recommended_actions.json` もこのキーで書く
--------------------
### タスク5・6 実行レポート（2026/09/16 17:55）
- 対象: `tests/test_flow_quadrant_rules.py`（全面書き換え、TC-SFV-D-040〜041、9 件）、`domain/value_objects/flow_quadrant_rules.py`
- 結果: タスク 5 Red（`AttributeError: status_template`）→ タスク 6 Green（関連 188 件）
- 懸念事項: `build_flow_quadrant_rule_rows(recommended_actions=DEFAULT_RECOMMENDED_ACTIONS)` と省略可能な引数を 1 つ設けた。test-design は引数なしの呼び出しを想定しているが、タスク 27 で wiring が上書き済み `RecommendedActions` を注入したとき、判定ルールダイアログの文言がセルと食い違わないようにするため。旧テストの「月数引数を取らない」は「必須引数を取らない・`month` を含む引数がない」に読み替えた
- 改善事項: `responsible_departments()` 経由をやめ、行の 状況・推奨アクション・責任部署 を同じ `RecommendedAction` から一括で引く（定義表 1 か所の原則）
- 設計の Good ポイント: 凡例行は判定期間に依存しないため `status_template` をプレースホルダのまま持つ。ダイアログ側で `{period}` を選択中の判定期間に置換するか、そのまま「判定期間」と読ませるかはタスク 29 で決める
- チーム共有ポイント: タスク 21 の `list_page.py` では `build_flow_quadrant_rule_rows(recommended_actions)` と注入する
--------------------
### タスク7〜19 実行レポート（2026/09/16 18:10）
- 対象:
  - 7/8 `tests/test_list_query.py`（全面書き換え、D-050〜053、45 件）→ `list_query.py`（`parse_flow_quadrant` に旧キー・ラベル・旧称の写像を追加）
  - 9/10 `tests/test_list_filter.py`（判定軸断言を撤去、`period` 年数・`axis` 不在を断言）→ `list_filter.py` は hotfix 済みで変更なし（Red なしで Green）
  - 11/12 `tests/test_list_rows.py`（新規、D-058・D-063、15 件）→ `list_rows.py`（`flow_status` / `recommended_action` / `responsible_department` を `RecommendedActions` から付与。`recommended_actions` 引数を追加）。併せて既存 `tests/test_list_summary.py` の旧定数・判定軸を新 API に移行（既定行の最終入荷日を 2025/01/10 にして 1 年判定でも旧テストの意味を保つ）
  - 13/14 `tests/test_row_counts.py` / `tests/test_row_display.py` → `row_counts.py`（項目名を `low_flow_no_incoming` / `low_flow_no_shipment` に改称、`by_quadrant` を追加）。`row_display.py` は変更不要
  - 15/16 `tests/test_list_client_data.py`（D-054〜056）→ `list_client_data.py`（`recommendedActions` と行の `flowStatus` / `recommendedAction` を追加、`recommended_actions` 引数）
  - 17/18 `tests/test_export_csv.py`（D-060・062、既存 24 列の順序固定）→ `export_csv.py`（`判定軸` 列は常に空、流動区分は `normalize_flow_quadrant` で新称に）
  - 19 `tests/test_legacy_alert_identifiers_removed.py`（旧称・旧キー・判定軸の走査を追加。`flow_quadrant.py` の `LEGACY_QUADRANT_ALIASES` のみ除外）
- 結果: 7〜18 Green。19 は templates / static / use_cases に旧識別子が残るため Red（タスク 21〜33 で解消）
- 懸念事項: **タスク 14 の項目名改称は計画より波及が大きい。** `RowCounts.supply_risk` 等を参照していた `infrastructure/persistence/summary_snapshot_repository.py`・`summary_repository.py`、`use_cases/portal_dashboard.py`・`save_confirmation.py`・`reset_confirmations.py`・`summary_api.py`、`tests/test_ioa_startup.py` を同時に改称した（API 応答の JSON キーも `supplyRisk` → `lowFlowNoIncoming`、`excessStockRisk` → `lowFlowNoShipment`）。JS 側の追随はタスク 30・31、テストの追随はタスク 34 で行う。理由: タスク 1 の edge_cases テストと本タスク 19 の走査が `supply_risk` の残存を許さないため
- 改善事項: `filter_summary_rows` / `sort_summary_rows` は `list_rows.py` にあるため、tasks.md で `test_list_filter.py` に書く予定だった絞り込み・既定ソートの断言は `test_list_rows.py` に置いた
- 設計の Good ポイント: 状況の描画をサーバ（`list_rows.py`）とクライアント（`recommendedActions.statusTemplate`）の両方で同じテンプレートから行える。サーバ側は CSV・初期表示、クライアント側は判定期間切替に使う
- チーム共有ポイント: `flowQuadrantDepartments` は `recommendedActions[key].departments` と同じ値を配信している（JS 移行後に片方へ寄せる候補）
--------------------
### タスク20〜28 実行レポート（2026/09/16 18:21）
- 対象:
  - 20/21 `tests/test_inventory_order_alert_application.py`（A-003・A-005 を追加）→ `use_cases/list_page.py`（`FlowAxisOption` / `FlowPeriodOption` / `flow_axis_options` / `flow_period_options` を削除、`evaluation_periods` と `recommended_actions` をコンテキストに追加、コンストラクタで `RecommendedActions` を受ける）
  - 22/23 `application/portal/tests/test_portal_dashboard.py`（A-004。判定期間 1 年固定の行 `2025/04/02 - 2026/06/15` を追加、項目名を新区分に）→ `use_cases/portal_dashboard.py`（`BANNER_FLOW_CONDITION_LABEL = "判定期間 1年"`）。hotfix の `test_ioa_startup.py` の断言も追随
  - 24 `tests/test_reconcile_confirmations.py`（A-006・I-010 を追加、旧定数を改称）、`tests/test_confirmation_save_result.py`（`axis` を外し保存値を新称に、JSON キー `lowFlowNoIncoming`）、`tests/test_domain_confirmation.py`（定数改称）。`confirmation_repository.py` は `normalize_flow_quadrant` 済みのため変更なし
  - 25/26 `tests/test_recommended_actions_config.py`（新規、I-007〜009、6 件）→ `infrastructure/config/__init__.py`・`recommended_actions.py`（新規）。運用者向けに `recommended_actions.example.json` を同梱（実ファイル `recommended_actions.json` は置かない＝既定文言）
  - 27 `interfaces/wiring.py`（`list_page_usecase()` / `export_csv_usecase()` に `load_recommended_actions()` を注入）、`use_cases/export_csv.py`（`recommended_actions` を受け取り行付与に渡す。`flow_axis` の行値セットは撤去し domain 側で常に空）。A-007 を `test_inventory_order_alert_application.py` に追加
  - 28 `interfaces/views.py`（`flow_axis_options` / `flow_period_options` → `evaluation_periods`、ペイロード生成に `recommended_actions` を渡す）
- 結果: すべて Green（`test_clean_architecture` 含む）。`manage.py check` 問題なし
- 懸念事項: `ListPageContext.recommended_actions` は views がペイロード生成のために使う。use_case → interfaces の依存方向は保たれているが、views が domain の `build_list_client_payload` を直接呼ぶ既存構造はそのまま
- 改善事項: A-007 は wiring の `load_recommended_actions` を `monkeypatch` で差し替えて検証した（定義ファイルを実際に置くと他テストに影響するため）
- 設計の Good ポイント: 定義ファイルの読み込み失敗は WARNING ログ＋既定にフォールバックし、一覧表示を止めない（NF-007）
- チーム共有ポイント: 文言を変えるときは `infrastructure/config/recommended_actions.example.json` をコピーして `recommended_actions.json` を作る。再起動不要（リクエストごとに読む）
--------------------
### タスク29〜36 実行レポート（2026/09/16 18:46）
- 対象:
  - 29 `templates/inventory_order_alert/list.html`: 判定期間セレクタ `#ioa-evaluation-period` をアクション行の先頭に、「判定条件」パネル（`.ioa-flow-selector`、`#ioa-flow-axis`、`#ioa-flow-period`）を撤去、流動区分フィルタをフィルタパネルへ移動、流動区分セルを `ioa-flow-cell` 構成（区分 / 入荷実績なしバッジ / 状況 / 推奨アクション / 責任部署。通常流動品は空）に、件数サマリを新区分名に、判定ルールダイアログに 状況 / 推奨アクション 列（`data-status-template` で `{period}` を JS が置換）、詳細ダイアログに 状況 / 推奨アクション / 判定期間。行に `data-flow-status` 等を追加。JS キャッシュバスター `20260916-single-flow-view`
  - 30 `static/js/inventory-order-alert-list-client.js`: `flowAxis` / `flowPeriod` / `resolveFlowPeriod` / `flowAxes` / `flowPeriods` を撤去し `state.periodKey`（Y1/Y3/Y5）と `payload.evaluationPeriods` / `defaultPeriodKey` に。`renderStatusText()`（テンプレート置換のみ）、`renderFlowCell()`、件数キー `lowFlowNoIncoming` / `lowFlowNoShipment`、URL 同期は `period`（年数）のみ（残っていた `axis` は削除）。判定ルールダイアログの `{period}` 置換も `syncFlowSelector()` で行う。公開 API に `getFlowStatus` / `getRecommendedAction` / `getEvaluationPeriodLabel` を追加し `getFlowConditionLabel` を削除
  - 31 `static/js/inventory-order-alert-list.js`: 詳細ダイアログに 状況 / 推奨アクション / 判定期間 を描画（listClient がなければ行の `data-*` を使う）、保存後の件数ラベルを新区分名に
  - 32 `static/css/app.css`: `.alert-row--low-flow-no-incoming` / `--low-flow-no-shipment` へ改称（色は旧区分を継承）、`.ioa-flow-selector` 系を削除、`.ioa-evaluation-period-*`・`.ioa-flow-cell*`（`min-width: 22em`、`@media (max-width: 1100px)` で状況・責任部署を非表示）・`.ioa-no-incoming-badge` を追加、判定ルールダイアログを 900px に広げ 6 列の幅を設定。`templates/base.html` の CSS キャッシュバスター更新
  - 33 `templates/portal/dashboard.html`: 帯の区分名を新称に（条件ラベルは use case 由来の「判定期間 1年」）
  - 34/36 `tests/test_inventory_order_alert_views.py`: 旧断言を置換し X-001〜X-012 を追加（4 区分の行を投入する `_store_four_quadrants()`）。既存の `_dormant_stock_row` の最終出荷日を 2025/02/01 にして 1 年判定で在庫死蔵品になるようにした
  - 35 `tests/test_inventory_order_alert_list_js.py`: 判定軸依存の断言を X-017〜X-019 に置換、CSS 幅・クラス名の断言を追随
  - 併せて改修した既存テスト（旧定数・旧キーの機械置換）: `test_inventory_order_alert_row_template.py`、`test_table_display.py`、`test_snapshot_patch.py`、`test_mari_stock_edge_cases.py`、`test_shipment_trend_edge_cases.py`、`test_summary_api.py`（`axis` を外し `period` 年数で断言、旧 URL の無視も追加）、`test_summary_storage.py`。`models.py` / `export_csv.py` のコメント中の旧称も改めた（タスク 19 の走査対象のため）
- 結果: `pytest application/inventory_order_alert application/portal config` **1196 passed**、`manage.py check` 問題なし、`node --check` 両 JS 通過。タスク 19 の走査も Green
- 懸念事項: JS は `node --check`（構文）とソース断言のみで、ブラウザでの動作確認は未実施。判定期間切替時のセル再描画・判定ルールダイアログの `{period}` 置換・詳細ダイアログの状況表示は実機で確認が必要（タスク 40 で報告）
- 改善事項: 判定ルールダイアログの状況列は `{period}` を置換して選択中の判定期間で読めるようにした（設計は「そのまま」も許容していたが、セルと同じ文言で読める方が分かりやすい）
- 設計の Good ポイント: サーバ描画（初期表示・CSV）とクライアント描画（判定期間切替）が同じ `statusTemplate` を使うため、文言の二重管理がない
- チーム共有ポイント: 行の `data-flow-status` / `data-recommended-action` / `data-responsible-department` は listClient が無い環境（JS 無効・初期化失敗）でも詳細ダイアログが最低限描けるためのフォールバック
--------------------
### タスク37〜40 実行レポート（2026/09/16 19:00）
- 対象:
  - 37 `docs/在庫発注アラート_機能仕様書.md`: §2.2.1 受入基準・§2.3 REQ-F-004/011/012・§3・§4.1.3・§4.1.4・§4.1.5（アクション行に判定期間セレクタ、判定条件セレクタの撤去を「改訂前」注記に、流動区分セルの構成）・§4.1.6・§4.1.7・§4.2・§5.2・§6.2（状況テンプレート・推奨アクション・判定期間表・旧称の写像・代表例）・§6.3・§8.1・§8.3・§10.5・§13 Q4・改訂履歴 5.0。旧称・判定軸は「改訂前」注記と改訂履歴以外に残っていない
  - 38 `docs/spec/02_low-flow-visibility/requirements.md`: REQ-LFV-F-002・F-003・F-018 と UC-03 に置換注記（本文は残す）、変更履歴を追記
  - 39 `Document/本番環境デプロイ手順.md`: §11.1「アプリ固有のリリース後作業」を新設し、確認状態リセットの手順（設定画面 → `POST /api/inventory-order-alert/confirmation/reset`、メモ履歴は残る）と利用者への周知文（区分改称・帯の件数基準・確認記録リセット・旧 URL の扱い）、改訂履歴 2.5
  - 40 検証: `pytest`（リポジトリ全体）**1,825 passed**、`manage.py check` 問題なし、`node --check` 両 JS 通過。実データ（2026/09/07 取込、2,298 行）で旧 3 か月 → 新 1 年の件数変化（入荷なし 250→293、死蔵 903→613、出荷なし 111→93、通常 1,034→1,299）と 96160-00500 のセル内容を確認し、`04_shipment-history-chart/DECISIONS.md` に **ステージ17** として記録。`git status` に意図しない変更なし
- 結果: 第 1 段階（タスク 1〜40）完了
- 懸念事項: **ブラウザでの目視確認は未実施**（判定期間切替の追随・狭幅表示・行背景色）。**API 応答の `counts` キー改称**（`supplyRisk` → `lowFlowNoIncoming` 等）はポータル外の呼び出し元があれば追随が要る。開発 DB に確認記録が 0 件のため、確認状態リセットの効果は本番で初めて観測される
- 改善事項: 機能仕様書の §6.2 は用語集 S-203 の表を状況テンプレート付きで再掲する形にし、文言の正を用語集 → 仕様書 → `recommended_action.py` の順で追えるようにした
- 設計の Good ポイント: 移行措置（確認状態リセット）を既存の設定画面機能で賄い、新規のマイグレーション・コードを増やしていない
- チーム共有ポイント: 第 2 段階（タスク 41〜68）は本レポートをユーザーが確認してから着手する（tasks.md 方針）。着手時は `test-design.md §3.1` の ROW_100 / ROW_104 / ROW_137_A / ROW_137_B を先に用意する
--------------------
### タスク41〜59 実行レポート（2026/09/17 08:35）
- 対象:
  - 41/42 `tests/test_unconfirmed_order_trend.py`（新規、D-070〜075、8 件）→ `domain/value_objects/unconfirmed_order_trend.py`（新規。`build_unconfirmed_order_trend` と、SQL の `:window_end` にも使う `unconfirmed_order_window_end`）
  - 43/44 `tests/test_reconciliation_unit.py`（新規、D-080〜087、11 件）→ `domain/value_objects/reconciliation_unit.py`（新規。Union-Find。**組が空の行は連結しない**点で 04 の JS 実装と異なる（JS は `P:|` キーで全部つながる）。JS は §3.2 どおり当面残す）
  - 45/46 `tests/test_demand_forecast.py`（新規、D-090〜109、24 件）→ `domain/value_objects/demand_forecast.py`（新規）
  - 47/48 `tests/test_table_display.py`（D-059 を追加）→ `domain/value_objects/table_display.py`（`SORT_ONLY_COLUMNS = (("months_of_stock", "在庫月数"),)`、`NULLS_LAST_COLUMNS`、`_sort_key` で昇順・降順とも空を末尾に）。tasks.md は `list_filter.py` としていたがソートの実装は `table_display.py`
  - 49/50 `tests/test_list_client_data.py` → `list_client_data.py`（行に `internalItemCd` / `unconfirmedOrderTrend` / `reconciliationUnitKey` / `demandForecast{basis, currentMonthRemaining, monthly, monthlyAverage, monthsOfStock, stockoutForecastMonth}`、ペイロードに `sortOnlyColumns`）
  - 51/52 `tests/test_export_csv.py`（D-061）→ `export_csv.py`（末尾 4 列。既存 24 列の順序は不変、確認関連 5 列の連続も維持）
  - 53 `tests/test_import_stock_usecase.py`（新規、A-001〜002、5 件）
  - 54 `domain/repositories/ports.py`（`EnrichRows` 型と `StockImporter.enrich_rows`）
  - 55 `use_cases/import_stock.py`（`enrich_rows=attach_demand_forecast`）。併せて `domain/value_objects/summary.py` に `StockImportInfo.aggregation_warning` を追加し、`use_cases/list_page.py` が取込結果メッセージに追記
  - 56/57 `tests/test_unconfirmed_order_query.py`（新規、I-001〜002・006、6 件）→ `infrastructure/oracle/summary_queries.py`（`fetch_unconfirmed_orders`、`OracleQueryError` を警告に変える `fetch_unconfirmed_orders_or_warn`）
  - 58/59 `tests/test_build_summary_rows.py`（I-003〜006、A-001 の順序）→ `summary_queries.build_summary_rows`（`internal_item_cd` / `unconfirmed_order_trend` を付与、`warnings` 引数）、`infrastructure/oracle/list_rows_builder.py`（`warnings` を通す）、`infrastructure/oracle/summary_aggregation.py`（集計 → `enrich_rows` → 保存、戻り値を (エラー, 件数, 警告) の 3 つ組に）、`infrastructure/persistence/slims_stock_repository.py`（`enrich_rows` を受け `aggregation_warning` を返す）。既存の `test_import_slims_stock_csv_command.py` のモック戻り値を 3 つ組に
- 結果: すべて Green（`test_clean_architecture` 含む）
- 懸念事項:
  - **設計からの逸脱（要確認）**: I-006 は「`aggregation_error` に内示取得失敗を追記」としていたが、`aggregation_error` が空でないと一覧が「集計に失敗しました」扱い（`has_list_data = False`、CSV 出力不可、帯はエラー）になり「取込を失敗させない」と矛盾する。**警告は `StockImportInfo.aggregation_warning`（新設）で返し、取込結果メッセージにだけ出す**方式にした。スナップショットには警告を保存しない（次回取込で解消される一時的な情報のため）
  - **在庫切れ予測月の規則**: design §4.6「初めて負になる月」を厳密に適用した（残 0 はまだ在庫あり）。test-design D-100 の期待値「2027-06」は計算が合わない（1,000 ÷ 100 で 2027/07 に 0、2027/08 に負）ため **2027-08** で固定した。D-102（在庫 0 で需要あり）は「在庫 0 以下なら当月」を別規則として置いた
  - **実績ベースの `monthly`**: 設計は翌月〜翌々々月を内示の値としているが、実績ベースでは内示がないため **月平均を丸めた値を 3 か月に置く**（在庫切れ予測月の計算で 3 か月間だけ需要 0 になるのを避けるため）
  - **内作品番が解決できない行**: test-design I-004 は `""` を期待していたが、既存の `resolve_internal_item_cd` は得意先品番で代替する規則のため、それを維持（内示は突合しないので全 0 になる点は同じ）
  - 96160-00500 の照合単位は在庫月数 150.6 か月 > 上限 120 か月のため在庫切れ予測月は `None`（「十分」）になる。test-design §3.3 の「在庫月数 ≒ 150」と整合
- 改善事項: `months_of_stock` は一覧の列にせず **ソート専用項目**（`sortOnlyColumns`）にした（一覧を横に広げず、緊急度はセル内に出す設計 §6.3 を守るため）。JS の並び替えダイアログはタスク 61 で追随
- 設計の Good ポイント: `ReconciliationUnits.rows_of()` と `attach_demand_forecast` の単位キャッシュにより、2,298 行・1,994 単位でも単位ごとの計算は 1 回
- チーム共有ポイント: 取込ポートの `enrich_rows` は「集計 → 後処理 → 保存」を infrastructure の構造を壊さずに実現する接点。将来の行加工（例: 発注推奨）も同じ経路で足せる
--------------------
### タスク60〜68 実行レポート（2026/09/17 08:57）
- 対象:
  - 60 `templates/inventory_order_alert/list.html`: セルに `ioa-flow-urgency`（サーバ描画。JS と同じ文言規則）、行に `data-demand-forecast-basis` / `data-months-of-stock` / `data-stockout-forecast-month`、詳細ダイアログに `ioa-detail-demand-forecast-section`（推定在庫推移とメモの間）。キャッシュバスター `20260917-demand-forecast`（`base.html` の CSS も）
  - 61 `static/js/inventory-order-alert-list-client.js`: `urgencyTextOf()`（basis なし・在庫月数なしは非表示、予測月なしは「十分」）、`monthsOfStockSortValue()`（方向を見て空を末尾に）、`sortOnlyColumns` を並び替えダイアログの選択肢に合流、`getDemandForecast` / `getUnconfirmedOrderTrend` / `getUrgencyText`
  - 62 `static/js/inventory-order-alert-list.js`: `renderDemandForecast()`（算出根拠・月別内示・月平均・在庫月数・在庫切れ予測月・照合単位の在庫内訳。`parseAnchorQty` を流用）
  - 63 `static/css/app.css`: `.ioa-flow-urgency`、需要予測区分の dl 幅
  - 64/65 `tests/test_inventory_order_alert_views.py`（X-013〜016、在庫月数ソート）、`tests/test_inventory_order_alert_list_js.py`（X-020、緊急度・需要予測区分の断言）。既存の取込モック（`test_stock_storage.py` 等）を 3 つ組の戻り値に追随
  - 66 `docs/在庫発注アラート_機能仕様書.md`: §4.1.5（緊急度・在庫月数ソート）・§4.1.6（需要予測区分、6 区分）・§6.2（需要予測の規則表・実データ）・§7.1.5（内示受注の取得）・§7.2・§8.3（28 列）・§10.5・改訂履歴 5.1
  - 67 実データ検証（Oracle 読み取りのみ）→ `04_shipment-history-chart/DECISIONS.md` ステージ18。96160-00500 は 内示 (224, 216, 197)・在庫 31,970・150.6 か月で test-design §3.3 と一致。内示取得 4.33 秒（R-6 の 5 秒以内）
  - 68 `pytest` 全体 **1,904 passed**、`manage.py check` 問題なし、`node --check` 通過、`git status` に意図しない変更なし
- 結果: 第 2 段階（タスク 41〜68）完了。05_single-flow-view の実装は全タスク完了
- 懸念事項: ブラウザ目視は未実施。開発・本番のスナップショットは旧形式のままで、**SLIMS CSV を再取込するまで緊急度・需要予測は表示されない**（旧スナップショット互換で画面は動く）。04 の JS 照合単位が仕入先未解決の行を 1 単位にまとめている疑い（DECISIONS 要確認 #7）。配信ペイロードは設計見積り（100 バイト/行）より大きい約 500 バイト/行
- 改善事項: 緊急度の文言はサーバ（テンプレート）と JS の 2 か所にある。状況テンプレートのように domain 由来の 1 か所にまとめる余地がある
- 設計の Good ポイント: 需要予測は取込時に確定してスナップショットに持つため、一覧・CSV・詳細で同じ値を使い、表示時の計算がない
- チーム共有ポイント: 在庫月数の並び替えは URL `sort=months_of_stock&dir=asc` でも指定できる（空は末尾）。内示受注の数量単位（バラ数か箱数か）は未確認のため、在庫月数が桁違いの品番は単位の確認から
--------------------

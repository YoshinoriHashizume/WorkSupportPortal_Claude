# テスト設計書: 低流動品・在庫死蔵品の状況把握機能

文書ID: TEST-LOW-FLOW-VISIBILITY-2026-001
作成日: 2026/08/27
更新日: 2026/08/28
対応文書: `./design.md`（DESIGN-LOW-FLOW-VISIBILITY-2026-001） / `./requirements.md`（REQ-LOW-FLOW-VISIBILITY-2026-001）
テスト戦略reference: test-strategy version 1.1（updated 2026-04-25）
テストフレームワークreference: django-pytest version 1.0（updated 2026-04-11）

---

## 1. テスト戦略

### 1.1 テスト対象のスコープ

#### テスト対象

| 分類 | 対象 | 設計書の該当箇所 |
|------|------|----------------|
| 新規ドメイン | 判定軸・判定期間・流動区分・入荷実績なし・判定条件の組（VO） | §4.2 |
| 新規ドメイン | 流動区分の判定関数群（純関数） | §4.4 |
| 新規ドメイン | 判定ルール凡例（`flow_quadrant_rules.py`） | §6.6.5 |
| 置換ドメイン | 行への区分付与・フィルタ・ソート・件数集計・表示・CSV 列・クライアントペイロード・クエリ解析 | §7.2 |
| 置換ユースケース | 一覧表示 / CSV 出力 / メニュー帯 / 確認保存 / スナップショット部分更新 / サマリ API | §7.2 |
| 置換インフラ | 集計スナップショット読込・確認記録・設定・件数カラムの詰め替え | §5.1 / §5.2 / §7.2 |
| 置換インターフェース | 一覧画面 / CSV / 設定画面 / API / テンプレート / JavaScript / CSS | §6 / §7.2 |
| 撤去の検証 | 旧アラートレベル一式の残存 0 件（R-1） | §7.3 / §9 R-1 |

#### テスト対象外

| 対象 | 理由 |
|------|------|
| Oracle 集計 SQL（`summary_aggregation` の SQL 本体） | 本要件で SQL を変更しない（requirements §6.2）。既存テストの回帰確認のみ |
| SLIMS 在庫 CSV の取込処理 | 変更なし。既存テストを維持 |
| 確認メモ（`InventoryOrderAlertConfirmationMemoEntry`） | 変更なし（REQ-LFV-F-014） |
| 認可基盤そのもの | 既存を踏襲（REQ-LFV-NF-003）。一覧・CSV・帯のアクセス制御が既存どおり効くことのみ確認 |
| ブラウザ実操作の E2E（Selenium 等） | 本プロジェクトに E2E 基盤がない。JavaScript は「ソース文字列アサーション」で代替（§1.2） |
| 契約情報（補給供給責任年数）・他入先情報を用いた判定 | 要件スコープ外 |

### 1.2 テストレイヤーの方針

| レイヤー | テスト種別 | テスト方針 | DB依存 |
|---------|----------|----------|--------|
| Domain（VO・判定関数・ファーストクラスコレクション） | 単体 | 実物のみで検証。モック不使用。**最優先・最多数** | なし |
| Use Cases | 単体（結合寄り） | リポジトリ（Callable ポート）は関数モックに差し替え、**ドメインモデルは実物**を通す | なし |
| Infrastructure（persistence） | 結合 | 実際のテスト DB に対して検証。`@pytest.mark.django_db` を付ける | あり |
| Infrastructure（oracle） | 単体 | `conftest.py` が `ORACLE_USE_MOCK=true` を既定にするためモック接続で検証 | なし |
| Interfaces（views / urls / templatetags） | 結合 | Django テストクライアントで HTTP レベルの検証。`@pytest.mark.django_db` | あり |
| Interfaces（JavaScript） | 単体 | **ソース文字列アサーション**（`*.js` を読み込み、必要な識別子の存在／旧識別子の不在を検証）。既存 `test_inventory_order_alert_list_js.py` の方式を踏襲 | なし |
| Interfaces（CSS） | 単体 | `static/css/app.css` を読み込み、セレクタと配色値を検証。他アプリの前例（`portal/tests/test_portal_list_filter_css.py`）に倣う | なし |

#### テストコードの配置・書き方（reference からの逸脱を明示）

`django-pytest.md` は `tests/domain/` `tests/use_cases/` 等のサブディレクトリ配置、`class TestXxx:` 形式、
全テストクラス・メソッドへの docstring を規定している。しかし `application/inventory_order_alert/tests/` の
既存 39 ファイルはすべて **フラット配置・モジュールレベル関数・docstring なし** である。

本機能では **既存慣習に合わせる**（周囲のコードと書き方を揃えることを優先する）。
サブディレクトリを新設すると同一アプリ内に 2 方式が混在し、テストの探索性がかえって落ちるためである。

| 項目 | reference の規定 | 本機能の採用 | 判断 |
|------|----------------|------------|------|
| 配置 | `tests/{layer}/` サブディレクトリ | `tests/` 直下フラット | **逸脱**（既存慣習優先） |
| 形式 | `class TestXxx:` | モジュールレベル関数 | **逸脱**（既存慣習優先） |
| docstring | 全クラス・全メソッド必須 | 付けない。ただし**意図が名前から読み取れない境界値テストには 1 行コメントを付す** | **逸脱**（既存慣習優先） |
| 命名 | `test_{何を}_{条件}_{期待結果}` | 同左を厳守 | **採用** |
| 構造 | Arrange-Act-Assert | 同左 | **採用** |
| `@pytest.mark.django_db` | Infrastructure / Interfaces のみ | 同左 | **採用** |

この逸脱はテスト設計レビュー（test-design-review-l1）で指摘され得るため、意図的な判断として本節に記録する。

### 1.3 テスト優先順位

| 優先度 | 対象 | 理由 |
|:---:|------|------|
| **P1** | `flow_quadrant.py` の判定関数・VO（§4.2 / §4.4） | 本機能の中核。4 象限の分岐と暦月境界を誤ると全画面が誤表示になる |
| **P1** | `normalize_flow_quadrant` の旧ラベル互換写像（§5.2） | 既存確認記録の読み込み失敗は一覧の描画停止に直結する（NF-002） |
| **P1** | `is_flow_escalated` と確認記録の差し戻し（§5.2） | 誤差し戻しは現場の手戻りを生む |
| **P2** | 行への区分付与・フィルタ・ソート・件数集計（§7.2 domain） | 一覧の見え方を決める |
| **P2** | ユースケース 6 種（§7.2 use_cases） | 画面・CSV・帯の出力契約 |
| **P3** | Infrastructure（件数カラムの詰め替え・確認記録の読み書き） | 既存データとの連続性 |
| **P3** | Interfaces（views / URL フォールバック / CSV / テンプレート） | 異常系フォールバックの担保 |
| **P4** | JavaScript / CSS のソースアサーション、撤去残存チェック | 回帰防止の網 |

Domain 層から着手し、Domain のテストがすべて緑になるまで上位レイヤーに進まない。

### 1.4 TDD方針

CLAUDE.md §2 のとおり Phase 5 は TDD で進める（REQ-LFV-NF-006）。

```
1. テストケース表の 1 行を選び、失敗するテストを書く（Red）
   → pytest application/inventory_order_alert/tests/test_xxx.py::test_yyy -x
2. テストを通す最小限の実装を書く（Green）
3. アプリ全体のテストで回帰を確認する（Refactor）
   → pytest application/inventory_order_alert/
```

- **旧実装の撤去は「削除してから直す」順**で進める。`alert_level.py` を先に削除し、
  `ImportError` を未修正箇所の検知手段として使う（設計書 §9 R-1）。
  この期間はアプリ全体のテストが赤になるため、**Red の範囲を tasks.md のタスク単位で区切る**。
- 撤去タスクの完了条件は `grep -rn "alert_level\|alertLevel\|alert_only\|alertOnly" application/inventory_order_alert static templates scripts` の残存 0 件（X-022 で自動化する）。

---

## 2. テストケース一覧

優先度は §1.3 の P1〜P4 に対応する。

### 2.1 Domain層テスト

#### バリューオブジェクト: `EvaluationPeriod` / `EvaluationPeriods`（V-211 判定期間）

テストファイル: `tests/test_flow_quadrant.py`

| # | テストケース | 入力 | 期待結果 | 対応REQ-ID | 優先度 |
|---|------------|------|---------|-----------|--------|
| D-001 | `test_evaluation_period_months_for_low_flow_axis_equals_value` | `EvaluationPeriod("low_flow", 3)` | `months == 3` | F-003 | P1 |
| D-002 | `test_evaluation_period_months_for_dormant_axis_multiplies_by_twelve` | `EvaluationPeriod("dormant", 5)` | `months == 60` | F-003 | P1 |
| D-003 | `test_evaluation_period_key_prefixes_axis_initial` | 低流動3 / 死蔵1 | `"L3"` / `"D1"` | F-003 | P1 |
| D-004 | `test_evaluation_period_label_uses_month_unit_for_low_flow_axis` | 低流動6 | `"6か月"` | F-003 / NF-004 | P1 |
| D-005 | `test_evaluation_period_label_uses_year_unit_for_dormant_axis` | 死蔵2 | `"2年"` | F-003 / NF-004 | P1 |
| D-006 | `test_evaluation_periods_for_low_flow_axis_returns_one_three_six_in_order` | `for_axis("low_flow")` | `(1, 3, 6)` の順 | F-003 | P1 |
| D-007 | `test_evaluation_periods_for_dormant_axis_returns_one_two_five_in_order` | `for_axis("dormant")` | `(1, 2, 5)` の順 | F-003 | P1 |
| D-008 | `test_evaluation_periods_for_unknown_axis_returns_empty` | `for_axis("foo")` | `()` | F-017 #5 | P1 |
| D-009 | `test_evaluation_periods_default_for_low_flow_axis_is_three_months` | `default_for_axis("low_flow")` | 低流動3か月 | F-003 | P1 |
| D-010 | `test_evaluation_periods_default_for_dormant_axis_is_one_year` | `default_for_axis("dormant")` | 死蔵1年 | F-003 | P1 |
| D-011 | `test_evaluation_periods_default_for_unknown_axis_falls_back_to_low_flow_three_months` | `default_for_axis("foo")` | 低流動3か月 | F-017 #5 | P1 |
| D-012 | `test_evaluation_periods_find_returns_period_for_known_key` | `find("D5")` | 死蔵5年 | F-003 | P1 |
| D-013 | `test_evaluation_periods_find_returns_none_for_undefined_key` | `find("L2")` | `None` | F-017 #6 | P1 |
| D-014 | `test_evaluation_periods_find_returns_none_for_empty_key` | `find("")` | `None` | F-017 #5 | P1 |
| D-015 | `test_evaluation_periods_contains_exactly_six_fixed_values` | `len(EVALUATION_PERIODS)` / `list(...)` | `6` / `L1,L3,L6,D1,D2,D5` の順 | F-003 | P1 |
| D-016 | `test_evaluation_period_with_same_axis_and_value_are_equal` | 同値2個 | `==` が真、`set` で1個 | F-003 | P2 |
| D-017 | `test_evaluation_period_is_immutable` | `period.value = 6` | `FrozenInstanceError` | NF-005 | P2 |

#### バリューオブジェクト: `FlowAxis`（V-210 判定軸）

| # | テストケース | 入力 | 期待結果 | 対応REQ-ID | 優先度 |
|---|------------|------|---------|-----------|--------|
| D-018 | `test_flow_axis_labels_map_to_ubiquitous_language_terms` | `FLOW_AXIS_LABELS` | `low_flow→"低流動判定軸"` / `dormant→"死蔵判定軸"` | NF-004 | P1 |
| D-019 | `test_default_flow_axis_is_low_flow` | `DEFAULT_FLOW_AXIS` | `"low_flow"` | F-002 | P1 |

#### バリューオブジェクト: `FlowSelection`（判定条件の組）

| # | テストケース | 入力 | 期待結果 | 対応REQ-ID | 優先度 |
|---|------------|------|---------|-----------|--------|
| D-020 | `test_flow_selection_exposes_axis_key_and_labels` | `FlowSelection(EvaluationPeriod("low_flow", 3))` | `axis=="low_flow"` / `key=="L3"` / `axis_label=="低流動判定軸"` / `period_label=="3か月"` | F-002 / F-004 | P1 |
| D-021 | `test_reference_flow_selection_is_low_flow_axis_three_months` | `REFERENCE_FLOW_SELECTION` | 低流動判定軸・3か月 | F-013 / F-014 | P1 |
| D-022 | `test_flow_selection_with_same_period_are_equal` | 同値2個 | `==` が真 | F-002 | P2 |

#### バリューオブジェクト: `FlowQuadrant`（S-203 流動区分）

| # | テストケース | 入力 | 期待結果 | 対応REQ-ID | 優先度 |
|---|------------|------|---------|-----------|--------|
| D-023 | `test_flow_quadrant_keys_map_label_to_ascii_key` | `FLOW_QUADRANT_KEYS` | 供給リスク品→`supply-risk` / 在庫死蔵品→`dormant-stock` / 在庫過剰リスク品→`excess-stock-risk` / 通常流動品→`normal-flow` | F-005 / NF-004 | P1 |
| D-024 | `test_flow_quadrant_labels_are_inverse_of_keys` | 両 dict | 相互に逆写像、各4件 | NF-004 | P1 |
| D-025 | `test_flow_quadrants_are_ordered_by_urgency` | `FLOW_QUADRANTS` | 供給リスク品→在庫死蔵品→在庫過剰リスク品→通常流動品 | F-010 | P1 |
| D-026 | `test_flow_quadrant_sort_rank_assigns_zero_to_supply_risk` | 4ラベル | `0, 1, 2, 3` | F-010 | P1 |
| D-027 | `test_flow_quadrant_labels_do_not_contain_prohibited_terms` | 4ラベル + 補助テキスト | 「未流動品」「デッドストック」「不良在庫」「象限」を含まない | NF-004 | P2 |
| D-028 | `test_longest_flow_quadrant_label_fits_confirmation_field_length` | 最長ラベル | 文字数 ≤ 40 | F-014 | P3 |

#### ドメインサービス: `is_within_evaluation_period`（V-212 期間内入荷 / V-213 期間内出荷）

**基準日 `as_of_date` は BOM 基準日（V-209）**であり、本日付ではない（requirements §6.2）。

| # | テストケース | 入力（`as_of_date` / `months` / `target`） | 期待結果 | 対応REQ-ID | 優先度 |
|---|------------|------|---------|-----------|--------|
| D-029 | `test_is_within_evaluation_period_returns_false_for_missing_date` | 2026/8/27 / 3 / `None` | `False` | F-001 / F-017 #1 | P1 |
| D-030 | `test_is_within_evaluation_period_returns_true_on_exact_boundary_date` | 2026/8/27 / 3 / **2026/5/27** | `True`（`>=` 比較） | F-001 | P1 |
| D-031 | `test_is_within_evaluation_period_returns_false_one_day_before_boundary` | 2026/8/27 / 3 / **2026/5/26** | `False` | F-001 | P1 |
| D-032 | `test_is_within_evaluation_period_returns_true_for_bom_reference_date_itself` | 2026/8/27 / 3 / 2026/8/27 | `True` | F-001 | P1 |
| D-033 | `test_is_within_evaluation_period_returns_true_for_future_date` | 2026/8/27 / 3 / 2026/12/1 | `True`（データ不整合として除外しない） | F-017 #3 | P1 |
| D-034 | `test_is_within_evaluation_period_rounds_month_end_to_shorter_month` | 2026/8/31 / 6 / **2026/2/28** | `True`（境界日は 2026/2/28） | F-001 / F-017 | P1 |
| D-035 | `test_is_within_evaluation_period_excludes_day_before_rounded_month_end` | 2026/8/31 / 6 / 2026/2/27 | `False` | F-001 | P1 |
| D-036 | `test_is_within_evaluation_period_rounds_month_end_to_leap_day` | 2024/8/31 / 6 / **2024/2/29** | `True`（うるう年） | F-001 | P1 |
| D-037 | `test_is_within_evaluation_period_handles_one_month_minimum` | 2026/8/27 / 1 / 2026/7/27 | `True` | F-003（最小） | P1 |
| D-038 | `test_is_within_evaluation_period_handles_sixty_months_for_five_years` | 2026/8/27 / 60 / **2021/8/27** | `True` | F-003（最大） | P1 |
| D-039 | `test_is_within_evaluation_period_excludes_day_before_five_year_boundary` | 2026/8/27 / 60 / 2021/8/26 | `False` | F-003（最大-1） | P1 |
| D-040 | `test_is_within_evaluation_period_crosses_year_boundary` | 2026/1/15 / 3 / 2025/10/15 | `True` | F-001 | P2 |

#### ドメインサービス: `resolve_flow_quadrant`（REQ-LFV-F-001）

`as_of_date = 2026/8/27`、`selection = 低流動判定軸・3か月`（境界日 2026/5/27）を基本とする。

| # | テストケース | 入力（最終入荷日 / 最終出荷日） | 期待結果 | 対応REQ-ID | 優先度 |
|---|------------|------|---------|-----------|--------|
| D-041 | `test_resolve_flow_quadrant_returns_supply_risk_when_incoming_absent_and_shipment_present` | 2026/1/10 / 2026/8/1 | 供給リスク品 | F-001 | P1 |
| D-042 | `test_resolve_flow_quadrant_returns_dormant_stock_when_both_absent` | 2026/1/10 / 2026/1/20 | 在庫死蔵品 | F-001 | P1 |
| D-043 | `test_resolve_flow_quadrant_returns_excess_stock_risk_when_incoming_present_and_shipment_absent` | 2026/8/1 / 2026/1/20 | 在庫過剰リスク品 | F-001 | P1 |
| D-044 | `test_resolve_flow_quadrant_returns_normal_flow_when_both_present` | 2026/8/1 / 2026/8/10 | 通常流動品 | F-001 | P1 |
| D-045 | `test_resolve_flow_quadrant_returns_dormant_stock_when_both_dates_are_none` | `None` / `None` | 在庫死蔵品 | F-017 #1 | P1 |
| D-046 | `test_resolve_flow_quadrant_returns_supply_risk_when_incoming_date_is_none_and_shipment_recent` | `None` / 2026/8/1 | 供給リスク品 | F-017 #2 | P1 |
| D-047 | `test_resolve_flow_quadrant_returns_dormant_stock_when_shipment_date_is_none_and_incoming_old` | 2026/1/10 / `None` | 在庫死蔵品 | F-017 #1 | P1 |
| D-048 | `test_resolve_flow_quadrant_returns_excess_stock_risk_when_shipment_date_is_none_and_incoming_recent` | 2026/8/1 / `None` | 在庫過剰リスク品 | F-001 | P1 |
| D-049 | `test_resolve_flow_quadrant_classifies_boundary_dates_as_within_period` | 2026/5/27 / 2026/5/27 | 通常流動品 | F-001 | P1 |
| D-050 | `test_resolve_flow_quadrant_widening_period_changes_dormant_stock_to_normal_flow` | 2026/4/1 / 2026/4/1、低流動1か月→6か月 | 在庫死蔵品 → 通常流動品 | F-003 | P1 |
| D-051 | `test_resolve_flow_quadrant_differs_between_low_flow_and_dormant_axis` | 2025/1/10 / 2025/1/10、低流動3か月 / 死蔵5年 | 在庫死蔵品 / 通常流動品 | F-002 | P1 |
| D-052 | `test_resolve_flow_quadrant_ignores_stock_quantity` | 同一日付・在庫数の異なる 2 行 | 同一の流動区分（在庫数は引数に取らない） | F-001 | P1 |
| D-053 | `test_resolve_flow_quadrant_returns_one_of_four_labels_for_all_input_combinations` | 4通り × 6判定条件 | 常に 4 ラベルのいずれか。例外を送出しない | F-001 / §8 | P1 |

#### ドメインサービス: `resolve_flow_quadrant_matrix`（§3.2 案B）

| # | テストケース | 入力 | 期待結果 | 対応REQ-ID | 優先度 |
|---|------------|------|---------|-----------|--------|
| D-054 | `test_resolve_flow_quadrant_matrix_contains_all_six_period_keys` | 任意の日付 | キーが `L1,L3,L6,D1,D2,D5` の6件 | F-002 / F-003 | P1 |
| D-055 | `test_resolve_flow_quadrant_matrix_values_are_ascii_keys` | 任意の日付 | 値が `supply-risk` 等の ASCII キー（日本語ラベルではない） | F-005 / §6.2 | P1 |
| D-056 | `test_resolve_flow_quadrant_matrix_matches_resolve_flow_quadrant_for_every_period` | 4通り × 6条件 | `matrix[key]` が `resolve_flow_quadrant` の結果のキーと一致 | F-001 / F-016 | P1 |
| D-057 | `test_resolve_flow_quadrant_matrix_returns_dormant_stock_for_all_periods_when_dates_are_none` | `None` / `None` | 6キーすべて `dormant-stock` | F-017 #1 | P1 |

#### ドメインサービス: `is_no_incoming_record`（V-214 入荷実績なし）

| # | テストケース | 入力 | 期待結果 | 対応REQ-ID | 優先度 |
|---|------------|------|---------|-----------|--------|
| D-058 | `test_is_no_incoming_record_returns_true_when_last_incoming_date_is_none` | `None` | `True` | F-006 | P1 |
| D-059 | `test_is_no_incoming_record_returns_false_when_last_incoming_date_exists` | 2010/1/1（極端に古い） | `False` | F-006 | P1 |
| D-060 | `test_is_no_incoming_record_does_not_depend_on_evaluation_period` | 同一入力・判定期間 6 通り | 結果が変わらない（引数に判定期間を取らない） | F-006 | P1 |
| D-061 | `test_no_incoming_record_can_coexist_with_non_supply_risk_quadrant` | 入荷 `None` / 出荷 `None` | 流動区分は在庫死蔵品、`is_no_incoming_record` は `True` | F-006 | P1 |

#### ドメインサービス: `responsible_departments`（R-201 責任部署）

| # | テストケース | 入力 | 期待結果 | 対応REQ-ID | 優先度 |
|---|------------|------|---------|-----------|--------|
| D-062 | `test_responsible_departments_for_supply_risk_includes_three_groups` | 供給リスク品 | 調達G・営業G・生産管理 | F-007 | P2 |
| D-063 | `test_responsible_departments_for_dormant_stock_is_procurement_group` | 在庫死蔵品 | 調達G | F-007 | P2 |
| D-064 | `test_responsible_departments_for_excess_stock_risk_is_sales_group` | 在庫過剰リスク品 | 営業G | F-007 | P2 |
| D-065 | `test_responsible_departments_for_normal_flow_is_production_control` | 通常流動品 | 生産管理 | F-007 | P2 |
| D-066 | `test_responsible_departments_returns_empty_for_unknown_quadrant` | `"謎"` | `()`。例外を送出しない | §8 | P2 |

#### ドメインサービス: `normalize_flow_quadrant`（§5.2 旧ラベル互換写像）

| # | テストケース | 入力 | 期待結果 | 対応REQ-ID | 優先度 |
|---|------------|------|---------|-----------|--------|
| D-067 | `test_normalize_flow_quadrant_maps_legacy_critical_to_supply_risk` | `"重点"` | 供給リスク品 | F-014 / NF-002 | P1 |
| D-068 | `test_normalize_flow_quadrant_maps_legacy_warning_no_shipment_to_excess_stock_risk` | `"警告（出荷なし）"` | 在庫過剰リスク品 | F-014 / NF-002 | P1 |
| D-069 | `test_normalize_flow_quadrant_maps_legacy_warning_with_shipment_to_normal_flow` | `"警告（出荷あり）"` | 通常流動品 | F-014 / NF-002 | P1 |
| D-070 | `test_normalize_flow_quadrant_maps_legacy_no_alert_to_normal_flow` | `"アラート無し"` | 通常流動品（安全側） | F-014 / NF-002 | P1 |
| D-071 | `test_normalize_flow_quadrant_maps_legacy_aliases_from_alert_level_module` | `"なし"` / `"アラートなし"` / `"問題なし"` / `"警告（出荷）"` / `"警告（入荷）"` | 旧 `normalize_alert_level` の別名解決を引き継いだ結果 | F-014 / NF-002 | P1 |
| D-072 | `test_normalize_flow_quadrant_maps_empty_string_to_normal_flow` | `""` | 通常流動品 | F-017 #7 | P1 |
| D-073 | `test_normalize_flow_quadrant_maps_unknown_label_to_normal_flow` | `"謎のラベル"` | 通常流動品。例外を送出しない | F-017 #7 / §8 | P1 |
| D-074 | `test_normalize_flow_quadrant_keeps_current_quadrant_labels_unchanged` | 4ラベル | そのまま返る（冪等） | F-014 | P1 |
| D-075 | `test_normalize_flow_quadrant_trims_surrounding_whitespace` | `"  重点  "` | 供給リスク品 | F-017 #7 | P2 |
| D-076 | `test_normalize_flow_quadrant_accepts_none` | `None` | 通常流動品。例外を送出しない | F-017 #7 | P1 |

#### ドメインサービス: `is_flow_escalated`（REQ-LFV-F-014 深刻化判定）

| # | テストケース | 入力（確認時 → 現在） | 期待結果 | 対応REQ-ID | 優先度 |
|---|------------|------|---------|-----------|--------|
| D-077 | `test_is_flow_escalated_returns_true_when_rank_rises_from_normal_flow_to_supply_risk` | 通常流動品 → 供給リスク品 | `True` | F-014 | P1 |
| D-078 | `test_is_flow_escalated_returns_true_when_rank_rises_from_dormant_stock_to_supply_risk` | 在庫死蔵品 → 供給リスク品 | `True` | F-014 | P1 |
| D-079 | `test_is_flow_escalated_returns_true_when_rank_rises_from_excess_stock_risk_to_dormant_stock` | 在庫過剰リスク品 → 在庫死蔵品 | `True` | F-014 | P1 |
| D-080 | `test_is_flow_escalated_returns_false_when_rank_falls` | 供給リスク品 → 通常流動品 | `False` | F-014 | P1 |
| D-081 | `test_is_flow_escalated_returns_false_for_same_quadrant` | 供給リスク品 → 供給リスク品 | `False` | F-014 | P1 |
| D-082 | `test_is_flow_escalated_normalizes_legacy_previous_label_before_comparing` | `"重点"` → 通常流動品 | `False`（重点＝供給リスク品 rank0） | F-014 / NF-002 | P1 |
| D-083 | `test_is_flow_escalated_treats_unknown_previous_label_as_normal_flow` | `"謎"` → 供給リスク品 | `True`（未知は rank3 に倒れる） | F-017 #7 | P1 |

#### バリューオブジェクト: `flow_quadrant_rules.build_flow_quadrant_rule_rows`（§6.6.5）

テストファイル: `tests/test_flow_quadrant_rules.py`

| # | テストケース | 入力 | 期待結果 | 対応REQ-ID | 優先度 |
|---|------------|------|---------|-----------|--------|
| D-084 | `test_build_flow_quadrant_rule_rows_returns_four_rows_in_urgency_order` | なし | 4行、供給リスク品→在庫死蔵品→在庫過剰リスク品→通常流動品 | F-015 | P2 |
| D-085 | `test_build_flow_quadrant_rule_rows_includes_incoming_shipment_conditions` | なし | 各行に期間内入荷「なし/あり」・期間内出荷「なし/あり」 | F-015 | P2 |
| D-086 | `test_build_flow_quadrant_rule_rows_includes_responsible_departments` | なし | 各行に責任部署（S-203 表と一致） | F-007 / F-015 | P2 |
| D-087 | `test_build_flow_quadrant_rule_rows_takes_no_month_arguments` | 呼び出しシグネチャ | 引数なしで呼べる（月数に依存しない） | F-015 | P2 |

#### バリューオブジェクト: `list_rows.apply_flow_quadrants_to_rows`

テストファイル: `tests/test_list_summary.py`（既存を改修）

| # | テストケース | 入力 | 期待結果 | 対応REQ-ID | 優先度 |
|---|------------|------|---------|-----------|--------|
| D-088 | `test_apply_flow_quadrants_to_rows_adds_quadrant_key_matrix_and_flags` | 1行（日付あり） | `flow_quadrant` / `flow_quadrant_key` / `flow_quadrants`(6キー) / `no_incoming_record` / `responsible_department` が付く | F-001 / F-006 / F-007 | P2 |
| D-089 | `test_apply_flow_quadrants_to_rows_keeps_existing_row_keys` | 既存キーを持つ行 | 既存キーが失われない | NF-002 | P2 |
| D-090 | `test_apply_flow_quadrants_to_rows_treats_unparsable_date_as_out_of_period` | `last_incoming_date="2026/13/45"` | 行を落とさず、期間外（＝入荷なし）として判定 | F-017 / §8 | P2 |
| D-091 | `test_apply_flow_quadrants_to_rows_treats_empty_date_string_as_out_of_period` | `last_ship_date=""` | 期間外として判定。例外を送出しない | F-001 / F-017 #1 | P2 |
| D-092 | `test_apply_flow_quadrants_to_rows_returns_empty_list_for_no_rows` | `[]` | `[]`。例外を送出しない | F-017 #8 | P2 |
| D-093 | `test_apply_flow_quadrants_to_rows_does_not_change_row_count` | 100行 | 100行のまま（行の増減なし） | NF-001 | P2 |

#### バリューオブジェクト: `list_rows.filter_summary_rows`

| # | テストケース | 入力 | 期待結果 | 対応REQ-ID | 優先度 |
|---|------------|------|---------|-----------|--------|
| D-094 | `test_filter_summary_rows_keeps_only_selected_flow_quadrant` | `flow_quadrant="supply-risk"` | 供給リスク品の行のみ | F-009 | P2 |
| D-095 | `test_filter_summary_rows_with_attention_only_excludes_normal_flow` | `attention_only=True` | 通常流動品を除く3区分 | F-009 | P2 |
| D-096 | `test_filter_summary_rows_with_unknown_flow_quadrant_returns_all_rows` | `flow_quadrant="謎"` | 全件（空へフォールバック） | F-017 / §8 | P2 |
| D-097 | `test_filter_summary_rows_combines_flow_quadrant_with_confirmation_filter_as_and` | `flow_quadrant` + `unconfirmedOnly` | AND 条件で絞られる | F-009 | P2 |
| D-098 | `test_filter_summary_rows_combines_flow_quadrant_with_customer_code_filter_as_and` | `flow_quadrant` + 得意先コード | AND 条件で絞られる | F-009 | P2 |
| D-099 | `test_filter_summary_rows_does_not_accept_alert_only_keyword` | `alert_only=True` | `TypeError`（引数が撤去されている） | F-009 / R-1 | P3 |

#### バリューオブジェクト: `table_display` / `list_rows.sort_summary_rows`

テストファイル: `tests/test_table_display.py`（既存を改修）

| # | テストケース | 入力 | 期待結果 | 対応REQ-ID | 優先度 |
|---|------------|------|---------|-----------|--------|
| D-100 | `test_sortable_columns_first_entry_is_flow_quadrant` | `SORTABLE_COLUMNS[0]` | `("flow_quadrant", "流動区分")` | F-004 / F-010 | P2 |
| D-101 | `test_sortable_columns_include_responsible_department_after_stock_qty` | `SORTABLE_COLUMNS` | `stock_qty` の直後に `("responsible_department", "責任部署")` | F-007 | P2 |
| D-102 | `test_sortable_columns_do_not_include_alert_level` | `SORTABLE_COLUMNS` | `alert_level` を含まない | R-1 | P2 |
| D-103 | `test_default_sort_is_flow_quadrant_ascending` | `DEFAULT_SORT` / `DEFAULT_DIRECTION` | `"flow_quadrant"` / `"asc"` | F-010 | P2 |
| D-104 | `test_sort_summary_rows_orders_flow_quadrant_by_urgency_rank_ascending` | 4区分を逆順に並べた4行 | 供給リスク品→在庫死蔵品→在庫過剰リスク品→通常流動品 | F-010 | P2 |
| D-105 | `test_sort_summary_rows_orders_flow_quadrant_descending` | 同上・`desc` | 逆順 | F-010 | P2 |
| D-106 | `test_sort_summary_rows_uses_rank_not_label_collation` | 同上 | ラベルの文字コード順（在庫死蔵品が先頭になる順）ではないこと | F-010 | P2 |
| D-107 | `test_sort_summary_rows_supports_flow_quadrant_in_five_key_multi_sort` | 5条件（先頭が流動区分） | 5条件すべてが効く | F-010 | P2 |
| D-108 | `test_sort_summary_rows_orders_responsible_department_by_flow_quadrant_rank` | 4区分 | 流動区分ランクと同一の並び | F-007 / F-010 | P3 |

#### バリューオブジェクト: `row_counts.count_rows`

テストファイル: `tests/test_row_counts.py`（既存を改修）

| # | テストケース | 入力 | 期待結果 | 対応REQ-ID | 優先度 |
|---|------------|------|---------|-----------|--------|
| D-109 | `test_count_rows_counts_each_flow_quadrant_separately` | 4区分 各2行 | `supply_risk=2` / `dormant_stock=2` / `excess_stock_risk=2` / `normal_flow=2` | F-008 | P2 |
| D-110 | `test_count_rows_attention_equals_sum_of_three_risk_quadrants` | 同上 | `attention == 6` | F-008 / F-009 | P2 |
| D-111 | `test_count_rows_flow_quadrant_counts_sum_to_total` | 任意の行集合 | 4区分の和 == `total` | F-008 | P2 |
| D-112 | `test_count_rows_includes_confirmed_rows_in_flow_quadrant_counts` | 確認済み1・未確認1（同区分） | 区分件数 2、`confirmed=1` / `unconfirmed=1` | F-008 / F-013 | P2 |
| D-113 | `test_count_rows_left_and_right_totals_match` | 任意の行集合 | 区分4値の和 == 確認状態3値の和 | F-008 | P2 |
| D-114 | `test_count_rows_returns_all_zero_for_empty_rows` | `[]` | すべて0。例外を送出しない | F-017 #8 | P2 |
| D-115 | `test_count_rows_counts_unknown_flow_quadrant_as_normal_flow` | `flow_quadrant="謎"` の1行 | `normal_flow=1` | F-017 #7 | P2 |
| D-116 | `test_row_counts_has_no_critical_or_warning_fields` | `RowCounts()` | `critical` / `warning` / `warning_ship` / `warning_incoming` / `alert_none` / `alert` を持たない | R-1 | P3 |

#### バリューオブジェクト: `row_display`

テストファイル: `tests/test_row_display.py`（既存を改修）

| # | テストケース | 入力 | 期待結果 | 対応REQ-ID | 優先度 |
|---|------------|------|---------|-----------|--------|
| D-117 | `test_display_flow_quadrant_returns_label_for_row` | `{"flow_quadrant": "供給リスク品"}` | `"供給リスク品"` | F-004 | P2 |
| D-118 | `test_display_flow_quadrant_normalizes_legacy_label` | `{"flow_quadrant": "重点"}` | `"供給リスク品"` | F-014 | P2 |
| D-119 | `test_row_alert_class_returns_confirmed_class_for_confirmed_row` | 供給リスク品 + 確認済み | `"確認済"` | F-005 | P2 |
| D-120 | `test_row_alert_class_returns_in_progress_class_for_in_progress_row` | 供給リスク品 + 確認中 | `"確認中"` | F-005 | P2 |
| D-121 | `test_row_alert_class_returns_flow_quadrant_key_for_unconfirmed_row` | 供給リスク品 + 未確認 | `"supply-risk"` | F-005 | P2 |
| D-122 | `test_row_alert_class_returns_normal_flow_key_for_normal_flow_row` | 通常流動品 + 未確認 | `"normal-flow"` | F-005 | P2 |
| D-123 | `test_row_display_module_has_no_counts_toward_alert_summary` | モジュール属性 | `counts_toward_alert_summary` が存在しない | R-1 / §7.3 | P3 |

#### バリューオブジェクト: `list_query.parse_list_query`

テストファイル: `tests/test_list_query.py`（既存を改修）

| # | テストケース | 入力（クエリ） | 期待結果 | 対応REQ-ID | 優先度 |
|---|------------|------|---------|-----------|--------|
| D-124 | `test_parse_list_query_defaults_to_low_flow_axis_three_months` | `{}` | 低流動判定軸・3か月 | F-002 / F-003 | P2 |
| D-125 | `test_parse_list_query_accepts_dormant_axis_with_default_one_year` | `axis=dormant` | 死蔵判定軸・1年 | F-003 | P2 |
| D-126 | `test_parse_list_query_accepts_explicit_period_for_axis` | `axis=dormant&period=5` | 死蔵判定軸・5年 | F-003 | P2 |
| D-127 | `test_parse_list_query_falls_back_when_period_does_not_belong_to_axis` | `axis=dormant&period=3` | 死蔵判定軸・**1年** | F-017 #6 | P2 |
| D-128 | `test_parse_list_query_falls_back_when_axis_is_unknown` | `axis=foo&period=6` | 低流動判定軸・**3か月** | F-017 #5 | P2 |
| D-129 | `test_parse_list_query_falls_back_when_period_is_not_numeric` | `axis=low_flow&period=abc` | 低流動判定軸・3か月 | F-017 #5 | P2 |
| D-130 | `test_parse_list_query_falls_back_when_period_is_out_of_range` | `period=999` | 軸の既定値 | F-017 #5 | P2 |
| D-131 | `test_parse_list_query_accepts_flow_quadrant_key` | `flow_quadrant=supply-risk` | `flow_quadrant == "supply-risk"` | F-009 | P2 |
| D-132 | `test_parse_list_query_clears_unknown_flow_quadrant` | `flow_quadrant=謎` | `""`（全件） | F-017 / §8 | P2 |
| D-133 | `test_parse_list_query_accepts_attention_only_flag` | `attentionOnly=true` | `attention_only is True` | F-009 | P2 |
| D-134 | `test_list_query_has_no_alert_only_or_warning_month_fields` | `ListQuery()` | `alert_only` / `warning_shipment_months` / `warning_incoming_months` / `critical_enabled` を持たない | R-1 | P3 |

#### バリューオブジェクト: `list_filter.build_display_query_string`

テストファイル: `tests/test_list_filter.py`（既存を改修）

| # | テストケース | 入力 | 期待結果 | 対応REQ-ID | 優先度 |
|---|------------|------|---------|-----------|--------|
| D-135 | `test_build_display_query_string_includes_axis_period_and_flow_quadrant` | 死蔵5年・供給リスク品 | `axis=dormant` / `period=5` / `flow_quadrant=supply-risk` を含む | F-012 | P2 |
| D-136 | `test_build_display_query_string_keeps_selection_when_sort_changes` | ソート変更のリンク生成 | `axis` / `period` が保持される | F-012 | P2 |
| D-137 | `test_build_display_query_string_keeps_selection_when_page_changes` | ページ移動のリンク生成 | 同上 | F-012 | P2 |
| D-138 | `test_build_display_query_string_omits_empty_flow_quadrant` | `flow_quadrant=""` | `flow_quadrant` を含まない | F-012 | P3 |

#### バリューオブジェクト: `export_csv`（列定義）

テストファイル: `tests/test_export_csv.py`（既存を改修）

| # | テストケース | 入力 | 期待結果 | 対応REQ-ID | 優先度 |
|---|------------|------|---------|-----------|--------|
| D-139 | `test_export_columns_replace_alert_level_with_flow_quadrant` | `EXPORT_COLUMNS` | `("flow_quadrant", "流動区分")` を含み `alert_level` を含まない | F-011 | P2 |
| D-140 | `test_export_columns_include_flow_axis_and_evaluation_period` | 同上 | 「判定軸」「判定期間」列がある | F-011 | P2 |
| D-141 | `test_export_columns_include_no_incoming_record_and_responsible_department` | 同上 | 「入荷実績なし」「責任部署」列がある | F-006 / F-007 / F-011 | P2 |
| D-142 | `test_export_columns_keep_order_after_confirmation_status` | 同上 | `confirmation_status` 以降の既存列順が不変 | NF-002 | P2 |

#### バリューオブジェクト: `list_client_data.build_list_client_payload`

テストファイル: `tests/test_list_client_data.py`（既存を改修）

| # | テストケース | 入力 | 期待結果 | 対応REQ-ID | 優先度 |
|---|------------|------|---------|-----------|--------|
| D-143 | `test_build_list_client_payload_includes_flow_axes_and_periods` | 1行 | `flowAxes`(2件) / `flowPeriods`（`low_flow` 3件・`dormant` 3件） | F-002 / F-003 | P2 |
| D-144 | `test_build_list_client_payload_includes_flow_quadrant_labels_and_order` | 1行 | `flowQuadrantLabels`(4件) / `flowQuadrantOrder`（緊急度順） | F-004 / F-010 | P2 |
| D-145 | `test_build_list_client_payload_includes_default_flow_selection` | 1行 | `defaultFlowSelection == {"axis": "low_flow", "period": 3}` | F-002 / F-003 | P2 |
| D-146 | `test_build_list_client_payload_row_includes_six_flow_quadrants` | 1行 | `row["flowQuadrants"]` が `L1,L3,L6,D1,D2,D5` の6キー | F-016 / NF-001 | P2 |
| D-147 | `test_build_list_client_payload_row_includes_no_incoming_record_flag` | 最終入荷日なしの行 | `row["noIncomingRecord"] is True` | F-006 | P2 |
| D-148 | `test_build_list_client_payload_row_includes_responsible_department` | 供給リスク品の行 | `"調達G・営業G・生産管理"` | F-007 | P2 |
| D-149 | `test_build_list_client_payload_has_no_alert_level_keys` | 1行 | `alertLevel` / `alertOnly` を含まない | R-1 | P3 |

#### バリューオブジェクト: `app_settings` / `confirmation`（撤去の検証）

テストファイル: `tests/test_app_settings_usecase.py` / `tests/test_settings_service.py` / `tests/test_domain_confirmation.py`（既存を改修）

| # | テストケース | 入力 | 期待結果 | 対応REQ-ID | 優先度 |
|---|------------|------|---------|-----------|--------|
| D-150 | `test_app_settings_has_no_warning_month_or_critical_enabled_fields` | `AppSettings()` | `warning_shipment_months` / `warning_incoming_months` / `critical_enabled` を持たない | F-015 | P3 |
| D-151 | `test_app_settings_keeps_warning_days_and_stock_stale_days` | `AppSettings()` | 両フィールドが残る（在庫陳腐化判定で使用） | F-015 / NF-002 | P3 |
| D-152 | `test_parse_settings_payload_ignores_critical_enabled_key` | `{"criticalEnabled": True}` | 無視され、例外にならない | F-015 / §8 | P3 |
| D-153 | `test_settings_payload_has_no_warning_month_or_critical_enabled_keys` | `settings_payload(...)` | 3キーを含まない | F-015 | P3 |
| D-154 | `test_app_settings_module_has_no_alert_settings_input` | モジュール属性 | `AlertSettingsInput` / `parse_alert_settings_payload` / `clamp_warning_months` / `MIN_WARNING_MONTHS` / `MAX_WARNING_MONTHS` が存在しない | F-015 / R-1 | P3 |
| D-155 | `test_confirmation_record_has_confirmed_flow_quadrant_field` | `ConfirmationRecord(...)` | `confirmed_flow_quadrant` を持ち `confirmed_alert_level` を持たない | F-014 | P2 |

### 2.2 Application層テスト

リポジトリ（Callable ポート）は関数モックに差し替え、**ドメインモデルは実物**を通す（test-strategy §3.2）。
DB に触れないため `@pytest.mark.django_db` は付けない。

#### ユースケース: `ListPage`（`tests/test_inventory_order_alert_views.py` / `tests/test_inventory_order_alert_row_template.py` を改修）

| # | テストケース | 入力 | 期待結果 | 対応REQ-ID | 優先度 |
|---|------------|------|---------|-----------|--------|
| A-001 | `test_list_page_context_includes_flow_selection_and_options` | 既定クエリ | `flow_selection`（低流動3か月） / `flow_axis_options`(2) / `flow_period_options`(軸別3件) | F-002 / F-003 | P2 |
| A-002 | `test_list_page_context_includes_flow_quadrant_filter` | `flow_quadrant=dormant-stock` | `flow_quadrant_filter == "dormant-stock"` | F-009 | P2 |
| A-003 | `test_list_page_context_includes_flow_quadrant_rule_rows` | 既定 | 4行の凡例 | F-015 | P2 |
| A-004 | `test_list_page_context_has_no_warning_month_fields` | 既定 | `warning_shipment_months` / `warning_incoming_months` / `warning_month_options` を持たない | F-015 / R-1 | P3 |
| A-005 | `test_list_page_switching_axis_keeps_same_row_set` | 低流動3か月 / 死蔵5年 | 行数・行の識別子集合が同一。流動区分のみ変わる | F-002 | P2 |
| A-006 | `test_list_page_without_stock_import_keeps_existing_no_data_banner` | 在庫未取込 | `has_list_data is False`、既存バナー文言を維持 | F-017 #4 / NF-002 | P2 |
| A-007 | `test_list_page_with_aggregation_error_returns_zero_counts` | 集計エラーあり | エラーメッセージ表示、件数すべて0 | §8 | P2 |
| A-008 | `test_list_page_with_no_rows_returns_zero_counts_without_error` | 0行 | 件数すべて0、エラーなし | F-017 #8 | P2 |
| A-009 | `test_list_page_does_not_call_oracle_when_axis_changes` | 軸切替2回 | 集計スナップショット読込のみ。Oracle 問い合わせのモックが呼ばれない | F-016 / NF-001 | P1 |
| A-010 | `test_rows_for_template_sets_alert_row_class_to_flow_quadrant_key` | 供給リスク品・未確認 | `alert_row_class == "supply-risk"` | F-005 | P2 |
| A-011 | `test_rows_for_template_prefers_confirmation_class_over_flow_quadrant` | 供給リスク品・確認済み | `alert_row_class == "確認済"` | F-005 | P2 |

#### ユースケース: `ExportCsv`（`tests/test_export_csv.py` を改修）

| # | テストケース | 入力 | 期待結果 | 対応REQ-ID | 優先度 |
|---|------------|------|---------|-----------|--------|
| A-012 | `test_export_csv_without_query_params_uses_default_flow_selection` | `execute()` | 判定軸「低流動判定軸」・判定期間「3か月」 | F-011 | P2 |
| A-013 | `test_export_csv_reflects_selected_axis_and_period` | `execute(query_params={"axis": "dormant", "period": "2"})` | 全行の判定軸「死蔵判定軸」・判定期間「2年」 | F-011 | P2 |
| A-014 | `test_export_csv_flow_quadrant_column_matches_selected_period` | 死蔵5年で通常流動品になる行 | 流動区分列が「通常流動品」 | F-011 / F-016 | P2 |
| A-015 | `test_export_csv_outputs_all_rows_ignoring_filters` | `flow_quadrant=supply-risk` を渡す | 絞り込まれず全件出力 | F-011 | P2 |
| A-016 | `test_export_csv_keeps_utf8_bom` | `execute()` | 先頭が UTF-8 BOM | F-011 / NF-002 | P2 |
| A-017 | `test_export_csv_no_incoming_record_column_shows_ari_or_empty` | 入荷なし行 / 入荷あり行 | 「あり」 / `""` | F-006 / F-011 | P2 |
| A-018 | `test_export_csv_responsible_department_column_matches_quadrant` | 供給リスク品行 | 「調達G・営業G・生産管理」 | F-007 / F-011 | P2 |
| A-019 | `test_export_csv_falls_back_to_default_for_invalid_query_params` | `{"axis": "foo", "period": "999"}` | 低流動判定軸・3か月。例外にしない | F-017 #5 / §8 | P2 |
| A-020 | `test_export_csv_with_no_rows_outputs_header_only` | 0行 | ヘッダ行のみ。例外にしない | F-017 #8 | P2 |

#### ユースケース: `PortalDashboard`（`tests/test_inventory_order_alert_views.py` / `tests/test_summary_api.py` を改修）

| # | テストケース | 入力 | 期待結果 | 対応REQ-ID | 優先度 |
|---|------------|------|---------|-----------|--------|
| A-021 | `test_dashboard_banner_counts_each_flow_quadrant` | 4区分 各2行 | `supply_risk=2` / `dormant_stock=2` / `excess_stock_risk=2` / `unconfirmed` | F-013 | P2 |
| A-022 | `test_dashboard_banner_attention_excludes_normal_flow` | 同上 | `attention == 6` | F-013 | P2 |
| A-023 | `test_dashboard_banner_tone_is_neutral_when_error_message_present` | エラーあり（供給リスク品も存在） | `tone == "neutral"`（エラーが最優先） | §8 | P2 |
| A-024 | `test_dashboard_banner_tone_is_critical_when_supply_risk_exists` | 供給リスク品1・在庫死蔵品1 | `tone == "critical"` | F-013 | P2 |
| A-025 | `test_dashboard_banner_tone_is_warning_when_only_dormant_or_excess_exist` | 在庫死蔵品1のみ / 在庫過剰リスク品1のみ | `tone == "warning"` | F-013 | P2 |
| A-026 | `test_dashboard_banner_tone_is_ok_when_only_normal_flow_exists` | 通常流動品のみ | `tone == "ok"` / `has_alerts is False` | F-013 | P2 |
| A-027 | `test_dashboard_banner_includes_confirmed_rows_in_quadrant_counts` | 確認済み1・未確認1（同区分） | 区分件数 2 | F-013 | P2 |
| A-028 | `test_dashboard_banner_always_uses_reference_flow_selection` | 一覧では死蔵5年を選択中の状態 | 帯の件数は低流動3か月で算出（画面選択に依存しない） | F-013 | P1 |
| A-029 | `test_dashboard_banner_returns_zero_counts_without_stock_import` | 在庫未取込 | すべて0、`has_stock_data is False` | F-017 #4 | P2 |
| A-030 | `test_dashboard_banner_has_no_critical_or_warning_fields` | `DashboardBannerContext(...)` | `critical` / `warning` を持たない | R-1 | P3 |

#### ユースケース: `SummaryApi` / `SaveConfirmationUseCase` / `PatchSnapshotRow`

| # | テストケース | 入力 | 期待結果 | 対応REQ-ID | 優先度 |
|---|------------|------|---------|-----------|--------|
| A-031 | `test_summary_api_counts_payload_uses_flow_quadrant_keys` | 任意の行集合 | `supplyRisk` / `dormantStock` / `excessStockRisk` / `normalFlow` を持ち `critical` / `warning` を持たない | F-008 | P2 |
| A-032 | `test_summary_api_attention_only_excludes_normal_flow` | `attentionOnly=true` | 通常流動品を除く行のみ | F-009 | P2 |
| A-033 | `test_summary_api_reflects_selected_axis_and_period` | `axis=dormant&period=5` | 各行の流動区分が死蔵5年基準 | F-002 / F-016 | P2 |
| A-034 | `test_summary_api_merge_query_with_settings_does_not_override_flow_selection` | 設定値あり | 判定軸・判定期間が設定値で上書きされない | F-015 | P2 |
| A-035 | `test_save_confirmation_records_flow_quadrant_from_reference_selection` | 一覧で死蔵5年選択中に確認保存 | 保存される流動区分は**低流動3か月**基準 | F-014 | P1 |
| A-036 | `test_save_confirmation_response_counts_use_flow_quadrants` | 保存後 | レスポンス `counts` が流動区分ベース | F-008 / F-014 | P2 |
| A-037 | `test_patch_snapshot_row_applies_flow_quadrant_with_reference_selection` | 行の部分更新 | 更新行に低流動3か月基準の流動区分が付く | F-014 / F-016 | P2 |
| A-038 | `test_save_alert_settings_use_case_module_does_not_exist` | `import` | `ModuleNotFoundError` | F-015 / R-1 | P3 |
| A-039 | `test_wiring_has_no_save_alert_settings_usecase` | `wiring` モジュール | `save_alert_settings_usecase` が存在せず `__all__` にもない | F-015 / NF-005 | P3 |

### 2.3 Infrastructure層テスト

`@pytest.mark.django_db` を付ける。Oracle は `conftest.py` により既定でモック。

| # | テストケース | 入力 | 期待結果 | 対応REQ-ID | 優先度 |
|---|------------|------|---------|-----------|--------|
| I-001 | `test_load_latest_summary_returns_rows_with_flow_quadrant` | 保存済みスナップショット | 各行に `flow_quadrant` / `flow_quadrants` / `no_incoming_record` が付く | F-016 | P3 |
| I-002 | `test_load_latest_summary_recomputes_flow_quadrant_on_each_read` | 同一スナップショットを2回読む | 保存値ではなく毎回判定される（`rows` に区分が永続化されていない） | F-016 | P1 |
| I-003 | `test_summary_snapshot_rows_schema_is_unchanged_after_roundtrip` | 保存→読込 | `rows` の要素キー集合が保存時と一致（流動区分は含まれない） | F-016 / NF-002 | P1 |
| I-004 | `test_summary_repository_writes_supply_risk_count_to_critical_count` | 供給リスク品3行 | `critical_count == 3`（低流動3か月基準） | F-013 / NF-002 | P3 |
| I-005 | `test_summary_repository_writes_dormant_and_excess_sum_to_warning_count` | 在庫死蔵品2・在庫過剰リスク品1 | `warning_count == 3` | F-013 / NF-002 | P3 |
| I-006 | `test_summary_snapshot_repository_writes_same_count_rule` | 同上（スナップショット経路） | `critical_count` / `warning_count` が同一規則 | NF-002 | P3 |
| I-007 | `test_summary_repository_does_not_load_app_settings` | 読込1回 | `load_app_settings` のモックが呼ばれない | F-015 | P3 |
| I-008 | `test_load_latest_summary_does_not_query_oracle` | 読込1回 | Oracle 接続が発生しない | NF-001 | P2 |
| I-009 | `test_confirmation_repository_saves_and_loads_confirmed_flow_quadrant` | 供給リスク品で保存 | 同値で読み戻る | F-014 | P2 |
| I-010 | `test_confirmation_repository_reads_legacy_alert_level_without_error` | 旧値「重点」を直接 DB に入れた行 | 供給リスク品として読める。例外にしない | F-014 / F-017 #7 / NF-002 | P1 |
| I-011 | `test_confirmation_repository_reads_unknown_label_as_normal_flow` | 旧値「謎」 | 通常流動品。例外にしない | F-017 #7 | P1 |
| I-012 | `test_reconcile_confirmations_resets_row_when_flow_escalated` | 確認時=通常流動品、取込後=供給リスク品 | 未確認に戻る | F-014 | P1 |
| I-013 | `test_reconcile_confirmations_keeps_row_when_flow_not_escalated` | 確認時=供給リスク品、取込後=通常流動品 | 確認済みのまま | F-014 | P1 |
| I-014 | `test_reconcile_confirmations_keeps_row_when_flow_unchanged` | 同一区分 | 確認済みのまま | F-014 | P1 |
| I-015 | `test_reconcile_confirmations_normalizes_legacy_no_alert_label_before_comparing` | 確認時=「アラート無し」、取込後=供給リスク品 | 未確認に戻る（正規化後 rank3 → rank0） | F-014 / NF-002 | P1 |
| I-016 | `test_reconcile_confirmations_uses_reference_flow_selection_only` | 死蔵5年なら深刻化しない状況 | 低流動3か月基準で判定される（画面選択に依存しない） | F-014 | P1 |
| I-017 | `test_settings_repository_has_no_save_warning_month_settings` | モジュール属性 | 存在しない | F-015 / R-1 | P3 |
| I-018 | `test_load_app_settings_has_no_warning_month_or_critical_enabled` | 読込結果 | 3項目を持たない（DB カラムは残置） | F-015 / §5.3 | P3 |
| I-019 | `test_settings_table_keeps_legacy_columns` | モデル定義 | `warning_shipment_months` / `warning_incoming_months` / `critical_enabled` のカラム定義は残る | §5.3 / NF-002 | P3 |
| I-020 | `test_confirmation_model_has_confirmed_flow_quadrant_field` | モデル `_meta` | `confirmed_flow_quadrant`（`max_length == 40`）が存在し `confirmed_alert_level` が存在しない | F-014 | P2 |
| I-021 | `test_migration_0011_renames_confirmed_alert_level_field` | マイグレーションファイルの `operations` | `RenameField` 1件、`old_name="confirmed_alert_level"` / `new_name="confirmed_flow_quadrant"` | F-014 / NF-002 | P2 |
| I-022 | `test_no_pending_model_changes_without_migration` | `makemigrations --check --dry-run` | 差分なし | NF-002 | P2 |
| I-023 | `test_summary_aggregation_builds_list_query_with_reference_flow_selection` | 集計実行 | `ListQuery` が `REFERENCE_FLOW_SELECTION` で組まれ、`alert_only` を渡さない | F-013 / R-1 | P3 |
| I-024 | `test_summary_aggregation_sql_is_unchanged` | 発行 SQL 文字列 | 既存の SQL と一致（列の追加・変更なし） | requirements §6.2 | P2 |

> **I-021 / I-022 の補足**: `conftest.py` の `django_db_use_migrations` が `False` を返すため、
> テスト DB はマイグレーションではなくモデル定義から生成される。したがって
> **`RenameField` の実行そのものはテストで検証されない**。I-021 はマイグレーションファイルの
> 内容検査（DB 非依存）、I-022 はモデルとマイグレーションの整合検査であり、
> **実 DB への適用は §5.2 のとおり本番相当環境での手動確認（tasks.md の受入項目）で担保する**。

### 2.4 Interfaces層テスト

| # | テストケース | 入力 | 期待結果 | 対応REQ-ID | 優先度 |
|---|------------|------|---------|-----------|--------|
| X-001 | `test_list_page_renders_flow_condition_selector` | `GET /app/production/inventory-order-alert` | 200。判定軸 `select[name=axis]` と判定期間 `select[name=period]` を含む | F-002 / F-003 | P3 |
| X-002 | `test_list_page_shows_current_flow_condition_text` | 同上 | 「低流動判定軸」「3か月」を含む。「象限」を含まない | F-004 / NF-004 | P3 |
| X-003 | `test_list_page_reflects_dormant_axis_from_query` | `?axis=dormant&period=5` | 「死蔵判定軸」「5年」を表示 | F-002 / F-003 / F-012 | P3 |
| X-004 | `test_list_page_falls_back_for_unknown_axis_without_error` | `?axis=foo` | 200。低流動判定軸・3か月。エラー画面を出さない | F-017 #5 | P3 |
| X-005 | `test_list_page_falls_back_for_period_not_in_axis` | `?axis=dormant&period=3` | 200。死蔵判定軸・1年 | F-017 #6 | P3 |
| X-006 | `test_list_page_falls_back_for_unknown_flow_quadrant` | `?flow_quadrant=謎` | 200。全件表示 | F-017 / §8 | P3 |
| X-007 | `test_list_page_does_not_log_fallback` | `?axis=foo`（`caplog`） | フォールバックのログ出力がない | NF-007 | P3 |
| X-008 | `test_list_page_requires_production_control_menu_group` | 権限なしユーザー | 既存どおり拒否される | NF-003 | P3 |
| X-009 | `test_list_page_shows_flow_quadrant_column_header` | 200 | 「流動区分」「責任部署」を含み「アラート」列見出しを含まない | F-004 / F-007 | P3 |
| X-010 | `test_export_csv_response_contains_flow_quadrant_column` | `GET .../export` | ヘッダに「流動区分」「判定軸」「判定期間」「入荷実績なし」「責任部署」 | F-011 | P3 |
| X-011 | `test_export_csv_response_reflects_query_params` | `?axis=dormant&period=2` | 判定期間列が「2年」 | F-011 / F-012 | P3 |
| X-012 | `test_export_csv_requires_production_control_menu_group` | 権限なし | 既存どおり拒否 | NF-003 | P3 |
| X-013 | `test_alert_settings_api_is_removed` | `PUT /api/inventory-order-alert/alert-settings` | 404 | F-015 | P3 |
| X-014 | `test_shipment_trend_alert_settings_api_still_exists` | shipment_trend 側の同名 API | 404 **にならない**（誤削除防止） | R-8 | P2 |
| X-015 | `test_summary_api_returns_flow_quadrant_counts` | `GET /api/inventory-order-alert/summary` | `counts` が流動区分ベース | F-008 | P3 |
| X-016 | `test_summary_api_accepts_attention_only` | `?attentionOnly=true` | 通常流動品を除く | F-009 | P3 |
| X-017 | `test_settings_page_has_no_warning_month_inputs` | `GET .../settings` | `warningShipmentMonths` / `warningIncomingMonths` / `ioa-setting-critical-enabled` を含まない | F-015 | P3 |
| X-018 | `test_settings_page_keeps_stock_stale_days_input` | 同上 | `stockStaleDays` は残る | NF-002 | P3 |
| X-019 | `test_row_template_applies_ascii_flow_quadrant_class` | 供給リスク品・未確認の行 | `alert-row--supply-risk` を含む | F-005 | P3 |
| X-020 | `test_row_template_keeps_confirmation_class_priority` | 供給リスク品・確認済み | `alert-row--確認済` を含む | F-005 | P3 |
| X-021 | `test_row_template_shows_no_incoming_badge_inside_flow_quadrant_cell` | 入荷実績なしの行 | 「入荷なし」バッジを流動区分セル内に含む | F-006 | P3 |
| X-022 | `test_ioa_display_templatetag_returns_flow_quadrant_label` | templatetag | 流動区分ラベルを返す | F-004 | P3 |
| X-023 | `test_ioa_row_alert_class_templatetag_returns_flow_quadrant_key` | templatetag | ASCII キーを返す | F-005 | P3 |
| X-024 | `test_dashboard_banner_text_includes_flow_condition` | `GET` メニュー画面 | 「供給リスク品」「在庫死蔵品」「在庫過剰リスク品」「低流動判定軸・3か月」を含む | F-013 | P3 |
| X-025 | `test_app_css_defines_ascii_flow_quadrant_row_selectors` | `static/css/app.css` | `.alert-row--supply-risk` `#fde8e8` 等、4区分すべての背景色・hover 色が定義されている | F-005 / §6.6.7 | P4 |
| X-026 | `test_app_css_has_no_japanese_flow_quadrant_selectors` | 同上 | `.alert-row--重点` `.alert-row--警告` `.alert-row--アラート無し` を含まない | F-005 / R-1 | P4 |
| X-027 | `test_app_css_keeps_shipment_trend_row_selectors` | 同上 | `.st-row-` 系セレクタが残っている | R-5 | P4 |
| X-028 | `test_app_css_keeps_confirmation_row_selectors` | 同上 | `.alert-row--確認済` / `.alert-row--確認中` が残っている | F-005 | P4 |
| X-029 | `test_list_client_js_ranks_flow_quadrant_by_urgency` | `inventory-order-alert-list-client.js` | `FLOW_QUADRANT_RANK`（または同等の識別子）を持ち、`supply-risk` が先頭 | F-010 | P4 |
| X-030 | `test_list_client_js_reads_precomputed_flow_quadrants` | 同上 | `flowQuadrants` からの引き直しコードを含む | F-002 / F-016 | P4 |
| X-031 | `test_list_client_js_has_no_calendar_month_calculation` | 同上 | `add_calendar_months` / `addCalendarMonths` / `setMonth(` を含まない（判定ロジックを持たない） | §3.2 / NF-001 | P4 |
| X-032 | `test_list_client_js_syncs_axis_period_and_flow_quadrant_to_url` | 同上 | `updateUrl` 相当に `axis` / `period` / `flowQuadrant` が含まれる | F-012 | P4 |
| X-033 | `test_list_client_js_resets_page_on_flow_condition_change` | 同上 | 判定条件変更時にページを1へ戻す記述がある | F-002 / F-009 | P4 |
| X-034 | `test_list_js_has_no_alert_settings_save_request` | `inventory-order-alert-list.js` | `alert-settings` への保存リクエストを含まない | F-015 | P4 |
| X-035 | `test_list_js_has_no_alert_level_identifiers` | 両 JS | `alertLevel` / `alertOnly` / `ALERT_RANK` を含まない | R-1 | P4 |
| X-036 | `test_no_alert_level_identifier_remains_in_inventory_order_alert` | `application/inventory_order_alert` / `static/js` / `templates/inventory_order_alert` / `scripts` を走査 | `alert_level` / `alertLevel` / `alert_only` / `alertOnly` の出現 0 件（本テスト自身の除外あり） | R-1 | P2 |
| X-037 | `test_verify_post_receipt_shipment_count_script_uses_attention_only` | `scripts/verify_post_receipt_shipment_count.py` | `--attention-only` を持ち `--alert-only` を持たない | R-1 | P4 |
| X-038 | `test_clean_architecture_rules_still_hold` | `config/tests/test_clean_architecture.py` | 既存テストが緑（domain / use_cases に `import django` がない） | NF-005 | P2 |

---

## 3. テストデータ

### 3.1 正常系テストデータ

#### 基準日と 4 象限の代表行

BOM 基準日（V-209）を **2026/8/27** に固定する。低流動判定軸・3か月の境界日は **2026/5/27**。

| 行名 | 最終入荷日 | 最終出荷日 | 在庫数 | 低流動3か月での流動区分 | 入荷実績なし |
|------|-----------|-----------|-------|-------------------|-----------|
| `ROW_SUPPLY_RISK` | 2026/1/10 | 2026/8/1 | 500 | 供給リスク品 | いいえ |
| `ROW_SUPPLY_RISK_NO_INCOMING` | （空） | 2026/8/1 | 120 | 供給リスク品 | **はい** |
| `ROW_DORMANT_STOCK` | 2026/1/10 | 2026/1/20 | 3000 | 在庫死蔵品 | いいえ |
| `ROW_EXCESS_STOCK_RISK` | 2026/8/1 | 2026/1/20 | 8000 | 在庫過剰リスク品 | いいえ |
| `ROW_NORMAL_FLOW` | 2026/8/1 | 2026/8/10 | 400 | 通常流動品 | いいえ |
| `ROW_BOUNDARY` | 2026/5/27 | 2026/5/27 | 100 | 通常流動品（境界ちょうど） | いいえ |

同じ 6 行を判定軸・判定期間ごとに使い回し、区分の変化を検証する（D-050 / D-051 / A-005 / A-013）。

| 行名 | 低流動1か月 | 低流動3か月 | 低流動6か月 | 死蔵1年 | 死蔵5年 |
|------|:---:|:---:|:---:|:---:|:---:|
| `ROW_SUPPLY_RISK` | 供給リスク品 | 供給リスク品 | 供給リスク品 | 通常流動品 | 通常流動品 |
| `ROW_DORMANT_STOCK` | 在庫死蔵品 | 在庫死蔵品 | 在庫死蔵品 | 通常流動品 | 通常流動品 |
| `ROW_EXCESS_STOCK_RISK` | 在庫過剰リスク品 | 在庫過剰リスク品 | 在庫過剰リスク品 | 通常流動品 | 通常流動品 |

（この表そのものをパラメトライズドテストの期待値表として使う。）

#### 判定条件

| 定数 | 値 |
|------|---|
| `SELECTION_L1` | 低流動判定軸・1か月（`key="L1"`） |
| `SELECTION_L3` | 低流動判定軸・3か月（`key="L3"`、= `REFERENCE_FLOW_SELECTION`） |
| `SELECTION_L6` | 低流動判定軸・6か月（`key="L6"`） |
| `SELECTION_D1` | 死蔵判定軸・1年（`key="D1"`） |
| `SELECTION_D2` | 死蔵判定軸・2年（`key="D2"`） |
| `SELECTION_D5` | 死蔵判定軸・5年（`key="D5"`） |

#### 確認記録

| 行名 | `confirmed_flow_quadrant` | 確認状態 |
|------|--------------------------|---------|
| `CONF_CURRENT` | 通常流動品 | 確認済み |
| `CONF_LEGACY_CRITICAL` | `"重点"`（旧値） | 確認済み |
| `CONF_LEGACY_NO_ALERT` | `"アラート無し"`（旧値） | 確認済み |
| `CONF_UNKNOWN` | `"謎のラベル"` | 確認済み |

### 3.2 異常系テストデータ

| データ名 | 値 | 用途 |
|---------|---|------|
| `DATE_NONE` | `None` | D-029 / D-045 / D-058 |
| `DATE_EMPTY_STRING` | `""` | D-091 |
| `DATE_UNPARSABLE` | `"2026/13/45"` | D-090 / §8 |
| `DATE_FUTURE` | 2026/12/1（基準日より未来） | D-033 / F-017 #3 |
| `DATE_MONTH_END` | 基準日 2026/8/31・target 2026/2/28 | D-034 / D-035 |
| `DATE_LEAP` | 基準日 2024/8/31・target 2024/2/29 | D-036 |
| `AXIS_UNKNOWN` | `"foo"` | D-008 / D-128 / X-004 |
| `PERIOD_MISMATCHED` | `axis=dormant&period=3` | D-127 / X-005 |
| `PERIOD_NON_NUMERIC` | `"abc"` | D-129 |
| `PERIOD_OUT_OF_RANGE` | `"999"` | D-130 |
| `QUADRANT_UNKNOWN` | `"謎"` | D-096 / D-132 / X-006 |
| `LEGACY_LABELS` | `重点` / `警告（出荷なし）` / `警告（出荷あり）` / `アラート無し` / `なし` / `アラートなし` / `問題なし` / `警告（出荷）` / `警告（入荷）` | D-067〜D-071 |
| `ROWS_EMPTY` | `[]` | D-092 / D-114 / A-008 / A-020 |
| `ROWS_LARGE` | 5,000 行（NF-001 の計測用） | E-002 / E-003 |

本番データは使用しない（test-strategy §6）。日付は常に固定値をコード内に直接記述し、`date.today()` を用いない。

---

## 4. 境界値・異常系のカバレッジ

### 4.1 境界値テスト

| 対象 | 境界値 | テストケース |
|------|--------|------------|
| 判定期間の境界日（低流動3か月・基準日 2026/8/27） | 境界ちょうど 2026/5/27 / 境界-1日 2026/5/26 | D-030 / D-031 |
| 判定期間の最小（1か月） | 2026/7/27 | D-037 |
| 判定期間の最大（死蔵5年=60か月） | 2021/8/27 / 2021/8/26 | D-038 / D-039 |
| 基準日そのもの | target == `as_of_date` | D-032 |
| 基準日より未来 | target > `as_of_date` | D-033 |
| 暦月末日の丸め | 2026/8/31 の 6か月前 → 2026/2/28 | D-034 / D-035 |
| うるう年の丸め | 2024/8/31 の 6か月前 → 2024/2/29 | D-036 |
| 年跨ぎ | 2026/1/15 の 3か月前 → 2025/10/15 | D-040 |
| 判定期間の集合サイズ | `len(EVALUATION_PERIODS) == 6`（過不足なし） | D-015 |
| 判定期間キーの未定義値 | `"L2"`（軸に存在しない組み合わせ） | D-013 |
| 流動区分の並び順ランク | 最小0（供給リスク品）／最大3（通常流動品） | D-026 |
| 確認記録のフィールド長 | 最長ラベル 8 文字 ≤ `max_length` 40 | D-028 / I-020 |
| ソート条件数 | 5 条件（既存上限） | D-107 |
| 行数 | 0 行 / 1 行 / 多数（5,000 行） | D-092・D-114 / D-088 / E-002 |
| ファーストクラスコレクション | 空（未知軸で `()`）／要素1（`find` 単一ヒット）／要素6（全列挙） | D-008 / D-012 / D-015 |

### 4.2 異常系テスト

| 対象 | 異常ケース | 期待される振る舞い | テストケース |
|------|----------|------------------|------------|
| 最終入荷日・最終出荷日 | ともに空（`None`） | 在庫死蔵品。例外にしない | D-045 / A-007 |
| 最終入荷日 | 空・出荷あり | 供給リスク品 + 入荷実績なし | D-046 / D-061 |
| 日付文字列 | 解析不能（`"2026/13/45"`） | `None` として扱い行を落とさない | D-090 |
| 日付文字列 | 空文字 | 期間外として扱う | D-091 |
| 日付 | 基準日より未来 | 期間内とみなす（除外しない） | D-033 |
| `axis` | 未知の値 | 低流動判定軸・3か月へ静かにフォールバック | D-128 / X-004 / X-007 |
| `period` | 軸に対応しない値 | 当該軸の既定値へフォールバック | D-127 / X-005 |
| `period` | 数値でない / 範囲外 | 軸の既定値へフォールバック | D-129 / D-130 |
| `flow_quadrant` | 未知のキー | 空（全件）へフォールバック | D-132 / X-006 |
| 確認記録のラベル | 旧アラートレベル | 互換写像で正規化 | D-067〜D-071 / I-010 |
| 確認記録のラベル | 未知 / 空 / `None` | 通常流動品（安全側）。例外にしない | D-072 / D-073 / D-076 / I-011 |
| SLIMS 在庫 | 未取込 | 既存バナー。流動区分が不定であることが分かる表示 | A-006 / A-029 |
| 集計 | `aggregation_error` あり | エラー表示・件数0・`tone == "neutral"` | A-007 / A-023 |
| 行数 | 0 件 | 件数サマリすべて 0。エラーにしない | D-114 / A-008 / A-020 |
| 責任部署 | 未知の流動区分 | `()`。例外にしない | D-066 |
| 撤去済み引数 | `filter_summary_rows(alert_only=True)` | `TypeError` | D-099 |
| 撤去済み API | `PUT .../alert-settings` | 404 | X-013 |

**原則の検証**: 「判定は例外を投げない」（設計書 §8）を横断的に確認するため、
D-053 で 4 通り × 6 判定条件、および異常入力の組み合わせを網羅的に回し、
**いずれも例外を送出せず 4 ラベルのいずれかを返す**ことをアサートする。

### 4.3 エッジケース

| # | ケース | 検証内容 | 対応REQ-ID | 優先度 |
|---|--------|---------|-----------|--------|
| E-001 | クライアント配信ペイロードの増分 | 1 行あたりの `flowQuadrants` + `noIncomingRecord` + `responsibleDepartment` の JSON バイト数が **100 バイト以下**であること（設計書 §9 R-3 の「約90バイト」の実測） | NF-001 / R-3 | P2 |
| E-002 | 大量行でのペイロード生成 | 5,000 行で `build_list_client_payload` を実行し、行数が保たれること・生成が完了すること。所要時間を記録し、置き換え前後で**同等**であることを確認する | NF-001 | P2 |
| E-003 | 大量行での判定 | 5,000 行 × 6 判定条件 = 30,000 回の判定が現実的時間で完了すること | NF-001 | P3 |
| E-004 | 判定軸切替で行集合が不変 | 低流動1か月 ↔ 死蔵5年で、表示対象行の識別子集合が完全一致すること | F-002 | P2 |
| E-005 | 件数サマリ左右の一致 | 任意の行集合で「流動区分4値の和」==「確認状態3値の和」== `total` | F-008 | P2 |
| E-006 | メニュー帯と一覧の件数差 | 一覧で死蔵5年を選んでいても帯の件数が変わらないこと（R-4 の意図的な差の固定化） | F-013 / R-4 | P2 |
| E-007 | 確認記録の同時実行 | 同一行に対する確認保存とデータ更新（取込）が競合した場合、既存のロック機構（`import_lock`）の挙動が変わらないこと | NF-002 | P3 |
| E-008 | 移行直後の深刻化判定 | 全確認記録が旧ラベルの状態で 1 回目の取込を行い、**例外なく完了し**、正規化後のランクに基づいて差し戻しが行われること（R-2 の受容内容の確認） | F-014 / R-2 | P1 |
| E-009 | 呼称の使い分け | 低流動判定軸のとき、列値は「在庫死蔵品」だが補助テキストは「低流動品」を含むこと。両軸で「未流動品」「デッドストック」「不良在庫」を含まないこと | F-018 / NF-004 | P2 |
| E-010 | 判定期間の全組み合わせ回帰 | 6 判定条件 × 4 象限 = 24 通りをパラメトライズドテストで一括検証（`@pytest.mark.parametrize`） | F-001 / F-003 | P1 |

---

## 5. テスト環境

### 5.1 テスト実行コマンド

> **reference との差異（重要）**: `django-pytest.md` は `make test-fast` / `make test-all` / `make test-cov` を
> 前提としているが、**本リポジトリに `Makefile` は存在しない**（`/django_app/src` および `/django_app` の
> いずれにも無いことを確認済み）。また同 reference が挙げる `config/settings/test.py` も存在せず、
> `pytest.ini` は `DJANGO_SETTINGS_MODULE = config.settings.development` を指定している。
> したがって本機能では **`pytest` を直接実行する**。

| 目的 | コマンド |
|------|---------|
| Domain 層のみ（TDD の内側ループ、DB 不要） | `pytest application/inventory_order_alert/tests/test_flow_quadrant.py -x` |
| 1 テストのみ | `pytest application/inventory_order_alert/tests/test_flow_quadrant.py::test_resolve_flow_quadrant_returns_supply_risk_when_incoming_absent_and_shipment_present -x` |
| アプリ全体 | `pytest application/inventory_order_alert/` |
| アーキテクチャ検証 | `pytest config/tests/test_clean_architecture.py` |
| 全体（回帰確認） | `pytest` |
| カバレッジ | `pytest --cov=application/inventory_order_alert --cov-report=term-missing application/inventory_order_alert/` |
| マイグレーション整合（I-022） | `python manage.py makemigrations --check --dry-run` |
| 旧識別子の残存チェック（X-036 の手動版） | `grep -rn "alert_level\|alertLevel\|alert_only\|alertOnly" application/inventory_order_alert static/js templates/inventory_order_alert scripts` |

実行はすべて `/django_app/src`（DevContainer の workspace ルート）を作業ディレクトリとする。

### 5.2 テストデータの準備方法

| 方式 | 用途 | 備考 |
|------|------|------|
| **コード内直接記述** | Domain 層のすべて、Application 層の行データ | 既存慣習。日付は固定値のリテラル（`date(2026, 8, 27)`）。`date.today()` を使わない |
| **モジュール定数** | §3.1 の 6 行と 6 判定条件 | `tests/test_flow_quadrant.py` の冒頭に定義し、他のテストからは import せず各ファイルで必要分を再定義する（既存慣習：テスト間の暗黙結合を作らない） |
| **`@pytest.mark.parametrize`** | 24 通りの象限 × 判定条件（E-010）、旧ラベル互換写像（D-071）、フォールバック（D-127〜D-130） | 期待値表を §3.1 / §5.2 の表からそのまま書き下す |
| **Django ORM で直接生成** | Infrastructure / Interfaces 層のスナップショット・確認記録・設定 | `@pytest.mark.django_db`。既存の `tests/test_summary_storage.py` の生成手順に倣う |
| **実ファイル** | SLIMS 在庫 CSV（既存 `tests/fixtures/slims_stock_sample_wkatqt.csv`） | 本機能で新規追加しない |
| **ソース文字列読み込み** | JavaScript（X-029〜X-035）・CSS（X-025〜X-028）・スクリプト（X-037） | `Path(__file__).resolve().parents[3] / "static" / "js" / "..."` の既存パターン |

#### 環境の前提

- **Oracle**: `conftest.py` の `pytest_configure` が `ORACLE_USE_MOCK=true` を既定にするため、
  実 Oracle には接続しない。本機能は Oracle SQL を変更しないため、実接続テストは不要。
- **DB マイグレーション**: `conftest.py` の `django_db_use_migrations` が `False` を返すため、
  テスト DB はモデル定義から生成される。**マイグレーション 0011（`RenameField`）の実行は
  テストで検証されない**（§2.3 の I-021 / I-022 の補足を参照）。
- **テスト DB のガード**: `config/test_db_guard.assert_pytest_uses_test_database` が
  本番 DB への接続を防いでいる。この仕組みは変更しない。

### 5.3 新規・改修するテストファイル

既存テストの所在は実ファイルを走査して確認した（`grep -ln` による対象モジュールの逆引き）。

| ファイル | 処置 | 主な対象 |
|---------|------|---------|
| `tests/test_flow_quadrant.py` | **新規** | D-001〜D-083（本機能の中核。判定関数・VO・互換写像・深刻化判定） |
| `tests/test_flow_quadrant_rules.py` | **新規** | D-084〜D-087 |
| `tests/test_flow_quadrant_migration.py` | **新規** | I-021 / I-022（マイグレーションファイル内容検査・モデル整合） |
| `tests/test_legacy_alert_identifiers_removed.py` | **新規** | A-038 / A-039 / X-036 / X-037（R-1 の完了条件の自動化） |
| `tests/test_flow_quadrant_css.py` | **新規** | X-025〜X-028 |
| `tests/test_alert_level.py` | **削除** | `test_flow_quadrant.py` に置き換え |
| `tests/test_alert_rules.py` | **削除** | `test_flow_quadrant_rules.py` に置き換え |
| `tests/test_save_alert_settings.py` | **削除** | 機能の撤去（設計書 §6.5） |
| `tests/test_list_summary.py` | 改修 | D-088〜D-099（`list_rows` の区分付与・フィルタ・ソート） |
| `tests/test_row_counts.py` | 改修 | D-109〜D-116 |
| `tests/test_row_display.py` | 改修 | D-117〜D-123 |
| `tests/test_list_query.py` | 改修 | D-124〜D-134 |
| `tests/test_list_filter.py` | 改修 | D-135〜D-138 |
| `tests/test_table_display.py` | 改修 | D-100〜D-108 |
| `tests/test_list_client_data.py` | 改修 | D-143〜D-149 |
| `tests/test_domain_confirmation.py` | 改修 | D-155 |
| `tests/test_app_settings_usecase.py` | 改修 | D-150〜D-154 / A-034 |
| `tests/test_settings_service.py` | 改修 | D-150〜D-154 / I-017 / I-018 |
| `tests/test_export_csv.py` | 改修 | D-139〜D-142 / A-012〜A-020 |
| `tests/test_inventory_order_alert_views.py` | 改修 | A-001〜A-009 / A-021〜A-030 / X-001〜X-016 |
| `tests/test_inventory_order_alert_row_template.py` | 改修 | A-010 / A-011 / X-019〜X-023 |
| `tests/test_summary_api.py` | 改修 | A-031〜A-034 |
| `tests/test_confirmation_save_result.py` | 改修 | A-035 / A-036 |
| `tests/test_save_confirmation.py` | 改修 | A-035 / A-036（入力側。`alert_level=` / `confirmed_alert_level` の追随） |
| `tests/test_snapshot_patch.py` | 改修 | A-037 |
| `tests/test_summary_storage.py` | 改修 | I-001〜I-008 / I-019 / I-020 |
| `tests/test_reconcile_confirmations.py` | 改修 | I-009〜I-016 |
| `tests/test_build_summary_rows.py` | 改修 | I-023 / I-024（`infrastructure/oracle/summary_aggregation.py` / `summary_queries.py`） |
| `tests/test_settings_page_views.py` | 改修 | X-017 / X-018 |
| `tests/test_inventory_order_alert_list_js.py` | 改修 | X-029〜X-035（`static/js/inventory-order-alert-list-client.js` / `inventory-order-alert-list.js`） |
| `tests/test_verify_post_receipt_shipment_count.py` | 改修 | X-037 |
| `tests/test_dates.py` | 現状維持 | `add_calendar_months` の既存テスト。本機能では変更しない（新規述語は `test_flow_quadrant.py` 側に置く） |

**変更しないテストファイル**（回帰確認のみ）:
`test_build_summary_rows.py` を除く在庫取込系（`test_import_slims_stock_csv_command.py` / `test_slims_stock_location.py` /
`test_stock_join.py` / `test_stock_storage.py`）、`test_memo_history.py`、`test_import_lock.py`、
`test_internal_item.py`、`test_code_sort` 相当、`test_format_display.py`、`test_user_display.py`、
`test_dev_data_guard.py`、`test_inventory_order_alert_application.py`。

---

## 6. 要件トレーサビリティ

要件定義書の全 25 要件と、本テスト設計書のテストケースの対応。**空欄なし**。

| 要件ID | 要件 | 主なテストケース |
|--------|------|----------------|
| REQ-LFV-F-001 | 流動区分の判定 | D-029〜D-053 / D-088 / E-010 |
| REQ-LFV-F-002 | 判定軸の切り替え | D-018〜D-020 / D-051 / D-054 / A-005 / E-004 / X-003 / X-030 |
| REQ-LFV-F-003 | 判定期間の選択 | D-001〜D-015 / D-037〜D-039 / D-050 / D-125〜D-127 / A-001 |
| REQ-LFV-F-004 | 一覧の流動区分列 | D-023 / D-100 / D-117 / X-002 / X-009 / X-022 |
| REQ-LFV-F-005 | 行の強調 | D-119〜D-122 / X-019 / X-020 / X-025〜X-028 |
| REQ-LFV-F-006 | 入荷実績なしの表示 | D-058〜D-061 / D-088 / D-147 / A-017 / X-021 |
| REQ-LFV-F-007 | 責任部署の表示 | D-062〜D-066 / D-086 / D-101 / D-108 / D-148 / A-018 |
| REQ-LFV-F-008 | 件数サマリの流動区分化 | D-109〜D-116 / A-031 / A-036 / E-005 / X-015 |
| REQ-LFV-F-009 | 流動区分による絞り込み | D-094〜D-099 / D-131 / D-133 / A-002 / A-032 / X-016 |
| REQ-LFV-F-010 | 流動区分によるソート | D-025 / D-026 / D-100〜D-108 / D-144 / X-029 |
| REQ-LFV-F-011 | CSV 出力への反映 | D-139〜D-142 / A-012〜A-020 / X-010 / X-011 |
| REQ-LFV-F-012 | 選択状態の保持 | D-135〜D-138 / X-003 / X-011 / X-032 |
| REQ-LFV-F-013 | メニュー画面アラート帯 | D-021 / A-021〜A-029 / I-004〜I-006 / I-023 / E-006 / X-024 |
| REQ-LFV-F-014 | 確認記録との整合 | D-028 / D-067〜D-083 / D-155 / A-035 / A-037 / I-009〜I-016 / I-020 / I-021 / E-008 |
| REQ-LFV-F-015 | 警告条件の扱い | D-084〜D-087 / D-150〜D-154 / A-003 / A-004 / A-034 / A-038 / A-039 / I-017〜I-019 / X-013 / X-017 / X-034 |
| REQ-LFV-F-016 | 表示時再判定 | D-056 / D-146 / A-009 / A-014 / A-033 / A-037 / I-002 / I-003 |
| REQ-LFV-F-017 | 異常系・エッジケース（8件） | #1 D-029/D-045/D-047・#2 D-046・#3 D-033・#4 A-006/A-029・#5 D-008/D-011/D-128〜D-130/X-004・#6 D-013/D-127/X-005・#7 D-072/D-073/D-076/D-083/D-115/I-011・#8 D-092/D-114/A-008/A-020 |
| REQ-LFV-F-018 | 呼称の使い分け | D-027 / E-009 / X-002 |
| REQ-LFV-NF-001 | 性能 | A-009 / D-093 / D-146 / I-008 / E-001〜E-003 / X-031 |
| REQ-LFV-NF-002 | 既存データとの互換性 | D-067〜D-071 / D-089 / D-142 / D-151 / I-003〜I-006 / I-010 / I-019 / I-021 / I-022 / E-007 |
| REQ-LFV-NF-003 | 認可 | X-008 / X-012 |
| REQ-LFV-NF-004 | 用語の一貫性 | D-004 / D-005 / D-018 / D-023 / D-024 / D-027 / E-009 / X-002 |
| REQ-LFV-NF-005 | アーキテクチャ制約 | D-017 / A-039 / X-038 |
| REQ-LFV-NF-006 | 品質・テスト | §1.4（TDD サイクル） / §4.1（境界値） / 本文書全体 |
| REQ-LFV-NF-007 | 運用・可観測性 | X-007（フォールバックのログなし） / I-022（移行バッチなし＝マイグレーション1件のみ） |

### 設計書の要素とテストケースの対応（漏れ確認）

| 設計書の要素 | テストケース |
|------------|------------|
| §4.2.1 `FlowAxis` | D-018 / D-019 |
| §4.2.2 `EvaluationPeriod` / `EvaluationPeriods`（ファーストクラスコレクション） | D-001〜D-017 |
| §4.2.3 `FlowQuadrant`（ラベル・キー・ランク・責任部署） | D-023〜D-028 / D-062〜D-066 |
| §4.2.4 `is_no_incoming_record` | D-058〜D-061 |
| §4.2.5 `FlowSelection` / `REFERENCE_FLOW_SELECTION` | D-020〜D-022 |
| §4.4 `is_within_evaluation_period` | D-029〜D-040 |
| §4.4 `resolve_flow_quadrant` | D-041〜D-053 |
| §4.4 `resolve_flow_quadrant_matrix` | D-054〜D-057 |
| §4.4 `normalize_flow_quadrant` | D-067〜D-076 |
| §4.4 `is_flow_escalated` | D-077〜D-083 |
| §4.4 境界表（4行） | D-029 / D-030 / D-033 / D-034〜D-036 |
| §5.1 `critical_count` / `warning_count` の詰め替え（4箇所） | I-004〜I-006 |
| §5.2 旧ラベル互換写像（6行） | D-067〜D-073 / I-010 / I-011 |
| §5.2 深刻化判定 | D-077〜D-083 / I-012〜I-016 |
| §5.3 残置カラム | I-019 |
| §6.1 URL クエリ（3種・フォールバック） | D-124〜D-133 / X-003〜X-007 |
| §6.2 クライアント配信ペイロード | D-143〜D-149 / E-001 |
| §6.3 CSV | D-139〜D-142 / A-012〜A-020 |
| §6.4 `DashboardBannerContext`（tone 4分岐） | A-021〜A-030 |
| §6.5 撤去する API・VO | D-150〜D-154 / A-038 / A-039 / I-017 / X-013 / X-014 / X-017 |
| §6.6.1 判定条件セレクタ | X-001〜X-003 / X-033 |
| §6.6.2 一覧列 | D-100〜D-102 / X-009 / X-021 |
| §6.6.3 件数サマリ | D-109〜D-116 / E-005 |
| §6.6.4 絞り込み | D-094〜D-099 / X-016 |
| §6.6.5 判定ルールダイアログ | D-084〜D-087 / A-003 |
| §6.6.6 呼称の使い分け | D-027 / E-009 |
| §6.6.7 配色（4区分） | X-025〜X-028 |
| §7.3 削除ファイル・`counts_toward_alert_summary` | D-123 / A-038 / X-036 |
| §8 エラーハンドリング（10ケース） | §4.2 の表で全件対応 |
| §9 R-1（撤去残存） | X-036 / X-037 / D-099 / D-102 / D-116 / D-123 / D-134 / D-149 |
| §9 R-2（安全側の正規化） | D-070 / D-083 / E-008 |
| §9 R-3（ペイロード増） | E-001 / E-002 |
| §9 R-4（件数不一致） | E-006 / X-024 |
| §9 R-5（CSS 共有ブロック） | X-027 |
| §9 R-6（RenameField ロールバック） | I-021（逆方向の自動生成を確認）+ 手動確認 |
| §9 R-7（責任部署が暫定） | X-009（見出しの注記） |
| §9 R-8（`shipment_trend` の同名 API） | X-014 |

---

## レビュー履歴

<!-- test-design-review-l1 がこのセクションに追記する。作成時点では見出しのみ残す。 -->

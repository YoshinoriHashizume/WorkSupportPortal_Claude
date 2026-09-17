# テスト設計書: 単一の判定期間による流動区分と推奨アクションの表示

文書ID: TEST-SINGLE-FLOW-VIEW-2026-001
作成日: 2026/09/16
更新日:
対応文書: [design.md](./design.md)（DESIGN-SINGLE-FLOW-VIEW-2026-001、Design-L1 PASS）、[requirements.md](./requirements.md)（REQ-SINGLE-FLOW-VIEW-2026-001、承認済み）、[ubiquitous_language.md](../../ubiquitous_language.md)
テスト戦略reference: test-strategy version 1.1
テストフレームワークreference: django-pytest version 1.0

---

## 1. テスト戦略

### 1.1 テスト対象のスコープ

| 対象 | テストする | 備考 |
|---|---|---|
| 判定期間 VO・流動区分の判定・ランク・旧称写像（design §4.1〜4.2） | ○ | 第 1 段階。最重点 |
| 推奨アクション・状況テンプレート（§4.3）と定義ファイルの上書き | ○ | 第 1 段階 |
| 内示推移・照合単位・需要予測・在庫切れ予測月・在庫月数（§4.4〜4.6） | ○ | 第 2 段階。最重点 |
| 一覧クエリ・ペイロード・件数・CSV・判定ルール表（§6.1〜6.3・6.8） | ○ | 第 1/2 段階 |
| 取込ユースケースの制御フロー（§6.7）・内示受注クエリ（§6.6） | ○ | 第 2 段階 |
| 一覧画面・ダッシュボード・詳細ダイアログの HTML/JS（§6.3〜6.5） | ○ | HTTP 結合テスト＋JS ソース断言（既存方式） |
| 深刻化による未確認化（A-201）のランク比較 | ○ | 既存テストの基準差し替え |
| リリース時の確認状態リセット（REQ-SFV-F-020） | 手順として確認 | 既存機能。受け入れ基準 #11 で検証 |
| 推定在庫推移（V-218）の JS 実装 | × | 変更なし（04 の既存テストで担保） |
| Oracle 実接続 | × | `rows_as_dicts` を返すスタブ接続で SQL 文字列と変換を検証（既存 `test_incoming_trend_query.py` の方式） |

### 1.2 テストレイヤーの方針

| レイヤー | テスト種別 | テスト方針 | DB依存 |
|---------|----------|----------|--------|
| Domain（`flow_quadrant` / `recommended_action` / `unconfirmed_order_trend` / `reconciliation_unit` / `demand_forecast` / `list_query` / `list_client_data` / `export_csv` / `row_counts`） | 単体 | 純粋関数・VO を直接呼ぶ。dict 行はテスト内で最小構成を組む | 不要 |
| Application（`import_stock` / `list_page` / `portal_dashboard` / `export_csv`） | 単体 | ゲートウェイ・リポジトリを Mock/スタブに置換。domain は実物 | 不要 |
| Infrastructure（`summary_queries.fetch_unconfirmed_orders` / `summary_aggregation` / `config/recommended_actions`） | 結合 | Oracle はカーソルスタブ。定義ファイルは `tmp_path` に実ファイルを置く | 不要（Oracle スタブ）/ 一部 DB |
| Interfaces（一覧・CSV・ダッシュボード・設定） | 結合 | Django test client で HTTP → HTML/JSON/CSV を検証。既存の `store_summary_snapshot` fixture で行を投入 | 必要 |
| JS（`inventory-order-alert-list*.js`） | ソース断言 | 既存 `test_inventory_order_alert_list_js.py` 方式。数値ロジックは JS に置かないため断言は配線と描画に限る | 不要 |

### 1.3 テスト優先順位

1. **Domain（P0）**: 判定期間・流動区分・ランク・需要予測・在庫切れ予測月・在庫月数。ここが業務価値そのもの（コアサブドメイン）
2. **Application（P1）**: 取込フローで需要予測が付与されること、内示受注の取得失敗が取込を止めないこと
3. **Interfaces（P1）**: 旧称・判定軸が画面に出ないこと、旧 URL でエラーにならないこと、CSV 列
4. **Infrastructure（P2）**: SQL 条件・定義ファイルの読み込み

### 1.4 TDD方針

CLAUDE.md §2 のとおり Phase 5 は TDD（Red → Green → Refactor）。テストケース ID をテスト関数の docstring に記し、`make test-fast` 相当（`pytest application/inventory_order_alert/tests -k "not views"`）で Domain/Application を回し、コミット前に全件を実行する。実データでの数値検証（§3.3）は自動テストとは別に Node/Python で実施し DECISIONS.md に記録する（04 と同じ）。

---

## 2. テストケース一覧

ID 規約: `TC-SFV-{D|A|I|X}-nnn`（D=Domain, A=Application, I=Infrastructure, X=Interfaces/JS）。段階列は 1/2。

### 2.1 Domain層テスト

#### バリューオブジェクト: EvaluationPeriod / EvaluationPeriods（`flow_quadrant.py`、段階 1）

| # | テストケース | 入力 | 期待結果 | 対応REQ-ID | 優先度 |
|---|---|---|---|---|---|
| TC-SFV-D-001 | 1/3/5 年で生成できる | `EvaluationPeriod(1)`, `(3)`, `(5)` | `months` が 12/36/60、`key` が `Y1/Y3/Y5`、`label` が `1年/3年/5年` | F-001 | P0 |
| TC-SFV-D-002 | 1/3/5 以外は生成を拒否する | `EvaluationPeriod(2)`, `(6)`, `(0)`, `(-1)` | `ValueError` | F-001, F-002 | P0 |
| TC-SFV-D-003 | 等価性と不変性 | `EvaluationPeriod(3) == EvaluationPeriod(3)`、属性代入 | 等しい／`FrozenInstanceError` | F-001 | P2 |
| TC-SFV-D-004 | コレクションは 3 件固定で既定が 1 年 | `EVALUATION_PERIODS` | `len == 3`、`default.years == 1`、`find("Y3").years == 3`、`find("L3") is None`、`find_by_years(2) is None` | F-001, F-002 | P0 |
| TC-SFV-D-005 | 判定軸の定数・メソッドが存在しない | モジュール属性 | `FLOW_AXIS_LOW_FLOW` / `FLOW_AXIS_DORMANT` / `for_axis` / `default_for_axis` が `hasattr` で偽 | F-002 | P1 |
| TC-SFV-D-006 | 固定基準は既定の判定期間 | `REFERENCE_FLOW_SELECTION` | `.period == DEFAULT_EVALUATION_PERIOD`（1 年） | F-015 | P0 |

#### バリューオブジェクト: 流動区分（`flow_quadrant.py`、段階 1）

| # | テストケース | 入力 | 期待結果 | 対応REQ-ID | 優先度 |
|---|---|---|---|---|---|
| TC-SFV-D-010 | 期間内入荷なし・出荷ありは低流動品（入荷なし） | 基準日 2026/09/07、判定期間 1 年、最終入荷 2025/04/02、最終出荷 2026/06/01 | `QUADRANT_LOW_FLOW_NO_INCOMING` | F-003 | P0 |
| TC-SFV-D-011 | 期間内入荷あり・出荷なしは低流動品（出荷なし） | 判定期間 3 年、最終入荷 2025/04/02、最終出荷 2023/07/27 | `QUADRANT_LOW_FLOW_NO_SHIPMENT` | F-003 | P0 |
| TC-SFV-D-012 | 両方なしは在庫死蔵品 | 判定期間 1 年、最終入荷 2025/04/02、最終出荷 2023/07/27 | `QUADRANT_DORMANT_STOCK` | F-003 | P0 |
| TC-SFV-D-013 | 両方ありは通常流動品 | 判定期間 5 年、同上の日付 | `QUADRANT_NORMAL_FLOW` | F-003 | P0 |
| TC-SFV-D-014 | 96160-00500 の受け入れ基準 #2 を再現 | 基準日 2026/09/07、入荷 2025/04/02、出荷 2023/07/27 を 1/3/5 年で | 死蔵 / 出荷なし / 通常 | F-003, 受入#2 | P0 |
| TC-SFV-D-015 | 境界日ちょうどは期間内 | 基準日 2026/09/07、判定期間 1 年、最終出荷 2025/09/07 | 期間内出荷あり | F-001 | P0 |
| TC-SFV-D-016 | 境界日の前日は期間外 | 最終出荷 2025/09/06 | 期間内出荷なし | F-001 | P0 |
| TC-SFV-D-017 | 未来の日付は期間内、空は期間外 | 最終入荷 2027/01/01 / `None` | あり / なし | F-018 | P1 |
| TC-SFV-D-018 | 事前判定行列は Y1/Y3/Y5 の 3 キー | `resolve_flow_quadrant_matrix(...)` | キー集合 `{"Y1","Y3","Y5"}`、値は新キー | F-003 | P0 |
| TC-SFV-D-019 | ランクは 入荷なし0 → 死蔵1 → 出荷なし2 → 通常3 | `flow_quadrant_sort_rank` | 0/1/2/3 | F-010 | P0 |
| TC-SFV-D-020 | 旧称ラベルは新区分へ正規化 | `"供給リスク品"`, `"在庫過剰リスク品"`, `"重点"`, `"警告（出荷なし）"` | 入荷なし / 出荷なし / 入荷なし / 出荷なし | F-003, F-017 | P0 |
| TC-SFV-D-021 | 旧キーは新キーへ正規化 | `"supply-risk"`, `"excess-stock-risk"` | 入荷なし / 出荷なし のラベル | F-002, F-010 | P0 |
| TC-SFV-D-022 | 未知の値は通常流動品に寄せる | `"象限1"`, `""`, `None` | `QUADRANT_NORMAL_FLOW` | F-018 | P1 |
| TC-SFV-D-023 | 深刻化の判定はランクの小さい方向のみ | (死蔵→入荷なし), (通常→死蔵), (入荷なし→死蔵), (旧称 供給リスク品→入荷なし) | True, True, False, False | F-015 | P0 |
| TC-SFV-D-024 | 責任部署の割当て | 4 区分 | 調達G・営業G・生産管理 / 調達G / 営業G / 生産管理 | F-004 | P1 |
| TC-SFV-D-025 | 旧称の定数名が存在しない | モジュール属性 | `QUADRANT_SUPPLY_RISK` / `QUADRANT_EXCESS_STOCK_RISK` が存在しない | F-019 | P1 |

#### バリューオブジェクト: RecommendedAction / RecommendedActions（`recommended_action.py`、段階 1）

| # | テストケース | 入力 | 期待結果 | 対応REQ-ID | 優先度 |
|---|---|---|---|---|---|
| TC-SFV-D-030 | 既定の 4 区分がすべて定義されている | `DEFAULT_RECOMMENDED_ACTIONS` | 4 件。低流動品（入荷なし）の `action` に「仕入先」「生産継続」を含む | F-006 | P0 |
| TC-SFV-D-031 | 通常流動品は状況・アクションが空 | `for_quadrant(通常流動品)` | `status_template == ""`、`action == ""` | F-004 | P0 |
| TC-SFV-D-032 | 未知の区分で生成を拒否 | `RecommendedAction(quadrant="供給リスク品", ...)` | `ValueError` | F-019 | P1 |
| TC-SFV-D-033 | 4 区分に欠けがあるコレクションは拒否 | 3 件で `RecommendedActions(...)` | `ValueError` | F-006 | P1 |
| TC-SFV-D-034 | 文言の上書きは action のみ差し替わる | `with_action_texts({"low-flow-no-incoming": "X"})` | 当該区分の `action == "X"`、`status_template`・`departments` は不変。他区分は既定 | F-006, NF-007 | P0 |
| TC-SFV-D-035 | 上書きの未知キーは無視 | `with_action_texts({"foo": "X"})` | 既定と等しい | F-018 | P2 |
| TC-SFV-D-036 | 状況の描画（入荷なし） | 判定期間 1 年、最終入荷 `2025/04/02` | 「最終入荷 2025/04/02」と「1年」を含む | F-004, F-005 | P0 |
| TC-SFV-D-037 | 入荷実績なしは日付の代わりに文言 | `no_incoming_record=True`、最終入荷 `""` | 「入荷実績なし」を含み `{last_incoming}` が残らない | F-005 | P0 |
| TC-SFV-D-038 | 状況の描画（出荷なし・死蔵） | 出荷なし: 最終出荷 `2023/07/27` / 死蔵: 両方 | それぞれ該当日付を含む。プレースホルダが残らない | F-004 | P1 |

#### 判定ルール表（`flow_quadrant_rules.py`、段階 1）

| # | テストケース | 入力 | 期待結果 | 対応REQ-ID | 優先度 |
|---|---|---|---|---|---|
| TC-SFV-D-040 | 判定ルール行に状況・推奨アクションが含まれる | `build_flow_quadrant_rule_rows()` | 4 行。各行に `quadrant` / `status_template` / `action` / `departments`。順序はランク順 | F-012 | P1 |
| TC-SFV-D-041 | 判定ルール行に判定軸の項目がない | 同上 | `axis` 属性なし、文言に「判定軸」を含まない | F-012, F-019 | P1 |

#### 一覧クエリ・ペイロード・件数・CSV（`list_query.py` / `list_client_data.py` / `row_counts.py` / `export_csv.py`）

| # | テストケース | 入力 | 期待結果 | 対応REQ-ID | 優先度 | 段階 |
|---|---|---|---|---|---|---|
| TC-SFV-D-050 | `period` の年数を解釈する | `{"period": "3"}` | `FlowSelection(EvaluationPeriod(3))` | F-001 | P0 | 1 |
| TC-SFV-D-051 | `period` 不正・旧値・空は既定 | `"6"`, `"2"`, `"abc"`, `""`, 未指定 | 1 年 | F-002, F-018 | P0 | 1 |
| TC-SFV-D-052 | `axis` は無視される | `{"axis": "dormant", "period": "3"}` | 3 年（axis に影響されない） | F-002 | P0 | 1 |
| TC-SFV-D-053 | `flow_quadrant` の旧キーは新キーへ | `{"flow_quadrant": "supply-risk"}` | `"low-flow-no-incoming"` | F-010 | P0 | 1 |
| TC-SFV-D-054 | ペイロードに判定期間 3 値と既定キー | `build_list_client_payload(...)` | `evaluationPeriods` が 3 件（years/key/label）、`defaultPeriodKey == "Y1"`、`flowAxes`・`flowPeriods` キーなし | F-001, F-002 | P0 | 1 |
| TC-SFV-D-055 | ペイロードの推奨アクション定義 | 同上 | `recommendedActions[key]` に `statusTemplate` / `action` / `departments` が 4 区分ぶん | F-004, F-006 | P0 | 1 |
| TC-SFV-D-056 | 行の `flowQuadrants` は Y キー | 行 1 件 | `{"Y1","Y3","Y5"}` | F-003 | P0 | 1 |
| TC-SFV-D-057 | 件数サマリは新区分名の 4 キー | 各区分 1 行ずつ | `{"低流動品（入荷なし）":1, "在庫死蔵品":1, "低流動品（出荷なし）":1, "通常流動品":1}` | F-011 | P0 | 1 |
| TC-SFV-D-058 | ソート既定はランク → 出荷数量降順 | 4 区分の行 | 入荷なし → 死蔵 → 出荷なし → 通常 | F-010 | P0 | 1 |
| TC-SFV-D-059 | 在庫月数ソートは空を末尾 | 在庫月数 3.0 / None / 0.5 | 昇順 0.5, 3.0, None／降順 3.0, 0.5, None | F-010 | P1 | 2 |
| TC-SFV-D-060 | CSV の流動区分は新区分名、判定軸列は空 | 行 1 件（入荷なし） | `流動区分 == "低流動品（入荷なし）"`、`判定軸 == ""`、`判定期間 == "1年"` | F-013, F-019 | P0 | 1 |
| TC-SFV-D-061 | CSV の既存列順は不変で新規列は末尾 | 列定義 | 既存 24 列の順序が現行と一致し、その後に `在庫月数`, `在庫切れ予測月`, `需要予測の算出根拠`, `推奨アクション` | F-013, §6.3 | P0 | 2 |
| TC-SFV-D-062 | CSV に旧称が出ない | 4 区分の行 | 出力全体に「供給リスク品」「在庫過剰リスク品」を含まない | F-019 | P1 | 1 |
| TC-SFV-D-063 | 行に状況・推奨アクションが付与される | `apply_flow_quadrants_to_rows` | `flow_status` / `recommended_action` / `responsible_department` が区分に応じて設定。通常流動品は空 | F-004 | P0 | 1 |

#### バリューオブジェクト: 内示推移（`unconfirmed_order_trend.py`、段階 2）

| # | テストケース | 入力 | 期待結果 | 対応REQ-ID | 優先度 |
|---|---|---|---|---|---|
| TC-SFV-D-070 | 当月残＋3 か月の固定 4 件 | 基準日 2026/09/15、明細 (9/20, 100), (10/5, 200), (11/1, 300), (12/31, 400) | `[{"2026-09":100},{"2026-10":200},{"2026-11":300},{"2026-12":400}]` | F-007 | P0 |
| TC-SFV-D-071 | 当月の基準日より前の所要日は当月残に含めない | (9/10, 50), (9/15, 60) | 当月残 60（境界日ちょうどは含む） | F-007 | P0 |
| TC-SFV-D-072 | 窓の外（4 か月目以降）は無視 | (2027/01/05, 999) | 4 件とも影響なし | F-007 | P1 |
| TC-SFV-D-073 | 内示がない月は 0、明細なしは全 0 | `[]` | `[0,0,0,0]` の 4 件 | F-007, F-017 | P0 |
| TC-SFV-D-074 | 負の数量は 0 として扱う | (10/5, -100), (10/6, 30) | 10 月 30 | F-018 | P0 |
| TC-SFV-D-075 | 年またぎ | 基準日 2026/11/20 | `2026-11, 2026-12, 2027-01, 2027-02` | F-007 | P1 |

#### ファーストクラスコレクション: ReconciliationUnits（`reconciliation_unit.py`、段階 2）

| # | テストケース | 入力 | 期待結果 | 対応REQ-ID | 優先度 |
|---|---|---|---|---|---|
| TC-SFV-D-080 | 1 得意先品番・1 組は単独の単位 | 行 A(item X, pair P) | 1 単位、`item_cds == {X}`、`level1_pairs == {P}` | F-008 | P0 |
| TC-SFV-D-081 | 組を共有する 2 得意先品番は 1 単位 | A(X,P), B(Y,P) | 1 単位、`item_cds == {X,Y}`（96160-00500 と 10523-X0A02 の構造） | F-008 | P0 |
| TC-SFV-D-082 | 得意先品番が複数の組を持つと連結する | A(X,P), B(X,Q), C(Z,Q) | 1 単位、`item_cds == {X,Z}`、`level1_pairs == {P,Q}`（94223-80600 の構造） | F-008, F-018 | P0 |
| TC-SFV-D-083 | 無関係な行は別単位 | A(X,P), B(Y,Q) | 2 単位 | F-008 | P0 |
| TC-SFV-D-084 | 同じ得意先品番の複数得意先は 1 単位に複数行 | A(cust100,X,P), B(cust137,X,P) | 1 単位、`row_keys` に 2 件 | F-008 | P0 |
| TC-SFV-D-085 | `unit_of` は代表キーが同じ単位を返す | 上記 D-081 | `unit_of("X") is unit_of("Y")`（同一）、`key` は最小の得意先品番 | F-009, F-014 | P1 |
| TC-SFV-D-086 | 空の行リスト | `[]` | 0 単位、`unit_of("X")` は `None` | F-017 | P1 |
| TC-SFV-D-087 | level1 が空の行は自身だけの単位 | A(X, ("","")) | 単独。他の空 pair 行と**連結しない**（空キーで全部がつながらないこと） | F-018 | P0 |

#### バリューオブジェクト: DemandForecast と算出関数（`demand_forecast.py`、段階 2）

| # | テストケース | 入力 | 期待結果 | 対応REQ-ID | 優先度 |
|---|---|---|---|---|---|
| TC-SFV-D-090 | 内示があれば内示ベース | 単位 1 行、内示推移 `[10, 100, 200, 300]` | `basis == "内示"`、`current_month_remaining == 10`、`monthly == (100,200,300)`、`monthly_average == 200.0` | F-008 | P0 |
| TC-SFV-D-091 | (得意先, 内作品番) の重複を除いて合算 | 得意先 137 の行が item 96160-00500 と 10523-X0A02 の 2 行（同じ内作品番・同じ内示 30/30/28）＋得意先 104 の行（194/186/169） | 10 月 224、11 月 216、12 月 197（137 は 1 回だけ） | F-008, 受入#4 | P0 |
| TC-SFV-D-092 | 内示が 3 か月に満たない場合は存在する月で平均 | 内示推移 `[0, 300, 0, 0]` は「3 か月とも 0」ではないので内示ベース、平均は 300/1 ではなく**存在する月**の定義に従う | 設計 §4.6 の定義どおり（内示が入っている月数で割る）。期待値をテストで固定 | F-008, §6.2 | P0 |
| TC-SFV-D-093 | 内示ゼロで出荷実績があれば実績ベース | 内示 `[0,0,0,0]`、出荷推移の直近 12 か月合計 1,200 | `basis == "実績ベース"`、`monthly_average == 100.0` | F-008 | P0 |
| TC-SFV-D-094 | 内示も出荷もゼロなら なし | 内示 `[0,0,0,0]`、出荷 0 | `basis == "なし"`、`monthly_average == 0` | F-008 | P0 |
| TC-SFV-D-095 | 内示推移を持たない旧行は なし（または実績ベース） | 行に `unconfirmed_order_trend` キーなし、出荷あり | `basis == "実績ベース"`（出荷なしなら なし） | F-017 | P0 |
| TC-SFV-D-096 | basis は 3 値以外を拒否 | `DemandForecast(basis="内示受注", ...)` | `ValueError` | — | P1 |
| TC-SFV-D-097 | 在庫月数 = 在庫合計 ÷ 月平均、小数 1 桁 | 在庫 31,970、平均 212.3 | `150.6` | F-009 | P0 |
| TC-SFV-D-098 | 在庫月数は需要なし・平均 0 で空 | basis なし / 平均 0 | `None` | F-009 | P0 |
| TC-SFV-D-099 | 在庫切れ予測月（内示で当月残を引く） | 基準日 2026/09/15、在庫 500、当月残 100、monthly (200,200,200) | 残 400 → 10 月 200 → 11 月 0 → 12 月 -200 → `"2026-12"` | F-009 | P0 |
| TC-SFV-D-100 | 在庫切れ予測月（4 か月目以降は平均） | 在庫 1,000、当月残 0、monthly (100,100,100)、平均 100 | 2027-06 に負（10 か月目） | F-009 | P0 |
| TC-SFV-D-101 | 在庫が当月残より少なければ当月 | 在庫 50、当月残 100 | `"2026-09"` | F-018 | P0 |
| TC-SFV-D-102 | 在庫 0 で需要ありは当月・在庫月数 0.0 | 在庫 0、平均 100 | `"2026-09"` / `0.0` | F-018 | P0 |
| TC-SFV-D-103 | 120 か月以内に尽きなければ空 | 在庫 1,000,000、平均 1 | `None` | F-018 | P1 |
| TC-SFV-D-104 | 需要なしなら予測月は空 | basis なし | `None` | F-009 | P0 |
| TC-SFV-D-105 | 単位の在庫合計: 該当なし（空）は 0、未取得は 0 | 行 A `stock_qty=""`、行 B `stock_qty="100"`、行 C キーなし | `100.0` | F-009 | P0 |
| TC-SFV-D-106 | 単位の全品番が未取得なら在庫合計は None | 全行 `stock_qty` キーなし | `None` → 在庫月数・予測月とも `None` | F-009, F-018 | P0 |
| TC-SFV-D-107 | 同じ得意先品番の重複行は在庫を 1 回だけ数える | 得意先 100/137 の 96160-00500 行（各 12,970） | 12,970（25,940 ではない） | F-009 | P0 |
| TC-SFV-D-108 | `attach_demand_forecast` は全行に単位の値を複製する | D-091 の 3 行 | 3 行とも同じ `demand_forecast_basis` / `months_of_stock` / `stockout_forecast_month` / `reconciliation_unit_key` | F-008, F-009 | P0 |
| TC-SFV-D-109 | `attach_demand_forecast` は入力行を破壊しない | 同上 | 元の dict に新キーが増えていない（コピーを返す） | NF-005 | P2 |

### 2.2 Application層テスト

| # | テストケース | 入力 | 期待結果 | 対応REQ-ID | 優先度 | 段階 |
|---|---|---|---|---|---|---|
| TC-SFV-A-001 | 取込フローで需要予測が付与されてから保存される | `ImportStock.execute` を集計ゲートウェイ（内示推移つき行を返すスタブ）とスナップショットリポジトリ（Mock）で実行 | `store` に渡された行に `demand_forecast_basis` 等が含まれる。呼び出し順は 集計 → 付与 → 保存 | F-007〜F-009 | P0 | 2 |
| TC-SFV-A-002 | 内示受注の取得失敗でも取込は成功する | ゲートウェイが内示なし＋`aggregation_error="内示受注の取得に失敗: ORA-…"` を返す | 取込は完了、需要予測は実績ベース／なし、取込結果メッセージにエラー文を含む | F-018, NF-007 | P0 | 2 |
| TC-SFV-A-003 | 一覧ユースケースは判定期間を年数で受け取り文脈に出す | `query_params={"period":"5"}` | `context.flow_selection.period.years == 5`、文脈に `flow_axis_options` がない | F-001, F-002 | P0 | 1 |
| TC-SFV-A-004 | ダッシュボードの件数は判定期間 1 年で固定判定 | 行: 入荷 2025/04、出荷 2026/06（1 年なら入荷なし、3 年なら通常） | 帯の件数で「低流動品（入荷なし）」に数えられる。条件ラベルに「1年」を含み「3か月」「判定軸」を含まない | F-015 | P0 | 1 |
| TC-SFV-A-005 | CSV ユースケースは選択中の判定期間で判定する | `period=5` | 出力行の流動区分が 5 年判定の値 | F-013 | P1 | 1 |
| TC-SFV-A-006 | 深刻化による未確認化は新ランクで判定する（既存テストの基準差し替え） | 確認時 在庫死蔵品 → 再取込後 低流動品（入荷なし） | 未確認に戻る。逆方向は戻らない | F-015 | P0 | 1 |
| TC-SFV-A-007 | 推奨アクションの上書きが一覧ペイロードに反映される | wiring で `RecommendedActions` に上書きを与える | `recommendedActions["low-flow-no-incoming"].action` が上書き値 | F-006 | P1 | 1 |

### 2.3 Infrastructure層テスト

| # | テストケース | 入力 | 期待結果 | 対応REQ-ID | 優先度 | 段階 |
|---|---|---|---|---|---|---|
| TC-SFV-I-001 | 内示受注クエリの条件 | `fetch_unconfirmed_orders(stub_conn, as_of_date=2026/09/15)` | SQL に `T_UNCNFM_ODR`、`DEL_FLG = '0'`、`UNCNFM_REQUIRED_DATE >= :as_of_date`、`< :window_end` を含み、`window_end == 2027-01-01` | F-007, NF-001 | P0 | 2 |
| TC-SFV-I-002 | 内示受注の行変換 | カーソルスタブが `(cust, item, date, qty)` を返す | `(cust_code, item_cd, date, int)` のタプル。空白 TRIM、`None` 数量は 0 | F-007 | P0 | 2 |
| TC-SFV-I-003 | 内示受注クエリは取込で 1 回だけ発行 | `build_summary_rows` を通す | `fetch_unconfirmed_orders` の呼び出し回数 1 | NF-001 | P1 | 2 |
| TC-SFV-I-004 | 行に内作品番と内示推移が付与される | 既存 `test_build_summary_rows` の fixture に内示を追加 | 行に `internal_item_cd`、`unconfirmed_order_trend`（4 件）。内作品番が解決できない行は `""` と全 0 | F-007, F-018 | P0 | 2 |
| TC-SFV-I-005 | `build_summary_rows` は需要予測を計算しない | 同上 | 行に `demand_forecast_basis` が**ない**（use_case が付与する） | NF-005 | P1 | 2 |
| TC-SFV-I-006 | Oracle 例外時は内示推移を空にして続行 | `fetch_unconfirmed_orders` が `OracleQueryError` | 行は返り、`aggregation_error` に「内示受注の取得に失敗」を含む | F-018 | P0 | 2 |
| TC-SFV-I-007 | 定義ファイルがあれば文言を上書き | `tmp_path/recommended_actions.json` に `{"low-flow-no-incoming":"X"}` | `load_recommended_actions(path).for_quadrant(入荷なし).action == "X"` | F-006, NF-007 | P0 | 1 |
| TC-SFV-I-008 | 定義ファイルがなければ既定 | 存在しないパス | `DEFAULT_RECOMMENDED_ACTIONS` と等価 | F-006 | P0 | 1 |
| TC-SFV-I-009 | 定義ファイルが不正 JSON なら警告ログを出して既定 | 壊れた JSON | 既定と等価、`caplog` に WARNING | F-018 | P1 | 1 |
| TC-SFV-I-010 | 確認記録の旧称は読込時に新区分へ | `confirmed_flow_quadrant="供給リスク品"` の確認記録 | 突合後に `低流動品（入荷なし）` として扱われる | F-017 | P1 | 1 |

### 2.4 Interfaces層テスト

| # | テストケース | 入力 | 期待結果 | 対応REQ-ID | 優先度 | 段階 |
|---|---|---|---|---|---|---|
| TC-SFV-X-001 | 判定軸セレクタがなく判定期間セレクタがアクション行にある | 一覧 HTML | `id="ioa-flow-axis"` なし、`id="ioa-evaluation-period"` が `ioa-table-actions` 内で `ioa-alert-rules-open` より前 | F-001, F-002, 受入#1 | P0 | 1 |
| TC-SFV-X-002 | 判定期間の選択肢は 1/3/5 年のみ | 同上 | `option` が `1年/3年/5年` の 3 件、既定選択 1 年 | F-001 | P0 | 1 |
| TC-SFV-X-003 | 画面に旧称・判定軸が出ない | 4 区分の行を投入した一覧 HTML | 「供給リスク品」「在庫過剰リスク品」「判定軸」「低流動判定軸」「死蔵判定軸」を含まない | F-019 | P0 | 1 |
| TC-SFV-X-004 | セルに区分・状況・推奨アクション・責任部署が出る | 入荷なしの行 | `ioa-flow-quadrant` に「低流動品（入荷なし）」、`ioa-flow-status` に最終入荷日、`ioa-flow-action`、`ioa-flow-departments` | F-004, 受入#3 | P0 | 1 |
| TC-SFV-X-005 | 通常流動品のセルは空 | 通常の行 | `<td class="ioa-flow-cell">` 内に区分・アクションのテキストがない | F-004 | P0 | 1 |
| TC-SFV-X-006 | 入荷実績なしバッジが併記される | 最終入荷日空の行 | `ioa-no-incoming-badge` あり、状況に「入荷実績なし」 | F-004, F-005 | P1 | 1 |
| TC-SFV-X-007 | 旧 URL（axis・月単位 period）でエラーにならない | `?axis=low_flow&period=3` | 200、判定期間 1 年で表示 | F-002, 受入#10 | P0 | 1 |
| TC-SFV-X-008 | 旧キーの絞り込みは新区分で絞れる | `?flow_quadrant=supply-risk` | 200、絞り込み値が `low-flow-no-incoming` | F-010 | P1 | 1 |
| TC-SFV-X-009 | 件数サマリが新区分名 | 一覧 HTML | 「低流動品（入荷なし） N 件 / 在庫死蔵品 N 件 / 低流動品（出荷なし） N 件 / 通常流動品 N 件」 | F-011 | P0 | 1 |
| TC-SFV-X-010 | 判定ルールダイアログの列 | 一覧 HTML | ヘッダに 状況 / 推奨アクション / 責任部署、判定軸の説明なし | F-012 | P1 | 1 |
| TC-SFV-X-011 | 詳細ダイアログの流動区分区分 | 一覧 HTML（テンプレート） | `ioa-detail-flow-status` / `ioa-detail-recommended-action` / `ioa-detail-evaluation-period` の要素がある | F-014 | P1 | 1 |
| TC-SFV-X-012 | メニュー画面のアラート帯が新区分名・1 年 | ダッシュボード HTML | 4 区分名、「判定期間 1年」、「3か月」なし | F-015, 受入#6 | P0 | 1 |
| TC-SFV-X-013 | CSV 出力の列と値 | `export.csv?period=1` | ヘッダに `流動区分`、値は新区分名、`判定軸` 列は空、第 2 段階で末尾 4 列 | F-013, 受入#7 | P0 | 1/2 |
| TC-SFV-X-014 | 旧スナップショット（内示なし）で一覧が表示できる | `unconfirmed_order_trend` のない行を投入 | 200、緊急度要素は非表示、需要予測「なし」 | F-017, 受入#9 | P0 | 2 |
| TC-SFV-X-015 | 緊急度の表示（内示ベース） | 需要予測つきの行 | `ioa-flow-urgency` に在庫月数・在庫切れ予測月・「内示」 | F-004, F-009 | P0 | 2 |
| TC-SFV-X-016 | 詳細ダイアログの需要予測区分 | テンプレート | `ioa-detail-demand-forecast-section` が推定在庫推移とメモの間にある | F-014 | P1 | 2 |
| TC-SFV-X-017 | JS: 状態に `flowAxis` がなく `evaluationPeriod` がある | list-client.js ソース | `flowAxis` を含まない、`state.periodKey`（または相当）と `evaluationPeriods` を参照 | F-002 | P1 | 1 |
| TC-SFV-X-018 | JS: セル描画は `recommendedActions` のテンプレートに置換するだけ | 同上 | `statusTemplate` の `{period}` / `{last_incoming}` / `{last_ship}` を `replace` している。判定条件（日付比較）を JS に持たない | F-004, NF-005 | P1 | 1 |
| TC-SFV-X-019 | JS: URL 同期に `period` のみ | 同上 | `params.set("period", …)` あり、`params.set("axis"` なし | F-016 | P1 | 1 |
| TC-SFV-X-020 | JS: 在庫月数ソートのキー | 同上 | `months_of_stock` のソート分岐（空は末尾） | F-010 | P2 | 2 |
| TC-SFV-X-021 | 設定画面の確認状態リセットが従来どおり動く（移行措置の手段） | 管理者で `POST /api/inventory-order-alert/confirmation/reset` | 全件未確認、メモ履歴は残る（既存テストで担保。本書からは受入#11 として参照） | F-020, 受入#11 | P0 | 1 |

---

## 3. テストデータ

### 3.1 正常系テストデータ

**行の最小構成（Domain 用）**

```python
ROW_100 = {"cust_code": "100", "item_cd": "96160-00500", "internal_item_cd": "96160-00500-9065",
           "level1_item_cd": "96160-00500-9065", "level1_vend_cd": "9065",
           "last_incoming_date": "2025/04/02", "last_ship_date": "2023/07/27",
           "stock_qty": "12970", "shipment_trend": [...24件 全0...],
           "unconfirmed_order_trend": [{"month":"2026-09","qty":0}, ... 全0]}
ROW_104 = {... "cust_code": "104", 出荷 8,000（直近12か月に分散）, 内示 [0,194,186,169] ...}
ROW_137_A = {... "cust_code": "137", "item_cd": "96160-00500", 内示 [0,30,30,28] ...}
ROW_137_B = {... "cust_code": "137", "item_cd": "10523-X0A02", "stock_qty": "19000", 内示 [0,30,30,28] ...}
```

- 96160-00500 の照合単位（D-081・D-091・D-107）は実データの構造をそのまま最小化したもの。期待値: 在庫合計 31,970、10 月需要 224
- 94223-80600 型（D-082）: 1 得意先品番が 4 組の level1 に紐づく構造を 2 組に縮めて使う

**判定期間の境界（D-015〜D-017）**: 基準日 `2026/09/07`、1 年境界 `2025/09/07`

**内示推移（D-070〜D-075）**: 基準日 `2026/09/15`、明細は `(date, qty)` タプル

**Interfaces 用**: 既存の `_sample_export_row()` と `store_summary_snapshot(import_record, rows, as_of_date=date(2026, 6, 17))` を流用し、行の日付だけ区分ごとに差し替える

### 3.2 異常系テストデータ

| データ | 用途 |
|---|---|
| `period` = `"6"`, `"2"`, `"abc"`, `""`, `"-1"` | D-051 |
| `flow_quadrant` = `"supply-risk"`, `"象限1"`, `""` | D-021, D-022, D-053 |
| `confirmed_flow_quadrant` = `"供給リスク品"`, `"重点"` | D-020, I-010 |
| 内示数量 `-100`、`None` | D-074, I-002 |
| `stock_qty` = `""`（該当なし）／キーなし（未取得） | D-105, D-106 |
| `level1_item_cd` = `""`, `level1_vend_cd` = `""` | D-087 |
| 壊れた JSON `{"low-flow-no-incoming": ` | I-009 |
| `OracleQueryError("ORA-12541")` | I-006, A-002 |
| `unconfirmed_order_trend` キーなしの行 | D-095, X-014 |

### 3.3 実データでの数値検証（自動テスト外、DECISIONS.md に記録）

| 検証 | 期待 |
|---|---|
| 2026/09/07 取込スナップショットで照合単位を Python 実装で構築 | 1,994 単位、複数品番 25 単位・144 行（04 の JS 実装と一致） |
| 96160-00500 の需要予測 | basis 内示、10 月 224、在庫合計 31,970、在庫月数 ≒ 150 |
| 内示がない低流動品（入荷なし）の行の割合 | 約 26%（74% が内示あり）が実績ベース／なしになる |
| メニュー画面のアラート帯の件数変化（3 か月 → 1 年） | 変化量を記録し周知文に使う（R-3） |
| 単位（バラ数）の整合（R-5） | 在庫月数が桁で異常な単位がないか上位/下位 10 件を目視 |

---

## 4. 境界値・異常系のカバレッジ

### 4.1 境界値テスト

| 対象 | 境界値 | テストケース |
|------|--------|------------|
| 判定期間の年数 | 0 / 1 / 2 / 3 / 5 / 6 | D-001, D-002, D-051 |
| 期間内判定の日付 | 境界日の前日 / 当日 / 翌日 / 未来 / 空 | D-015〜D-017 |
| 内示推移の窓 | 当月の基準日前日 / 当日 / 翌々々月末 / 4 か月目初日 | D-071, D-072 |
| 内示数量 | -1 / 0 / 正 | D-074 |
| 在庫合計 | 当月残未満 / ちょうど 0 / 大量（120 か月超） | D-101〜D-103 |
| 需要の月平均 | 0 / 正 | D-098 |
| 在庫月数の丸め | 150.55 → 150.6 | D-097 |
| 照合単位の行数 | 0 / 1 / 複数 | D-080, D-086 |
| 推奨アクションの区分数 | 3 / 4 | D-033 |

### 4.2 異常系テスト

| 対象 | 異常ケース | 期待される振る舞い |
|------|----------|------------------|
| URL パラメータ | 旧軸・旧期間・不正値 | 既定にフォールバック、200 |
| 確認記録 | 旧称で保存 | 新区分に正規化して比較 |
| 内示受注の取得 | Oracle 例外 | 取込成功・内示空・メッセージ |
| 内作品番の解決 | 対応なし・有効期間外 | 内示推移空・実績ベース／なし |
| 定義ファイル | なし・不正 JSON | 既定文言・警告ログ |
| 旧スナップショット | 追加キーなし | 需要予測なし・画面 200 |
| 在庫 | 全品番未取得 | 在庫月数・予測月 None |
| level1 空 | 空キー同士の連結 | 連結しない（D-087） |

### 4.3 エッジケース

| ケース | 扱い | テストケース |
|---|---|---|
| 同じ得意先が 2 つの得意先品番で同じ内作品番を持つ（内示の重複） | (得意先, 内作品番) で 1 回 | D-091 |
| 同じ得意先品番の行が複数得意先（在庫の重複） | 得意先品番で 1 回 | D-107 |
| 1 得意先品番が複数の内作品番（94223-80600 型） | 連結成分で扱う | D-082 |
| 立ち上がり品（内示あり・出荷なし・在庫 0） | 区分は通常／出荷なし、予測月は当月、緊急度の対象外 | D-102（値）、X-015 で表示条件 |
| 年またぎの内示窓 | 2027-01/02 を含む | D-075 |
| 取込の同時実行 | 既存の排他（`import_lock`）で担保。本書では対象外 | — |
| 大量データ（2,298 行） | 照合単位の構築は O(n α(n))。§3.3 の実データ検証で所要時間を記録 | — |

---

## 5. テスト環境

### 5.1 テスト実行コマンド

```bash
# Domain / Application（DB 不要・高速）
pytest application/inventory_order_alert/tests -q -k "flow_quadrant or recommended_action or unconfirmed_order or reconciliation_unit or demand_forecast or list_query or list_client_data or export_csv or import_stock"

# アプリ全体
pytest application/inventory_order_alert/tests -q

# コミット前（全体＋アーキテクチャ検証）
pytest -q && python manage.py check
```

### 5.2 テストデータの準備方法

| 方式 | 用途 |
|---|---|
| テストコード内の dict（§3.1） | Domain / Application |
| `unittest.mock.Mock` / スタブ接続（`rows_as_dicts` 互換） | Application のゲートウェイ、Infrastructure の Oracle |
| `tmp_path` に JSON | 定義ファイル |
| `store_summary_snapshot()` fixture（既存） | Interfaces |
| 既存 `tests/fixtures/` | 変更なし |

### 5.3 既存テストへの影響

| 既存テスト | 対応 |
|---|---|
| `test_flow_quadrant.py` / `test_flow_quadrant_edge_cases.py` / `test_flow_quadrant_rules.py` | 判定軸・旧称の前提を本書の D-0xx に置き換える |
| `test_list_query.py` / `test_list_filter.py` / `test_list_client_data.py` / `test_row_counts.py` / `test_row_display.py` / `test_export_csv.py` | 新区分名・`period` 年数・ペイロードキーに追随 |
| `test_reconcile_confirmations.py` / `test_save_confirmation.py` | 固定基準 1 年・新区分名に追随（A-006） |
| `test_inventory_order_alert_views.py` / `test_settings_page_views.py` / portal のダッシュボードテスト | 旧称・判定軸の断言を X-0xx に置き換える |
| `test_legacy_alert_identifiers_removed.py` | 旧称に `供給リスク品` / `在庫過剰リスク品` / `low_flow` / `dormant` 軸を追加 |
| `test_inventory_order_alert_list_js.py` | `flowAxis` 関連の断言を X-017〜X-020 に置き換える。V-218 の断言は維持 |

---

## レビュー履歴

<!-- test-design-review-l1 がこのセクションに追記する。 -->

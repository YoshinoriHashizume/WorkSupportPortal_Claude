# 機能設計書: 流動区分の 7 分類化

文書ID: DES-FLOW-QUADRANT-REFINEMENT-2026-001
作成日: 2026/09/18
更新日: 2026/09/21（在庫切れ予測月の改訂・06 補正 3 とのすり合わせ・「入荷 < 需要」の比較対象の確定）
対応文書: [requirements.md](requirements.md)（REQ-FLOW-QUADRANT-REFINEMENT-2026-001）、[test-design.md](test-design.md)、[ubiquitous_language.md](../../ubiquitous_language.md)、[05_single-flow-view/design.md](../05_single-flow-view/design.md)、[06_stockout-risk/design.md](../06_stockout-risk/design.md)

---

## 変更履歴

| 日付 | 変更内容 |
|------|----------|
| 2026/09/18 | 初版作成 |
| 2026/09/21 | §2.5 に `stockout_forecast_month` の在庫 0 特例の削除、§2.6 を 06 補正 3（危険 = 補充不足、免除は MRP、MRP 先送り）とすり合わせて欠品の判定順を確定 |
| 2026/09/21 | §1 に期間判断の統一基準（判定期間に一本化・理由も 3 期間ぶん）を追加。§2.2 の理由「出荷の記録なし」を「{period}以上出荷なし・経路要確認」（期間内出荷なし・欠品 2 区分）に改訂。§2.3・§2.8・§5.1 を追随 |
| 2026/09/21 | §2.2 の「入荷 < 需要」を確定: 入荷側は `row_last_incoming_month_qty`（最終入荷日が属する月の合計。入荷推移が月次のみで日単位の窓を切れないため）、需要側は `row_next_month_demand`（翌月の内示）。当初案の `row_incoming_qty_in_window` と月平均需要は使わない |

---

## 1. 設計方針

1. **判定は既存の `apply_flow_quadrants_to_rows`（domain/list_rows）に集約**し、取込時（既定の判定期間）・表示時（利用者の判定期間）の両方で同じ関数を通す。新しい入力（在庫の有無・需要の有無・直近入荷の有無）は保存済みの行の値から導く
2. **取込時の順序を変える**: 需要予測 → 流動区分の引き直し → 在庫切れリスク。需要ありの判定に需要予測（照合単位）を使うため、`ImportStock._enrich_rows` で `attach_demand_forecast` の後に `apply_flow_quadrants_to_rows` を再適用してから `attach_stockout_risk` を呼ぶ
3. **在庫切れリスクは流動区分に依存させず、在庫の有無で分岐**する。「補充サイクル稼働中」の緩和は在庫ありの行のみ。在庫なし・需要ありの行（欠品）は対象外にしない
4. 閾値（`recent_incoming_days` 30）は第 1 段階では domain の定数（`FlowThresholds` の既定値）。第 2 段階で設定に載せる。当初案の `demand_window_months`（需要の窓）は、需要ありを内示のみで判定する改訂（REQ-FQR-F-001/F-002、2026/09/18）により **設けない**（既に実装済みなら撤去する）
5. 旧識別子（4 区分）のキー・ラベル・ランクは維持し、追加のみ行う。旧ランクの値が変わる（0→2 など）ため、ランクの数値を保存している箇所がないことを確認する（確認記録はラベルを保存している）
6. **期間判断の基準を判定期間（V-211）に一本化する**（2026/09/21、ユーザー判断「基準は一つにしたい」）。期間にかかわる判断はすべて判定期間で行い、値は「選択 UI がある画面（一覧）は利用者の選択値、選択 UI がない場所（メニュー帯・深刻化判定）は既定 1 年」の 1 規則で決まる。個別に固定値を持つ規則は増やさない。
   判定期間とは意味の違う窓（直近入荷 30 日・安全日数・既定リードタイム・監視期間）は用途を限定して据え置く。
   流動区分の理由も同じ基準に従うため、**理由は流動区分と同じく 3 期間ぶん（Y1/Y3/Y5）持たせ**、一覧の期間切替ではクライアントが引き直す（判定ロジックは JS に持ち込まない。05 design §3.1）

## 2. ドメイン

### 2.1 flow_quadrant.py

```python
QUADRANT_STOCKOUT_NO_INCOMING = "欠品（入荷なし）"      # key: stockout-no-incoming, rank 0
QUADRANT_STOCKOUT = "欠品"                   # key: stockout, rank 1（2026/09/18 に 欠品（入荷即出荷）/ stockout-pass-through から改名）
QUADRANT_LOW_FLOW_NO_INCOMING                          # rank 2
QUADRANT_DORMANT_STOCK                                 # rank 3
QUADRANT_LOW_FLOW_NO_SHIPMENT                          # rank 4
QUADRANT_DISCONTINUATION_CANDIDATE = "打ち切り候補"     # key: discontinuation-candidate, rank 5
QUADRANT_NORMAL_FLOW                                   # rank 6

DEFAULT_RECENT_INCOMING_DAYS = 30

@dataclass(frozen=True)
class FlowThresholds:
    recent_incoming_days: int = 30   # 1..90

@dataclass(frozen=True)
class FlowFacts:
    """1 行ぶんの判定材料。日付以外は既に真偽に落としてある。"""
    last_incoming_date: date | None
    last_ship_date: date | None
    stock_missing: bool = False    # SLIMS 在庫なし（未取得は False）
    has_demand: bool = False       # 需要あり（内示推移に数量がある）
    recent_incoming: bool = False  # 直近入荷あり

def is_recent_incoming(last_incoming_date, *, as_of_date, days) -> bool
def resolve_flow_quadrant(last_incoming_date, last_ship_date, *, as_of_date, selection,
                          stock_missing=False, has_demand=False, recent_incoming=False) -> str
def resolve_flow_quadrant_matrix(..., stock_missing=False, has_demand=False, recent_incoming=False) -> dict[str, str]
```

`resolve_flow_quadrant` の順序:

```
if stock_missing:
    if not has_demand: return 打ち切り候補
    return 欠品 if recent_incoming else 欠品（入荷なし）
（以下従来の 4 分岐）
```

`FLOW_QUADRANTS` はランク順 7 値。`LEGACY_QUADRANT_ALIASES` に「欠品（入荷即出荷）」「stockout-pass-through」→ 欠品 を追加（同日中の一時的な名称。保存済みデータがあっても読める）。`is_flow_escalated` は新ランクをそのまま使う。

### 2.2 flow_facts.py（新規）: 行から判定材料を導く

```python
def row_stock_missing(row) -> bool
    # "stock_qty" キーがあり空文字 かつ 照合単位の在庫合計（demand_forecast_stock_total）が None/0/空
    # （キーがなければ在庫未取得 → False）
def row_has_demand(row) -> bool
    # demand_forecast_basis があれば それが「内示」
    # なければ 内示推移（unconfirmed_order_trend）の翌月〜翌々々月に qty>0 があるか（出荷推移は見ない）
def row_recent_incoming(row, *, as_of_date, days) -> bool
def row_last_incoming_month_qty(row, *, as_of_date) -> int
    # 最終入荷日（V-215）が属する月の入荷推移（V-217）の合計。最終入荷日が空・該当月が推移にない → 0
def row_next_month_demand(row) -> int
    # 需要予測（V-220）の翌月の内示。basis が 内示 でなければ 0
def build_flow_facts(row, *, as_of_date, thresholds) -> FlowFacts
def flow_reasons(row, quadrant, facts, *, as_of_date, selection) -> list[str]
    # selection: FlowSelection（判定期間）。期間にかかわる理由はここから判定する（§1-6）
```

`flow_reasons`（REQ-FQR-F-005）:

| 区分 | 条件 | 文言（定数） | 判定期間 |
|---|---|---|---|
| 欠品（入荷なし） | 最終入荷日が空 | `FLOW_REASON_NO_INCOMING_RECORD` = 「入荷の記録なし・経路要確認」 | 使わない |
| 欠品・欠品（入荷なし） | **期間内出荷（V-213）がない**（2026/09/21 改訂） | `FLOW_REASON_NO_SHIPMENT_IN_PERIOD` = 「**{period}以上出荷なし・経路要確認**」（`{period}` は表示中の判定期間ラベル） | **使う** |
| 欠品 | 最終入荷日が属する月の入荷合計 < 翌月の内示（2026/09/21 確定。REQ-FQR-F-005） | `FLOW_REASON_INCOMING_BELOW_DEMAND` = 「入荷 < 需要」 | 使わない |
| 低流動品（出荷なし） | 内示あり（basis = 内示） | `FLOW_REASON_UNCONFIRMED_WITHOUT_SHIPMENT` = 「内示あり（立ち上がり／出荷経路要確認）」 | 区分を通じて使う |
| 打ち切り候補 | `phase_out_date` が基準日より前 | 「適用終了日 YYYY/MM/DD」（`format_phase_out_reason`） | 使わない |

行には次の 2 つを付与する。

- `flow_reasons: list[str]` — 表示中の判定期間で描いた理由（サーバ描画・CSV・旧クライアント向け）
- `flow_reasons_by_period: dict[str, list[str]]` — 判定期間キー（Y1/Y3/Y5）→ 理由。クライアントが期間切替で引き直す（`flow_quadrants` と同じ形）

詳細ダイアログの流動区分セクションに箇条書きで表示（`flowReasons` / `flowReasonsByPeriod`）。

> **［2026/09/21 改訂前］** 2 行目の条件は「欠品 で最終出荷日が空」だった。一覧は出荷実績のある行から作られるため該当が構造上存在せず、理由が一度も出なかった（実データ 2,299 行中 0 件）。

### 2.3 list_rows.apply_flow_quadrants_to_rows

- 引数に `thresholds: FlowThresholds = FlowThresholds()` を追加
- 行ごとに `build_flow_facts` → `resolve_flow_quadrant` / `resolve_flow_quadrant_matrix` に facts を渡す → `flow_reasons`（表示中の判定期間）と `flow_reasons_by_period`（Y1/Y3/Y5）を付与。
  理由は区分ごとに決まるため、期間ごとの区分（行列）と同じループで組み立てる
- 状況（`flow_status`）の描画は従来どおり `render_status`。`{demand}`（月平均需要）と `{phase_out}` は使わず、状況テンプレートは日付と期間のみ

### 2.4 recommended_action.py

7 件に拡張（`RecommendedActions` の検証も 7 値）。定義（用語集 S-203）:

| 区分 | 状況テンプレート | 推奨アクション | 責任部署 |
|---|---|---|---|
| 欠品（入荷なし） | 在庫なし・需要あり、最終入荷 {last_incoming}（直近 30 日入荷なし） | 発注状況・仕入先の納期を至急確認。発注がなければ即発注 | 調達G・生産管理 |
| 欠品 | 在庫なし・入荷はあるが在庫が残らない（最終入荷 {last_incoming}・最終出荷 {last_ship}） | 供給遅延。工程の連鎖で止まっている箇所を確認し納期前倒しを依頼 | 生産管理・調達G |
| 低流動品（入荷なし） | （従来） | （従来） | 調達G・営業G・生産管理 |
| 在庫死蔵品 | （従来） | （従来） | 調達G |
| 低流動品（出荷なし） | （従来） | （従来） | 営業G |
| 打ち切り候補 | 在庫なし・内示なし（最終出荷 {last_ship}） | 営業へ終了を確認。終了なら確認済みにする | 営業G |
| 通常流動品 | 空 | 空 | 生産管理 |

「直近 30 日」はプレースホルダ `{recent_days}` で埋める（`render_status` / `describe_status_template` に `recent_days` を渡す。既定 30）。当初案の `{demand_window}` は撤去する（2026/09/18 改訂）。

### 2.5 demand_forecast.py

実績ベースのフォールバックを **削除** する（REQ-FQR-F-002、2026/09/18 改訂）。

- `BASIS_ACTUAL`・`ACTUAL_BASIS_MONTHS` と、出荷推移から月平均を作る分岐を削除。`DEMAND_FORECAST_BASES = (内示, なし)`、`DemandForecastBasis = Literal["内示", "なし"]`
- `build_demand_forecast` は内示推移の合算のみ。翌月〜翌々々月の合計が 0 なら `NO_DEMAND`
- 旧スナップショットに `demand_forecast_basis = "実績ベース"` が残っていても、`stockout_risk._forecast_of` は `BASIS_UNCONFIRMED` 以外を `NO_DEMAND` に寄せる（旧行を危険に上げない）
- `stockout_risk.py` の `REASON_ACTUAL_BASIS`（「需要は実績ベース」）と `BASIS_ACTUAL` の分岐を削除
- 推定在庫推移グラフ（list.js）の予測部分は `demandForecast.basis === "内示"` のときのみ描く。`monthly` に月平均を入れる実績ベースの前提コメントを撤去
- `stockout_forecast_month`: `stock_total <= 0 → 当月` の特例を削除する（2026/09/21、REQ-FQR-F-002）。`remaining = stock_total − current_month_remaining` が負なら当月、以降は月別需要を引いて初めて負になる月。在庫 0 で需要が翌々月から始まれば翌々月になる

### 2.6 stockout_risk.py

`assess_stockout_risk(..., stock_missing: bool = False, recent_incoming: bool = False)` を追加（2026/09/21 改訂: 06 補正 3 の判定順を土台に、欠品は免除なしで通す）。

```
監視（需要なし／予測月なし／在庫未取得／監視期間より先）は従来どおり
short = qty == 0 or qty < 不足数量
replenishment_active = (not stock_missing) and is_mrp and last_incoming within (LT + 安全日数)   # 在庫あり かつ MRP のみ
upstream_in_flight   = upstream_pending_qty > 0   # 欠品でも有効（上流で流れていれば今すぐ手を打つ行ではない）
mrp_deferral         = (not stock_missing) and is_mrp and 通常流動品 and not within_lead_time and qty == 0 and not has_overdue and not upstream_overdue

unknown → 注意
within_lead_time and short and not replenishment_active and not upstream_in_flight → 危険
mrp_deferral → 対象外
short or has_overdue → 注意
stock_missing → 注意（欠品は対象外にしない）
それ以外 → 対象外
```

理由: 欠品（`stock_missing`）の危険・注意には「在庫なし」(`REASON_STOCK_MISSING`) を先頭に付け、`recent_incoming`（流動区分の直近入荷、30 日）なら「供給遅延（入荷即出荷）」(`REASON_SUPPLY_DELAY`) を添える。以降は従来の理由。「直近に入荷あり」は在庫ありの MRP 行のみ。

`attach_stockout_risk` は `row_stock_missing(row)`・`row_recent_incoming(row, ...)` を渡す（flow_facts を import）。在庫合計 None（未取得）は従来どおり監視。

### 2.7 row_counts.py

`RowCounts` に `stockout_no_incoming` / `stockout` / `discontinuation_candidate` を追加。`by_quadrant` は 7 キー（ランク順）。

`attention` は **通常流動品以外の合計**（= `total − normal_flow`、7 区分では 6 区分ぶん）とする（2026/09/21 明確化）。
一覧の「要対応のみ」フィルタが除くのは通常流動品だけであり、推奨アクション（T-207）が空なのも通常流動品だけなので、
件数と絞り込みの意味を一致させる。7 区分の和が `total` に一致する不変条件（TC-SFV-E-005）も維持する。

### 2.8 row_display / table_display / list_client_data / export_csv / list_query

- 流動区分のキー集合を `FLOW_QUADRANT_KEYS` から取るため変更は最小。`list_client_data` に `flowReasons`・`flowReasonsByPeriod`、`flowQuadrantOrder`（ランク順キー）を追加
- CSV: 流動区分の値が 7 種になるのみ。列追加なし（理由は列にしない。詳細ダイアログのみ）
- `list_query`: `flow_quadrant` の許容値は `FLOW_QUADRANT_LABELS` 由来のため変更なし

### 2.9 flow_quadrant_rules.py

`_RULE_CONDITIONS` を 7 行に。`FlowQuadrantRuleRow` に `stock`（あり/なし/—）・`demand`（あり/なし/—）・`recent_incoming`（あり/なし/—）を追加。判定ルールダイアログの列: 区分 / 在庫 / 需要 / 直近入荷 / 期間内入荷 / 期間内出荷 / 状況 / 推奨アクション / 責任部署。

## 3. ユースケース

### 3.1 ImportStock._enrich_rows

```python
with_forecast = attach_demand_forecast(rows, as_of_date)
with_flow = apply_flow_quadrants_to_rows(with_forecast, as_of_date=as_of_date,
                                         query=ListQuery(as_of_date=as_of_date, flow_selection=REFERENCE_FLOW_SELECTION))
return attach_stockout_risk(with_flow, as_of_date, settings=...)
```

`reconcile_confirmations_after_import` は enrich 後の行を使うので、A-201 は新区分で判定される。

### 3.2 portal_dashboard

帯の文言: 「欠品（入荷なし） N 件／欠品 N 件／低流動品（入荷なし） N 件／在庫死蔵品 N 件」。`tone` は在庫切れリスク優先（変更なし。ただし欠品 2 区分が 1 件以上なら `critical`）。`summary_api` のカウントに 3 キーを追加（`stockoutNoIncoming` / `stockout` / `discontinuationCandidate`。2026/09/21: 区分名の改名に合わせ `stockoutPassThrough` ではなく `stockout`）。

## 4. インフラ

### 4.1 summary_queries: 適用終了日

`fetch_cust_item_phase_out_dates(connection) -> dict[(cust_cd, cust_item_cd), date]`（`M_CUST_ITEM.EFF_PHASE_OUT_DATE` の MAX）。取得失敗は警告に載せて空扱い（`_or_warn`）。行に `phase_out_date`（"YYYY/MM/DD" または ""）を付ける。

## 5. インターフェース

### 5.1 list.html / JS

- 判定ルールダイアログ: 7 行・列追加（§2.9）
- 判定ルールダイアログの説明文: 期間判断の基準（§1-6）と判定材料の定義を示す。需要の定義は内示のみ（出荷実績は見ない）
- 詳細ダイアログ 流動区分セクション: 理由を箇条書きで表示。期間切替に追随するため `flowReasonsByPeriod[periodKey]` を引く
- 流動区分フィルタ: 7 選択肢（順はランク順）
- クライアント JS: `FLOW_RANK` を 7 キーに。判定期間切替は `flow_quadrants[periodKey]` と `flowReasonsByPeriod[periodKey]` を引くのみ（欠品・打ち切り候補の区分は全キー同値だが、理由は期間で変わりうる）
- CSS: `.flow-quadrant--stockout-no-incoming` 等のバッジ色（行色はつけない）

### 5.2 設定画面（第 2 段階）

`recent_incoming_days` を追加。`AppSettings` にフィールド（既定 30、範囲 1〜90）・payload キー（`recentIncomingDays`）・`to_flow_thresholds()` を設ける。取込時の `FlowThresholds` は設定から作る。表示時（list_page）の再判定とメニュー帯（portal_dashboard）も同じ設定を使う（`ListPage`・`PortalDashboard` は既に `load_app_settings` を受け取っている）。

**DB カラムは既存の `recent_incoming_days`（既定 90）を再利用する**（2026/09/21）。旧アラートレベル方式の残置カラムで 05 以降どこからも読まれておらず、意味（直近入荷とみなす日数）も同じであるため、カラムを増やさない。ただし保存済みの値 90 は旧方式の閾値であって新しい窓の設定ではないので、マイグレーションで **既定値を 30 に変更し、既存行の値も 30 に戻す**（データ移行）。

判定期間（V-211）とは別の窓である点は用語集 V-211 の「期間判断の基準」のとおり。設定画面では判定期間と混同しないよう、用途（欠品 2 区分の振り分けのみ）を説明に書く。

## 6. 互換

- 旧行（`stock_qty` キーなし）: `stock_missing=False` → 4 区分
- 旧行（`demand_forecast_basis` なし）: 内示推移から需要を導く。`demand_forecast_basis = "実績ベース"` の旧行は需要なし扱い（取込し直せば「なし」になる）
- 確認記録の `confirmed_flow_quadrant` は旧称も `normalize_flow_quadrant` で正規化。ランク比較は新ランク

## 7. 影響ファイル一覧

| レイヤー | ファイル | 変更 |
|---|---|---|
| domain | flow_quadrant.py | 7 区分・FlowThresholds・resolve の拡張 |
| domain | flow_facts.py（新規） | 行 → 判定材料・理由 |
| domain | recommended_action.py | 7 件・`{recent_days}`（`{demand_window}` は撤去） |
| domain | flow_quadrant_rules.py | 7 行・条件列 |
| domain | demand_forecast.py | 実績ベースの削除（内示のみ） |
| domain | stockout_risk.py | 在庫なし分岐・理由 |
| domain | row_counts.py / list_client_data.py / list_rows.py | 集計・クライアントデータ・理由付与 |
| use_cases | import_stock.py / portal_dashboard.py / summary_api.py | 順序・帯・API |
| infrastructure | oracle/summary_queries.py | 適用終了日 |
| infrastructure | config/recommended_actions.example.json | 7 キー |
| interfaces | templates list.html / dashboard.html、static js/css | 表示 |
| docs | 機能仕様書 rev 6.0（別タスク） | |

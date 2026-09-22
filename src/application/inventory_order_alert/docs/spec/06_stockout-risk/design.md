# 機能設計書: 在庫切れリスクの判定と表示

文書ID: DESIGN-STOCKOUT-RISK-2026-001
作成日: 2026/09/17
更新日: 2026/09/21
対応文書: [requirements.md](./requirements.md)（REQ-STOCKOUT-RISK-2026-001、草案承認 2026/09/17）、[ubiquitous_language.md](../../ubiquitous_language.md)（V-224〜V-230、S-204）、[05_single-flow-view/design.md](../05_single-flow-view/design.md)（需要予測・`enrich_rows` 経路の出典）、[strategic_design.md](../../../../../docs/strategic_design.md)

**状態: 草案（Phase 3、承認ゲート ③ 待ち。ユーザー指示「出てきたデータを見て決めるので一旦これで進めて」により実装を先行）**

---

## 1. 設計の目的

在庫切れ予測月（V-221、05 で実装済み）に発注残（V-224）・リードタイム（V-225）・発注方式（V-227）を突き合わせ、行ごとに在庫切れリスク（S-204）と理由を **取込時に** 判定してスナップショットに保存する。一覧・詳細・CSV・メニュー帯は保存値を表示するだけにする（05 の需要予測と同じ構造）。

## 2. 対象コンテキスト

在庫発注アラート（生産管理・コア）。MARI は読み取りのみ。他コンテキストの import はしない（5年9組と発注残の取得条件を揃えるが、コードは共有しない）。

## 3. アーキテクチャ概要

```
取込（use_cases/import_stock.py）
  rows = 集計（infrastructure: build_summary_rows）
           … 行に open_purchase_orders（発注残の明細）/ lead_time_days / lead_time_source / ordering_method を付与（生データ）
  rows = attach_demand_forecast(rows, as_of_date)            … 05（domain）
  rows = attach_stockout_risk(rows, as_of_date, settings)   … 本件（domain）: 照合単位で補充見込み → 判定 → 各行に複製
  保存
```

- `ImportStock` は `enrich_rows` として上記 2 つを **合成した関数** を渡す。設定値（安全日数・既定リードタイム・監視期間）は `load_app_settings()` から取り、wiring で注入する
- Oracle からの取得（発注残・品目マスタ）は `build_summary_rows` に加える（取込ごとに 1 回ずつ）。失敗は警告（`aggregation_warning`）にして取込を止めない。発注残の取得失敗は行に `open_purchase_orders_unknown = True` を立てる

### 3.1 段階分け

| 段階 | 内容 |
|---|---|
| 第 1 段階 | 判定（F-001〜F-006）、一覧列・並び替え・絞り込み（F-007・F-008）、件数サマリ・メニュー帯（F-009）、CSV（F-012）、互換（F-013・F-014）。設定値は `AppSettings` に項目を追加し **既定値で動かす**（設定画面の UI は第 2 段階） |
| 第 2 段階 | 設定画面の 3 項目（F-010）、確認記録への保存と危険化による未確認化（F-011） |

## 4. ドメインモデル

### 4.1 発注残と補充見込み — `open_purchase_order.py`（新規）

```python
@dataclass(frozen=True)
class OpenPurchaseOrder:            # V-224
    item_cd: str                    # 仕入先品番
    vend_cd: str
    due_date: date                  # 回答納期があればそれ、なければ納期
    remaining_qty: int              # 発注数量 − 検収数量（負は 0）

@dataclass(frozen=True)
class ReplenishmentOutlook:         # V-226
    qty: int                        # 補充期限までに納期がある残数合計（長期納期超過を除く）
    later_qty: int                  # 補充期限より後（納期なしを含む）の残数合計（参考）
    stale_qty: int                  # 長期納期超過（V-230）の残数合計（参考。補充には数えない）
    earliest_due: date | None       # 最も早い納期（qty に数えた分）
    has_overdue: bool               # 納期が基準日より前の発注残がある（長期納期超過を含む）
    unknown: bool = False           # 取得失敗

def replenishment_deadline(as_of_date, stockout_month, *, safety_days) -> date        # V-229 = max(予測月 1 日, 基準日) + 安全日数
def build_replenishment_outlook(orders, *, as_of_date, stockout_month, deadline, stale_after_days, level1_pairs=None) -> ReplenishmentOutlook
```

- `deadline` は補充期限（V-229）、`stale_after_days` は リードタイム（連鎖の合計）＋安全日数（2026/09/21 追加）。納期 `d` の直下の発注残は次のとおり振り分ける: `as_of − d > stale_after_days` → `stale_qty`（`has_overdue` も真）/ `d ≤ deadline` → `qty`（`d < as_of` なら `has_overdue`）/ それ以外（納期なしを含む）→ `later_qty`
- `stockout_month` が `None` のときは `qty = 0` で `ReplenishmentOutlook` を返す（判定は監視になるため使わない）
- 行には `open_purchase_orders`（`[{"order_cd","item_cd","vend_cd","due_date","remaining_qty"}]`）を生データとして持たせ、照合単位（T-208）内の全行から集めて重複（同じ発注明細）を **`order_cd`（`PUCH_ODR_CD`）** で除く。`order_cd` が空の旧スナップショット行は従来どおり `(item_cd, vend_cd, due_date, remaining_qty)` で除く（2026/09/18 改訂: 同品番・同納期・同数量の別明細（実データ 1,059 明細・残数 771,140）が潰れていたため。`OpenPurchaseOrder.order_cd` を追加）

### 4.1a 工程の連鎖（2026/09/18 追加）

行に `process_chain: [{"item_cd", "vend_cd", "vend_name", "lead_time_days", "lead_time_source"}]` を工程順（完成品直下 → 上流）で持つ。infrastructure が `fetch_bom_chain_by_root()`（`M_PS` を `CONNECT BY` で末端まで、`OUTSIDE_TYP = '2'`、有効期間内）で作り、仕入先は `fetch_vendor_by_component()`、リードタイムは `M_ITEM` から引く。`open_purchase_orders` は連鎖の全工程の (item_cd, vend_cd) について集める。

- `ReplenishmentOutlook` に `upstream_qty` / `upstream_overdue` / `upstream_pending_qty`（上流のうち **納期超過でなく納期 ≤ 補充期限** の残数。納期なしは含めない。2026/09/18 追加、2026/09/21 納期の窓）を追加。**補充見込み（qty）は直下の工程の発注残のみ**、上流工程の発注残は理由と危険の判定に使う。理由は `upstream_pending_qty > 0` で `上流工程に発注残あり`、`upstream_overdue` で `上流工程で納期遅れ` を **独立に** 付ける（混在なら両方）。危険は `upstream_pending_qty > 0` なら注意に落とす（納期超過が混在していても、納期内の分が流れている以上は危険にしない）
- 判定のリードタイム = `sum(stage.lead_time_days for stage in process_chain)`（空なら直下の工程の値）。行の `lead_time_days` はこの合計、`lead_time_source` は 1 工程でも既定値なら `default`

### 4.2 発注方式とリードタイム — `ordering_profile.py`（新規）

```python
ORDERING_MANUAL = "手動発注"; ORDERING_MRP = "MRP 発注"; ORDERING_UNKNOWN = "不明"
def ordering_method_from_code(code) -> str        # "4" → 手動発注, "5" → MRP 発注, その他 → 不明
def resolve_lead_time_days(master_value, *, default_days) -> tuple[int, str]   # (日数, "master" | "default")
```

### 4.3 在庫切れリスク — `stockout_risk.py`（新規）

```python
RISK_DANGER = "危険"; RISK_CAUTION = "注意"; RISK_WATCH = "監視"; RISK_NONE = "対象外"
STOCKOUT_RISK_RANK = {危険: 0, 注意: 1, 監視: 2, 対象外: 3}
STOCKOUT_RISKS = (危険, 注意, 監視, 対象外)

@dataclass(frozen=True)
class StockoutRiskSettings:          # AppSettings から写す
    safety_days: int = 14
    default_lead_time_days: int = 5
    watch_months: int = 6

@dataclass(frozen=True)
class StockoutRiskAssessment:
    risk: str
    reasons: tuple[str, ...]          # F-006 の理由（表示文言そのもの）
    days_until_stockout: int | None   # V-228
    shortage_qty: int | None          # 不足数量
    lead_time_days: int
    lead_time_source: str             # master / default
    ordering_method: str

def days_until_stockout(as_of_date, stockout_month) -> int | None
def demand_until_month(forecast, *, as_of_date, stockout_month) -> int      # 当月残 + 翌月〜（予測月まで、4 か月目以降は平均）
def assess_stockout_risk(*, forecast, stock_total, stockout_month, outlook, profile, flow_quadrant, settings, as_of_date) -> StockoutRiskAssessment
def attach_stockout_risk(rows, as_of_date, *, settings) -> list[dict]        # 照合単位ごとに 1 回判定し各行に複製
```

**判定順（F-005）**

1. 需要予測の算出根拠が「なし」／在庫切れ予測月が空／在庫合計が未取得 → **監視**
2. 在庫切れ予測月 > 基準日 + 監視期間（か月）→ **監視**
3. `outlook.unknown` → **注意**（理由「発注残を取得できませんでした」）
4. `short = outlook.qty == 0 or outlook.qty < 不足数量`。猶予日数 ≤ リードタイム + 安全日数 かつ `short` かつ 免除なし → **危険**。免除 = (i) `ordering_method == MRP 発注` かつ **補充サイクル稼働中**（最終入荷日が基準日 − (LT + 安全日数) 以降。理由「直近に入荷あり」）/ (ii) `outlook.upstream_pending_qty > 0`（理由「上流工程に発注残あり」。納期超過が混在すれば「上流工程で納期遅れ」も付く）。免除なら 5 へ（2026/09/21 改訂: `qty == 0` → `short`、免除 (i) を MRP に限定）
5. `ordering_method == MRP 発注` かつ 流動区分 = 通常流動品 かつ 猶予日数 > LT + 安全日数 かつ `outlook.qty == 0` かつ `not outlook.has_overdue` かつ `not outlook.upstream_overdue` → **対象外**（MRP 先送り。2026/09/21 追加。対応要 3 区分は仕入先確認が先に要るため注意に残す）
6. `outlook.qty == 0` または `outlook.qty < 不足数量` または `outlook.has_overdue` → **注意**
7. それ以外 → **対象外**

**理由（F-006）**: 危険・注意にのみ付与。`直近に入荷あり`（MRP 発注 かつ 補充サイクル稼働中）/ `発注忘れの可能性`（手動発注 かつ 直下の発注残が 1 件もない: `qty == later_qty == stale_qty == 0`）/ `仕入先の生産可否を先に確認`（低流動品（入荷なし）／在庫死蔵品）/ `納期遅れ`（has_overdue）/ `数量不足`（0 < qty < 不足数量）/ `リードタイム内`（猶予 ≤ LT + 安全日数）/ `立ち上がり品`（低流動品（出荷なし）かつ 内示）/ `リードタイム未設定`（source = default）/ `仕入先未解決`（level1 空）/ `需要は実績ベース`。

**行に付与するキー（§5）**: `stockout_risk`, `stockout_risk_reasons`（list）, `days_until_stockout`, `shortage_qty`, `replenishment_qty`, `replenishment_later_qty`, `replenishment_stale_qty`（2026/09/21 追加。旧行は 0）, `replenishment_earliest_due`（`YYYY/MM/DD` or ""）, `replenishment_has_overdue`, `replenishment_unknown`, `lead_time_days`, `lead_time_source`, `ordering_method`。

### 4.4 設定 — `app_settings.py` 改修

`AppSettings` に `safety_days`（1〜60、既定 14）、`default_lead_time_days`（1〜60、既定 5）、`watch_months`（1〜12、既定 6）を追加。`SettingsInput` / `parse_settings_payload` / `settings_payload` も追随（キー `safetyDays` / `defaultLeadTimeDays` / `watchMonths`）。`to_stockout_risk_settings()` を持つ。

### 4.5 集約

新しい集約は作らない。スナップショット行への項目追加のみ（第 1 段階）。

## 5. データモデル

### 5.1 スナップショット行（JSON、マイグレーション不要）

| キー | 型 | 内容 |
|---|---|---|
| `open_purchase_orders` | list | 仕入先品番×仕入先の発注残明細（生データ。`order_cd` は `PUCH_ODR_CD`、`due_date` は `YYYY/MM/DD`。残数 > 0 のみ） |
| `open_purchase_orders_unknown` | bool | 取得失敗 |
| `lead_time_days` / `lead_time_source` / `ordering_method` | int / str / str | 品目マスタ由来（`level1_item_cd` で引く） |
| `stockout_risk` 〜 `replenishment_*` / `shortage_qty` / `days_until_stockout` | — | §4.3 |

### 5.2 設定（マイグレーション 0012）

`InventoryOrderAlertSettings` に `safety_days`（default 14）、`default_lead_time_days`（default 5）、`watch_months`（default 6）を追加。

### 5.3 確認記録（第 2 段階、マイグレーション 0013）

`InventoryOrderAlertConfirmation.confirmed_stockout_risk`（`CharField(max_length=10, blank=True, default="")`）。

## 6. API / インターフェース設計

### 6.1 Oracle（`summary_queries.py`）

```sql
-- 発注残（V-224）。5年9組の残数算出と同じ条件。取込ごとに 1 回
SELECT TRIM(p.PUCH_ODR_CD), TRIM(p.ITEM_CD), TRIM(p.VEND_CD), p.PUCH_ODR_DLV_DATE, p.CONFIRM_DLV_DATE,
       p.PUCH_ODR_QTY - NVL((SELECT SUM(a.ACPT_QTY) FROM T_PAST_INSPC_ACPT a WHERE a.PUCH_ODR_CD = p.PUCH_ODR_CD), 0) AS ZAN
  FROM T_RLSD_PUCH_ODR p
 WHERE p.PUCH_ODR_STS_TYP = '2' AND NVL(p.ODR_CANCEL_SLIP_ISS_FLG, '0') = '0'

-- 品目マスタ（V-225・V-227）。一覧の仕入先品番を 900 件ずつ IN で
SELECT TRIM(ITEM_CD), FIXED_LT, MRP_ODR_TYP FROM M_ITEM WHERE ITEM_CD IN (...)
```

- `fetch_open_purchase_orders()` は `(order_cd, item_cd, vend_cd, due, remaining)` を返し、残数 ≤ 0 の明細は Python 側で落とす（REQ-SOR-F-001 の「残数 > 0」。2026/09/18 追加）
- `fetch_open_purchase_orders_or_warn()` は `OracleQueryError` を警告に変える（内示受注と同じ）。品目マスタの失敗も警告（リードタイムは既定値・発注方式は不明）
- `build_summary_rows` は行に `open_purchase_orders`（`(level1_item_cd, level1_vend_cd)` で引いた明細）と `lead_time_days` / `lead_time_source` / `ordering_method` を付ける。**判定はしない**

### 6.2 取込（`use_cases/import_stock.py`）

`ImportStock(import_stock, load_app_settings)`。`execute` は `enrich_rows=compose(attach_demand_forecast, attach_stockout_risk(settings))` を渡す。

### 6.3 ペイロード（`list_client_data.py`）

行に `stockoutRisk` / `stockoutRiskKey`（`danger` / `caution` / `watch` / `none`）/ `stockoutRiskReasons` / `daysUntilStockout` / `shortageQty` / `replenishment{qty, laterQty, staleQty, earliestDue, hasOverdue, unknown}` / `leadTimeDays` / `leadTimeSource` / `orderingMethod`。ペイロードに `stockoutRiskOrder`（キーの順）と `stockoutRiskLabels`。

### 6.4 一覧（`list.html` / `list-client.js` / `app.css`）

- `SORTABLE_COLUMNS` の先頭に `("stockout_risk", "在庫切れリスク")` を追加（セルは段階名のみ、対象外は空）。ソート専用に `days_until_stockout`（空は末尾）を追加
- 既定ソート: `stockout_risk asc` → 同順位は `days_until_stockout asc` → `flow_quadrant asc`（domain `sort_summary_rows` と JS の tiebreaker を揃える）
- 行クラス: 確認状態（`確認済` / `確認中`）> 在庫切れリスク（`stockout-danger` / `stockout-caution` / `stockout-watch` / `stockout-none`）。CSS は危険=赤系（`#fde8e8`）・注意=黄系（`#fff8e1`）、監視・対象外は色なし。**流動区分は行の色にも色見本にも使わない**（2026/09/18 改訂。判定ルールダイアログの `ioa-alert-rules-row--{key}` の行色・色見本も撤去）。同順位の並びはサーバ（`table_display.sort_rows` の tiebreaker）と JS（`Core.sortRows` の tiebreaker）で揃える: 猶予日数 昇順（空は末尾）→ 流動区分ランク → 得意先コード → 得意先品番
- フィルタパネルに「在庫切れリスク」「発注方式」セレクトを追加（URL `stockout_risk` / `ordering_method`）
- 件数サマリ上段: 「危険 N 件 / 注意 N 件 / 監視 N 件 / 対象外 N 件」（`RowCounts` に `danger` / `caution` / `watch` / `none_risk`）。流動区分の件数は詳細（判定ルールダイアログ）へ
- 詳細ダイアログ「需要予測」区分に在庫切れリスク・理由・猶予日数・補充見込み・不足数量・リードタイム・発注方式を追加

- 詳細ダイアログの「補充見込み（発注残）」は `qty（最早納期 …・納期超過あり）` に続けて、`laterQty > 0` なら「補充期限より後 N」、`staleQty > 0` なら「長期納期超過 N は除外」を添える（2026/09/21）

### 6.4a 推定在庫推移グラフの予測部分（`inventory-order-alert-list.js`、2026/09/18 追加）

- 実績 24 か月（既存）に **翌月〜翌々々月の 3 点**を足し、点線（`ioa-anchored-stock-trend-line--forecast`）で描く。起点は実績の最終点（現在の在庫）
- 予測値: `翌月 = 在庫 − 当月残の内示 − 翌月の需要 + 予定入荷（納期 ≤ 翌月末、納期超過は当月扱い）`、以降同様。需要は `demandForecast.currentMonthRemaining`（当月残）と `demandForecast.monthly[0..2]`（翌月〜翌々々月。**照合単位の合計**で、サーバの在庫切れ予測月と同じ根拠。実績ベースは Python 側で月平均が入っている）。基礎は `demandForecast.basis`（2026/09/18 改訂: 行単位の `unconfirmedOrderTrend` を使うと、複数得意先を含む照合単位で起点在庫（単位合計）と需要（行）の粒度がずれ、縦線「在庫切れ予測」と食い違ったため）
- 予定入荷は `processChain[0].openOrders`（完成品直下の工程の発注残）を納期の月で束ね、薄い棒（`ioa-anchored-stock-trend-bar--planned`）で重ねる
- `stockoutForecastMonth` が描画範囲内なら縦の破線と「在庫切れ予測」ラベル
- 凡例に「予測在庫（内示・発注残）」「予定入荷（発注残）」を追加。Python 側の変更なし（配信済みデータのみ）

### 6.5 メニュー帯（`portal_dashboard.py` / `dashboard.html`）

「危険 N 件 / 注意 N 件 / 未確認 N 件（判定期間 1年・監視期間 6か月）」。危険 > 0 で `critical`、注意のみで `warning`。件数はスナップショット保存値を数える（判定期間の再計算は流動区分のみ）。

### 6.6 CSV（`export_csv.py`）

末尾に `在庫切れリスク` / `在庫切れリスクの理由`（`・` 区切り）/ `猶予日数` / `補充見込み` / `補充見込みの最早納期` / `納期超過` / `不足数量` / `リードタイム` / `発注方式`。既存 28 列は不変。

## 7. 既存コードへの変更点

### 7.1 新規

`domain/value_objects/open_purchase_order.py`、`ordering_profile.py`、`stockout_risk.py`、`migrations/0012_stockout_risk_settings.py`、テスト各種。

### 7.2 変更

`app_settings.py`、`models.py`、`settings_repository.py`、`summary_queries.py`、`import_stock.py`、`wiring.py`、`list_rows.py`（既定ソート）、`row_counts.py`、`row_display.py`（行クラス）、`table_display.py`、`list_query.py`（フィルタ）、`list_client_data.py`、`export_csv.py`、`list_page.py`、`portal_dashboard.py`、`list.html`、`dashboard.html`、両 JS、`app.css`。

## 8. エラーハンドリング方針

| 事象 | 扱い |
|---|---|
| 発注残の取得失敗 | 取込は成功。行に `open_purchase_orders_unknown`、判定は注意、警告メッセージ |
| 品目マスタの取得失敗 | 取込は成功。リードタイム既定・発注方式不明、警告メッセージ |
| 残数が負 | 0 |
| 納期が空 | 補充見込みに数えない（予測月より後と同じ） |
| 旧スナップショット | 監視・理由なし。ペイロードは `stockoutRisk = "監視"`、`replenishment.unknown = false` |

## 9. リスクと対策

| リスク | 対策 |
|---|---|
| 在庫切れ予測が月単位で猶予日数が粗い | 安全日数（既定 14 日）で吸収。実データで危険の件数を見て調整 |
| 立ち上がり品が危険に上がる | 理由「立ち上がり品」を付け、件数を DECISIONS に記録して判断（§6.4 事項 7） |
| 発注残の取得時間 | 状態 2 に絞る（3,310 明細）。実測して 10 秒以内を確認 |
| 通常流動品が注意で大量に出る | MRP 発注で発注期限が先・発注残なしの行を対象外にする（F-005、2026/09/21）。件数は DECISIONS に記録 |
| 長期納期超過を補充から外すと危険が増える | 危険には理由「納期遅れ」が付き対処（仕入先へ納期確認）が明確。件数の前後比較を DECISIONS に記録 |
| 多段品（連鎖 3 工程以上）がリードタイム合計で危険になりやすい | 実データで件数を記録し、過検出なら「上流材が直下の仕入先に届いている」ことを検収実績で判定する案を検討（2026/09/21） |
| 補充期限を月初＋安全日数にすると月末納期の発注残が「間に合わない」側に落ちる | 意図した保守化。MRP 発注は直近入荷の免除で危険にならず、手動発注は理由「発注忘れの可能性」を付けず（発注残あり）注意 (a) 止まり。件数を DECISIONS に記録 |

## レビュー履歴

（未実施）

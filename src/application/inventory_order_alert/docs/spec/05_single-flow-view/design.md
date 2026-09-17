# 機能設計書: 単一の判定期間による流動区分と推奨アクションの表示

文書ID: DESIGN-SINGLE-FLOW-VIEW-2026-001
作成日: 2026/09/16
更新日: 2026/09/16
対応文書: [requirements.md](./requirements.md)（REQ-SINGLE-FLOW-VIEW-2026-001、L3 PASS・承認済み 2026/09/16）、[ubiquitous_language.md](../../ubiquitous_language.md)（2026-09-16 改訂）、[04_shipment-history-chart/design.md](../04_shipment-history-chart/design.md)（照合単位・推定在庫推移の既存設計）、[strategic_design.md](../../../../../docs/strategic_design.md)
アーキテクチャreference: django-clean-architecture version 1.0（updated 2026-04-11。make-design / design-review-l1 / implement-review-l1 で一致を確認）

---

## 1. 設計の目的

要件定義書の 4 つの目的（1 回で全体を把握／状況と行動の提示／緊急度の提示／目的との整合）を、次の技術的な変更で実現する。

| 目的 | 技術的な実現 |
|---|---|
| 1 回で全体を把握 | 判定軸（`EvaluationPeriod.axis`）を廃止し、判定期間を年数のみの VO にする。行ごとの事前判定行列（`flow_quadrants`）のキーを 6 値（L1/L3/L6/D1/D2/D5）から 3 値（Y1/Y3/Y5）にする |
| 状況と行動の提示 | 流動区分 4 値の**ラベル・ランク・状況テンプレート・推奨アクション・責任部署**を domain の単一の定義表に集約し、一覧セル・判定ルール・詳細・CSV・メニュー画面のアラート帯がすべてそこから引く。推奨アクションの文言は定義ファイルで差し替え可能にする |
| 緊急度の提示 | SLIMS 取込時に内示受注を 1 クエリで取得し、**照合単位ごとの需要予測・在庫切れ予測月・在庫月数を domain で算出して行に保持**する。クライアントは表示のみ |
| 目的との整合 | メニュー画面のアラート帯・深刻化による未確認化の固定基準を「判定期間 1 年」に一本化する |

**要件定義書からの設計上の逸脱（2026/09/16 承認済み）**: REQ-SFV-F-008 と用語集 V-220 補足は「合算は配信済みの全行で行う（クライアント側）」と書かれていたが、本設計では **取込時に domain（Python）で算出しスナップショットに保持**する。理由は §3.2。承認に伴い要件定義書 F-008・用語集 V-220 補足の当該文言を「取込時に全行で合算する」に改める。

---

## 2. 対象コンテキスト

**B: 在庫発注アラート**（`application/inventory_order_alert/`、生産管理メニューグループ、コアサブドメイン）。

### 2.1 境界の遵守

- 内示受注（`T_UNCNFM_ODR`）は 5年9組（C）でも参照するテーブルだが、**本コンテキストの `infrastructure/oracle/` に専用クエリを置く**。`application.gonenkukumi` からの import は行わない（strategic_design §3「コンテキストをまたぐ直接参照は行わない」）
- Oracle 接続は共有カーネル H（`application.sales.infrastructure.oracle.client`）の ACL 経由（既存の `summary_queries.py` と同じ）
- 用語「内示受注」の定義は 5年9組 T-504 を参照するが、モデル（VO）は本コンテキストで独立に持つ（strategic_design §4.2「判断の文脈が異なればモデルも分ける」）
- ポータル（G）のダッシュボードは、既存どおり `use_cases/portal_dashboard.py` を wiring 経由で呼ぶ

---

## 3. アーキテクチャ概要

```
interfaces/          views.py（一覧・CSV・API）… wiring 経由で use_cases を呼ぶ。変更は文脈値の受け渡しのみ
      ↓
use_cases/           list_page / export_csv / import_stock / portal_dashboard / save_confirmation / patch_snapshot_row
      ↓                （判定期間の受け取り、CSV 列の追加、取込時の需要予測算出の呼び出し）
domain/              value_objects/flow_quadrant.py        … 判定期間・流動区分・ランク・責任部署（改修）
                     value_objects/flow_quadrant_rules.py  … 判定ルール表（改修）
                     value_objects/recommended_action.py   … 推奨アクション・状況テンプレート（新規）
                     value_objects/unconfirmed_order_trend.py … 内示推移（新規）
                     value_objects/reconciliation_unit.py  … 照合単位（新規、04 の JS 実装を Python 化）
                     value_objects/demand_forecast.py      … 需要予測・在庫切れ予測月・在庫月数（新規）
      ↑
infrastructure/      oracle/summary_queries.py … fetch_unconfirmed_orders（新規関数）、build_summary_rows に内示推移と内作品番を付与（業務計算は含めない）
                     config/recommended_actions.py … 定義ファイル（同ディレクトリの JSON）の読み込み（新規）
                     persistence/confirmation_repository.py … 変更なし（固定基準は domain 定数から取る）
```

### 3.1 判定は既存どおり「サーバで事前判定・クライアントで切替」（02 design 案 B の踏襲）

判定期間の切替でサーバへ問い合わせない（REQ-SFV-NF-001）。行に `flow_quadrants = {"Y1": key, "Y3": key, "Y5": key}` を持たせ、JS は選択中のキーで引くだけにする。**判定ロジックは domain にのみ置く**（JS に判定条件を書かない。現行の方針を維持）。

### 3.2 需要予測は取込時に domain で算出する（要件からの逸脱と理由）

| 観点 | クライアント側（要件の記述） | 取込時に domain 側（本設計） |
|---|---|---|
| CSV 出力（F-013 第 2 段階）の在庫月数・在庫切れ予測月 | サーバ側で再実装が必要（二重実装） | 保持値を出すだけ |
| ビジネスルールの置き場所 | JS（テスト不能。04 で「JS の数値検証は手動」が継続課題） | domain（pytest で境界値を固定できる） |
| フィルタ非依存 | 実装で担保 | 取込時に全行で計算するので構造的に非依存 |
| 配信量 | 増えない | 行あたり 3 値（`demand_forecast_basis` / `months_of_stock` / `stockout_forecast_month`）＋内示推移 4 値。推定在庫推移の +1.6KB/行に比べ十分小さい |
| 04 の推定在庫推移（V-218、JS 実装） | 整合 | 照合単位の Python 実装を新設し、**JS 側の照合単位実装は当面残す**（V-218 の再実装は本書のスコープ外。§9 R-4） |

### 3.3 段階分け（REQ §6.3）

| 段階 | 本書の該当 |
|---|---|
| 第 1 段階 | §4.1〜4.3・§5.1・§6.1〜6.5・§6.8・§7 の「第 1 段階」列 |
| 第 2 段階 | §4.4〜4.6・§5.2・§6.6〜6.7・§7 の「第 2 段階」列 |

---

## 4. ドメインモデル

### 4.1 判定期間（V-211）— `flow_quadrant.py` 改修

```python
EVALUATION_PERIOD_YEARS = (1, 3, 5)

@dataclass(frozen=True)
class EvaluationPeriod:
    years: int                      # 1 / 3 / 5
    def __post_init__(self) -> None:
        if self.years not in EVALUATION_PERIOD_YEARS:
            raise ValueError(f"判定期間は {EVALUATION_PERIOD_YEARS} 年のいずれか: {self.years}")
    @property
    def months(self) -> int: return self.years * 12
    @property
    def key(self) -> str: return f"Y{self.years}"      # 行列のキー・URL 値
    @property
    def label(self) -> str: return f"{self.years}年"

class EvaluationPeriods:            # ファーストクラスコレクション（既存クラスを年数のみに単純化）
    def find(self, key: str) -> EvaluationPeriod | None
    def find_by_years(self, years: int) -> EvaluationPeriod | None
    @property
    def default(self) -> EvaluationPeriod          # Y1

EVALUATION_PERIODS = EvaluationPeriods((EvaluationPeriod(1), EvaluationPeriod(3), EvaluationPeriod(5)))
DEFAULT_EVALUATION_PERIOD = EvaluationPeriod(1)

@dataclass(frozen=True)
class FlowSelection:                # 利用者の選択。axis 関連プロパティは削除
    period: EvaluationPeriod

#: メニュー画面のアラート帯・深刻化による未確認化（A-201）の固定基準 = 既定の判定期間
REFERENCE_FLOW_SELECTION = FlowSelection(DEFAULT_EVALUATION_PERIOD)
```

- `FLOW_AXIS_*`・`DEFAULT_FLOW_AXIS`・`for_axis()`・`default_for_axis()`・`FlowSelection.axis / axis_label` は**削除**する
- `EvaluationPeriod` は `__post_init__` で 1/3/5 以外を拒否する（不正な VO を生成できない）。URL 等の外部入力からは `EvaluationPeriods.find_by_years()` を経由し、`None` なら既定にフォールバックする（例外を画面に出さない）
- `is_within_evaluation_period()` / `resolve_flow_quadrant()` の判定規則は変更しない（境界日ちょうどは期間内、未来は期間内、空は期間外）

### 4.2 流動区分（S-203）— `flow_quadrant.py` 改修

```python
QUADRANT_LOW_FLOW_NO_INCOMING = "低流動品（入荷なし）"   # 旧 供給リスク品
QUADRANT_DORMANT_STOCK        = "在庫死蔵品"
QUADRANT_LOW_FLOW_NO_SHIPMENT = "低流動品（出荷なし）"   # 旧 在庫過剰リスク品
QUADRANT_NORMAL_FLOW          = "通常流動品"

FLOW_QUADRANT_KEYS = {              # CSS キー・URL 値・行列の値
    QUADRANT_LOW_FLOW_NO_INCOMING: "low-flow-no-incoming",
    QUADRANT_DORMANT_STOCK:        "dormant-stock",
    QUADRANT_LOW_FLOW_NO_SHIPMENT: "low-flow-no-shipment",
    QUADRANT_NORMAL_FLOW:          "normal-flow",
}
FLOW_QUADRANT_SORT_RANK = {入荷なし: 0, 死蔵: 1, 出荷なし: 2, 通常: 3}   # S-203 のランク。旧ランクと同じ位置
LEGACY_QUADRANT_ALIASES += {"供給リスク品": 入荷なし, "在庫過剰リスク品": 出荷なし,
                            "supply-risk": 入荷なし, "excess-stock-risk": 出荷なし}   # ラベルとキーの両方
```

- `resolve_flow_quadrant()` の分岐は変わらない（`not has_incoming` → 出荷ありなら **入荷なし**、なければ死蔵）。返す定数名だけ変わる
- `normalize_flow_quadrant()` が旧称・旧キーを新区分へ写像する → 確認記録・URL・旧スナップショットの互換（REQ-SFV-F-002・F-003・F-017）
- `is_flow_escalated()` は変更なし（ランク比較）。ランクの**値と順序が旧定義と同一**なので、深刻化判定の意味も保たれる

### 4.3 推奨アクション（T-207）と状況テンプレート — `recommended_action.py` 新規

```python
@dataclass(frozen=True)
class RecommendedAction:         # T-207。英語名は用語集どおり
    quadrant: str
    status_template: str        # S-203 の「状況」の実装。例: "出荷は継続、最終入荷 {last_incoming}（{period}以上入荷なし）"
    action: str                 # 推奨アクションの文言
    departments: tuple[str, ...] # 責任部署（R-201）
    def __post_init__(self) -> None:   # quadrant は FLOW_QUADRANT_KEYS のラベルに限る

@dataclass(frozen=True)
class RecommendedActions:        # ファーストクラスコレクション（4 区分ぶん、欠けを許さない）
    def for_quadrant(self, quadrant: str) -> RecommendedAction
    def with_action_texts(self, overrides: Mapping[str, str]) -> "RecommendedActions"   # 定義ファイルの上書きを適用

DEFAULT_RECOMMENDED_ACTIONS = RecommendedActions((...S-203 の表の文言...))

def render_status(action: RecommendedAction, *, period: EvaluationPeriod, last_incoming: str, last_ship: str, no_incoming_record: bool) -> str
```

- **状況**のプレースホルダは `{period}`（判定期間ラベル）/ `{last_incoming}` / `{last_ship}`。入荷実績なしの行は `{last_incoming}` を「入荷実績なし」に置換（REQ-SFV-F-005）
- 通常流動品の `status_template` と `action` は空文字（セルを空にする）
- 責任部署は既存 `RESPONSIBLE_DEPARTMENTS` をここに移し、`flow_quadrant.py` の `responsible_departments()` はこのコレクションを引く（定義表を 1 か所にする）
- 推奨アクションの**差し替え**: `infrastructure/config/recommended_actions.py` が同じディレクトリの `infrastructure/config/recommended_actions.json`（`{"low-flow-no-incoming": "...", ...}`）を読み、`with_action_texts()` で上書きする。ファイルがなければ既定。**コードを変えずに文言を変えられる**（REQ-SFV-F-006・NF-007）。設定画面での編集は将来。置き場所を `infrastructure/config/` にするのは reference のレイヤー構成（環境依存の設定読み込みは `infrastructure/config/`）に合わせるため
- 「状況テンプレート」は用語集 S-203 の「状況」を実装するためのプレースホルダ付き文字列であり、用語集 T-207 補足に実装上の束ね方を記載する

### 4.4 内示推移（V-219）— `unconfirmed_order_trend.py` 新規（第 2 段階）

```python
def build_unconfirmed_order_trend(
    orders: list[tuple[date, int]],          # (所要日, 数量)
    *, as_of_date: date,
) -> list[dict[str, object]]:
    """当月残（as_of_date 以降）＋翌月〜翌々々月の固定 4 件。数量が負なら 0。"""
```

- 出荷推移（`build_monthly_shipment_trend`）と同じ `{"month": "YYYY-MM", "qty": int}` 形式。先頭要素だけ「当月残」（`as_of_date` 以降の所要日のみ集計）
- 単位は得意先 × 内作品番。行には `internal_item_cd` を併せて保持する（照合単位で重複除去するため）

### 4.5 照合単位（T-208）— `reconciliation_unit.py` 新規（第 2 段階）

```python
@dataclass(frozen=True)
class ReconciliationUnit:
    key: str                                # 成分の代表キー（最小の得意先品番）
    item_cds: frozenset[str]                # 得意先品番
    level1_pairs: frozenset[tuple[str, str]]# (内作品番×仕入先) の組
    row_keys: tuple[tuple[str, str], ...]   # 所属行の (得意先コード, 得意先品番)。リストの並び順に依存させない

class ReconciliationUnits:                  # ファーストクラスコレクション
    @classmethod
    def build(cls, rows: list[dict]) -> "ReconciliationUnits"   # Union-Find（04 §6.6 の JS と同じ辺の定義）
    def unit_of(self, item_cd: str) -> ReconciliationUnit
```

- 04 で JS に実装した Union-Find を Python に移し、**同じ辺の定義**（得意先品番 ―― (level1_item_cd, level1_vend_cd)）で連結成分を作る。JS 実装は当面残す（§3.2）

### 4.6 需要予測・在庫切れ予測月・在庫月数（V-220〜V-222）— `demand_forecast.py` 新規（第 2 段階）

```python
BASIS_UNCONFIRMED = "内示"; BASIS_ACTUAL = "実績ベース"; BASIS_NONE = "なし"
DemandForecastBasis = Literal["内示", "実績ベース", "なし"]

@dataclass(frozen=True)
class DemandForecast:
    basis: DemandForecastBasis              # __post_init__ で 3 値以外を拒否
    current_month_remaining: int            # 当月残の内示受注数量
    monthly: tuple[int, int, int]           # 翌月〜翌々々月
    monthly_average: float                  # 存在する月のみで平均（実績ベースは 12 か月平均出荷）

def build_demand_forecast(unit_rows: list[dict], *, as_of_date: date) -> DemandForecast:
    # 1. (cust_code, internal_item_cd) で重複を除いて unconfirmed_order_trend を月ごとに合算
    # 2. 3 か月の合計が 0 なら、全行の shipment_trend の直近 12 か月合計 / 12 を実績ベースとする
    # 3. どちらも 0 なら なし

def stock_total_of(unit_rows) -> float | None          # 該当なし(空)=0、未取得は 0、全品番が未取得なら None
def stockout_forecast_month(stock_total, forecast, *, as_of_date) -> str | None
def months_of_stock(stock_total, forecast) -> float | None   # 小数 1 桁
```

- **在庫切れ予測月**: `残 = stock_total − current_month_remaining`。残 < 0 なら当月。以降、翌月から `monthly[i]`（4 か月目以降は `monthly_average`）を順に引き、初めて負になる月。上限は 120 か月（超えたら `None` ＝「十分」表示。REQ-SFV-F-018）
- **在庫月数**: `stock_total ÷ monthly_average`。`monthly_average` が 0 または basis が「なし」なら `None`
- 在庫数の 3 状態は `stock_quantity.py` の `is_stock_fetched()` で判定し、未取得は 0 として合算、全品番が未取得なら `None`（V-221 補足）

### 4.7 集約

本機能で新しい集約は作らない。集計スナップショット（既存 `InventoryOrderAlertSummarySnapshot`、行は JSON）に項目を追加するのみ。確認記録（E-201）は変更しない。

---

## 5. データモデル

### 5.1 第 1 段階（スキーマ変更なし）

| 対象 | 変更 |
|---|---|
| `InventoryOrderAlertSummarySnapshot.rows[*].flow_quadrants` | キーを `L1/L3/L6/D1/D2/D5` → `Y1/Y3/Y5` に変更（読込時に毎回再判定するため、**旧スナップショットは読込時に新キーで再計算される**。保存値に依存しない） |
| `rows[*].flow_quadrant` / `flow_quadrant_key` | 新ラベル・新キー |
| `InventoryOrderAlertConfirmation.confirmed_flow_quadrant` | 変更なし。旧称は `normalize_flow_quadrant()` で読める。**リリース時に管理者がリセットする**（REQ-SFV-F-020） |
| `InventoryOrderAlertSettings` | 変更なし |
| 推奨アクション定義ファイル | `infrastructure/config/recommended_actions.json`（任意。なければ既定） |

### 5.2 第 2 段階（JSON 項目の追加、マイグレーション不要）

`rows[*]` に追加するキー:

| キー | 型 | 内容 |
|---|---|---|
| `internal_item_cd` | str | 内作品番（`internal_for()` の解決結果。既に算出しているが未保存だった） |
| `unconfirmed_order_trend` | list[4] | 内示推移（当月残＋3 か月） |
| `reconciliation_unit_key` | str | 照合単位の代表キー（詳細ダイアログで同一単位の行を引くため） |
| `demand_forecast_basis` | str | `内示` / `実績ベース` / `なし` |
| `demand_forecast_monthly` | list[3] | 翌月〜翌々々月の需要予測（照合単位の合算値） |
| `months_of_stock` | float \| null | 在庫月数 |
| `stockout_forecast_month` | str \| null | 在庫切れ予測月 |

- 旧スナップショットにキーがなければ `basis = なし`・在庫月数/予測月は非表示（REQ-SFV-F-017）
- 照合単位の集計値は単位内の全行に**同じ値を複製**して保持する（行単位で自己完結させ、CSV・一覧を単純にする。増分は行あたり 100 バイト程度）

---

## 6. API / インターフェース設計

### 6.1 一覧のクエリパラメータ（REQ-SFV-F-001・F-002・F-016）

| パラメータ | 値 | 備考 |
|---|---|---|
| `period` | `1` / `3` / `5` | 既定 1。不正値・旧値（`6` など）は既定にフォールバック |
| `axis` | — | **受け付けない**（存在しても無視） |
| `flow_quadrant` | `low-flow-no-incoming` / `dormant-stock` / `low-flow-no-shipment` / `normal-flow` | 旧キー `supply-risk` / `excess-stock-risk` は `normalize_flow_quadrant()` で新キーへ写像 |
| `sort` | 既存＋ `months_of_stock` | 空は末尾（第 2 段階） |

`list_query.parse_flow_selection()` は `period` の年数だけを見る。

### 6.2 クライアント配信ペイロード（`list_client_data.py`）

| キー | 変更 |
|---|---|
| `flowAxes` / `flowPeriods` | 削除 → `evaluationPeriods: [{years, key, label}]`、`defaultPeriodKey: "Y1"` |
| `flowQuadrantLabels` / `flowQuadrantOrder` / `flowQuadrantDepartments` | 新区分名・新キー |
| `recommendedActions` | **新規**: `{key: {statusTemplate, action, departments}}`（§4.3 の定義表） |
| 行 `flowQuadrants` | `{"Y1": key, "Y3": key, "Y5": key}` |
| 行 `internalItemCd` / `unconfirmedOrderTrend` / `reconciliationUnitKey` / `demandForecast{basis, monthly, monthsOfStock, stockoutForecastMonth}` | 第 2 段階で追加 |

### 6.3 一覧画面（`list.html` / `inventory-order-alert-list-client.js` / `app.css`）

**ヘッダのアクション行**（REQ-SFV-F-001）:

```
[判定期間 ▼1年] [判定ルール] [SLIMS在庫CSV] [CSV出力] [設定]
```

- `#ioa-flow-axis` と旧 `#ioa-flow-period`・「判定条件」パネルを撤去。判定期間セレクタ `#ioa-evaluation-period` をアクション行の先頭に置く
- 流動区分フィルタ `#ioa-flow-quadrant` はフィルタパネルに残し、選択肢を新区分にする（REQ-SFV-F-010）

**流動区分列のセル**（REQ-SFV-F-004、2026/09/17 改訂）:

```html
<td class="ioa-flow-cell"><span class="ioa-flow-quadrant">低流動品（入荷なし）</span></td>
```

- 通常流動品は `<td>` を空にする
- 状況・緊急度・推奨アクション・責任部署は **詳細ダイアログ（§6.4）にのみ表示**する。状況は JS が `statusTemplate` に選択中の判定期間ラベルと行の日付を埋めて描く（テンプレートは domain 由来、JS は文字列置換のみ）。行の `data-flow-status` / `data-recommended-action` / `data-responsible-department` / `data-months-of-stock` / `data-stockout-forecast-month` は詳細ダイアログのフォールバック用に残す
- 入荷実績なし（V-214）のバッジは出さない（最終入荷日列が空欄で分かる）
- 列幅は他列と同じ扱い（`min-width` の指定なし）
- 行の背景色クラス `alert-row--{key}` はキー名の変更に追随（`supply-risk` → `low-flow-no-incoming` 等）。色は旧区分のものを引き継ぐ

> **［2026/09/17 改訂前］** セルに `ioa-flow-cell-head`（区分＋バッジ）/ `ioa-flow-status` / `ioa-flow-urgency` / `ioa-flow-action` / `ioa-flow-departments` を積み、`min-width: 22em`・狭幅で状況と責任部署を隠す構成だった。

**件数サマリ**（REQ-SFV-F-011）: `counts` の 4 キーを新区分名に。

**判定ルールダイアログ**（REQ-SFV-F-012）: `flow_quadrant_rules.py` の `FlowQuadrantRuleRow` に `status_template` / `action` を追加し、列を 期間内入荷 / 期間内出荷 / 流動区分 / 状況 / 推奨アクション / 責任部署 にする。判定軸の説明文は削除。

### 6.4 詳細ダイアログ（REQ-SFV-F-014）

- 「流動区分」区分: 区分 / 状況 / 推奨アクション / 責任部署 / 判定期間（例: `1年`）
- 第 2 段階で「需要予測」区分を「推定在庫推移」と「メモ」の間に追加: 算出根拠、月別（当月残・翌月〜翌々々月）の内示受注数量、在庫月数、在庫切れ予測月、照合単位の在庫内訳（04 §6.6 の `renderAnchorBreakdown` を流用）

### 6.5 メニュー画面アラート帯・深刻化による未確認化（REQ-SFV-F-015）

- `portal_dashboard.BANNER_FLOW_SELECTION = REFERENCE_FLOW_SELECTION`（既存のまま）。`BANNER_FLOW_CONDITION_LABEL` は「判定期間 1年」に
- `summary_aggregation.py` / `summary_repository.py` / `save_confirmation.py` / `patch_snapshot_row.py` の `REFERENCE_FLOW_SELECTION` 参照は変更不要（定数の中身が変わるだけ）
- `confirmation_repository.py` の `is_flow_escalated()` は変更なし。**リリース手順に「設定画面の確認状態リセットを実行」を追加**（REQ-SFV-F-020）

### 6.6 内示受注の取得（`summary_queries.py`、第 2 段階、REQ-SFV-F-007）

```sql
SELECT TRIM(CUST_CD) AS CUST_CD, TRIM(ITEM_CD) AS ITEM_CD,
       UNCNFM_REQUIRED_DATE, NVL(UNCNFM_REQUIRED_QTY, 0) AS QTY
  FROM T_UNCNFM_ODR
 WHERE DEL_FLG = '0'
   AND UNCNFM_REQUIRED_DATE >= :as_of_date
   AND UNCNFM_REQUIRED_DATE <  :window_end        -- 翌々々月の翌月 1 日
```

- 得意先品番への写像は SQL で `M_CUST_ITEM` を JOIN せず、**Python 側で既存の `internal_for()` の結果（行の `internal_item_cd`）で引く**（既存の最終入荷日・出荷回数と同じ解決規則を使うため。REQ-SFV-F-007「同じ基準日で行う」）
- `group_shipments_by_pair()` を流用して `(cust_code, item_cd)` でグループ化し、`build_unconfirmed_order_trend()` で 4 件にする
- 取得失敗（`OracleQueryError`）は **取込を失敗させない**。内示推移を空にして続行し、`aggregation_error` に「内示受注の取得に失敗: …」を追記して取込結果メッセージに出す（REQ-SFV-F-018）

### 6.7 取込時の需要予測算出（`use_cases/import_stock.py` が制御、第 2 段階）

```
use_cases/import_stock.py（制御フロー）
  rows = aggregation_gateway.build_summary_rows(...)      … infrastructure: Oracle 取得。行に internal_item_cd / unconfirmed_order_trend を付与
  rows = attach_demand_forecast(rows, as_of_date=...)     … domain 関数（demand_forecast.py）: ReconciliationUnits.build
                                                             → 単位ごとに build_demand_forecast
                                                             → 各行に basis / monthly / months_of_stock / stockout_forecast_month / unit_key を複製
  snapshot_repository.store(rows, ...)                     … infrastructure: 保存
```

- **需要予測の算出はユースケース層が domain を呼ぶ**。`summary_aggregation.py`（infrastructure）は Oracle からの取得と行への生データ付与に限定し、業務計算を含めない（reference: ユースケースの制御フローはアプリケーションサービス）。既存の `build_summary_rows` が流動区分の付与まで infrastructure で行っている流儀とは意図的に分ける（§9 R-8）

### 6.8 CSV 出力（`export_csv.py`、REQ-SFV-F-013）

| 段階 | 変更 |
|---|---|
| 第 1 段階 | `流動区分` の値を新区分名に。`判定軸` 列は**空文字で出力を維持**（列順互換のため列は残す）。`判定期間` は `1年` 等 |
| 第 2 段階 | 末尾に `在庫月数` / `在庫切れ予測月` / `需要予測の算出根拠` / `推奨アクション` を追加（`責任部署` は既存列） |

---

## 7. 既存コードへの変更点

### 7.1 新規ファイル

| ファイル | 段階 | 内容 |
|---|---|---|
| `domain/value_objects/recommended_action.py` | 1 | 推奨アクション（T-207）・状況テンプレート・責任部署の定義表（`RecommendedActions` FCC） |
| `infrastructure/config/recommended_actions.py` | 1 | 定義ファイル JSON の読み込みと上書き適用 |
| `infrastructure/config/recommended_actions.json`（任意） | 1 | 文言の差し替え用 |
| `domain/value_objects/unconfirmed_order_trend.py` | 2 | 内示推移 |
| `domain/value_objects/reconciliation_unit.py` | 2 | 照合単位（Union-Find） |
| `domain/value_objects/demand_forecast.py` | 2 | 需要予測・在庫切れ予測月・在庫月数 |
| `tests/test_flow_quadrant_single_period.py` ほか | 1/2 | 各 VO のテスト |

### 7.2 変更ファイル

| ファイル | 段階 | 変更概要 |
|---|---|---|
| `domain/value_objects/flow_quadrant.py` | 1 | 判定軸の削除、判定期間を年数 VO に、区分の改称・キー変更、旧称エイリアス追加 |
| `domain/value_objects/flow_quadrant_rules.py` | 1 | 判定ルール表に状況・推奨アクションを追加 |
| `domain/value_objects/list_query.py` / `list_filter.py` | 1 | `axis` の廃止、`period` の年数解釈、`months_of_stock` ソート（2） |
| `domain/value_objects/list_rows.py` | 1 | 行列キー Y1/Y3/Y5、状況・推奨アクションの付与 |
| `domain/value_objects/list_client_data.py` | 1/2 | ペイロードのキー変更（§6.2） |
| `domain/value_objects/row_counts.py` / `row_display.py` / `export_csv.py` | 1/2 | 新区分名、CSV 列 |
| `use_cases/list_page.py` / `portal_dashboard.py` | 1 | 判定軸関連のコンテキスト削除、帯の条件ラベル |
| `use_cases/import_stock.py` | 2 | 需要予測の算出（`attach_demand_forecast`）を取込フローに組み込む |
| `infrastructure/oracle/summary_aggregation.py` / `summary_queries.py` | 2 | 内示受注の取得と行への付与（業務計算は含めない） |
| `interfaces/wiring.py` / `views.py` | 1 | 推奨アクション定義ファイルの読み込みを wiring で組み立て |
| `templates/inventory_order_alert/list.html` | 1/2 | セレクタの移設・撤去、セル構成、判定ルール表、詳細ダイアログ |
| `templates/portal/dashboard.html` | 1 | 新区分名 |
| `static/js/inventory-order-alert-list-client.js` / `inventory-order-alert-list.js` | 1/2 | `flowAxis` の撤去、`evaluationPeriods`、セル描画、詳細の需要予測区分 |
| `static/css/app.css` | 1 | セルのレイアウト、背景色クラス名の追随 |
| `docs/在庫発注アラート_機能仕様書.md` / `02_low-flow-visibility/requirements.md` | 1 | §4.1.5・§4.1.6・§5.2・§6.2 の改訂、02 に置換注記 |
| 既存テスト（`test_flow_quadrant*.py` / `test_inventory_order_alert_views.py` / `test_summary_api.py` / `test_reconcile_confirmations.py` / `test_export_csv*.py` / `test_portal_dashboard*.py` ほか） | 1/2 | 新区分名・新キー・新パラメータへの追随 |

### 7.3 削除するもの

- `FLOW_AXIS_LOW_FLOW` / `FLOW_AXIS_DORMANT` / `FLOW_AXIS_LABELS` / `FLOW_AXIS_HELP_TEXTS` / `DEFAULT_FLOW_AXIS` / `DEFAULT_LOW_FLOW_VALUE` / `DEFAULT_DORMANT_VALUE`
- `EvaluationPeriods.for_axis()` / `default_for_axis()`、`FlowSelection.axis` / `axis_label`
- テンプレートの `#ioa-flow-axis` セレクタと「判定条件」パネル、JS の `flowAxis` 状態と `resolveFlowPeriod(flowPeriods, axis, …)`
- CSV の `判定軸` 列の**値**（列自体は空で残す）

---

## 8. エラーハンドリング方針

| 事象 | 扱い |
|---|---|
| `period` が不正・旧値 | `DEFAULT_EVALUATION_PERIOD` にフォールバック。例外を投げない |
| `flow_quadrant` が旧キー・未知 | 旧キーは新キーへ写像、未知は「全て」 |
| 確認記録の `confirmed_flow_quadrant` が旧称 | `normalize_flow_quadrant()` で新区分へ（リリース時のリセット後は発生しない） |
| 内示受注の取得失敗 | 取込は成功。内示推移は空、需要予測は実績ベース／なし。`aggregation_error` に追記しログ出力 |
| 内示受注数量が負 | 0 として扱う |
| 得意先品番 → 内作品番が解決できない | `internal_item_cd = ""`、内示推移は空（実績ベース／なし） |
| 照合単位の全品番が在庫未取得 | 在庫月数・在庫切れ予測月は `None` |
| 定義ファイル JSON が不正 | 起動時に警告ログを出し既定文言を使う（画面は落とさない） |
| 旧スナップショット（追加キーなし） | 需要予測「なし」、行列は読込時に再計算 |

判定・算出関数は**例外を投げない**（02・04 と同じ方針）。

---

## 9. リスクと対策

| # | リスク | 対策 |
|---|---|---|
| R-1 | 区分名・キー名の変更漏れ（テンプレート・CSS・テスト・ダッシュボード） | `grep` で旧称・旧キー（`supply-risk` / `excess-stock-risk` / `low_flow` / `dormant` 軸）を洗い出し、`test_clean_architecture` に加えて「旧称が画面 HTML に出ない」テスト（REQ-SFV-F-019）を追加 |
| R-2 | 確認記録の基準変更で初回取込に大量リセット | REQ-SFV-F-020 のとおりリリース手順で手動リセット。Document/ の本番デプロイ手順に追記 |
| R-3 | メニュー画面のアラート帯の件数が大きく変わる | リリース周知（REQ §6.3）。件数の変化量は第 1 段階の実装後に実データで測り DECISIONS に記録 |
| R-4 | 照合単位が JS（V-218）と Python（V-220）の二重実装になる | 辺の定義を design で一致させ、テストで同一データに対する成分数（1,994 単位）を照合。V-218 の Python 化は別タスク |
| R-5 | 単位（バラ数）の不一致で在庫月数が桁で狂う | REQ §6.2 の前提。第 2 段階の実装時に実データ（96160-00500 等）で在庫月数の妥当性を目視確認し DECISIONS に記録 |
| R-6 | 内示受注クエリの取込時間増 | 直近 3 か月に `UNCNFM_REQUIRED_DATE` で絞る（実測 約 116 千件）。目標 +5 秒以内を取込ログで確認 |
| R-7 | 要件・用語集との文言差（F-008「配信済みの全行で」） | 本書承認に伴い要件定義書 F-008・用語集 V-220 補足を「取込時に全行で合算」に改訂する（2026/09/16 実施） |
| R-8 | 照合単位・需要予測が `list[dict]` の行を直接扱い、dict 中心のドメインモデル（issues/ISSUE-0001）を踏襲する | 本書で新たに悪化させない（新設 VO は dataclass で、行の読み書きは `demand_forecast.attach_demand_forecast()` に閉じ込める）。行のエンティティ化は ISSUE-0001 の別タスク |

---

## レビュー履歴

### Design-L1レビュー (2026/09/16 09:56)

**アーキテクチャreference**: django-clean-architecture version 1.0（make-design / design-review-l1 / implement-review-l1 で一致）

| 観点 | OK | 警告 | NG |
|------|-----|------|-----|
| 1. 戦略的設計との整合性 | 5件 | 0件 | 0件 |
| 2. ドメインモデルの妥当性 | 4件 | 2件 | 0件 |
| 3. ビジネスルールの配置 | 3件 | 2件 | 0件 |
| 4. ユビキタス言語との整合性 | 3件 | 3件 | 0件 |

**総合判定**: PASS

| # | 観点 | 重要度 | 該当箇所 | 指摘内容 | 対応 |
|---|------|--------|---------|---------|------|
| 1 | 観点2 | 警告 | §4.1 | `EvaluationPeriod.years` に値域の制約がなく不正な VO を生成できる | 修正済み(2026/09/16、`__post_init__` で 1/3/5 を強制) |
| 2 | 観点2 | 警告 | §4.5・§4.6 | `DemandForecast.basis` が自由な str、`ReconciliationUnit.row_indexes` がリスト順に依存 | 修正済み(2026/09/16、`Literal` ＋ `__post_init__`、`row_keys` に変更) |
| 3 | 観点2 | 警告 | §4.4〜4.6 | dict 中心の行モデル（ISSUE-0001）の踏襲が明記されていない | 修正済み(2026/09/16、§9 R-8) |
| 4 | 観点3 | 警告 | §4.3・§5.1・§7.1 | 定義ファイルの置き場所が reference のレイヤー構成にない | 修正済み(2026/09/16、`infrastructure/config/` に移動) |
| 5 | 観点3 | 警告 | §6.7 | 需要予測算出の制御フローが infrastructure に寄っていた | 修正済み(2026/09/16、`use_cases/import_stock.py` が domain を呼ぶ構成に変更) |
| 6 | 観点4 | 警告 | §4.3 | `FlowQuadrantGuidance` が用語集 T-207 の英語名 `RecommendedAction` と不一致、「状況テンプレート」が未定義 | 修正済み(2026/09/16、`RecommendedAction` / `RecommendedActions` に改名。用語集 T-207 補足に実装上の束ね方を追記) |
| 7 | 観点4 | 警告 | §1・§4.1・§9 | 「メニュー帯」の表記揺れ | 修正済み(2026/09/16、「メニュー画面のアラート帯」に統一) |

**未解決の指摘**: 0件

**次のアクション**: テスト設計書（test-design.md）の作成へ

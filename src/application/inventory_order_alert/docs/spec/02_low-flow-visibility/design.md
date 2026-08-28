# 機能設計書: 低流動品・在庫死蔵品の状況把握機能

文書ID: DESIGN-LOW-FLOW-VISIBILITY-2026-001
作成日: 2026/08/27
更新日:
対応文書: ./requirements.md (REQ-LOW-FLOW-VISIBILITY-2026-001)
アーキテクチャreference: django-clean-architecture version 1.0 (updated 2026-04-11)

---

## 1. 設計の目的

要件定義書 REQ-LOW-FLOW-VISIBILITY-2026-001 が定める「流動区分（S-203）による状況把握」を、
在庫発注アラートの既存一覧画面に実装する。技術的な到達目標は次の4点である。

1. **判定ロジックの一元化**: 流動区分の判定を domain 層の純関数に閉じ込め、
   Python / JavaScript / テンプレートのいずれからも同一の結果が得られるようにする。
   JavaScript には判定ロジックを持ち込まない（サーバが全通りを事前計算して配信する）。
2. **バッチ・スキーマ変更なしの導入**: 流動区分は既存の最終入荷日（V-201）・最終出荷日（V-202）・
   BOM 基準日（V-209）だけで計算できる。集計スナップショット（`InventoryOrderAlertSummarySnapshot.rows`）の
   スキーマも、Oracle 集計 SQL も変更しない（REQ-LFV-F-016 / NF-002 / NF-007）。
3. **旧アラートレベルの置換**: アラートレベル（S-202）を流動区分（S-203）に置き換え、
   旧実装を domain から撤去する。DB カラムはデータ保全のため残置する。
4. **判定軸・判定期間の即時切り替え**: 再取込・サーバ往復なしで、6通り（低流動 1/3/6か月・死蔵 1/2/5年）を
   切り替えられるようにする（REQ-LFV-F-002 / F-003）。

## 2. 対象コンテキスト

`docs/strategic_design.md` に従い、本機能は次の位置にある。

| 項目 | 内容 |
|------|------|
| 境界コンテキスト | **B: 在庫発注アラート**（コア／生産管理メニューグループ） |
| パッケージ | `application/inventory_order_alert/` |
| 上流（供給） | 基幹 Oracle (MARI)（**読み取り専用**・共有カーネル `application/sales/infrastructure/oracle/`）／SLIMS 在庫CSV |
| 下流（利用） | ポータル（コンテキスト A）— メニュー画面のアラート帯（REQ-LFV-F-013） |

### 2.1 境界の遵守

- **Oracle への追加問い合わせを行わない。** 流動区分の判定に必要な値はすべて既存の集計行に含まれている。
- **ポータルとの越境は合成ルート経由のみ。** `application/portal/interfaces/wiring.py` が
  `inventory_order_alert.interfaces.wiring.portal_dashboard_usecase()` を呼ぶ既存パターンを踏襲し、
  ポータル側から本コンテキストの use_cases / domain / models を直接参照しない
  （strategic_design.md §4.3 が明示的に許可した唯一の越境パターン）。
- **共有カーネルの変更なし。** `application/shared/domain/value_objects/`（prefix_filter / code_sort /
  dependent_cust_filter / list_table）には手を入れない。流動区分は本コンテキスト固有の概念である。

## 3. アーキテクチャ概要

```
interfaces/            views.py（HTTP 入出力）／urls.py／wiring.py（合成ルート）
      ↓
use_cases/             ListPage / ExportCsv / PortalDashboard / SummaryApi / PatchSnapshotRow
      ↓
domain/                value_objects/flow_quadrant.py（★新規・判定の中核）
      ↑                value_objects/{list_rows, row_counts, row_display, table_display, ...}
infrastructure/        persistence/summary_repository.py（読込時に流動区分を付与）
```

本機能で新設・変更するレイヤーと責務:

| レイヤー | 本機能での責務 | Django 依存 |
|---------|--------------|------------|
| domain | 流動区分の判定、判定軸・判定期間の値域、責任部署の導出、並び順ランク、旧値の正規化 | **禁止**（`import django` を書かない） |
| use_cases | 一覧・CSV・メニュー帯の組み立て。判定軸・判定期間の選択値の解決 | **禁止** |
| infrastructure | 集計行の読込と流動区分の付与、確認記録の永続化 | 許可 |
| interfaces | クエリ文字列の受け取り、テンプレート・JSON への詰め替え | 許可 |

### 3.1 判定タイミングの方針（REQ-LFV-F-016）

既存の `summary_repository.load_latest_summary()` は、スナップショットに保存された行に対して
**読込のたびに** `apply_alert_levels_to_rows()` でアラートレベルを計算している
（アラートレベルはスナップショットに保存されていない）。流動区分もこの経路に乗せる。

したがって:

- `InventoryOrderAlertSummarySnapshot.rows` のスキーマ変更は**不要**。
- 既存スナップショットの再取込も**不要**（NF-002 を満たす）。
- 判定軸・判定期間を切り替えても、スナップショットは書き換わらない。

### 3.2 判定軸・判定期間の切り替え方式（REQ-LFV-F-002 / F-003 / NF-001）

一覧画面は既に**全件をクライアントへ JSON 配信して JavaScript で描画する**方式である
（`build_list_client_payload()` → `#ioa-list-data` → `inventory-order-alert-list-client.js`）。
そのため切り替えの実現方式は次の2案がある。

| 案 | 内容 | 判定 |
|----|------|------|
| A | JavaScript が最終入荷日・最終出荷日から流動区分を再計算する | **不採用**。判定ロジックが Python と JS に二重化し、暦月計算（`add_calendar_months`）の移植ミスが致命的 |
| B | サーバが**6通りすべて**の流動区分を事前計算し、行ごとに配信する。JS は選択キーで引くだけ | **採用** |

案 B の配信形式（1行あたり）:

```json
"flowQuadrants": {"L1": "supply-risk", "L3": "supply-risk", "L6": "normal-flow",
                  "D1": "excess-stock-risk", "D2": "normal-flow", "D5": "normal-flow"},
"noIncomingRecord": true
```

キーは `L{1,3,6}`（低流動判定軸・か月）と `D{1,2,5}`（死蔵判定軸・年）の6固定。
値は流動区分キー（§4.2.3）。1行あたり約 90 バイトの増加であり、既存の `display` マップ
（14 列分）に比べて十分小さい。判定ロジックは domain の純関数1つに保たれる。

### 3.3 変更しない横断的関心事

| 関心事 | 判断 |
|-------|------|
| 認可（NF-003） | **新しい権限区分を設けない。** 画面へのアクセス可否は既存の `portal/interfaces/favorites.py` の認可述語と `is_admin` 判定のまま。流動区分は誰が見ても同じ値であり、責任部署（R-201）は表示のみで認可に用いない |
| バッチ（NF-007） | **新しいバッチを追加しない。** SLIMS 取込バッチの処理内容も、流動区分の付与のために増やさない |
| Oracle アクセス | **追加しない。** 既存の集計 SQL・接続設定に変更なし |
| アーキテクチャ検証 | `src/config/tests/test_clean_architecture.py` が依存方向と `import django` の混入を検証する。本機能で追加する `domain/value_objects/flow_quadrant.py` も同テストの対象になる |
| テスト方針（NF-006） | TDD で実装する。境界値（判定期間の境界日・未来日・空日付）のテスト設計は `test-design.md` に定義する |

## 4. ドメインモデル

### 4.1 エンティティ

**新規エンティティなし。** 流動区分は「ある集計行を、ある判定条件で見たときの分類結果」であり、
識別子もライフサイクルも持たない。既存エンティティ（確認記録 `InventoryOrderAlertConfirmation`）の
保持する値の意味が変わるのみ（§5.2）。

### 4.2 バリューオブジェクト

新規ファイル: `domain/value_objects/flow_quadrant.py`

#### 4.2.1 V-210 判定軸 `FlowAxis`

```python
FLOW_AXIS_LOW_FLOW = "low_flow"   # 低流動判定軸
FLOW_AXIS_DORMANT = "dormant"     # 死蔵判定軸
FLOW_AXIS_LABELS = {FLOW_AXIS_LOW_FLOW: "低流動判定軸", FLOW_AXIS_DORMANT: "死蔵判定軸"}
DEFAULT_FLOW_AXIS = FLOW_AXIS_LOW_FLOW
```

#### 4.2.2 V-211 判定期間 `EvaluationPeriod`

```python
@dataclass(frozen=True)
class EvaluationPeriod:
    axis: str          # FLOW_AXIS_LOW_FLOW | FLOW_AXIS_DORMANT
    value: int         # 低流動: 1/3/6（か月）、死蔵: 1/2/5（年）

    @property
    def months(self) -> int:      # 死蔵は value * 12
    @property
    def key(self) -> str:         # "L3" / "D1"
    @property
    def label(self) -> str:       # "3か月" / "1年"
```

ファーストクラスコレクション（CLAUDE.md §2 の必須事項）:

```python
class EvaluationPeriods:
    """判定期間の固定6値。列挙・既定値解決・キー検索を担う。"""
    def for_axis(self, axis: str) -> tuple[EvaluationPeriod, ...]
    def default_for_axis(self, axis: str) -> EvaluationPeriod
    def find(self, key: str) -> EvaluationPeriod | None
    def __iter__(self) / __len__(self)

EVALUATION_PERIODS = EvaluationPeriods((
    EvaluationPeriod(FLOW_AXIS_LOW_FLOW, 1), EvaluationPeriod(FLOW_AXIS_LOW_FLOW, 3),
    EvaluationPeriod(FLOW_AXIS_LOW_FLOW, 6),
    EvaluationPeriod(FLOW_AXIS_DORMANT, 1), EvaluationPeriod(FLOW_AXIS_DORMANT, 2),
    EvaluationPeriod(FLOW_AXIS_DORMANT, 5),
))

DEFAULT_LOW_FLOW_VALUE = 3   # REQ-LFV-F-003
DEFAULT_DORMANT_VALUE = 1    # REQ-LFV-F-003
```

#### 4.2.3 S-203 流動区分 `FlowQuadrant`

ラベル（画面・CSV に出す文字列）と、キー（CSS クラス・JSON・URL に使う ASCII 識別子）を分離する。
既存のアラートレベルは日本語ラベルをそのまま CSS クラス名に使っていたが（`.alert-row--重点`）、
流動区分では ASCII キーを使う（§7.4 の理由による）。

```python
QUADRANT_SUPPLY_RISK       = "供給リスク品"        # key: "supply-risk"
QUADRANT_DORMANT_STOCK     = "在庫死蔵品"          # key: "dormant-stock"
QUADRANT_EXCESS_STOCK_RISK = "在庫過剰リスク品"    # key: "excess-stock-risk"
QUADRANT_NORMAL_FLOW       = "通常流動品"          # key: "normal-flow"
```

| 期間内入荷 (V-212) | 期間内出荷 (V-213) | 流動区分 | キー | 並び順ランク | 責任部署 (R-201) |
|---|---|---|---|---|---|
| なし | あり | 供給リスク品 | `supply-risk` | 0 | 調達G・営業G・生産管理 |
| なし | なし | 在庫死蔵品 | `dormant-stock` | 1 | 調達G |
| あり | なし | 在庫過剰リスク品 | `excess-stock-risk` | 2 | 営業G |
| あり | あり | 通常流動品 | `normal-flow` | 3 | 生産管理 |

並び順ランクは REQ-LFV-F-010 の昇順（供給リスク品 → 在庫死蔵品 → 在庫過剰リスク品 → 通常流動品）に一致する。
これは緊急度の順である — 出荷が続いているのに入荷がない状態（供給リスク品）は欠品による顧客影響が直近に生じ、
在庫死蔵品は金額的損失だが即時性が低い。

```python
FLOW_QUADRANT_KEYS: dict[str, str]        # ラベル → キー
FLOW_QUADRANT_LABELS: dict[str, str]      # キー → ラベル
FLOW_QUADRANT_SORT_RANK: dict[str, int]   # ラベル → 0..3
FLOW_QUADRANTS: tuple[str, ...]           # 並び順ランク順のラベル4値
```

#### 4.2.4 V-214 入荷実績なし `NoIncomingRecord`

```python
def is_no_incoming_record(last_incoming_date: date | None) -> bool:
    return last_incoming_date is None
```

流動区分から独立した副次フラグ（REQ-LFV-F-006）。判定期間に依存しないため、行ごとに1個だけ持つ。

#### 4.2.5 判定条件の組 `FlowSelection`

判定軸と判定期間は常に組で扱う（軸に対応しない期間は存在しない）。組として1つの VO にまとめる。

```python
@dataclass(frozen=True)
class FlowSelection:
    period: EvaluationPeriod
    @property axis(self) -> str
    @property key(self) -> str          # "L3"
    @property axis_label(self) -> str   # "低流動判定軸"
    @property period_label(self) -> str # "3か月"

REFERENCE_FLOW_SELECTION = FlowSelection(EvaluationPeriod(FLOW_AXIS_LOW_FLOW, 3))
```

`REFERENCE_FLOW_SELECTION`（**基準判定条件**）は、利用者の選択に依存してはならない箇所で使う固定条件である。
用途は2つ、いずれも一覧の初期値と同じ「低流動判定軸・3か月」に揃える:

- メニュー画面のアラート帯（REQ-LFV-F-013）
- 確認記録の深刻化判定（REQ-LFV-F-014、§5.2）

### 4.3 集約

**新規集約なし。** 流動区分は集計行に付随する導出値であり、独立したトランザクション境界を持たない。
確認記録（`InventoryOrderAlertConfirmation`）は既存の集約のまま、保持する値の意味だけが変わる。

### 4.4 ドメインサービス

判定は状態を持たない純関数として `flow_quadrant.py` に置く。ドメインサービスクラスは設けない
（既存の `alert_level.py` と同じ流儀）。

```python
def is_within_evaluation_period(target: date | None, *, as_of_date: date, months: int) -> bool:
    """target が判定期間内か。None は「なし」。基準日より未来は期間内とみなす（REQ-LFV-F-017）。"""
    if target is None:
        return False
    return target >= add_calendar_months(as_of_date, -months)


def resolve_flow_quadrant(
    last_incoming_date: date | None,
    last_ship_date: date | None,
    *,
    as_of_date: date,
    selection: FlowSelection,
) -> str:
    """流動区分（S-203）を判定する。在庫数は判定に用いない。"""
    months = selection.period.months
    has_incoming = is_within_evaluation_period(last_incoming_date, as_of_date=as_of_date, months=months)
    has_shipment = is_within_evaluation_period(last_ship_date, as_of_date=as_of_date, months=months)
    if not has_incoming:
        return QUADRANT_SUPPLY_RISK if has_shipment else QUADRANT_DORMANT_STOCK
    return QUADRANT_NORMAL_FLOW if has_shipment else QUADRANT_EXCESS_STOCK_RISK


def resolve_flow_quadrant_matrix(
    last_incoming_date, last_ship_date, *, as_of_date
) -> dict[str, str]:
    """6通りの判定条件すべてで流動区分を求め、{"L1": "supply-risk", ...} を返す（§3.2 案B）。"""


def responsible_departments(quadrant: str) -> tuple[str, ...]:
    """R-201 責任部署。表示のみ・暫定（REQ-LFV-F-007）。"""


def flow_quadrant_sort_rank(quadrant: str) -> int:
def normalize_flow_quadrant(value: str) -> str      # §5.2 旧値の正規化を含む
def is_flow_escalated(previous: str, current: str) -> bool  # rank(current) < rank(previous)
```

**判定期間の起点**は BOM 基準日（V-209、`as_of_date`）である。既存 `dates.py` の
`add_calendar_months(base, months)` は負の月数でも正しく動く（`month_index // 12` が Python の
床除算で負方向に丸まる）ため、`-months` を与えて期間の開始日を求める。
死蔵判定軸の 1/2/5年 は 12/24/60 か月として同一関数で扱う。

境界の扱い（REQ-LFV-F-017 に対応）:

| ケース | 判定 |
|--------|------|
| 日付が空（`None`） | 期間外（「なし」） |
| `target == as_of_date - N か月`（境界ちょうど） | **期間内**（`>=` 比較） |
| `target > as_of_date`（基準日より未来） | **期間内** |
| 暦月の末日（例: 8/31 の 6か月前 → 2/28 または 2/29） | `add_calendar_months` の既存丸め規則に従う |

## 5. データモデル

### 5.1 変更しないもの

| テーブル | 判断 |
|---------|------|
| `InventoryOrderAlertSummarySnapshot` | **スキーマ変更なし。** `rows`(JSONField) の要素構造も変えない。流動区分は読込時に付与する（§3.1） |
| `SlimsStockImport` / `SlimsStockSnapshot` | 変更なし |
| `InventoryOrderAlertConfirmationMemoEntry` | 変更なし |

`InventoryOrderAlertSummarySnapshot.critical_count` / `warning_count` の扱い:

- カラムは**残置**する（削除マイグレーションはデータを失うため行わない）。
- 書き込み時は、`critical_count` に **供給リスク品**の件数、`warning_count` に
  **在庫死蔵品＋在庫過剰リスク品**の件数を、`REFERENCE_FLOW_SELECTION` で数えて入れる。
  旧アラートレベルの「重点／警告」と緊急度の位置づけが対応するため、既存行との連続性が保たれる。
- 書き込み箇所は `infrastructure/persistence/summary_repository.py` と
  `infrastructure/persistence/summary_snapshot_repository.py` の**2ファイル・計4箇所**であり、いずれも同じ規則で置き換える。
- 参照側（`SummaryLoadResult.critical_count` / `warning_count`）は既存のまま。実質の唯一の利用箇所は
  `tests/test_summary_storage.py` であり、画面表示は `count_rows()` の再計算値を使う。

### 5.2 変更するもの: 確認記録（REQ-LFV-F-014）

`InventoryOrderAlertConfirmation.confirmed_alert_level`（CharField(40)）は、
**確認時点の流動区分**を保持するフィールドに意味を変える。

| 項目 | 決定 |
|------|------|
| フィールド名 | `confirmed_alert_level` → **`confirmed_flow_quadrant`** にリネーム |
| マイグレーション | `0011_rename_confirmed_alert_level.py`（`RenameField` 1件のみ）。PostgreSQL の `ALTER TABLE ... RENAME COLUMN` は即時・データ保持 |
| `max_length` | 40 のまま（最長ラベル「在庫過剰リスク品」= 8文字） |
| 既存データ | **書き換えない**（データ移行バッチを作らない。NF-007） |

既存データには旧アラートレベルのラベルが入っている。読み取り時に `normalize_flow_quadrant()` が
次の互換写像で流動区分へ正規化する（REQ-LFV-F-017「確認記録に未知のラベル → 正規化」）。

| 旧アラートレベル | 旧条件（入荷／出荷） | 正規化後の流動区分 | 根拠 |
|---|---|---|---|
| 重点 | なし／あり | 供給リスク品 | 条件が完全一致 |
| 警告（出荷なし） | あり／なし | 在庫過剰リスク品 | 条件が対応 |
| 警告（出荷あり） | あり／あり | 通常流動品 | 条件が対応 |
| アラート無し（旧別名 なし／アラートなし／問題なし／空） | 混在 | 通常流動品 | 旧「アラート無し」は在庫死蔵品と通常流動品の双方を含むため、**差し戻しが起きにくい安全側**（最も低いランク）に倒す |
| 旧別名 警告（出荷）／警告（入荷） | — | 供給リスク品の対象外・上表に従う | 既存 `normalize_alert_level` の別名解決を引き継ぐ |
| 上記以外の未知の値 | — | 通常流動品 | 同上（安全側） |

**深刻化判定**（`reconcile_confirmations_after_import`）は `REFERENCE_FLOW_SELECTION`（低流動判定軸・3か月）で
現在の流動区分を求め、`is_flow_escalated(previous, current)` が真のときのみ確認記録を未確認へ差し戻す。
利用者が画面で選んだ判定軸・判定期間は**深刻化判定に影響しない**（取込バッチは利用者の画面状態を知り得ないため）。

### 5.3 残置する未使用カラム（REQ-LFV-F-015）

`InventoryOrderAlertSettings` の以下のカラムは、旧アラートレベル方式でのみ使われていた。
**カラムは残置し、アプリケーションからは参照しない**。models.py にコメントで「旧アラートレベル方式の残置カラム（未使用）」と明記する。
同テーブルには既に `recent_incoming_days` / `stale_incoming_days` / `balance_shipment_months` /
`incoming_grace_days` といった未使用カラムが残っており、既存の運用方針と一致する。

- `warning_shipment_months`（T-203 警告条件）
- `warning_incoming_months`（T-203 警告条件）
- `critical_enabled`

`warning_days` / `stock_stale_days` は在庫データ陳腐化判定などで引き続き使用するため、変更しない。

## 6. API / インターフェース設計

### 6.1 URL クエリパラメータ（REQ-LFV-F-012）

一覧画面（`/app/production/inventory-order-alert`）に2つのパラメータを追加する。

| パラメータ | 値 | 既定値 | 不正値のとき |
|-----------|-----|-------|-------------|
| `axis` | `low_flow` / `dormant` | `low_flow` | 既定値へフォールバック |
| `period` | 軸に対応する値（低流動 `1`/`3`/`6`、死蔵 `1`/`2`/`5`） | 軸の既定値（低流動 3、死蔵 1） | **当該軸の既定値**へフォールバック |
| `flow_quadrant` | 流動区分キー（`supply-risk` 等）／空=全件 | 空 | 空（全件）へフォールバック |

- `axis` を切り替えたときは `period` を当該軸の既定値へリセットする（REQ-LFV-F-003）。
- フォールバックは**静かに**行い、ログを出さない（NF-007）。利用者の URL 編集に由来する入力であり、
  運用監視上の価値がないため。画面には常に有効な軸・期間が表示され、URL も正規化された値に書き戻される。
- 既存の `build_display_query_string()`（`domain/value_objects/list_filter.py`）に
  `axis` / `period` / `flow_quadrant` を追加し、ソート・ページング・フィルタのリンク生成すべてに引き継がせる。
- クライアント側は既存の `updateUrl()`（`history.replaceState`）に同3項目を追加する。
  これにより**再読み込み後も選択が復元される**（REQ-LFV-F-012）。

### 6.2 クライアント配信ペイロード

`build_list_client_payload()` の追加項目:

```json
{
  "rows": [{ "...": "...", "flowQuadrants": {"L1": "...", ...}, "noIncomingRecord": true,
             "flowQuadrantKey": "supply-risk", "flowQuadrant": "供給リスク品",
             "responsibleDepartment": "調達G・営業G・生産管理" }],
  "flowAxes": [{"value": "low_flow", "label": "低流動判定軸"}, {"value": "dormant", "label": "死蔵判定軸"}],
  "flowPeriods": {"low_flow": [{"value": 1, "key": "L1", "label": "1か月"}, ...],
                  "dormant":  [{"value": 1, "key": "D1", "label": "1年"}, ...]},
  "flowQuadrantLabels": {"supply-risk": "供給リスク品", ...},
  "flowQuadrantOrder": ["supply-risk", "dormant-stock", "excess-stock-risk", "normal-flow"],
  "defaultFlowSelection": {"axis": "low_flow", "period": 3}
}
```

`row.flowQuadrantKey` / `flowQuadrant` / `responsibleDepartment` はサーバ描画時の選択条件に対応した値であり、
JavaScript は軸・期間が変わるたびに `row.flowQuadrants[key]` から引き直して更新する。
**JavaScript は判定ロジック（暦月計算・4象限の分岐）を一切持たない。**

### 6.3 CSV 出力（REQ-LFV-F-011）

`ExportCsv.execute()` は現在引数を取らず、`summary.rows` をそのまま出力している。
判定軸・判定期間を反映するため、入力経路を新設する。

```python
class ExportCsv:
    def execute(self, *, query_params: dict[str, str] | None = None) -> ExportCsvResult
```

- `views.export_csv` が `_query_params(request)` を渡す。
- 出力は**全件**（一覧の絞り込み・ページングを反映しない）、UTF-8 BOM 付きを維持する。
- `EXPORT_COLUMNS` の変更:

| 変更 | 列キー | 見出し |
|------|-------|-------|
| 置換 | `alert_level` → `flow_quadrant` | アラート → **流動区分** |
| 追加 | `flow_axis` | 判定軸 |
| 追加 | `evaluation_period` | 判定期間 |
| 追加 | `no_incoming_record` | 入荷実績なし（値は「あり」／空） |
| 追加 | `responsible_department` | 責任部署 |

判定軸・判定期間は**全行に同じ値を持つ列**として出力する。ヘッダ行の前に条件行を挿入する案は、
Excel 取り込み・既存の CSV 読み込み手順を壊すため採らない。
`confirmation_status` 以降の既存列の順序は変更しない。

### 6.4 メニュー画面のアラート帯（REQ-LFV-F-013）

`PortalDashboard` を流動区分ベースに置き換える。判定条件は `REFERENCE_FLOW_SELECTION`（低流動判定軸・3か月）で固定し、
**利用者は変更できない**（要件で固定値と定めたため）。

```python
@dataclass(frozen=True)
class DashboardBannerContext:
    supply_risk: int
    dormant_stock: int
    excess_stock_risk: int
    unconfirmed: int
    stock_as_of_label: str
    has_stock_data: bool
    stock_stale: bool
    error_message: str = ""

    @property
    def attention(self) -> int:        # supply_risk + dormant_stock + excess_stock_risk
    @property
    def has_alerts(self) -> bool:      # attention > 0
    @property
    def tone(self) -> str:             # 下表
```

| 条件 | tone | 帯の配色（既存クラスを流用） |
|------|------|--------------------|
| `error_message` あり | `neutral` | 既存のまま |
| `supply_risk > 0` | `critical` | 既存のまま |
| `dormant_stock > 0 or excess_stock_risk > 0` | `warning` | 既存のまま |
| それ以外 | `ok` | 既存のまま |

帯の文言: `供給リスク品 N 件 / 在庫死蔵品 N 件 / 在庫過剰リスク品 N 件 / 未確認 N 件`（低流動判定軸・3か月）。
判定条件を末尾に明記し、一覧で別の条件を選んでいる利用者が件数の差に混乱しないようにする（REQ-LFV-F-004 の趣旨）。

件数の数え方は既存を踏襲し、**確認済み・確認中の行も流動区分の件数に含める**
（`count_rows()` は確認状態で除外していない）。`unconfirmed` は従来どおり確認状態が「未確認」の行数である。

エラー時・在庫未取込時に 0 件で返す既存の挙動、`application/portal/interfaces/wiring.py` 経由の合成は変更しない。

### 6.5 撤去する API（REQ-LFV-F-015）

警告条件（T-203）は流動区分の判定に用いないため、その設定 UI と API を撤去する。

| 対象 | 処置 |
|------|------|
| `PUT /api/inventory-order-alert/alert-settings` | **削除**（`urls.py` / `views.api_save_alert_settings`） |
| `use_cases/save_alert_settings.py`（`SaveAlertSettings`） | **削除** |
| `infrastructure/persistence/settings_repository.save_warning_month_settings` | **削除** |
| `domain/repositories/ports.py` の対応ポート | **削除** |
| `templates/inventory_order_alert/settings.html` の「出荷ありの月数／出荷なしの月数」入力 | **削除** |
| `templates/inventory_order_alert/settings.html` の「重点アラート」チェックボックス（`criticalEnabled`） | **削除**。重点は流動区分に置き換わり、有効・無効の概念がなくなる |
| `AlertSettingsInput` / `parse_alert_settings_payload` / `clamp_warning_months` / `MIN|MAX_WARNING_MONTHS` | **削除** |
| `SettingsInput.critical_enabled` / `parse_settings_payload` の `criticalEnabled` 分岐 / `settings_payload` の3キー | **削除** |
| 一覧の「警告条件」ダイアログ | **置換**（§6.6） |

`application/shipment_trend/` にも同名の `api_save_alert_settings` があるが、**別コンテキストの別 API** であり
本変更の対象外である（誤って削除しないこと）。

### 6.6 画面設計

#### 6.6.1 判定条件セレクタ（REQ-LFV-F-002 / F-003 / F-004）

一覧のフィルタパネル上部に、常時見える位置で配置する。

```
┌ 判定条件 ─────────────────────────────────────────┐
│ 判定軸  [低流動判定軸 ▾]   判定期間  [3か月 ▾]   [判定ルール]  │
└──────────────────────────────────────────────┘
```

- 判定軸 `<select name="axis">`: 低流動判定軸 / 死蔵判定軸
- 判定期間 `<select name="period">`: 軸に応じて選択肢を差し替える（低流動 1か月/3か月/6か月、死蔵 1年/2年/5年）
- 一覧テーブルの上（件数サマリの近く）にも `低流動判定軸・3か月で判定` のテキストを表示し、
  **現在の軸と期間が常に判別可能**にする（REQ-LFV-F-004）。象限番号は表示しない。
- 切り替えは即時（サーバ往復なし）。ページは1に戻す。

#### 6.6.2 一覧列

| 変更 | 列 |
|------|----|
| 置換 | 「アラート」列 → **「流動区分」列**（`flow_quadrant`）。ソート可能列の先頭のまま |
| 追加 | 「入荷実績なし」の副次表示（REQ-LFV-F-006）。独立列を増やさず、**流動区分セル内のバッジ**（`入荷なし`）として表示する。列数増加によるテーブル横幅の悪化を避けるため |
| 追加 | **「責任部署」列**（`responsible_department`）。見出しに「暫定」の注記を `title` 属性で付ける（REQ-LFV-F-007） |

`SORTABLE_COLUMNS` の先頭 `("alert_level", "アラート")` を `("flow_quadrant", "流動区分")` に置換し、
`("responsible_department", "責任部署")` を `stock_qty` の後に追加する。
`DEFAULT_SORT = "flow_quadrant"` / `DEFAULT_DIRECTION = "asc"`。
責任部署は流動区分からの導出値であるため、その並びは流動区分ランク順とする（独自ランクを設けない）。

#### 6.6.3 件数サマリ（REQ-LFV-F-008）

```
供給リスク品 N 件 / 在庫死蔵品 N 件 / 在庫過剰リスク品 N 件 / 通常流動品 N 件
確認済み N 件 / 確認中 N 件 / 未確認 N 件
```

左右の合計が一致する既存の性質を維持する（流動区分4値は排他かつ網羅であるため、
`供給リスク品 + 在庫死蔵品 + 在庫過剰リスク品 + 通常流動品 = total` が常に成り立つ）。

#### 6.6.4 流動区分による絞り込み（REQ-LFV-F-009）

フィルタパネルに `<select name="flow_quadrant">`（全て／供給リスク品／在庫死蔵品／在庫過剰リスク品／通常流動品）を追加する。
クライアント側でのローカル処理とし、選択変更時はページ1に戻す。

旧 `ListQuery.alert_only`（`alertOnly` クエリ、JSON API `/api/inventory-order-alert/summary` 専用）は
**`flow_quadrant` に置換**する。`alertOnly=true` 相当（＝通常流動品を除く）は
`flowQuadrant` を空にしたうえで新パラメータ `attentionOnly=true` で表現する。

#### 6.6.5 判定ルールダイアログ（REQ-LFV-F-015 の置換先）

「警告条件」ボタンを「**判定ルール**」ボタンに変え、ダイアログの中身を流動区分の凡例表に置き換える。
月数セレクトと保存ボタンは撤去し、**読み取り専用**にする。

| 期間内入荷 | 期間内出荷 | 流動区分（色見本付き） | 責任部署 |
|---|---|---|---|
| なし | あり | 供給リスク品 | 調達G・営業G・生産管理 |
| なし | なし | 在庫死蔵品 | 調達G |
| あり | なし | 在庫過剰リスク品 | 営業G |
| あり | あり | 通常流動品 | 生産管理 |

ダイアログ冒頭に現在の判定条件（`低流動判定軸・3か月`）と、
「期間内入荷／期間内出荷は、BOM 基準日から遡った判定期間内に最終入荷日／最終出荷日があることを指します」の説明を置く。

`domain/value_objects/alert_rules.py` を `flow_quadrant_rules.py` に置き換える
（`AlertRuleRow` → `FlowQuadrantRuleRow`、`build_alert_rule_rows()` → `build_flow_quadrant_rule_rows()`）。
月数を引数に取らなくなるため、`ListPageContext` の `warning_shipment_months` /
`warning_incoming_months` / `warning_month_options` は撤去する。

#### 6.6.6 呼称の使い分け（REQ-LFV-F-018）

画面に表示するラベルは、**判定軸によらず流動区分（S-203）の4ラベルで固定**する。
判定軸ごとにラベルを変えると、CSV・確認記録・件数サマリの値が軸によって揺れ、突合できなくなるため。

一方、説明文・ダイアログ・機能仕様書などの**散文では**、低流動判定軸で見たときの結果を
総称して「低流動品（入出荷なし）」と表現する（T-205）。死蔵判定軸の場合は「在庫死蔵品」（T-206）を用いる。
「未流動品」「デッドストック」「不良在庫」は使用しない（ubiquitous_language.md の使用しない表現）。

具体的には、判定条件セレクタの補助テキストを次のようにする。

| 判定軸 | 補助テキスト |
|--------|------------|
| 低流動判定軸 | 「判定期間内に入出荷のない品目（低流動品）を洗い出します」 |
| 死蔵判定軸 | 「長期にわたり動きのない品目（在庫死蔵品）を洗い出します」 |

#### 6.6.7 行の強調（REQ-LFV-F-005）

CSS クラスは **ASCII キー**を用いる（`.alert-row--supply-risk` 等）。既存の日本語クラス
（`.alert-row--重点` 等）は撤去する。確認状態のクラス（`.alert-row--確認済` / `.alert-row--確認中`）は
流動区分と独立した概念であり、**現状のまま変更しない**。

| 流動区分 | クラス | 背景 | hover | 由来 |
|---|---|---|---|---|
| 供給リスク品 | `.alert-row--supply-risk` | `#fde8e8` | `#fecaca` | 旧「重点」の配色 |
| 在庫死蔵品 | `.alert-row--dormant-stock` | `#ffedd5` | `#fed7aa` | 旧「警告（出荷あり）」の配色 |
| 在庫過剰リスク品 | `.alert-row--excess-stock-risk` | `#fff8e1` | `#fde68a` | 旧「警告（出荷なし）」の配色 |
| 通常流動品 | `.alert-row--normal-flow` | `#fff` | `#f1f5f9` | 旧「アラート無し」の配色 |

既存パレットをそのまま流用する（新しい色を導入しない）。緊急度の順序と色の濃さの順序が一致する。

`static/css/app.css` の該当宣言は `application/shipment_trend/` の `.st-row-*` セレクタと
**同一ブロックを共有している**。日本語セレクタを ASCII セレクタに**置換**するだけとし、
`.st-row-decrease-strong` 等の他コンテキストのセレクタと宣言ブロックの構造には手を入れない。

## 7. 既存コードへの変更点

### 7.1 新規ファイル

| ファイル | 内容 |
|---------|------|
| `domain/value_objects/flow_quadrant.py` | 判定軸・判定期間・流動区分・責任部署・判定関数（§4.2 / §4.4） |
| `domain/value_objects/flow_quadrant_rules.py` | 判定ルールダイアログの凡例行（§6.6.5） |
| `migrations/0011_rename_confirmed_alert_level.py` | `RenameField` 1件（§5.2） |

### 7.2 変更ファイル

| ファイル | 変更概要 |
|---------|---------|
| `domain/value_objects/list_query.py` | `ListQuery` から `alert_only` / `warning_shipment_months` / `warning_incoming_months` / `critical_enabled` を削除し、`flow_selection: FlowSelection` / `flow_quadrant: str` / `attention_only: bool` を追加。`parse_list_query` / `merge_query_with_settings` を追随 |
| `domain/value_objects/list_rows.py` | `apply_alert_levels_to_rows` → `apply_flow_quadrants_to_rows`（行に `flow_quadrant` / `flow_quadrant_key` / `flow_quadrants`(6通り) / `no_incoming_record` / `responsible_department` を付与）。`filter_summary_rows` / `sort_summary_rows` を流動区分基準へ |
| `domain/value_objects/row_counts.py` | `RowCounts` を `supply_risk` / `dormant_stock` / `excess_stock_risk` / `normal_flow` / `attention`(前3者の和) に置換。確認状態の3件数は維持 |
| `domain/value_objects/row_display.py` | `display_alert_level` → `display_flow_quadrant`、`row_alert_class` → 流動区分キーを返す（確認済／確認中の優先は維持） |
| `domain/value_objects/table_display.py` | `SORTABLE_COLUMNS` の置換・追加、`DEFAULT_SORT`、`_sort_value()` の分岐を `flow_quadrant_sort_rank` へ |
| `domain/value_objects/list_filter.py` | `build_display_query_string` に `axis` / `period` / `flow_quadrant` を追加 |
| `domain/value_objects/export_csv.py` | `EXPORT_COLUMNS` の置換・追加（§6.3） |
| `domain/value_objects/list_client_data.py` | ペイロードに §6.2 の項目を追加 |
| `domain/value_objects/app_settings.py` | §6.5 の削除一覧を反映。`AppSettings` に残るのは `warning_days` / `stock_stale_days` と監査項目のみ |
| `domain/value_objects/confirmation.py` | `ConfirmationRecord.confirmed_alert_level` → `confirmed_flow_quadrant` |
| `domain/repositories/ports.py` | 警告条件保存ポートを削除 |
| `use_cases/list_page.py` | `ListPageContext` の警告条件3項目を削除、`alert_rule_rows` → `flow_quadrant_rule_rows`、`flow_selection` / `flow_axis_options` / `flow_period_options` / `flow_quadrant_filter` を追加 |
| `use_cases/export_csv.py` | `execute(*, query_params)` に変更（§6.3） |
| `use_cases/portal_dashboard.py` | `DashboardBannerContext` を流動区分ベースへ（§6.4） |
| `use_cases/summary_api.py` | `merge_query_with_settings` の警告条件上書きを削除、`_counts_payload` / `dashboard_summary_payload` を流動区分ベースへ |
| `use_cases/save_confirmation.py` | `lookup_alert_level_for_row` → `lookup_flow_quadrant_for_row`（`REFERENCE_FLOW_SELECTION` 基準）、レスポンスの `counts` を流動区分ベースへ |
| `use_cases/patch_snapshot_row.py` | `_apply_alert_levels` → `_apply_flow_quadrants`（`REFERENCE_FLOW_SELECTION`） |
| `infrastructure/persistence/summary_repository.py` | `apply_alert_levels_to_rows` の呼び出しを差し替え。`load_app_settings()` への依存は不要になるため削除 |
| `infrastructure/persistence/confirmation_repository.py` | フィールド名の追随、`normalize_flow_quadrant` / `is_flow_escalated` への差し替え |
| `infrastructure/persistence/settings_repository.py` | `save_warning_month_settings` を削除、`load_app_settings` から該当項目を削除 |
| `infrastructure/oracle/summary_aggregation.py` | `ListQuery` の生成を流動区分ベースへ（`REFERENCE_FLOW_SELECTION`） |
| `infrastructure/persistence/summary_snapshot_repository.py` | `critical_count` / `warning_count` への詰め替えを §5.1 の規則へ |
| `templatetags/inventory_order_alert_format.py` | `ioa_display` / `ioa_row_alert_class` を流動区分へ |
| `interfaces/views.py` | `api_save_alert_settings` 削除、`list_page` / `settings_page` / `export_csv` のコンテキスト追随 |
| `interfaces/urls.py` | `alert-settings` パスを削除 |
| `interfaces/wiring.py` | `save_alert_settings_usecase` を削除 |
| `models.py` | `confirmed_alert_level` → `confirmed_flow_quadrant`、残置カラムへのコメント付与（§5.3） |
| `templates/inventory_order_alert/list.html` | 判定条件セレクタ・件数サマリ・列・判定ルールダイアログ（§6.6） |
| `templates/inventory_order_alert/settings.html` | 月数入力と保存処理を削除 |
| `templates/portal/dashboard.html` | アラート帯の文言（§6.4） |
| `static/js/inventory-order-alert-list-client.js` | 判定条件セレクタの制御、`flowQuadrants` からの引き直し、`ALERT_RANK` → 流動区分ランク、`countRows` / `renderCounts` / `updateUrl` の追随 |
| `static/js/inventory-order-alert-list.js` | 警告条件ダイアログの保存処理を削除（開閉のみ残す）、行クラス更新の追随 |
| `static/css/app.css` | 日本語セレクタを ASCII セレクタへ置換（§6.6.7）、判定条件セレクタのスタイル |
| `scripts/verify_post_receipt_shipment_count.py` | `ListQuery(alert_only=...)` の追随（`--alert-only` オプションを `--attention-only` に改める） |

### 7.3 削除ファイル

| ファイル | 理由 |
|---------|------|
| `domain/value_objects/alert_level.py` | アラートレベル（S-202）は流動区分（S-203）に置き換わる |
| `domain/value_objects/alert_rules.py` | `flow_quadrant_rules.py` に置き換わる |
| `use_cases/save_alert_settings.py` | 警告条件の設定を廃止（§6.5） |
| `tests/test_alert_level.py` | `tests/test_flow_quadrant.py` に置き換わる |

あわせて `domain/value_objects/row_display.py` の `counts_toward_alert_summary()` を削除する。
定義されているがテスト以外から呼ばれておらず（件数集計は確認済み行も含めて数えている）、
旧アラート概念に紐づいた名前が残ると誤用を招くため。

`static/js/*.js` を変更したら `staticfiles/` 側は `collectstatic` で再生成する（手編集しない）。
`scripts/verify_post_receipt_shipment_count.py` は `ListQuery(alert_only=...)` を使っているため、
引数名の追随が必要（`--alert-only` オプションを `--attention-only` に改める）。

### 7.4 CSS クラス名を ASCII に変える理由

既存の `.alert-row--重点` のような日本語クラス名は、(1) JavaScript のクラス操作
（`classList.remove` の前方一致判定）で URL エンコードやフォント差の影響を受けやすく、
(2) `app.css` 内で `application/shipment_trend/` のセレクタと同一ブロックを共有しているため
grep での影響範囲特定が難しい。流動区分は4値すべてが新設であり、この機会に ASCII キーへ揃える。
確認状態のクラス（`確認済` / `確認中`）は本要件の対象外のため据え置き、混在は許容する。

### 7.5 機能仕様書の改訂

要件定義書 §6.3 のとおり、`application/inventory_order_alert/docs/在庫発注アラート_機能仕様書.md` の
§2.3（REQ-F-004 / 011 / 012 / 013 / 014）・§4.1.3〜4.1.5・§5・§6・§8 を改訂する。
これは実装タスクの一部として tasks.md に含める。

## 8. エラーハンドリング方針

| 状況（REQ-LFV-F-017 対応） | 挙動 |
|---|---|
| 最終入荷日・最終出荷日がともに空 | 在庫死蔵品（供給リスク品ではない）。例外にしない |
| 最終入荷日が空・出荷あり | 供給リスク品。あわせて「入荷実績なし」バッジを表示 |
| 日付が基準日より未来 | 期間内として扱う（§4.4 の境界表） |
| 日付文字列が解析不能 | `parse_optional_ymd` が `ValueError` を送出するため、`apply_flow_quadrants_to_rows` 内で捕捉し `None`（＝期間外）として扱う。行を落とさない |
| SLIMS 在庫が未取込 | 既存どおり一覧を表示しない（`has_list_data = False`）。流動区分は在庫数を判定に用いないが、行の生成自体が在庫取込に紐づくため既存挙動を維持 |
| `axis` / `period` が不正 | 既定値へフォールバック。ログなし（§6.1） |
| `axis` に対応しない `period`（例: `axis=dormant&period=3`） | 当該軸の既定値（死蔵なら1年）へフォールバック |
| `flow_quadrant` が未知のキー | 空（全件）へフォールバック |
| 確認記録に未知の `confirmed_flow_quadrant` | `normalize_flow_quadrant` で通常流動品へ正規化（§5.2）。例外にしない |
| 集計エラー（`aggregation_error`）あり | 既存どおりエラーメッセージを表示し、件数は 0 とする |
| 0 件 | 空一覧を表示し、件数サマリはすべて 0。エラーにしない |

原則: **判定は例外を投げない**。入力の欠損・不正はすべて安全側（判定不能＝期間外、未知ラベル＝最も低いランク）に倒す。
一覧の描画が止まることを最も避けるべき事態とみなす。

## 9. リスクと対策

| # | リスク | 影響 | 対策 |
|---|-------|------|------|
| R-1 | 旧アラートレベルの撤去範囲が広い（34ファイル・約201箇所） | 未修正の参照が残り実行時エラー | `alert_level.py` を**削除**することで、未修正の import が即座に `ImportError` になる。段階的な非推奨化はせず一括で切り替える。`grep -rn "alert_level\|alertLevel\|alert_only\|alertOnly"` の残存 0 件をタスク完了条件にする |
| R-2 | 確認記録の旧ラベルが正規化で「通常流動品」に倒れ、深刻化の差し戻しが起きにくくなる | 本来差し戻すべき記録が確認済みのまま残る | 安全側の設計として意図的に受け入れる（誤差し戻しによる現場の手戻りのほうが害が大きい）。移行後に1度でも取込が走れば、新しい流動区分が保存されて解消する。運用手順書に「導入直後の1回目の取込までは深刻化の差し戻しが控えめになる」と明記する |
| R-3 | 6通りの事前計算でクライアントペイロードが増える | 一覧の初期表示が遅くなる | 増加は1行あたり約90バイト。既存の `display`(14列) に比べ十分小さい。NF-001 の性能要件に対して実測で確認する（テスト設計書に計測項目を置く） |
| R-4 | メニュー帯（低流動判定軸・3か月固定）と一覧（利用者が選択）で件数が食い違う | 利用者が数字の不一致に混乱する | 帯の文言に判定条件を明記する（§6.4）。一覧側も常に判定条件を表示する（§6.6.1） |
| R-5 | `app.css` の宣言ブロックが `shipment_trend` と共有されている | セレクタ置換で他コンテキストの配色を壊す | 宣言ブロックの構造には触れず、`.alert-row--{日本語}` セレクタのみを ASCII セレクタに置換する。`shipment_trend` の一覧の目視確認を実装タスクの完了条件に含める |
| R-6 | `RenameField` マイグレーションのロールバック | 切り戻し時にカラム名が戻らない | Django の `RenameField` は逆方向マイグレーションを自動生成する。データは失われない |
| R-7 | 責任部署（R-201）が「暫定」のまま画面に出る | 利用者が確定情報と誤認する | 見出しに注記を付ける（§6.6.2）。契約情報・他入先情報が確定するまで割り当ての変更はしない旨を機能仕様書に記載する |
| R-8 | `shipment_trend` にも `api_save_alert_settings` がある | 誤って別コンテキストの API を削除する | §6.5 に明記。削除対象は `application/inventory_order_alert/` 配下のみ |

---

## 10. 要件トレーサビリティ

要件定義書（REQ-LOW-FLOW-VISIBILITY-2026-001）の全要件と、本設計書の対応箇所。

| 要件ID | 要件 | 設計上の対応箇所 |
|--------|------|----------------|
| REQ-LFV-F-001 | 流動区分の判定 | §4.2.3 / §4.4 `resolve_flow_quadrant` |
| REQ-LFV-F-002 | 判定軸の切り替え | §3.2 / §6.1 / §6.6.1 |
| REQ-LFV-F-003 | 判定期間の選択 | §4.2.2 `EvaluationPeriods` / §6.1 / §6.6.1 |
| REQ-LFV-F-004 | 一覧の流動区分列 | §6.6.1（判定条件の常時表示） / §6.6.2 |
| REQ-LFV-F-005 | 行の強調 | §6.6.7（配色値を確定） |
| REQ-LFV-F-006 | 入荷実績なしの副次フラグ | §4.2.4 / §6.6.2（流動区分セル内のバッジ） |
| REQ-LFV-F-007 | 責任部署の表示 | §4.2.3（割り当て表） / §6.6.2（暫定注記） |
| REQ-LFV-F-008 | 件数サマリの流動区分化 | §6.6.3 / §7.2 `row_counts.py` |
| REQ-LFV-F-009 | 流動区分による絞り込み | §6.6.4（`alertOnly` → `flow_quadrant` + `attentionOnly`） |
| REQ-LFV-F-010 | 流動区分によるソート | §4.2.3（並び順ランク） / §6.6.2 / §7.2 `table_display.py` |
| REQ-LFV-F-011 | CSV 出力への反映 | §6.3（列構成と `execute(query_params=...)`） |
| REQ-LFV-F-012 | 選択状態の保持 | §6.1（URL クエリ同期） |
| REQ-LFV-F-013 | メニュー画面アラート帯 | §6.4（`REFERENCE_FLOW_SELECTION` = 低流動判定軸・3か月） |
| REQ-LFV-F-014 | 確認記録との整合 | §4.2.5 / §5.2（`RenameField` + 互換写像） |
| REQ-LFV-F-015 | 警告条件の扱い | §5.3（カラム残置） / §6.5（API 撤去） / §6.6.5（ダイアログ置換） |
| REQ-LFV-F-016 | 表示時再判定 | §3.1（スナップショットのスキーマ変更なし） |
| REQ-LFV-F-017 | 異常系8件 | §4.4（境界表） / §8 |
| REQ-LFV-F-018 | 呼称の使い分け | §6.6.6 |
| REQ-LFV-NF-001 | 性能 | §3.2（案B の配信サイズ） / §9 R-3 |
| REQ-LFV-NF-002 | 既存データ互換性 | §3.1 / §5.1 / §5.2（再取込を必須としない） |
| REQ-LFV-NF-003 | 認可 | §3.3（新権限区分を設けない） |
| REQ-LFV-NF-004 | 用語の一貫性 | §4.2（ユビキタス言語の ID を全 VO に対応付け） / §6.6.6 |
| REQ-LFV-NF-005 | アーキテクチャ制約 | §3 / §3.3（`test_clean_architecture.py` による検証） |
| REQ-LFV-NF-006 | 品質・テスト | §3.3（TDD・境界値は test-design.md へ） |
| REQ-LFV-NF-007 | 運用 | §3.3（新バッチなし） / §5.2（移行バッチなし） / §6.1（フォールバックのログなし） |

---

## レビュー履歴

# 機能設計書: 詳細ダイアログへの出荷推移グラフの追加

文書ID: DESIGN-SHIPMENT-HISTORY-CHART-2026-001
作成日: 2026/09/01
更新日: 2026/09/03（入出荷推移の独立グラフ表示を撤去。§6.4・§6.5・§7.2・§9 R-6 を更新。DECISIONS.md参照）
対応文書: [requirements.md](./requirements.md)（REQ-SHIPMENT-HISTORY-CHART-2026-001）
アーキテクチャreference: django-clean-architecture version 1.0（`make-design`/`design-review-l1`/`implement-review-l1` と一致確認済み。03_mari-stock-visibility/design.md で確認済みのため本書では再掲のみ）

---

## 1. 設計の目的

要件定義書（REQ-SHC-F-001〜004）を受け、詳細ダイアログに **月次出荷数量の推移グラフ** を追加する。
在庫数そのものの時系列データが存在しないため、判定根拠（期間内出荷の有無）を可視化する代替手段として、既存の出荷実績取得結果を月次に束ね直す。**新たな Oracle クエリは追加しない。**

## 2. 対象コンテキスト

`strategic_design.md` における境界コンテキスト **B: 在庫発注アラート**（生産管理・コアサブドメイン）。

### 2.1 境界の遵守

- 出荷トレンド（コンテキスト外、`shipment_trend` アプリ）のクエリ関数・コードは**一切 import しない**（REQ-SHC-NF-005）。同じ `T_SHIP` を参照するが、集計キー（内作品番 vs 得意先品番）が異なり、そもそも流用できない。
- 共有カーネル（`application/sales/infrastructure/oracle/`。接続基盤・例外のみ）以外のコンテキスト間参照は行わない。

## 3. アーキテクチャ概要

```
[SLIMS 取込トリガー]
  → infrastructure/oracle/summary_aggregation.py: run_summary_aggregation()
    → infrastructure/oracle/summary_queries.py: build_summary_rows()
      → fetch_all_shipments()  … 既存。変更しない
      → 出荷を (cust_code, cust_item_cd) でグループ化 … 本機能で新設（infrastructure）
      → domain/value_objects/shipment_trend.py: build_monthly_shipment_trend()  … 本機能で新設（domain, 純粋関数）
      → row["shipment_trend"] へ格納
    → PostgreSQL へスナップショット保存（既存の JSONField。マイグレーション不要）

[詳細ダイアログを開く]
  → static/js/inventory-order-alert-list-client.js: getShipmentTrend(custCode, itemCd)  … 本機能で新設
  → static/js/inventory-order-alert-list.js: fillDetailSections() が SVG を描画  … 本機能で新設
  （Oracle・API 呼び出しなし。ページ初期表示時に埋め込み済みの JSON から読む）
```

### 3.1 なぜ新規 Oracle クエリが不要か（REQ-SHC-F-001）

`build_summary_rows()` は既に `fetch_all_shipments(connection)` で `T_SHIP` の全出荷明細（`cust_code`, `cust_item_cd`, `ship_date`, `ship_qty`）を取得済みで、`aggregate_shipment_stats()` が出荷回数（T-201）の算出に使っている。
本機能はこの **同じ `all_shipments` リストを月次に束ね直すだけ**であり、Oracle への追加問い合わせを一切発生させない。

### 3.2 パフォーマンス上の改善点（副次効果）

既存の `aggregate_shipment_stats()` は行ごとに `all_shipments`（全件）を線形スキャンする（O(行数 × 出荷明細数)）。
本機能では `all_shipments` を **1 回だけ `(cust_code, cust_item_cd)` でグループ化**してから各行の月次集計を引くため、月次集計自体は O(出荷明細数) で済む。
既存の `aggregate_shipment_stats()` 自体は変更しない（本要件のスコープ外。挙動を変えるリスクを避ける）。

### 3.3 入荷推移（V-217）はなぜ新規 Oracle クエリが必要か（REQ-SHC-F-005 / NF-008）

出荷とは対照的に、`build_summary_rows()` が既に取得しているのは `fetch_last_incoming_by_item_vend()` の結果（`(ITEM_CD, VEND_CD)` ごとの `MAX(ACPT_DATE)` のみ）であり、**個々の検収明細（日付・数量）は取得していない**。月次集計には個々の明細が必要なため、`T_PAST_INSPC_ACPT` への新規クエリが 1 本必要になる。

既存クエリ（`fetch_last_incoming_by_item_vend`）は絞り込みなしで全件を `GROUP BY` している。個々の明細を全件取得すると行数が大きく増えるおそれがあるため、本機能の新規クエリは **`ACPT_DATE >= window_start`**（直近24か月の開始日）で絞り込む。これは既存クエリより保守的（範囲を限定する分、負荷は小さい方向）。

## 4. ドメインモデル

### 4.1 バリューオブジェクト

#### `ShipmentTrendPoint`（概念上の型。実装は `dict[str, object]`）

| フィールド | 型 | 説明 |
|---|---|---|
| `month` | `str` | `"YYYY-MM"` 形式 |
| `qty` | `int` | 当該月の出荷数量合計。出荷実績がなければ `0` |

既存の行データが `dict[str, object]` 中心の設計（[ISSUE-0001](../../issues/ISSUE-0001-dict-centric-domain-model.md) で指摘済み・是正は別途検討中）に合わせ、本機能も dataclass 化はせず素の `dict` のリストとして扱う。既存パターンとの一貫性を優先する。

### 4.2 ドメイン関数

`domain/value_objects/shipment_trend.py`（新規）

```python
def build_monthly_shipment_trend(
    shipments: list[tuple[date, int]],
    *,
    as_of_date: date,
    months: int = 24,
) -> list[dict[str, object]]:
    """出荷明細（日付・数量）を、as_of_date の月を含む直近 months か月ぶんの月次集計にする。

    出荷実績がない月も 0 として含め、常に固定長 months 件を返す（古い順）。
    """
```

- 入力の `shipments` は特定の `(cust_code, cust_item_cd)` に**絞り込み済み**のリスト（呼び出し側で絞り込む。本関数はキーを知らない）。
- 月境界の算出は既存の `domain/value_objects/dates.py:add_calendar_months()` を再利用する。
- Django 非依存の純粋関数（`import django` なし）。単体テストが容易。

### 4.3 入荷推移（V-217）は同じ関数を再利用する

`build_monthly_shipment_trend()` は「日付・数量のリストを月次に束ねる」という**キーに依存しない汎用ロジック**であり、出荷固有の処理を一切含まない。入荷推移（V-217）の集計にも**同じ関数をそのまま再利用**する（`(level1_item_cd, level1_vend_cd)` に絞り込んだ入荷明細を渡すだけ）。

新しい関数・ファイルは作らない。関数名に `shipment` が残るが、リネームによる既存テストへの影響（ISSUE-0001 のような不要な手戻り）を避けるため、**docstring に汎用利用の注記を追加するにとどめる**（DECISIONS.md に命名の妥協点として記録）。

## 5. データモデル

### 5.1 変更しないもの

- `InventoryOrderAlertSummarySnapshot` モデル定義（`rows` は既存の `JSONField`）。**マイグレーション不要**。
- `fetch_all_shipments()` の SQL・戻り値の形。
- `aggregate_shipment_stats()` のロジック・戻り値。

### 5.2 集計スナップショットの行に追加するキー

| キー | 型 | 説明 |
|---|---|---|
| `shipment_trend` | `list[dict]` | `build_monthly_shipment_trend()` の戻り値をそのまま格納。固定長 24 件 |
| `incoming_trend` | `list[dict]` | 同上（入荷明細を集計した結果）。突合キーは `(level1_item_cd, level1_vend_cd)` |

`summary_row_codec.py` の `row_to_storable()` / `row_from_stored()` は**汎用的にキーをコピーする実装**（Decimal・date のみ特別扱い）のため、コード変更は不要。`qty` は `int` で格納するため Decimal 変換も発生しない。

### 5.3 既存スナップショットとの互換（REQ-SHC-F-004）

`shipment_trend` キーを持たない既存スナップショットを読み込んだ場合、行の `.get("shipment_trend")` は `None` になる。detail 側は「実績なし相当」の表示にする（未取得と該当なしを区別しない。DECISIONS.md の判断）。

## 6. API / インターフェース設計

### 6.1 集計処理（`infrastructure/oracle/summary_queries.py`）

```python
def group_shipments_by_pair(
    shipments: list[tuple[str, str, date, int]],
) -> dict[tuple[str, str], list[tuple[date, int]]]:
    """all_shipments を (cust_code, cust_item_cd) でグループ化する。"""
```

`build_summary_rows()` 内で 1 回だけ呼び、行ごとのループでは辞書引きのみ行う。

```python
shipments_by_pair = group_shipments_by_pair(all_shipments)
...
for cust_code, cust_item_cd, cust_chrg_psn_cd, internal_from_ship in ship_pairs:
    ...
    shipment_trend = build_monthly_shipment_trend(
        [(d, q) for d, q in shipments_by_pair.get((cust_code, cust_item_cd), [])],
        as_of_date=as_of_date,
    )
    rows.append({..., "shipment_trend": shipment_trend})
```

#### 入荷推移（V-217、REQ-SHC-F-005）

```python
def fetch_incoming_receipts(
    connection: object,
    window_start: date,
) -> list[tuple[str, str, date, int]]:
    """(item_cd, vend_cd, acpt_date, qty) の個々の検収明細を、window_start 以降に絞って取得する。

    既存の fetch_last_incoming_by_item_vend()（MAX(ACPT_DATE) のみ）とは異なり、
    月次集計に必要な個々の明細・数量を返す。直近 24 か月に絞り込むことで
    T_PAST_INSPC_ACPT の全件取得を避ける(design.md §3.3)。
    """
```

```sql
SELECT TRIM(ITEM_CD) AS ITEM_CD,
       TRIM(VEND_CD) AS VEND_CD,
       ACPT_DATE,
       NVL(INSPC_ACPT_QTY, 0) AS QTY
  FROM T_PAST_INSPC_ACPT
 WHERE ACPT_DATE >= :window_start
```

`INSPC_ACPT_QTY`（検収数量。検収を経て正式に受け入れられた数量）を用いる。`ACPT_QTY`（受入数量。検収前）は使わない（V-217 補足参照）。

`build_summary_rows()` 内で、`window_start` を `as_of_date` から算出し 1 回だけ呼ぶ。グループ化は `group_shipments_by_pair()` を**そのまま再利用**する（引数の意味が `(cust_code, cust_item_cd)` から `(item_cd, vend_cd)` に変わるだけで、関数のロジックは同一）。

```python
window_start = add_calendar_months(date(as_of_date.year, as_of_date.month, 1), -23)
incoming_receipts = fetch_incoming_receipts(connection, window_start)
incoming_by_pair = group_shipments_by_pair(incoming_receipts)  # 汎用関数を再利用
...
for cust_code, cust_item_cd, cust_chrg_psn_cd, internal_from_ship in ship_pairs:
    ...
    incoming_trend = build_monthly_shipment_trend(
        [(d, q) for d, q in incoming_by_pair.get((level1_item, level1_vend), [])],
        as_of_date=as_of_date,
    )
    rows.append({..., "incoming_trend": incoming_trend})
```

### 6.2 クライアント配信ペイロード（REQ-SHC-NF-001）

`list_client_data.py:row_to_client_dict()` は行の全キーを `_json_value()` 経由でそのまま `client_row` へコピーする実装のため、**コード変更なしで** `row["shipment_trend"]` が `client_row["shipment_trend"]`（snake_case のまま）として配信される。
camelCase の別名は追加しない（03_mari-stock-visibility での「同じ値の二重配信をしない」方針を踏襲）。

配信データ量: 1 行あたり `shipment_trend` は 24 件 × 約 20 バイト（`{"month":"2025-09","qty":120},`）で当初 **約 500 バイト**と見積もっていた。

> **実測値（2026/09/01、タスク17）**: **+794 バイト/行**（`test_shipment_trend_edge_cases.py::test_TC_SHC_E_001_payload_increase_per_row_is_measured`）。
> 見積りと実測が乖離した（[ISSUE-0005](../../issues/ISSUE-0005-no-payload-size-requirement.md) と同種の見積り誤り）。原因はキー名 `"month"` `"qty"` と JSON の区切り文字を過小評価していたため。
> 既存の 1 行あたりデータ量（実測約 4,000 バイト、03_mari-stock-visibility 実測値）に対し **約 2 割の増分**であり、致命的な水準ではないと判断するが、**DECISIONS.md の R-3（対象期間を60か月へ拡張するか）の判断に直接影響する**（60か月にすると単純比例で約2,000バイト/行になる見込み）。

> **実測値（2026/09/03、タスク31、入荷推移(V-217)追加後）**: `incoming_trend` は `shipment_trend` と同じ構造（24件 × `{"month","qty"}`）のため、**単独増分は +793 バイト/行**（出荷推移とほぼ同一）。**出荷推移+入荷推移を合わせた合計増分は +1,587 バイト/行**（`test_TC_SHC_E_001_payload_increase_per_row_with_both_trends_is_measured`）。
> 既存の 1 行あたりデータ量（約 4,000 バイト）に対し **約 4 割の増分**となる。60か月への拡張（DECISIONS.md R-3）を採用する場合はこの合計増分がさらに約2.5倍（約4,000バイト/行）になる見込みで、影響がより大きくなる点に注意。

### 6.3 詳細ダイアログのデータ供給経路（既存パターンの踏襲）

03_mari-stock-visibility の design.md §6.3.1 で確立した経路（一覧行の `data-*` 属性 + `listClient` のゲッター）を踏襲する。ただし `shipment_trend` は 24 件の配列であり `data-*` 属性文字列には適さないため、**`listClient` のゲッター経由でのみ**渡す（`data-*` 属性は追加しない）。

```js
// static/js/inventory-order-alert-list-client.js
getShipmentTrend(custCode, itemCd) {
  const row = findRow(custCode, itemCd);   // 既存のヘルパーを再利用
  return Array.isArray(row?.shipment_trend) ? row.shipment_trend : [];
},
getIncomingTrend(custCode, itemCd) {
  const row = findRow(custCode, itemCd);
  return Array.isArray(row?.incoming_trend) ? row.incoming_trend : [];
},
```

```js
// static/js/inventory-order-alert-list.js の fillDetailSections(row) 内
// 出荷推移・入荷推移は独立したグラフとしては表示しない（§6.4）。
// 推定在庫推移（§6.6）の算出のみに用いる。
const shipmentTrend = listClient?.getShipmentTrend?.(custCode, row.dataset.itemCd || "") || [];
const incomingTrend = listClient?.getIncomingTrend?.(custCode, row.dataset.itemCd || "") || [];
```

### 6.4 ［撤去済み］入出荷推移の独立グラフ表示（REQ-SHC-F-002 / F-005）

> **2026/09/03、ユーザー指示「左に台数と入出荷のグラフはいらない」により、本節が定義していた独立グラフ表示を撤去した。** 出荷推移（V-216）・入荷推移（V-217）の**算出処理・データ自体は引き続き行う**（§6.6 推定在庫推移の入力として必要なため）。撤去したのは、それらを**専用の折れ線グラフとして詳細ダイアログに表示する処理**（`renderShipmentTrendChart()` 関数と `.ioa-detail-shipment-trend-*` の DOM）のみ。判断の経緯は DECISIONS.md 参照。
>
> REQ-SHC-F-002（グラフ表示）・REQ-SHC-F-003（実績なし表示）・REQ-SHC-F-005 の「表示」に関する部分は、本節の撤去に伴い**適用しない**。データ算出に関する部分（REQ-SHC-F-001・F-004・F-005 の算出部分）は有効のまま。

### 6.5 詳細ダイアログの構成

03_mari-stock-visibility で確立した 4 区分（品目 / 流動区分 / 在庫 / メモ）に、**「推定在庫推移（参考値）」区分を「在庫」と「メモ」の間に追加**し、5 区分にする（§6.6）。入出荷推移の独立した区分は追加しない（§6.4）。

```
┌ 詳細 ────────────────────────────────────┐
│ ■ 品目 / ■ 流動区分 / ■ 在庫  … 既存      │
│                                            │
│ ■ 推定在庫推移（参考値）                    │
│   ● SLIMS起点  ● MARI起点  （凡例）        │
│   [SVG 折れ線グラフ 24か月・2系列・ゼロ基準線]│
│   または「推定在庫推移を算出できません」     │
│                                            │
│ ■ メモ … 既存                              │
└────────────────────────────────────────────┘
```

### 6.6 推定在庫推移の算出とグラフ描画（REQ-SHC-F-006、V-218）

出荷推移・入荷推移・SLIMS/MARI在庫数はいずれも**既にクライアントへ配信済み**のため、推定在庫推移の算出には新規 Oracle 問い合わせも配信データの追加も不要である。算出は `static/js/inventory-order-alert-list.js` に純粋関数として実装し、`fillDetailSections()` から呼ぶ。

**算出関数**:

```js
function buildAnchoredStockTrend(shipmentTrend, incomingTrend, anchorQty) {
  if (anchorQty === null) {
    return [];
  }
  const length = shipmentTrend.length;
  const result = new Array(length);
  result[length - 1] = { month: shipmentTrend[length - 1].month, qty: anchorQty };
  for (let index = length - 2; index >= 0; index -= 1) {
    const nextShipped = Number(shipmentTrend[index + 1]?.qty) || 0;
    const nextReceived = Number(incomingTrend[index + 1]?.qty) || 0;
    result[index] = {
      month: shipmentTrend[index].month,
      qty: result[index + 1].qty + nextShipped - nextReceived,
    };
  }
  return result;
}
```

- 直近月（配列末尾）を `anchorQty`（起点在庫数）とし、過去に向かって「当月末推定 = 翌月末推定 + 翌月出荷 − 翌月入荷」を適用する（§1.5）。
- `anchorQty` の解析は `parseAnchorQty(text)`（新設）で行う。カンマを除去して `Number()` に変換し、空文字・NaN の場合は `null` を返す（未取得を区別する。「0」は有効な起点として扱う）。呼び出し元は `row.dataset.stockQty`（SLIMS）・`row.dataset.mariStockQty`（MARI）を渡す。
- `anchorQty` が `null`（=在庫数が未取得）の場合、その起点の系列は算出せず空配列を返す。**MARI 在庫数が未取得の行では MARI起点の系列を描画しない**（REQ-SHC-F-006）。
- 推定値は**クランプしない**。マイナスもそのまま返す（§1.5）。

**描画関数**: `renderAnchoredStockChart(sectionEl, slimsSeries, mariSeries)`（新設）。

- 縦軸のスケールは `[Math.min(0, ...両系列の全qty), Math.max(1, ...両系列の全qty)]`。**0 を必ず範囲に含める**ことで、ゼロ基準線を常に描画できるようにする（クランプはしないが、視覚的な危険水準を示す線として 0 を明示する）。
- ゼロ基準線は破線（`stroke-dasharray`）で描画する。
- SLIMS起点を**インディゴ系**、MARI起点を**緑系**の折れ線で描く。凡例を上部に表示する。
- 両系列とも空配列（SLIMS・MARI いずれの在庫数も未取得、または出荷推移・入荷推移そのものが存在しない既存スナップショット）の場合は、グラフを描画せず「推定在庫推移を算出できません」を表示する。
- `fillDetailSections()` 内で、出荷推移・入荷推移・在庫数（`row.dataset.stockQty` / `row.dataset.mariStockQty`）から算出して描画する。

```js
// static/js/inventory-order-alert-list.js の fillDetailSections(row) 内に追加
const slimsAnchor = parseAnchorQty(row.dataset.stockQty);
const mariAnchor = parseAnchorQty(row.dataset.mariStockQty);
const slimsAnchoredTrend = buildAnchoredStockTrend(shipmentTrend, incomingTrend, slimsAnchor);
const mariAnchoredTrend = buildAnchoredStockTrend(shipmentTrend, incomingTrend, mariAnchor);
renderAnchoredStockChart(anchoredStockTrendSection, slimsAnchoredTrend, mariAnchoredTrend);
```

## 7. 既存コードへの変更点

### 7.1 新規ファイル

| ファイル | 内容 |
|---------|------|
| `domain/value_objects/shipment_trend.py` | 月次出荷推移の集計ロジック（純粋関数） |
| `tests/test_shipment_trend_vo.py` | 上記の単体テスト |
| `tests/test_shipment_trend_query.py` | `group_shipments_by_pair()` の単体テスト |

### 7.2 変更ファイル

| ファイル | 変更概要 |
|---------|---------|
| `infrastructure/oracle/summary_queries.py` | `group_shipments_by_pair()`・`fetch_incoming_receipts()` を追加。`build_summary_rows()` の行に `shipment_trend`・`incoming_trend` を付与（引き続き算出。表示はしない） |
| `templates/inventory_order_alert/list.html` | 詳細ダイアログに「推定在庫推移（参考値）」区分・凡例を追加（「入出荷推移」区分は追加後に撤去した） |
| `static/js/inventory-order-alert-list-client.js` | `getShipmentTrend()`・`getIncomingTrend()` ゲッターを追加（推定在庫推移の算出に使用） |
| `static/js/inventory-order-alert-list.js` | `buildAnchoredStockTrend()`・`parseAnchorQty()`・`renderAnchoredStockChart()` を新設し `fillDetailSections()` から呼ぶ。`renderShipmentTrendChart()` は一度追加した後に撤去した |
| `static/css/app.css` | 推定在庫推移グラフ区分・ゼロ基準線のスタイルを追加。入出荷推移グラフ専用のスタイルは追加後に撤去した |
| `docs/在庫発注アラート_機能仕様書.md` | §4.1.6（詳細ダイアログ）を改訂 |

### 7.3 削除するもの

- `static/js/inventory-order-alert-list.js` の `renderShipmentTrendChart()` 関数（一度追加した後、ユーザー指示により撤去。DECISIONS.md参照）
- `templates/inventory_order_alert/list.html` の `ioa-detail-shipment-trend-section`（同上）
- `static/css/app.css` の `.ioa-shipment-trend-*` 系スタイル（同上）

## 8. エラーハンドリング方針

| 状況 | 挙動 |
|---|---|
| 対象期間内に出荷実績が 1 件もない | 全月 0 の配列を返す（`build_monthly_shipment_trend` は空配列を返さない）。表示側で「実績なし」に振り替える（REQ-SHC-F-003） |
| 既存スナップショット（`shipment_trend` キーなし） | `row.get("shipment_trend")` が `None`。表示側で「実績なし」相当（REQ-SHC-F-004） |
| 出荷推移の集計中に例外が発生した | **取込全体を失敗させる**（既存の `run_summary_aggregation` の例外捕捉に合流。03_mari-stock-visibility と同じ方針。独自の例外型を新設しない） |
| `ship_qty` が負値（返品等） | 加工せずそのまま月次合計に含める（基幹の値を加工しない。03_mari-stock-visibility の MARI 在庫の方針を踏襲） |
| 入荷推移の集計中に例外が発生した | 出荷推移と同じく取込全体を失敗させる |
| `level1_item_cd` / `level1_vend_cd` が解決できない行 | `incoming_trend` は全月 0（該当キーなしとして扱う） |
| 推定在庫推移の起点（SLIMS在庫数・MARI在庫数）が未取得 | 該当起点の系列を算出せず（`parseAnchorQty` が `null` を返す）、その系列を描画しない。両方未取得なら「算出できません」表示 |
| 推定在庫推移の算出値がマイナスになる | クランプせずそのまま表示する（§1.5・§6.6。仕様どおりの挙動でありエラーではない） |

## 9. リスクと対策

| # | リスク | 影響 | 対策 |
|---|-------|------|------|
| R-1 | 配信ペイロードの増加 | 一覧の初期表示が遅くなる | §6.2 のとおり実測する。要件定義書に明示的な上限値がないため、design レビューで上限（例: 600 バイト/行）を追加するかを判断する |
| R-2 | 「在庫変動」という元の依頼と実装内容（出荷推移）の乖離 | 利用者の期待とズレる可能性 | DECISIONS.md に明記し、翌営業日に確認を得る |
| R-3 | 対象期間 24 か月が死蔵判定軸（最大 5 年）の判定根拠を包含しない | 5 年判定の行でグラフが判定期間全体をカバーしない | DECISIONS.md に明記し、期間の妥当性を翌営業日に確認する |
| R-4 | `aggregate_shipment_stats()` と本機能の月次集計が二重に全出荷明細を扱う | コードの重複（ロジックは別だが元データは同じ） | 許容する。`aggregate_shipment_stats()` 自体の変更はスコープ外とし、リスクを増やさない |
| R-5 | 入荷推移のクエリ追加で Oracle 負荷が増える | 取込処理が遅くなる可能性 | `ACPT_DATE >= window_start`（直近24か月）で絞り込み、全件取得を避ける（§3.3） |
| R-6 | ～～ ［解消済み］`renderShipmentTrendChart` 等の識別子に "shipment" が残るが入荷も扱う ～～ | 命名と実態の不一致で将来のメンテナが混乱しうる | 2026/09/03、当該グラフ表示自体をユーザー指示により撤去したため本リスクは解消した（§6.4・§7.3）。撤去後の推定在庫推移側の識別子（`ioa-anchored-stock-trend-*`）は命名と実態が一致している |
| R-7 | 推定在庫推移は出荷・入荷以外の在庫変動（棚卸差異・生産消費・返品等）を反映しない近似値 | 実際の在庫推移と乖離し、利用者が誤って実測値と誤認する可能性 | 区分見出し・注記に「参考値」であることを明記する。判定（流動区分）には用いない（REQ-SHC-NF-004） |

---

## レビュー履歴

### 自己実施 Design-L1 相当レビュー (2026/09/01)

- **戦略的設計との整合性**: OK。コンテキストB内に閉じ、共有カーネル外への参照なし。
- **レイヤー配置**: OK。月次集計ロジックを domain（純粋関数）に、Oracle 取得結果のグループ化を infrastructure に配置。domain に `import django` なし。
- **依存方向**: OK。infrastructure → domain の一方向。
- **既存コードの保護**: OK。`fetch_all_shipments()` / `aggregate_shipment_stats()` は無変更。
- **懸念**: R-1（ペイロード上限が要件定義書に未定義）、R-3（24か月固定の妥当性）は自己判断のため DECISIONS.md で翌営業日確認を依頼する。

### 追記レビュー（入荷推移追加分） (2026/09/03)

- **コンテキスト境界**: OK。`T_PAST_INSPC_ACPT` は既存の `fetch_last_incoming_by_item_vend()` が既に参照しているテーブルであり、新規テーブル参照ではない。
- **性能**: OK。日付範囲で絞り込む設計とした（R-5）。実測はタスク実行時に行う。
- **命名の妥協（R-6）**: 許容。関数名・クラス名は据え置き、ユーザー向け表示のみ「入出荷推移」に改めた。

### 追記レビュー（推定在庫推移 V-218 追加分） (2026/09/03)

- **性能・配信量**: OK。既に配信済みのデータ（出荷推移・入荷推移・在庫数）のみから算出するため、新規 Oracle 問い合わせ・配信データ増加ともになし（R-1 と同水準を維持）。
- **判定への不使用**: OK。REQ-SHC-NF-004 に V-218 を追加し、判定に使わない付加情報である旨を明記した。
- **実測との誤認防止**: 「参考値」である旨をユーザー承認済みの上で仕様に明記（R-7）。ユーザー自身の判断（マイナス値をそのまま見せる）を反映した。

### 追記レビュー（入出荷推移の独立グラフ表示の撤去） (2026/09/03)

- **経緯**: 推定在庫推移（V-218）を追加した直後、ユーザーから「左に台数と入出荷のグラフはいらない」との指示を受けた。AskUserQuestionで「詳細ダイアログの『入出荷推移』区分（出荷=青・入荷=橙の2系列グラフ）を区分ごと削除する」認識を確認した上で実施した。
- **データ算出への影響**: なし。出荷推移（V-216）・入荷推移（V-217）は推定在庫推移（V-218）の算出に引き続き必要なため、`shipment_trend`/`incoming_trend` の算出・配信・`getShipmentTrend`/`getIncomingTrend` ゲッターはすべて維持した。撤去したのは「専用グラフとして描画する」処理のみ（§6.4・§7.3）。
- **命名リスク（R-6）の解消**: 撤去対象だった `renderShipmentTrendChart` 等の識別子ごと削除したため、命名の妥協（"shipment" が入荷も扱う不一致）は自然に解消した。
- **テスト**: 撤去に伴い、独立グラフの存在を前提としたテスト（TC-SHC-X-001, X-003, X-004, X-005, X-009）を削除・置き換えた。データ算出のテスト（domain/infrastructure層）は無変更。

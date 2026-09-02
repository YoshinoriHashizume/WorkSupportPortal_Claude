# 機能設計書: 詳細ダイアログへの出荷推移グラフの追加

文書ID: DESIGN-SHIPMENT-HISTORY-CHART-2026-001
作成日: 2026/09/01
更新日:
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

## 5. データモデル

### 5.1 変更しないもの

- `InventoryOrderAlertSummarySnapshot` モデル定義（`rows` は既存の `JSONField`）。**マイグレーション不要**。
- `fetch_all_shipments()` の SQL・戻り値の形。
- `aggregate_shipment_stats()` のロジック・戻り値。

### 5.2 集計スナップショットの行に追加するキー

| キー | 型 | 説明 |
|---|---|---|
| `shipment_trend` | `list[dict]` | `build_monthly_shipment_trend()` の戻り値をそのまま格納。固定長 24 件 |

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

### 6.2 クライアント配信ペイロード（REQ-SHC-NF-001）

`list_client_data.py:row_to_client_dict()` は行の全キーを `_json_value()` 経由でそのまま `client_row` へコピーする実装のため、**コード変更なしで** `row["shipment_trend"]` が `client_row["shipment_trend"]`（snake_case のまま）として配信される。
camelCase の別名は追加しない（03_mari-stock-visibility での「同じ値の二重配信をしない」方針を踏襲）。

配信データ量: 1 行あたり `shipment_trend` は 24 件 × 約 20 バイト（`{"month":"2025-09","qty":120},`）で **約 500 バイト**の見積り。既存の 1 行あたりデータ量（実測約 4,000 バイト、03_mari-stock-visibility 実測値）と比べ増分は大きい。**test-design.md の E 系で必ず実測し、要件の許容値を確認する**（本要件は 03_mari-stock-visibility のような明示的な上限値を requirements.md に定めていないため、design レビューで上限を追加するかを判断する。DECISIONS.md 参照）。

### 6.3 詳細ダイアログのデータ供給経路（既存パターンの踏襲）

03_mari-stock-visibility の design.md §6.3.1 で確立した経路（一覧行の `data-*` 属性 + `listClient` のゲッター）を踏襲する。ただし `shipment_trend` は 24 件の配列であり `data-*` 属性文字列には適さないため、**`listClient` のゲッター経由でのみ**渡す（`data-*` 属性は追加しない）。

```js
// static/js/inventory-order-alert-list-client.js
getShipmentTrend(custCode, itemCd) {
  const row = findRow(custCode, itemCd);   // 既存のヘルパーを再利用
  return Array.isArray(row?.shipment_trend) ? row.shipment_trend : [];
},
```

```js
// static/js/inventory-order-alert-list.js の fillDetailSections(row) 内に追加
const trend = listClient?.getShipmentTrend?.(custCode, row.dataset.itemCd || "") || [];
renderShipmentTrendChart(detailFields.shipmentTrendChart, trend);
```

### 6.4 グラフ描画（REQ-SHC-F-002 / NF-006）

`static/js/inventory-order-alert-list.js` に `renderShipmentTrendChart(container, points)` を新設する。

- 外部ライブラリを使わず、SVG 要素を手組みして注入する（`shipment_trend` アプリの `buildChartSvgMarkup` と同じ方式だが、コードは独立実装。REQ-SHC-NF-005 / NF-006）。
- 折れ線（`<polyline>`）＋各点のマーカー（`<circle>`）。縦軸は 0 〜 データ最大値（最大値が 0 の場合は 1 として除算エラーを避ける）。
- 横軸ラベルは 24 点すべてには付けず、**間引いて表示**する（例: 4 か月おき）。24 本のラベルは詳細ダイアログの幅に収まらないため。
- 全点が 0（＝対象期間内に出荷実績が 1 件もない）場合は、**グラフを描画せず** `.ioa-detail-shipment-trend-empty` に「出荷実績がありません」を表示する（REQ-SHC-F-003）。
- `shipment_trend` が空配列（既存スナップショット互換。REQ-SHC-F-004）の場合も同じ「実績なし」表示にする。

### 6.5 詳細ダイアログの構成変更

03_mari-stock-visibility で確立した 4 区分（品目 / 流動区分 / 在庫 / メモ）に、**「出荷推移」区分を「在庫」と「メモ」の間に追加**し、5 区分にする。

```
┌ 詳細 ────────────────────────────────────┐
│ ■ 品目 / ■ 流動区分 / ■ 在庫  … 既存      │
│                                            │
│ ■ 出荷推移                                 │
│   [SVG 折れ線グラフ 24か月]                 │
│   または「出荷実績がありません」            │
│                                            │
│ ■ メモ … 既存                              │
└────────────────────────────────────────────┘
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
| `infrastructure/oracle/summary_queries.py` | `group_shipments_by_pair()` を追加。`build_summary_rows()` の行に `shipment_trend` を付与 |
| `templates/inventory_order_alert/list.html` | 詳細ダイアログに「出荷推移」区分を追加 |
| `static/js/inventory-order-alert-list-client.js` | `getShipmentTrend()` ゲッターを追加 |
| `static/js/inventory-order-alert-list.js` | `renderShipmentTrendChart()` を追加し `fillDetailSections()` から呼ぶ |
| `static/css/app.css` | 出荷推移グラフ区分のスタイルを追加 |
| `docs/在庫発注アラート_機能仕様書.md` | §4.1.6（詳細ダイアログ）を改訂 |

### 7.3 削除するもの

なし。

## 8. エラーハンドリング方針

| 状況 | 挙動 |
|---|---|
| 対象期間内に出荷実績が 1 件もない | 全月 0 の配列を返す（`build_monthly_shipment_trend` は空配列を返さない）。表示側で「実績なし」に振り替える（REQ-SHC-F-003） |
| 既存スナップショット（`shipment_trend` キーなし） | `row.get("shipment_trend")` が `None`。表示側で「実績なし」相当（REQ-SHC-F-004） |
| 出荷推移の集計中に例外が発生した | **取込全体を失敗させる**（既存の `run_summary_aggregation` の例外捕捉に合流。03_mari-stock-visibility と同じ方針。独自の例外型を新設しない） |
| `ship_qty` が負値（返品等） | 加工せずそのまま月次合計に含める（基幹の値を加工しない。03_mari-stock-visibility の MARI 在庫の方針を踏襲） |

## 9. リスクと対策

| # | リスク | 影響 | 対策 |
|---|-------|------|------|
| R-1 | 配信ペイロードの増加 | 一覧の初期表示が遅くなる | §6.2 のとおり実測する。要件定義書に明示的な上限値がないため、design レビューで上限（例: 600 バイト/行）を追加するかを判断する |
| R-2 | 「在庫変動」という元の依頼と実装内容（出荷推移）の乖離 | 利用者の期待とズレる可能性 | DECISIONS.md に明記し、翌営業日に確認を得る |
| R-3 | 対象期間 24 か月が死蔵判定軸（最大 5 年）の判定根拠を包含しない | 5 年判定の行でグラフが判定期間全体をカバーしない | DECISIONS.md に明記し、期間の妥当性を翌営業日に確認する |
| R-4 | `aggregate_shipment_stats()` と本機能の月次集計が二重に全出荷明細を扱う | コードの重複（ロジックは別だが元データは同じ） | 許容する。`aggregate_shipment_stats()` 自体の変更はスコープ外とし、リスクを増やさない |

---

## レビュー履歴

### 自己実施 Design-L1 相当レビュー (2026/09/01)

- **戦略的設計との整合性**: OK。コンテキストB内に閉じ、共有カーネル外への参照なし。
- **レイヤー配置**: OK。月次集計ロジックを domain（純粋関数）に、Oracle 取得結果のグループ化を infrastructure に配置。domain に `import django` なし。
- **依存方向**: OK。infrastructure → domain の一方向。
- **既存コードの保護**: OK。`fetch_all_shipments()` / `aggregate_shipment_stats()` は無変更。
- **懸念**: R-1（ペイロード上限が要件定義書に未定義）、R-3（24か月固定の妥当性）は自己判断のため DECISIONS.md で翌営業日確認を依頼する。

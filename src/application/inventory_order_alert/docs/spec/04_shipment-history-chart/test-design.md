# テスト設計書: 詳細ダイアログへの出荷推移グラフの追加

文書ID: TEST-SHIPMENT-HISTORY-CHART-2026-001
作成日: 2026/09/01
更新日:
対応文書: [design.md](./design.md)（DESIGN-SHIPMENT-HISTORY-CHART-2026-001）
テスト戦略reference: 03_mari-stock-visibility/test-design.md と同一方針を踏襲（本書では差分のみ記述）
テストフレームワークreference: django-pytest

---

## 1. テスト戦略

### 1.1 テスト対象のスコープ

- **対象**: 月次出荷推移の集計ロジック（domain）、Oracle 取得結果のグループ化（infrastructure）、集計行への付与、既存スナップショットとの互換、クライアント配信ペイロード、JS の描画ロジック（ソース文字列アサーション方式）。
- **対象外**: `fetch_all_shipments()` 自体（無変更）、`aggregate_shipment_stats()` 自体（無変更）。SVG の見た目（ピクセル比較はしない。要素の存在・データ属性で検証する）。

### 1.2 テストレイヤーの方針

| レイヤー | テスト種別 | 方針 | DB依存 |
|---|---|---|---|
| Domain（`shipment_trend.py`） | 単体テスト | 日付固定リテラルで月境界を厳密に検証 | なし |
| Infrastructure（`group_shipments_by_pair`） | 単体テスト | Oracle カーソルは `unittest.mock` | なし（グループ化自体はPython内） |
| Infrastructure（`build_summary_rows` 統合） | 既存の `_shipped_pair_patches` パッチ方式を拡張 | 既存テストと同じモック方式 | なし |
| Infrastructure（スナップショット往復） | 既存の `test_summary_storage.py` パターンを拡張 | Django ORM 使用 | あり |
| Interfaces（詳細ダイアログ） | ビュー統合テスト＋JS ソース文字列アサーション | 既存パターンを踏襲 | あり |

### 1.3 TDD方針

Red → Green → Refactor。各実装タスクの直前にテスト作成タスクを置く（tasks.md 参照）。

### 1.4 テストケースIDの規約

`TC-SHC-{層}-{連番}`。層: D=Domain, I=Infrastructure, A=Application, X=Interfaces, E=エッジケース/性能。

---

## 2. テストケース一覧

### 2.1 Domain層テスト（`shipment_trend.py`）

| # | テストケース | 入力 | 期待結果 | 対応REQ-ID | 優先度 |
|---|---|---|---|---|---|
| TC-SHC-D-001 | 出荷実績なしなら全月0の24件を返す | `shipments=[]`, `as_of_date=2026-06-17` | 24件、全て `qty=0`、月は 2024-07〜2026-06 | REQ-SHC-F-001 | P1 |
| TC-SHC-D-002 | 単月に複数出荷があれば合算する | 同月に qty=10, qty=5 が2件 | 当該月 `qty=15` | REQ-SHC-F-001 | P1 |
| TC-SHC-D-003 | as_of_date の月が最終月になる | `as_of_date=2026-06-17` | 最後の要素の `month == "2026-06"` | REQ-SHC-F-001 | P1 |
| TC-SHC-D-004 | 24か月より古い出荷は含まれない | `as_of_date=2026-06-17` の25か月前に出荷 | その月は結果に現れない（範囲外） | REQ-SHC-F-001 | P1 |
| TC-SHC-D-005 | 月は古い順に並ぶ | 複数月にまたがる出荷 | `result[i].month < result[i+1].month` | REQ-SHC-F-002 | P2 |
| TC-SHC-D-006 | 戻り値は常に固定長24件 | 出荷が1件だけ・24件超の月にまたがる等 | 常に `len(result) == 24` | REQ-SHC-F-002 | P1 |
| TC-SHC-D-007 | 月末日の出荷が月境界をまたがない | `ship_date` が月末・翌月頭に近い値 | 正しい月に分類される | REQ-SHC-F-001 | P2 |
| TC-SHC-D-008 | 負の出荷数量（返品）はそのまま合算する | `qty=-5` を含む | 加工せず合計に反映（design.md §8） | REQ-SHC-F-001 | P2 |
| TC-SHC-D-009 | `months` 引数を変えると長さが変わる | `months=6` | `len(result) == 6` | 設計の柔軟性確認 | P3 |

### 2.2 Infrastructure層テスト

#### `group_shipments_by_pair()`

| # | テストケース | 入力 | 期待結果 | 対応REQ-ID | 優先度 |
|---|---|---|---|---|---|
| TC-SHC-I-001 | cust_code + cust_item_cd でグループ化される | 2件が同一キー、1件が別キー | 2グループ、件数がそれぞれ一致 | REQ-SHC-F-001 | P1 |
| TC-SHC-I-002 | 空リストなら空辞書を返す | `[]` | `{}` | 境界値 | P2 |
| TC-SHC-I-003 | 該当キーがない行の月次は空リストで扱われる（呼び出し側で0埋め） | 未出荷ペア | `build_monthly_shipment_trend([])` が全月0を返すことと合わせて確認 | REQ-SHC-F-004 | P1 |

#### `build_summary_rows()` への付与

| # | テストケース | 入力 | 期待結果 | 対応REQ-ID | 優先度 |
|---|---|---|---|---|---|
| TC-SHC-I-004 | 出荷ありの行に shipment_trend が付与される | 既存 `_shipped_pair_patches` を利用 | `rows[0]["shipment_trend"]` が24件のリスト | REQ-SHC-F-001 | P1 |
| TC-SHC-I-005 | Oracle への追加問い合わせが発生しない | `build_summary_rows` 実行 | `fetch_all_shipments` の呼び出し回数が1回のまま（既存回数から増えない） | REQ-SHC-NF-001 | **P1** |
| TC-SHC-I-006 | 既存の出荷回数（post_shipment_count）算出結果が変わらない | 既存の代表行データ | 本機能導入前後で `post_shipment_count` 等が一致 | REQ-SHC-NF-003（既存ロジック無変更） | **P1** |

#### スナップショット往復

| # | テストケース | 入力 | 期待結果 | 対応REQ-ID | 優先度 |
|---|---|---|---|---|---|
| TC-SHC-I-007 | shipment_trend を含む行が保存・復元できる | 24件のリストを含む行 | 復元後も24件・値が一致（Decimal化されない） | REQ-SHC-NF-002 | P1 |
| TC-SHC-I-008 | 既存スナップショット（shipment_trend キーなし）の読込で例外を出さない | キーなしの行 | `row.get("shipment_trend")` が `None`。例外なし | REQ-SHC-F-004 | **P1** |

### 2.3 Application層テスト

| # | テストケース | 入力 | 期待結果 | 対応REQ-ID | 優先度 |
|---|---|---|---|---|---|
| TC-SHC-A-001 | 一覧表示のユースケースが shipment_trend を通過させる | `ListPage.execute()` | `context.all_rows[0]["shipment_trend"]` が取得できる | REQ-SHC-F-001 | P2 |
| TC-SHC-A-002 | 一覧表示で Oracle を呼ばない（既存方針の非回帰） | `ListPage.execute()` | 既存と同様、取込を実行しない | REQ-SHC-NF-001 | P1 |

### 2.4 Interfaces層テスト

| # | テストケース | 入力 | 期待結果 | 対応REQ-ID | 優先度 |
|---|---|---|---|---|---|
| TC-SHC-X-001 | 詳細ダイアログに「出荷推移」区分が存在する | 一覧ページHTML | `ioa-detail-shipment-trend-section` 等のクラスが存在 | REQ-SHC-F-002 | P1 |
| TC-SHC-X-002 | JS に getShipmentTrend ゲッターが定義されている | list-client.js ソース | 文字列 `getShipmentTrend` が存在 | design.md §6.3 | P1 |
| TC-SHC-X-003 | JS に renderShipmentTrendChart が定義され SVG を組み立てる | list.js ソース | `renderShipmentTrendChart` と `createElementNS` 等のSVG生成コードが存在 | REQ-SHC-F-002 | P1 |
| TC-SHC-X-004 | 実績なし時の表示ロジックが存在する | list.js ソース | 「出荷実績がありません」相当の分岐が存在 | REQ-SHC-F-003 | P1 |
| TC-SHC-X-005 | 既存の4区分（品目・流動区分・在庫・メモ）の順序が変わらない | 一覧ページHTML | 出荷推移区分が「在庫」と「メモ」の間に挿入されている | design.md §6.5 | P2 |
| TC-SHC-X-006 | 流動区分の判定結果が本要件の前後で変わらない | `pytest test_flow_quadrant.py` | 全件 Green（非回帰） | REQ-SHC-NF-004 | **P1** |
| TC-SHC-X-007 | `config/tests/test_clean_architecture.py` が Green | 全体テスト | レイヤー違反なし | REQ-SHC-NF-006 | **P1** |

---

## 3. テストデータ

### 3.1 代表データ

各テストファイル先頭にモジュール定数として定義する（他ファイルからは import しない）。

```python
# 例: test_shipment_trend_vo.py
AS_OF_DATE = date(2026, 6, 17)
```

### 3.2 異常系テストデータ

- 出荷実績が1件もない `(cust_code, cust_item_cd)` ペア
- 24か月の境界をまたぐ出荷日（ちょうど24か月前・25か月前）
- 負の出荷数量（返品を模したデータ）
- 既存スナップショット相当（`shipment_trend` キーを持たない行の辞書）

---

## 4. 境界値・異常系のカバレッジ

### 4.1 境界値テスト

| 対象 | 境界値 | テストケース |
|---|---|---|
| 対象期間の下限 | ちょうど24か月前 / 25か月前 | TC-SHC-D-004 |
| 月境界 | 月末日・月初日の出荷 | TC-SHC-D-007 |
| 出荷数量 | 0・負値 | TC-SHC-D-008 |

### 4.2 異常系テスト

| 対象 | 異常ケース | 期待される振る舞い |
|---|---|---|
| 出荷実績が全くない品目 | `shipments=[]` | 全月0の24件（TC-SHC-D-001）。表示側は「実績なし」（TC-SHC-X-004） |
| 既存スナップショット | `shipment_trend` キーなし | 例外にならず「実績なし」相当（TC-SHC-I-008） |

### 4.3 エッジケース

| # | 内容 |
|---|---|
| TC-SHC-E-001 | 配信ペイロードの1行あたり増分を実測する（design.md §6.2 の見積り約500バイトを検証） |
| TC-SHC-E-002 | 5,000行相当でも `build_list_client_payload` が完了する（既存の性能非回帰） |

---

## 5. テスト環境

### 5.1 テスト実行コマンド

| 目的 | コマンド |
|---|---|
| Domain層のみ | `pytest application/inventory_order_alert/tests/test_shipment_trend_vo.py -x` |
| アプリ全体 | `pytest application/inventory_order_alert/` |
| アーキテクチャ検証 | `pytest config/tests/test_clean_architecture.py` |
| 全体 | `pytest` |

作業ディレクトリは `/django_app/src`。

---

## 6. 要件トレーサビリティ

| 要件ID | テストケース |
|---|---|
| REQ-SHC-F-001 | TC-SHC-D-001〜004, D-006〜008, I-001, I-004 |
| REQ-SHC-F-002 | TC-SHC-D-005, D-006, X-001, X-003 |
| REQ-SHC-F-003 | TC-SHC-X-004 |
| REQ-SHC-F-004 | TC-SHC-I-003, I-008 |
| REQ-SHC-NF-001 | TC-SHC-I-005, A-002 |
| REQ-SHC-NF-002 | TC-SHC-I-007 |
| REQ-SHC-NF-003 | TC-SHC-I-006 |
| REQ-SHC-NF-004 | TC-SHC-X-006 |
| REQ-SHC-NF-005 | design.md §2.1 のレビューで確認（自動テスト化しない。import 文の目視確認） |
| REQ-SHC-NF-006 | TC-SHC-X-007 |
| REQ-SHC-NF-007（TDD） | tasks.md の各タスクで Red→Green を確認 |

---

## レビュー履歴

### 自己実施レビュー (2026/09/01)

網羅性・境界値・非回帰観点を確認し、NG相当の指摘なし。E-001（ペイロード実測）は design.md のリスクR-1と対応しており、実測後に許容値を確定する（DECISIONS.md 参照）。

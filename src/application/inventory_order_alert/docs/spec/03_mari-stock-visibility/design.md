# 機能設計書: MARI 在庫数の併記と一覧・詳細の表示整理

文書ID: DESIGN-MARI-STOCK-VISIBILITY-2026-001
作成日: 2026/08/31
更新日: 2026/08/31（§6.3.1 を追加し、§7.2 から `row_detail.py` を削除。本アプリに同ファイルは存在せず、詳細ダイアログは行の `data-*` 属性経由でデータを受け取るため）
対応文書: ./requirements.md (REQ-MARI-STOCK-VISIBILITY-2026-001)
アーキテクチャreference: django-clean-architecture version 1.0 (updated 2026-04-11)

---

## 1. 設計の目的

要件定義書 REQ-MARI-STOCK-VISIBILITY-2026-001 を実装するための技術的な到達目標は次の 4 点である。

1. **MARI 在庫数の取得を取込経路に閉じ込める**: `T_ITEM_STOCK` への問い合わせを SLIMS 取込時の 1 クエリに限定し、一覧表示時に MARI へ問い合わせない既存方針（機能仕様書 §4.1.1）を維持する。
2. **在庫数の出所を型と列名で明示する**: 「在庫数」という出所不明の呼称をコード・画面・CSV から無くし、SLIMS / MARI を判別可能にする。
3. **表示の責務を一覧と詳細に振り分ける**: 一覧は判断に必要な数値、詳細は補足情報（責任部署・在庫内訳）という役割分担にする。
4. **既存スナップショットとの互換を保つ**: MARI 在庫を持たない行を読み込んでも破綻せず、未取得と分かる表示にする。

### 1.1 前提となる戦略的設計の改訂（完了済み）

本要件は strategic_design.md §1.1 の中核制約に触れるため、**設計着手時点で以下の改訂を済ませている**（v1.2）。

| 改訂前 | 改訂後 |
|---|---|
| 在庫数量は MARI を信用しない / 実在庫は SLIMS が正 / 在庫は SLIMS CSV の取込結果を用いる | **実在庫の正は SLIMS** / MARI の在庫数は判断材料として併記する / 業務判断の基準は SLIMS CSV の取込結果を用いる。MARI 在庫は差異に気づくための参考値であり、判定条件には用いない |

**業務判断の基準が SLIMS である点は変えていない。** 本設計もこの前提に従い、MARI 在庫数を流動区分の判定に一切用いない。

## 2. 対象コンテキスト

`docs/strategic_design.md` に従い、本機能は次の位置にある。

| 項目 | 内容 |
|------|------|
| 境界コンテキスト | **B: 在庫発注アラート**（コア／生産管理メニューグループ） |
| パッケージ | `application/inventory_order_alert/` |
| 上流（供給） | 基幹 Oracle (MARI)（**読み取り専用**・共有カーネル `application/sales/infrastructure/oracle/`）／SLIMS 在庫 CSV |
| 下流（利用） | なし（本機能はポータルのアラート帯に影響しない） |

### 2.1 境界の遵守

- **他コンテキストのコードを参照しない。** MARI 在庫の取得は 5年9組（コンテキスト C）が `fetch_item_stock_total` として実装済みだが、**これを import しない**。strategic_design.md §3.1 は共有カーネルを `application/shared/` と Oracle 接続 ACL に限定しており、`gonenkukumi` のクエリ関数は共有物ではない。本コンテキストに同等のクエリを持つ。
- **共有カーネルの変更なし。** Oracle 接続は既存の `application/sales/infrastructure/oracle/client.py` を通す。
- **MARI への書き込みを行わない**（SELECT のみ）。

> **判断の記録**: クエリの重複（`SUM(NVL(STOCK_ON_HAND_QTY, 0)) FROM T_ITEM_STOCK`）は許容する。
> コンテキスト間の直接参照を避ける方が、strategic_design.md §4.2「コンテキスト間でデータを共有しない原則」に忠実であるため。
> 将来 3 つ以上のコンテキストが同じクエリを必要とした場合に、共有カーネルへの昇格を検討する。

## 3. アーキテクチャ概要

```
interfaces/            views.py（一覧・CSV の描画）／wiring.py（合成ルート）
      ↓
use_cases/             ListPage / ExportCsv
      ↓
domain/                value_objects/stock_quantity.py（★新規・在庫数の表現）
      ↑                value_objects/{list_rows, table_display, export_csv, list_client_data, row_detail}
infrastructure/        oracle/summary_queries.py（★MARI 在庫の取得を追加）
                       persistence/summary_row_codec.py（★列の詰め替え）
```

| レイヤー | 本機能での責務 | Django 依存 |
|---------|--------------|------------|
| domain | 在庫数の表現（値・未取得・空の区別）、表示用の整形 | **禁止** |
| use_cases | 一覧・CSV の組み立て。列構成の決定 | **禁止** |
| infrastructure | MARI 在庫の取得、スナップショットへの保存・復元 | 許可 |
| interfaces | テンプレートへの受け渡し | 許可 |

### 3.1 取得タイミングの方針（REQ-MSV-F-001）

MARI 在庫は **SLIMS 取込時の集計（`build_summary_rows`）の中で 1 回だけ取得**し、集計スナップショットの行に保存する。

- 一覧表示時は既存どおりスナップショットを読むだけで、MARI へ問い合わせない。
- 流動区分（S-203）が読込のたびに再判定されるのとは対照的に、**MARI 在庫は取込時点の値で固定**される。SLIMS 在庫と同じ扱いであり、利用者が「〇年〇月〇日時点の在庫」として解釈できる。

## 4. ドメインモデル

### 4.1 エンティティ

**新規エンティティなし。** MARI 在庫数は集計行に付随する数量であり、識別子もライフサイクルも持たない。

### 4.2 バリューオブジェクト

新規ファイル: `domain/value_objects/stock_quantity.py`

在庫数には **3 つの状態** があり、これを取り違えると誤った発注判断につながる。型で区別する。

| 状態 | 意味 | 画面表示 | CSV |
|---|---|---|---|
| **値あり** | 在庫が存在する（0 を含む） | 数値（3 桁カンマ区切り） | 数値 |
| **該当なし** | 突合先にその品番が存在しない | 空 | 空 |
| **未取得** | この機能の導入前に作られたスナップショット | **`－`** | 空 |

```python
#: 在庫数の未取得を表す標識。既存スナップショットには MARI 在庫のキー自体が無い。
STOCK_NOT_FETCHED = "－"

def format_stock_quantity(value: object, *, fetched: bool = True) -> str:
    """在庫数を表示用の文字列にする。値あり／該当なし／未取得を区別する。"""

def is_stock_fetched(row: dict[str, object], key: str) -> bool:
    """行に在庫数のキーが存在するか（未取得の判定）。"""
```

- **`0` と「該当なし」を混同しない**（REQ-MSV-F-003）。`0` は在庫が無いこと、空は突合先に品番が無いことを表す。
- 「未取得」は**行にキーが存在しないこと**で表す。既存スナップショットには `mari_stock_qty` キー自体が無いため、`in` 演算で判別できる。値を `None` で埋める設計は採らない（`None` と「該当なし」の空が区別できなくなるため）。

### 4.3 集約

**新規集約なし。** 在庫数は集計行の属性であり、独立したトランザクション境界を持たない。

### 4.4 ドメインサービス

設けない。在庫数の整形は純関数として `stock_quantity.py` に置く（既存の `format_display.py` と同じ流儀）。

## 5. データモデル

### 5.1 変更しないもの

| テーブル | 判断 |
|---------|------|
| `InventoryOrderAlertSummarySnapshot` | **スキーマ変更なし。** `rows`(JSONField) の**要素に キーを 1 つ追加**するのみでカラムは増やさない |
| `SlimsStockImport` / `SlimsStockSnapshot` | 変更なし |
| `InventoryOrderAlertConfirmation` | 変更なし |

### 5.2 集計スナップショットの行に追加するキー

| キー | 型 | 内容 |
|---|---|---|
| `mari_stock_qty` | number / `""` | MARI の在庫数。該当なしは空文字 |

- 既存キー `stock_qty`（SLIMS 由来）は**キー名を変えない**。改名するとスナップショットの後方互換が壊れ、REQ-MSV-NF-002 に反するため。**表示上の呼称のみ「在庫数(SLIMS)」に改める**。
- `summary_row_codec.py` の詰め替えで、キーが無い行はそのまま（未取得）とする。

> **判断の記録**: ユビキタス言語では V-206 を「SLIMS 在庫数」へ改称したが、**永続化キー `stock_qty` は据え置く**。
> 用語の改称は利用者に見える呼称の問題であり、既存データの互換を壊してまで内部キーを揃える利益はない。
> 同種の判断は 02_low-flow-visibility で `critical_count` / `warning_count` を据え置いた前例がある。

### 5.3 MARI 在庫の取得

```sql
SELECT TRIM(ITEM_CD) AS ITEM_CD,
       SUM(NVL(STOCK_ON_HAND_QTY, 0)) AS STOCK_QTY
  FROM T_ITEM_STOCK
 WHERE TRIM(ITEM_CD) IN (:item_cds)
 GROUP BY TRIM(ITEM_CD)
```

- 突合キーは **内作品番**（`ITEM_CD`）。`build_summary_rows` が既に `resolve_internal_item_cd()` で解決済みの値を使う（REQ-MSV-F-001「新たなキー解決を設けない」）。
- **1 クエリで全品番分をまとめて取得**する（REQ-MSV-NF-001）。品番数が Oracle の IN 句上限を超える場合は既存の `chunked()`（900 件単位）を用いる。これは既存の他クエリと同じ方式であり、**論理的には 1 回の取得**として扱う。
- 内作品番が解決できない行は問い合わせ対象に含めず、`mari_stock_qty` を空にする（REQ-MSV-F-008 #4）。

## 6. API / インターフェース設計

### 6.1 一覧の列構成（REQ-MSV-F-002 / F-005）

`SORTABLE_COLUMNS` を次のように変更する。

| 変更 | 列キー | 見出し |
|------|-------|-------|
| 置換 | `stock_qty` | 在庫数 → **在庫数(SLIMS)** |
| 追加 | `mari_stock_qty` | **在庫数(MARI)**（`stock_qty` の直後） |
| 削除 | `responsible_department` | 責任部署（詳細ダイアログへ移設） |

- 両在庫数列ともソート可能とし、既存の `stock_qty` のソート規則（空は最小として扱う）を `mari_stock_qty` にも適用する。
- **未取得（`－`）は空と同じ扱い**でソートする。値ではないため。

### 6.2 CSV 出力（REQ-MSV-F-004）

| 変更 | 列キー | 見出し |
|------|-------|-------|
| 置換 | `stock_qty` | 在庫数 → **在庫数(SLIMS)** |
| 追加 | `mari_stock_qty` | **在庫数(MARI)** |
| 維持 | `responsible_department` | 責任部署（**CSV には残す**） |

- CSV の未取得は **空**とする。`－` は画面表示のための記号であり、Excel に取り込むと文字列として扱われるため。
- `confirmation_status` 以降の既存列の順序は変更しない。

### 6.3 詳細ダイアログ（REQ-MSV-F-006）

現在は「詳細 → 在庫内訳(SLIMS) → メモ」の 3 ブロックで、行の基本情報が `ioa-location-meta` の 1 行に圧縮されている。これを **4 区分**に整理する。

```
┌ 詳細 ────────────────────────────────────┐
│ ■ 品目                                     │
│   得意先 / 得意先品番 / 仕入先 / 仕入先品番  │
│   最終入荷日 / 最終出荷日                   │
│                                            │
│ ■ 流動区分                                 │
│   供給リスク品  [入荷なし]                  │
│   責任部署: 調達G・営業G・生産管理           │
│   （低流動判定軸・3か月で判定）              │
│                                            │
│ ■ 在庫                                     │
│   在庫数(SLIMS): 100   在庫数(MARI): 95     │
│   ┌ 在庫内訳(SLIMS) ──────────────┐        │
│   │ 入荷日 / ロケーション / 在庫数  │        │
│   └───────────────────────────────┘        │
│                                            │
│ ■ メモ                                     │
│   （既存のメモ一覧・入力欄）                 │
└────────────────────────────────────────────┘
```

- 各区分に見出し（`ioa-detail-section-title`。既存クラスを流用）を置く。
- **流動区分の区分に責任部署を置く**。責任部署は流動区分からの導出値であり、並べて示すことで対応関係が読み取れる。
- 判定条件（判定軸・判定期間）を併記する。一覧と同じ条件で判定した結果であることを示すため。
- **在庫内訳・メモの機能は変更しない**（並び順・保存・履歴）。

#### 6.3.1 詳細ダイアログのデータ供給経路

本アプリの詳細ダイアログは **サーバ側に詳細専用のドメインVOを持たない**。`inventory-order-alert-list-client.js` が一覧行 `<tr class="ioa-data-row">` に付与する `data-*` 属性を、`inventory-order-alert-list.js` が読み出して埋める構造である（既存の `data-stock-qty` / `data-stock-location-detail` / `data-stock-as-of-label` と同じ経路）。

したがって 4 区分に必要な値は、次のとおり **既存の経路を拡張して**供給する。新しいドメインVO（`row_detail.py`）は作らない。作っても一覧ペイロードと二重に同じ値を運ぶだけで、配信量が増えるため。

| 表示項目 | 供給元 |
|---|---|
| 得意先 / 得意先品番 | 既存の `data-cust-code` / `data-cust-name` / `data-item-cd` |
| 仕入先 / 仕入先品番 / 最終入荷日 / 最終出荷日 | `data-*` を追加する |
| 流動区分・入荷実績なし | `data-flow-quadrant` / `data-no-incoming-record` を追加する |
| 責任部署 | 一覧ペイロードの `flowQuadrantDepartments` を流動区分キーで引く（一覧列からは外すが対応表は残す。§7.3） |
| 判定条件（判定軸・判定期間） | 一覧の判定条件セレクタの現在値 |
| 在庫数(SLIMS) / 在庫数(MARI) | 既存の `data-stock-qty` と、追加する `data-mari-stock-qty` |
| 在庫内訳 / メモ | 既存のまま変更しない |

### 6.4 クライアント配信ペイロード

行の生値 `mari_stock_qty` と `display` マップの `mari_stock_qty` を配信する。

**camelCase の別名（`mariStockQty`）は配信しない。** 利用側は 2 つしかなく、
どちらも既存のキーで足りるためである。

| 利用側 | 参照するキー |
|---|---|
| クライアント側のソート（`sortValue()`） | 行の生値 `mari_stock_qty` |
| セルの描画・詳細ダイアログの `data-*` 属性 | `display.mari_stock_qty` |

| 項目 | 増分の見積り |
|---|---|
| `"mari_stock_qty":123` | 約 22 バイト |
| `display` マップの `mari_stock_qty` エントリ | 約 25 バイト |
| **合計** | **約 47 バイト**（REQ-MSV-NF-001 の 50 バイト以内） |

> **実測値（2026/08/31）**: 1 行あたり **+41 バイト**（未取得行 3,974 → MARI 付き行 4,015）。
> 見積りとの乖離はなかった。計測手順は `tests/test_mari_stock_edge_cases.py` の
> `test_TC_MSV_E_001_payload_increase_per_row_is_within_budget` を参照。

> 02_low-flow-visibility では見積りが実測と 2.5 倍ずれた（[ISSUE-0005](../../issues/ISSUE-0005-no-payload-size-requirement.md)）。
> 今回はキー名と引用符を含めて数えている。**実測はテスト設計の E 系で必ず行う**。

一方、責任部署を一覧列から外すことで `display` マップの `responsible_department` エントリ（約 45 バイト）が**減る**。差し引きの増分はほぼゼロになる見込みである。

## 7. 既存コードへの変更点

### 7.1 新規ファイル

| ファイル | 内容 |
|---------|------|
| `domain/value_objects/stock_quantity.py` | 在庫数の 3 状態（値あり／該当なし／未取得）の表現と整形（§4.2） |

### 7.2 変更ファイル

| ファイル | 変更概要 |
|---------|---------|
| `infrastructure/oracle/summary_queries.py` | `fetch_mari_stock_totals()` を追加し、`build_summary_rows` の行に `mari_stock_qty` を付与 |
| `infrastructure/persistence/summary_row_codec.py` | `mari_stock_qty` の保存・復元。**キーが無い行はキーを作らない**（未取得の表現を保つ） |
| `domain/value_objects/table_display.py` | `SORTABLE_COLUMNS` の見出し変更・`mari_stock_qty` 追加・`responsible_department` 削除。`_sort_value()` に `mari_stock_qty` の分岐を追加 |
| `domain/value_objects/export_csv.py` | `EXPORT_COLUMNS` の見出し変更・`mari_stock_qty` 追加（責任部署は維持） |
| `domain/value_objects/list_client_data.py` | ペイロードに `mariStockQty` を追加。`display` マップに `mari_stock_qty` |
| `templates/inventory_order_alert/list.html` | 詳細ダイアログを 4 区分へ（§6.3）。一覧行に詳細用の `data-*` 属性を追加（§6.3.1。JS 側の行描画と対で維持する）。一覧の責任部署列は `SORTABLE_COLUMNS` 由来のため自動的に消える |
| `templatetags/inventory_order_alert_format.py` | `ioa_display` に在庫数の 3 状態を適用し、サーバ描画と JS 描画で未取得の表示を揃える（§4.2） |
| `static/js/inventory-order-alert-list-client.js` | `mari_stock_qty` のソート・描画。責任部署の列描画を削除。詳細ダイアログ用の `data-*` 属性を追加（§6.3.1） |
| `static/js/inventory-order-alert-list.js` | 詳細ダイアログへの値の流し込みを 4 区分に追随（§6.3.1） |
| `static/css/app.css` | 詳細ダイアログの区分見出しのスタイル |
| `docs/在庫発注アラート_機能仕様書.md` | §4.1.3（列定義）・§4.1.5（一覧 UI）・§4.1.6（詳細）・§6.1・§8.3 を改訂。**共通品の重複計上を明記**（REQ-MSV-F-011） |

### 7.3 削除するもの

一覧の責任部署列に関する**表示・ソートのコードのみ**。責任部署の導出（`responsible_departments()` / `format_responsible_departments()`）は詳細ダイアログと CSV で引き続き使うため**残す**。

## 8. エラーハンドリング方針

| 状況（REQ-MSV-F-008 / F-009 対応） | 挙動 |
|---|---|
| MARI に該当在庫がない | `mari_stock_qty` を空文字にする。画面は空、CSV も空 |
| MARI の在庫数が 0 | `0` を表示する。空とは区別する |
| MARI の在庫数が負値 | そのまま表示する。基幹の値を加工しない |
| 内作品番が解決できない行 | 問い合わせ対象に含めず空にする。SLIMS 在庫数・流動区分は従来どおり |
| **MARI 在庫の取得クエリが失敗した** | **取込全体を失敗させる**。既存の `run_summary_aggregation` の例外捕捉に委ね、`aggregation_error` を記録する。直前のスナップショットは保持される（REQ-MSV-F-009） |
| 既存スナップショット（キーなし）を読み込んだ | 画面は `－`、CSV は空。エラーにしない |
| 取込中に一覧を開いた | 既存の `import_lock` に従う。新たな排他制御を設けない（REQ-MSV-F-010） |

**原則**: MARI 在庫の取得は既存の集計処理の一部として扱い、**独自の例外型を新設しない**。失敗時は既存の集計エラー経路に合流させる。

## 9. リスクと対策

| # | リスク | 影響 | 対策 |
|---|-------|------|------|
| R-1 | `T_ITEM_STOCK` の件数が多く、取込時間が延びる | 取込が遅くなる | 品番を絞った IN 句で取得し、全件走査しない。既存の `chunked()` を用いる。取込時間の増加をテスト設計の E 系で実測する |
| R-2 | **`0` と「該当なし」の取り違え** | 在庫があると誤認して発注を見送る／その逆 | 型で区別し（§4.2）、境界を自動テストで固定する。CSV でも空を維持する |
| R-3 | **未取得（`－`）を「在庫ゼロ」と誤読する** | 同上 | 記号を数値と明確に異なるものにする。再取込すれば解消することを機能仕様書に明記する |
| R-4 | 共通品で同じ在庫が複数行に出る | 一覧の在庫数を合計して総在庫と誤認する | **SLIMS 在庫数も従来から同じ性質**であり新たな問題ではない。機能仕様書に明記する（REQ-MSV-F-011） |
| R-5 | 責任部署を一覧から外したことで見落とされる | 対応の引き取り先が分からなくなる | CSV には残す。詳細ダイアログでは流動区分と並べて示す（§6.3） |
| R-6 | 配信ペイロードの増加 | 一覧の初期表示が遅くなる | 責任部署の削除と相殺され増分はほぼゼロの見込み。**実測で確認する**（§6.4） |
| R-7 | MARI 在庫の取得失敗で取込が止まる | SLIMS 在庫の更新もできなくなる | 要件で合意済みの挙動（REQ-MSV-F-009）。直前のスナップショットは保持されるため一覧は使える。エラーメッセージで原因が分かるようにする |

---

## 10. 要件トレーサビリティ

| 要件ID | 要件 | 設計上の対応箇所 |
|--------|------|----------------|
| REQ-MSV-F-001 | MARI 在庫数の取得 | §3.1 / §5.3 |
| REQ-MSV-F-002 | 在庫数の出所の判別 | §6.1 |
| REQ-MSV-F-003 | 在庫が存在しない場合の表示 | §4.2 |
| REQ-MSV-F-004 | CSV 出力への反映 | §6.2 |
| REQ-MSV-F-005 | 責任部署の一覧からの除外 | §6.1 / §7.3 |
| REQ-MSV-F-006 | 詳細ダイアログの構成整理 | §6.3 |
| REQ-MSV-F-007 | 既存スナップショットとの互換 | §4.2 / §5.2 |
| REQ-MSV-F-008 | 異常系・エッジケースの扱い | §8 |
| REQ-MSV-F-009 | MARI 在庫取得の失敗時の扱い | §8 / §9 R-7 |
| REQ-MSV-F-010 | 取込の排他 | §8 |
| REQ-MSV-F-011 | 共通品の重複計上の許容 | §9 R-4 |
| REQ-MSV-NF-001 | 性能 | §5.3 / §6.4 / §9 R-1・R-6 |
| REQ-MSV-NF-002 | 既存データとの互換性 | §5.1 / §5.2 |
| REQ-MSV-NF-003 | 基幹システムの保護 | §2.1 / §5.3 |
| REQ-MSV-NF-004 | 判定への不使用 | §1.1 |
| REQ-MSV-NF-005 | 用語の一貫性 | §6.1 / §6.2 |
| REQ-MSV-NF-006 | アーキテクチャ制約 | §3 / §2.1 |
| REQ-MSV-NF-007 | 品質・テスト | test-design.md へ委ねる |

---

## レビュー履歴

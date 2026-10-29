---
文書ID: ISSUE-INVENTORY-ORDER-ALERT-IMP-2026-008
種別: 改善
ステータス: Verifying
優先度: 中
起票者: Hashizume（利用者からの要望）
起票日: 2026/10/29 14:35
更新日: 2026/10/29 14:45
クローズ日:
対象コンテキスト: inventory_order_alert
対象機能: 在庫時点（T-202）の表示（一覧・ダッシュボード帯・詳細ダイアログ・CSV 出力）
対応文書: なし
外部リンク:
---

# 在庫時点（T-202）の表示が暦日までのため、同日に複数回取り込むと新旧を見分けられない

## 現状の課題

SLIMS 在庫 CSV の取込日時は `SlimsStockImport.imported_at`（timestamptz）として
**時刻まで保存されている**が、画面・CSV への表示はいずれも `timezone.localdate()` で
**暦日に丸めている**。そのため次の不便がある。

- 同じ日に 2 回以上取り込んだ場合、**画面を見ても新旧を区別できない**。
  「朝に取り込んだ古い集計を見ているのか、さきほど取り込み直した結果を見ているのか」が分からない。
- 取込は在庫・内示・発注残を基幹から全件集計し直す重い処理であり、
  **判定結果（対応区分 S-204・在庫切れ日 V-232・発注期限 V-233）は取込時点の値で保存される**。
  取込のたびに結果が変わりうるため、「いつの取込か」は判定を読むうえでの前提情報にあたる。
- 在庫発注アラートの数値を会議資料・根拠として CSV 出力したとき、
  「在庫時点」列が暦日までだと**どの取込の結果か後から特定できない**。

なお `imported_at` は既に時刻を保持しているため、**データ側の不足はない**。表示だけの課題である。

## 改善提案

在庫時点（T-202）の表示を **暦日から日時（時分）に変更する**。対象は次の 5 箇所。

| # | 表示場所 | 現在 | 変更後 |
|---|---|---|---|
| 1 | 一覧の見出し | `2026年10月29日時点の集計結果を表示しています。` | `2026年10月29日 14:30 時点の集計結果を表示しています。` |
| 2 | SLIMS 在庫データが古い旨の警告バナー | `最終取込: 2026/10/29` | `最終取込: 2026/10/29 14:30` |
| 3 | ポータルのアラート帯 | `2026年10月29日時点の在庫` | `2026年10月29日 14:30 時点の在庫` |
| 4 | 一覧の詳細ダイアログ（在庫セクション） | 同上 | 同上 |
| 5 | CSV 出力の「在庫時点」列 | 同上 | 同上 |

時刻の表記は **`HH:MM`（時分・コロン区切り）** とする。
ポータル内の既存の日時表示（確認メモの作成日時等で使う `format_display_datetime`、
書式 `%Y/%m/%d %H:%M`）と揃えるため、秒は表示しない。

## 期待効果

- 同日複数回の取込で**新旧を判別できる**ようになる（現在は不可能）。
- CSV・ダッシュボードを根拠資料として使う際、**どの取込の結果かを特定できる**。
- 取込直後に「反映されたか」を画面で確認できるようになる
  （現在は暦日が同じため、取込前後で見出しが変わらない）。

## 代替案

| 案 | 内容 | 採否 |
|---|---|---|
| A | 秒まで表示する（`14:30:05`） | **不採用**。1 日に数回の取込では秒は判別に寄与せず、列幅を消費するだけ |
| B | 和文で統一する（`14時30分`） | **不採用**。確認メモ等の既存の日時表示（`H:MM`）と書式が割れる |
| C | 一覧の見出しとバナーだけ時刻を付ける | **不採用**。同じ「在庫時点」が画面によって暦日/日時と違って見えるのが最も混乱する |
| D | 在庫時点（T-202）そのものを日時に変更し、判定の基準日にも日時を使う | **不採用**。判定（在庫切れ日・発注期限・判定ホライズン V-239）は日単位で設計されており、基準日を日時にすると判定結果が動く。本件は表示のみの要望であるため、基準日は暦日のまま据え置く |

---
（以下、PDCA共通セクション。進行に応じて追記）

## 対策案 (Plan)

- 対策区分: **軽微**
  - 表示書式のみの変更であり、**判定ロジックは一切変更しない**
  - **マイグレーションなし**（`imported_at` は既存。DB スキーマは不変）
  - **JS の変更なし**（ラベル文字列を素通しするだけのため）。キャッシュバスター `?v=` の更新も不要
  - レイヤーは domain / infrastructure / template にまたがるが、いずれも
    「ラベル生成関数に渡す値を暦日から日時に差し替える」という単一の変更の波及であり、
    再設計・新ビジネスルールを含まないため spec は新設しない

### 変更方針

`format_stock_as_of_label()`（`domain/value_objects/dates.py`）を `date | datetime` の
両対応に拡張し、ラベル生成元を `stock_as_of_date`（暦日）から `imported_at`（日時）へ差し替える。

- 同ファイルには既に `JST = ZoneInfo("Asia/Tokyo")` があるため、
  **`import django` を増やさずにタイムゾーン変換ができる**（domain の Django 非依存を維持）
- `date` を受け取る分岐は従来の書式のまま残す（後方互換）
- **判定の基準日（`as_of_date`）は暦日のまま変更しない**

### 変更対象ファイル

| # | ファイル | 変更内容 |
|---|---|---|
| 1 | `domain/value_objects/dates.py` | `format_stock_as_of_label` を `date \| datetime` 対応に拡張 |
| 2 | `infrastructure/persistence/slims_stock_repository.py` | ラベル生成の引数を `stock_date` → `import_record.imported_at`（2 箇所）。`stock_as_of_date` は変更しない |
| 3 | `infrastructure/persistence/summary_row_codec.py` | 同上（1 箇所） |
| 4 | `infrastructure/oracle/summary_aggregation.py` | `build_list_rows(stock_as_of_date=...)` に `imported_at` を渡す。`query` の `as_of_date` は変更しない |
| 5 | `domain/value_objects/stock_join.py` | 型注釈を `date \| datetime \| None` に（挙動変更なし） |
| 6 | `domain/value_objects/list_rows.py` | 同上（型注釈のみ） |
| 7 | `templates/inventory_order_alert/list.html` | 見出しと警告バナーを `imported_at` ベースに（`H:i` 付き） |

変更しないもの: `templates/portal/dashboard.html`（`stock_as_of_label` をそのまま出力するため自動で反映）、
`static/js/inventory-order-alert-list.js` / `-list-client.js`、`domain/value_objects/export_csv.py` の列定義、
マイグレーション。

### テスト

| ファイル | 内容 |
|---|---|
| `tests/test_dates.py` | `format_stock_as_of_label` の新規テスト（aware datetime の JST 変換・naive datetime・`date` 後方互換） |
| `tests/test_inventory_order_alert_views.py` | 一覧の見出しと警告バナーに時分が出ることの確認 |

既存テストは変更不要の見込み（`時点の集計結果を表示しています。` はサフィックス一致、
`stockAsOfLabel` のアサートはフィクスチャ値の往復確認であるため）。

### ドキュメント更新

| ファイル | 変更内容 |
|---|---|
| `docs/ubiquitous_language.md` | **T-202 在庫時点** の定義を「最後に取り込んだ暦日」→「最後に取り込んだ日時」に改訂 |
| `docs/在庫発注アラート_機能仕様書.md` | 在庫時点の導出と表示書式、改訂履歴 |
| `docs/在庫発注アラート_テスト仕様書.md` | 該当箇所、改訂履歴 |

### リリース時の注意

| 表示箇所 | 反映タイミング |
|---|---|
| 一覧の見出し・警告バナー・ダッシュボード帯（#1・#2・#3） | **デプロイ直後に反映**（描画時に `imported_at` から生成するため） |
| 詳細ダイアログ・CSV の「在庫時点」（#4・#5） | **SLIMS 在庫 CSV の再取込が必要**（ラベル文字列が集計スナップショットに保存されているため） |

`Document/本番環境デプロイ手順.md` §11.2 のとおり再取込は元々必須であるため、追加作業は発生しない。

## 実施内容 (Do)

- 変更概要:
  - `format_stock_as_of_label()` を `date | datetime` の両対応に拡張し、datetime を渡した場合のみ時分を付ける
    （`date` を渡す既存呼び出しは従来の書式のまま）。`datetime` は `date` のサブクラスなので
    `isinstance(value, datetime)` を先に判定する。タイムゾーン変換は同ファイルに既にある
    `JST = ZoneInfo("Asia/Tokyo")` を使い、**`import django` を増やさずに domain の Django 非依存を維持**した。
  - ラベル生成元を `timezone.localdate(imported_at)`（暦日）から `imported_at`（日時）に差し替えた（3 ファイル・4 箇所）。
  - 一覧テンプレートの見出しと警告バナーを `stock_as_of_date` から `imported_at` に変え、`H:i` を付けた。
  - **判定の基準日（`as_of_date` / `query.as_of_date` / `store_summary_snapshot(as_of_date=...)`）は一切変更していない。**

- 対象ファイル（コード 6 / テンプレート 1）:

  | ファイル | 変更 |
  |---|---|
  | `domain/value_objects/dates.py` | `format_stock_as_of_label` を `date \| datetime` 対応に拡張 |
  | `domain/value_objects/stock_join.py` | 型注釈を `date \| datetime \| None` に（`datetime` の import 追加） |
  | `domain/value_objects/list_rows.py` | 同上（`datetime` の import 追加） |
  | `infrastructure/persistence/slims_stock_repository.py` | ラベル生成元を `imported_at` に（2 箇所） |
  | `infrastructure/persistence/summary_row_codec.py` | 同上（1 箇所） |
  | `infrastructure/oracle/summary_aggregation.py` | `build_list_rows(stock_as_of_date=imported_at)`。`query` は不変 |
  | `templates/inventory_order_alert/list.html` | 見出し・警告バナーを `imported_at` ベースに |

- 追加テスト:
  - `tests/test_dates.py` に 4 件（TC-IOA-SAO-001〜004）
  - `tests/test_inventory_order_alert_views.py` に 2 件（TC-IOA-SAO-005・006）

- ドキュメント: `ubiquitous_language.md`（T-202 を日時に改訂＋改定履歴）、
  `在庫発注アラート_機能仕様書.md`（rev 11.0 → **11.1**。受入基準 C-05・データ鮮度・在庫時点表示・CSV 列定義・
  ダッシュボード帯・取込時の導出・API レスポンス例 2 件・鮮度表示の必須性の計 9 箇所）、
  `在庫発注アラート_テスト仕様書.md`（rev 6.0 → **6.1**、TC-IOA-SAO-* を新設）

- 変更しなかったもの: マイグレーション（`imported_at` は既存）、`templates/portal/dashboard.html`、
  `static/js/inventory-order-alert-list.js` / `-list-client.js`、`domain/value_objects/export_csv.py` の列定義。
  **JS を触っていないためキャッシュバスター `?v=` の更新も不要。**

- コミット: （次のコミットで記入）

## 検証結果 (Check)

- 期待効果の達成: **済**
- テスト結果:
  - 新規 6 件: 通過（Red → Green を確認。実装前は 3 件が `2026年10月29日時点の在庫` を返して失敗）
  - **全件: 2,333 passed（3 分 20 秒）**。既存テストの期待値修正は **0 件**
    （見出しは `時点の集計結果を表示しています。` のサフィックス一致、`stockAsOfLabel` のアサートは
    フィクスチャ値の往復確認であるため影響がなかった）
- 実データでの確認（開発環境、読み取りのみ）:

  ```
  imported_at (UTC保存値)          = 2026-10-29 01:30:06+00:00
  imported_at (日本時間)           = 2026-10-29 10:30:06+09:00
  stock_as_of_date (判定の基準日)  = 2026-10-29        <- 暦日のまま（判定に影響なし）
  stock_as_of_label (表示ラベル)   = 2026年10月29日 10:30 時点の在庫
  ```

  境界値: UTC 20:05 → `2026年10月30日 05:05 時点の在庫`（日本時間で日付が繰り上がる）、
  naive `09:07` → ゼロ埋めで `09:07`、`date` → `2026年10月29日時点の在庫`（後方互換）。

- 既存スナップショットの確認: `snapshot id=29`（2,300 行）の保存済み行ラベルは
  `'2026年10月29日時点の在庫'`（旧形式）のままであることを確認した。
  → **詳細ダイアログと CSV への反映には SLIMS 在庫 CSV の再取込が必要**という対策案の注意事項を裏付けた。

- レビュー結果: Clean Architecture 検証（`config/tests/test_clean_architecture.py`）通過。
  domain に `import django` を持ち込んでいないこと、`composition.py` / `services/` を新設していないことを確認。

## 振り返り・標準化 (Act)

- 標準化した内容:
  - **「表示の粒度」と「判定の粒度」を分けて持つ**という方針を T-202 の補足に明記した。
    在庫時点は表示上は日時だが、判定（V-232 在庫切れ日・V-233 発注期限・V-239 判定ホライズン）は日単位である。
    今後 T-202 を触る際に、表示を細かくした流れで基準日まで日時にしてしまう事故を防ぐ。
  - **ラベル文字列を集計スナップショットに保存している箇所は、デプロイだけでは表示が変わらない**という
    性質を仕様書 rev 11.1 の記述に残した（`Document/本番環境デプロイ手順.md` §11.2 と同じ理由）。
    表示だけの変更でも再取込が要るケースがあることを、今後のリリース判断で見落とさないようにする。
- 反映先: ユビキタス言語（T-202 の補足・改定履歴）、機能仕様書（rev 11.1）、テスト仕様書（rev 6.1）
- 派生Issue: なし

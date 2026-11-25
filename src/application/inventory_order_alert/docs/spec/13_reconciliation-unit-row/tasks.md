文書ID: TASK-RECONCILIATION-UNIT-ROW-2026-001
作成日: 2026/11/25
更新日: 2026/11/25
対応文書: [design.md](./design.md)（DESIGN-RECONCILIATION-UNIT-ROW-2026-001）, [test-design.md](./test-design.md)（TEST-RECONCILIATION-UNIT-ROW-2026-001）

# 13_reconciliation-unit-row タスクリスト

## 状況チェックシート

**凡例**: [ ] 未着手 / [~] 進行中 / [✅YYYY/MM/DD HH:MM] 完了 / [- YYYY/MM/DD HH:MM] スキップ

| # | タスク | レイヤー | 状態 |
|---|--------|---------|------|
| 0 | 変更前の基準値を記録（一覧の配信 JSON の大きさ・照合単位ごとの対応区分・確認記録とメモの件数） | 全体 | [✅2026/11/25 17:35] |
| 1 | 照合単位行へのまとめのテスト作成（TC-RUR-D-001〜025） | domain | [✅2026/11/25 17:38] |
| 2 | `reconciliation_unit_row.py` 新設（`build_reconciliation_unit_rows`・`select_representative`） | domain | [✅2026/11/25 17:38] |
| 3 | 確認状態・メモのまとめのテスト作成（TC-RUR-D-030〜037） | domain | [✅2026/11/25 17:38] |
| 4 | `reconciliation_unit_row.py` に `unit_confirmation`・`merge_memo_entries`、`confirmation.py` の `attach_confirmation_fields` を照合単位行対応に | domain | [✅2026/11/25 17:38] |
| 5 | 絞り込み・選択肢・並べ替えのテスト作成（TC-RUR-D-040〜045） | domain | [✅2026/11/25 17:41] |
| 6 | `list_rows.py`（`filter_summary_rows`）・`list_filter.py`（選択肢）を一覧キー対応に | domain | [✅2026/11/25 17:41] |
| 7 | CSV・配信データ・件数のテスト作成（TC-RUR-D-050〜056） | domain | [✅2026/11/25 17:41] |
| 8 | `export_csv.py`（「、」連結）・`list_client_data.py`（一覧・内訳・行数のキー） | domain | [✅2026/11/25 17:41] |
| 9 | `ports.py` の確認記録・メモのポートを「得意先品番の集合」に | domain | [✅2026/11/25 17:41] |
| 10 | 確認記録の保存・読み込み・リセットのテスト作成（TC-RUR-I-001〜011） | infrastructure | [✅2026/11/25 17:47] |
| 11 | `models.py`（`item_cd` 一意・`entry_group`）とマイグレーションのテスト作成（TC-RUR-I-020〜025） | infrastructure | [✅2026/11/25 17:47] |
| 12 | `migrations/0017_confirmation_per_item.py` 新設（スキーマ変更＋データ移行＋件数照合） | infrastructure | [✅2026/11/25 17:47] |
| 13 | `confirmation_repository.py`（得意先品番キー・一括保存・メモ複製・リセットを照合単位行で判定） | infrastructure | [✅2026/11/25 17:47] |
| 14 | `summary_repository.py`（読み込み順を 在庫 → まとめ → 確認記録 → 流動区分 に） | infrastructure | [✅2026/11/25 17:47] |
| 15 | `summary_aggregation.py`・`use_cases/patch_snapshot_row.py`（確認リセットに照合単位行を渡す） | infrastructure | [✅2026/11/25 17:47] |
| 16 | 確認状態・メモの use case のテスト作成（TC-RUR-A-001〜005） | use_cases | [✅2026/11/25 17:47] |
| 17 | `save_confirmation.py`・`confirmation_memos.py` を照合単位行の得意先品番すべてに書く形に | use_cases | [✅2026/11/25 17:47] |
| 18 | `wiring.py` のポート差し替え | interfaces | [✅2026/11/25 17:47] |
| 19 | 画面・API・CSV のテスト作成（TC-RUR-V-001〜010） | interfaces | [✅2026/11/25 18:03] |
| 20 | `templates/inventory_order_alert/list.html`（得意先別内訳・内示推移の得意先別表の枠） | interfaces | [✅2026/11/25 18:03] |
| 21 | `static/js/inventory-order-alert-list-client.js`（一覧キーでの絞り込み・選択肢・「他 N」の描画） | interfaces | [✅2026/11/25 18:03] |
| 22 | `static/js/inventory-order-alert-list.js`（詳細ダイアログの得意先別内訳・内示推移の得意先別表） | interfaces | [✅2026/11/25 18:03] |
| 23 | 一覧の CSS（「他 N」の印・内訳の表） | interfaces | [✅2026/11/25 18:03] |
| 24 | 既存テストのうち行の単位が変わって期待値が変わるものの改訂、全テスト・アーキテクチャテストの実行 | 全体 | [✅2026/11/25 18:03] |
| 25 | 開発環境で migrate と受け入れ確認（TC-RUR-R-001〜011）・配信データ量の比較 | 全体 | [~] |
| 26 | 機能仕様書・テスト仕様書・用語集の改訂 | docs | [✅2026/11/25 18:06] |

## タスク詳細

### タスク0: 変更前の基準値を記録
- 対象ファイル: なし（結果は本書のタスク実行レポートに記録）
- 内容: 開発環境の最新スナップショットで、(1) 一覧画面に配信している JSON の大きさ、(2) 照合単位ごとの対応区分・在庫切れ日・発注期限、(3) 確認記録とメモの件数を記録する（読み取りのみ）
- 完了条件: 3 つの値が本書に記録されている。(2) はタスク25 で突き合わせるため scratchpad に JSON で保存する

### タスク1: 照合単位行へのまとめのテスト作成
- 対象ファイル: `application/inventory_order_alert/tests/test_reconciliation_unit_row.py`（新規）
- 内容: test-design §2.1 の D-001〜025。テストデータは §3.1 の単位 A・単位 B・単独行 S を辞書ファクトリで作る
- 完了条件: テストが ImportError または期待値の不一致で失敗する（Red）

### タスク2: `reconciliation_unit_row.py` 新設
- 対象ファイル: `application/inventory_order_alert/domain/value_objects/reconciliation_unit_row.py`（新規）
- 内容: design §4.2・§4.4。`ReconciliationUnits.build` で単位を求め、代表の行を選び、合算・重複除去は `stock_simulation` の `pair_keys` と同じ規則で行う。入力の辞書は書き換えない。Django を import しない
- 完了条件: D-001〜025 が通る。`test_clean_architecture.py` が通る

### タスク3: 確認状態・メモのまとめのテスト作成
- 対象ファイル: `tests/test_reconciliation_unit_row.py`（追記）
- 内容: D-030〜037
- 完了条件: Red

### タスク4: 確認状態・メモのまとめの実装
- 対象ファイル: `domain/value_objects/reconciliation_unit_row.py`（追記）、`domain/value_objects/confirmation.py`（`attach_confirmation_fields` と `ConfirmationRecord`）
- 内容: 確認記録の辞書のキーを得意先品番にし、照合単位行の `item_cds` から最も新しく更新された記録を選ぶ。メモは `entry_group`（空なら id）で 1 件にまとめ、新しい順
- 完了条件: D-030〜037 と既存の確認関連テストが通る（既存テストで (得意先, 品番) キーを前提にしているものは、タスク24 で改める旨を記録して一時的に失敗を許す）

### タスク5: 絞り込み・選択肢・並べ替えのテスト作成
- 対象ファイル: `tests/test_reconciliation_unit_row_filters.py`（新規）
- 内容: D-040〜045
- 完了条件: Red

### タスク6: 絞り込み・選択肢の実装
- 対象ファイル: `domain/value_objects/list_rows.py`、`domain/value_objects/list_filter.py`
- 内容: `filter_summary_rows` の得意先・仕入先を一覧キー（`cust_codes`・`level1_vend_cds`）のどれかで一致にする。選択肢は一覧キーの全値から作る。一覧キーのない行（旧データ）は単数キーで判定する
- 完了条件: D-040〜045 が通る

### タスク7: CSV・配信データ・件数のテスト作成
- 対象ファイル: `tests/test_reconciliation_unit_row_outputs.py`（新規）
- 内容: D-050〜056
- 完了条件: Red

### タスク8: CSV・配信データの実装
- 対象ファイル: `domain/value_objects/export_csv.py`、`domain/value_objects/list_client_data.py`
- 内容: CSV の得意先コード・得意先名・担当者コード・得意先品番・仕入先コード・仕入先名・仕入先品番を一覧キーの「、」連結に。配信データに `unitMemberCount`・一覧キー・`customerBreakdown` を足す
- 完了条件: D-050〜056 が通る

### タスク9: ポートの変更
- 対象ファイル: `domain/repositories/ports.py`
- 内容: `SaveConfirmation`・メモの追加・一覧取得・取込後のリセットのポートを、得意先品番の集合を受ける形にする
- 完了条件: 型が design §7 #7 と一致。アーキテクチャテストが通る

### タスク10: 確認記録の保存・読み込み・リセットのテスト作成
- 対象ファイル: `tests/test_confirmation_per_item.py`（新規）
- 内容: I-001〜011
- 完了条件: Red

### タスク11: モデルとマイグレーションのテスト作成
- 対象ファイル: `tests/test_migration_0017_confirmation_per_item.py`（新規）
- 内容: I-020〜025。`MigrationExecutor` で 0016 に戻してデータを作り、0017 へ進める
- 完了条件: Red（0017 がないため）

### タスク12: マイグレーション 0017 新設
- 対象ファイル: `models.py`、`migrations/0017_confirmation_per_item.py`（新規）
- 内容: design §5.1〜5.3。`entry_group` の追加 → データ移行（得意先品番ごとに最新を残す・メモを付け替える・件数を出力し、メモの件数が変わったら例外）→ 一意制約の付け替え。逆方向は制約を戻すだけ
- 完了条件: I-020〜025 が通る。`makemigrations --check` で差分なし

### タスク13: 確認記録の保存の実装
- 対象ファイル: `infrastructure/persistence/confirmation_repository.py`
- 内容: 得意先品番キーでの読み込み（`load_confirmation_map`）、`transaction.atomic` での一括保存、メモの複製（同じ `entry_group`）、`reconcile_confirmations_after_import` を照合単位行の流動区分で判定し単位の全品番を戻す
- 完了条件: I-001〜005・I-010〜011 が通る

### タスク14: 読み込み順の組み替え
- 対象ファイル: `infrastructure/persistence/summary_repository.py`
- 内容: design §3.1 の順（在庫の付与 → まとめ → 確認記録 → 流動区分 → 件数）
- 完了条件: I-006〜008 が通る

### タスク15: 取込後の確認リセットに照合単位行を渡す
- 対象ファイル: `infrastructure/oracle/summary_aggregation.py`、`use_cases/patch_snapshot_row.py`
- 内容: リセットに渡す前に `build_reconciliation_unit_rows` → `apply_flow_quadrants_to_rows`（基準判定条件）を通す
- 完了条件: I-010〜011 と既存の取込・スナップショット修正のテストが通る

### タスク16: use case のテスト作成
- 対象ファイル: `tests/test_reconciliation_unit_row_usecases.py`（新規）
- 内容: A-001〜005。集計の読込・保存ポートは偽物
- 完了条件: Red

### タスク17: use case の実装
- 対象ファイル: `use_cases/save_confirmation.py`、`use_cases/confirmation_memos.py`
- 内容: 受け取った（得意先, 品番）から最新の集計の照合単位行を探し、`item_cds` すべてに保存する。見つからなければ品番 1 件。返す件数は照合単位行で数える
- 完了条件: A-001〜005 が通る

### タスク18: wiring の差し替え
- 対象ファイル: `interfaces/wiring.py`
- 内容: タスク9 のポートに合わせて組み立てを変える
- 完了条件: アーキテクチャテストが通る

### タスク19: 画面・API・CSV のテスト作成
- 対象ファイル: `tests/test_reconciliation_unit_row_views.py`（新規）
- 内容: V-001〜010
- 完了条件: Red

### タスク20: テンプレート
- 対象ファイル: `templates/inventory_order_alert/list.html`
- 内容: 詳細ダイアログに「得意先別内訳」の表と、内示推移の得意先別表の枠を足す
- 完了条件: V-008 が通る

### タスク21: 一覧の JavaScript
- 対象ファイル: `static/js/inventory-order-alert-list-client.js`
- 内容: 得意先・担当者・得意先品番・仕入先品番の絞り込みを一覧キーで判定、選択肢を一覧キーから、表の各セルに「他 N」の印（`title` に全件）
- 完了条件: V-007・V-009・V-010 が通る

### タスク22: 詳細ダイアログの JavaScript
- 対象ファイル: `static/js/inventory-order-alert-list.js`
- 内容: `customerBreakdown` から得意先別内訳・内示推移の得意先別表を描く。得意先が 2 つ以上なら見出しに「得意先 N 社」
- 完了条件: V-008・V-010 が通る

### タスク23: CSS
- 対象ファイル: 一覧の CSS（`static/css/` の在庫発注アラート用）
- 内容: 「他 N」の印・内訳の表の見た目
- 完了条件: 画面で崩れがない（タスク25 で確認）

### タスク24: 既存テストの改訂と全テスト
- 対象ファイル: 既存テストのうち、(得意先, 品番) キーの確認記録や行数を前提にしたもの
- 内容: 期待値を照合単位行に合わせて改める（改めたテストと理由を本書に記録）。全テスト・`test_clean_architecture.py` を実行
- 完了条件: 全テストが通る

### タスク25: 開発環境での受け入れ確認
- 対象ファイル: なし（結果は本書に記録）
- 内容: migrate（0017）を実行し、移行の前後の件数を記録。TC-RUR-R-001〜011。タスク0 の基準値と突き合わせる
- 完了条件: R-001〜011 の結果が記録され、R-010（対応区分が変わらない）・R-009（件数が減らない）を満たす

### タスク26: 文書の改訂
- 対象ファイル: `docs/在庫発注アラート_機能仕様書.md`・`docs/在庫発注アラート_テスト仕様書.md`・`docs/ubiquitous_language.md`
- 内容: 一覧・件数・絞り込み・CSV・確認記録・API の単位が照合単位行になったこと、流動区分を照合単位で判定すること、変更履歴に実測の件数
- 完了条件: 3 文書の更新日・変更履歴が更新されている

## タスク実行レポート

（各タスク完了時にここへ追記する）

--------------------
### タスク0 実行レポート（2026/11/25 17:35）

開発環境の最新スナップショット（取込 ID 34・2026/11/25 15:48・1,996 行・1,726 照合単位）で測った（読み取りのみ）。

| 基準値 | 値 |
|---|---|
| 一覧画面の HTML | 20,666,798 バイト |
| うち配信データ（JSON） | **20,254,152 バイト** |
| 確認記録 / 確認メモ | 1 件 / 1 件 |
| 照合単位ごとの対応区分・在庫切れ日・発注期限 | scratchpad `baseline_13.json` に保存（タスク25 で突き合わせる） |

- 懸念事項: 配信データが約 20 MB ある。NF-003（増やさない）はこの値と比べる
- チーム共有ポイント: 確認記録は開発環境では 1 件しかないため、移行の検証はテストデータで行う
--------------------

--------------------
### タスク1〜4 実行レポート（2026/11/25 17:38）

`tests/test_reconciliation_unit_row.py`（D-001〜025・D-030〜037 の 33 件）を先に書き、読み込みエラーで失敗することを確かめてから（Red）、`domain/value_objects/reconciliation_unit_row.py` を新設し、`confirmation.py` を改修して通した（Green）。タスク1・3 のテストは同じファイルにまとめて書いた。

- 設計からの変更: `unit_confirmation`・`merge_memo_entries` は `confirmation.py` に置いた（`attach_confirmation_fields` から使うため。`reconciliation_unit_row.py` に置くと循環 import になる）。`reconciliation_unit_row.py` からも読み込めるようにしてある
- `ConfirmationRecord` に `updated_at`、`MemoEntryRecord` に `entry_group`・`entry_id` を既定値付きで足した
- `attach_confirmation_fields` の確認記録の辞書は得意先品番キーに変わった。既存の呼び出し（`summary_repository.py`）と既存テストはタスク14・24 で直す
- 懸念事項: 単位内に確認記録が 1 件だけなら、その記録の `memo_history`（作成者名を解決済み）をそのまま使う。2 件以上なら `author_names` を渡されないと作成者がユーザー名のまま出る。タスク13 でリポジトリから名前を渡す
--------------------

--------------------
### タスク5〜9 実行レポート（2026/11/25 17:41）

- タスク5・6: `tests/test_reconciliation_unit_row_filters.py`（D-040〜045）で Red を確かめ、`list_rows.filter_summary_rows`（一覧キーのどれかで一致）・`list_filter.build_filter_options`（得意先別内訳と仕入先品番の一覧から選択肢を作る）を改修して通した
- タスク7・8: `tests/test_reconciliation_unit_row_outputs.py`（D-050〜056）で Red は D-051（CSV の連結）だけだった。配信データは行の全キーをそのまま写す作り（`row_to_client_dict`）のため、照合単位行の一覧キー・内訳は手を入れなくても配信される。`export_csv.py` に複数値の列の「、」連結を足して通した
- タスク9: ポートは既存の引数を残し、`item_cds` を既定値付きで足した（偽物・既存の呼び出しを壊さない）
- **設計からの変更**: 配信データの一覧キーは design §6.1 の camelCase（`custCodes` など）ではなく、行のキーの snake_case（`cust_codes`・`customer_breakdown`・`unit_member_count` など）のまま使う。行の全キーが snake_case で写されるため、camelCase の別名を足すと同じ値を二重に配信し、NF-003（配信データ量）に反する。design.md・test-design.md（D-053）をタスク26 で直す
- 懸念事項: 配信データは行の全キーを写すため、`customer_breakdown` の月次系列がそのまま増える。量はタスク25 で測る
--------------------

--------------------
### タスク10〜18 実行レポート（2026/11/25 17:47）

- タスク10・11: `tests/test_confirmation_per_item.py`（I-001〜011）・`tests/test_migration_0017_confirmation_per_item.py`（I-020〜025）を書き、Red を確かめた
- **テスト方式の変更（I-020〜025）**: テストのスキーマはマイグレーションを使わずモデルから作る（ルート `conftest.py` の `django_db_use_migrations = False`）ため、0016 に戻して重複した記録を作る方式（test-design §5.2）は使えなかった。移行の判断を DB 非依存の関数 `plan_confirmation_merge`（migration 0017 内）に切り出してテストし、一意制約は今のモデルで確かめる形に改めた。実際の移行はタスク25 で開発 DB に migrate して確かめる。この書き直したテストはマイグレーション本体と同時に書いたため、関数単位の Red は踏めていない
- タスク12: `models.py`（得意先品番で一意・`entry_group`）と `migrations/0017_confirmation_per_item.py`（`entry_group` 追加 → 移行 → 一意制約の付け替え。メモの件数が変わったら例外）。`makemigrations --check` で差分なし
- タスク13: `confirmation_repository.py` を書き直した（得意先品番キー・`transaction.atomic` での一括保存・メモの複製と `entry_group`・照合単位行の流動区分でのリセット・`memo_author_names`）
- タスク14: `summary_repository.py` の読み込み順を「在庫 → まとめ → 確認記録 → 流動区分 → 件数」にした
- タスク15: 両方の呼び出し元で使う `list_rows.unit_rows_with_reference_flow` を domain に足し、`summary_aggregation.py`・`use_cases/patch_snapshot_row.py` から使う
- タスク16〜18: `tests/test_reconciliation_unit_row_usecases.py`（A-001〜005）で Red を確かめ、`save_confirmation.py`・`confirmation_memos.py`（`load_summary` を任意の引数で受ける）・`wiring.py` を直した。照合単位行を探す `find_unit_row`・`unit_item_cds_for` を `reconciliation_unit_row.py` に足した
- **タスク6 の漏れ**: サーバ側の絞り込みがもう 1 つ（`list_filter.apply_list_filters`。一覧画面の描画と保存後の件数で使う）あり、照合単位行の値で当たるように直した。テスト D-040b は実装の後に足したため Red は踏めていない
- 懸念事項: `ConfirmationMemos` は `load_summary` を毎回呼ぶ（スナップショットの読み込み＋まとめ）。メモの一覧・追加が少し重くなる
--------------------

--------------------
### タスク19〜24 実行レポート（2026/11/25 18:03）

- タスク20〜23 を先に実装し、タスク19 のテスト（`tests/test_reconciliation_unit_row_views.py` V-001〜010）を後から書いた。**画面・JS の部分は TDD の順（Red → Green）を踏めていない**
- タスク20: `list.html` の詳細ダイアログに「得意先別内訳」の表（得意先・得意先品番・担当者コード・出荷数合計・最終出荷日・内示推移（月別））を足した
- タスク21: `inventory-order-alert-list-client.js` に一覧キーでの絞り込み（`unitValues`・`matchesAnyPrefix`）、担当者→得意先の連動の材料を得意先別内訳に展開（`memberRows`。共通の `portal-list-dependent-cust-filter.js` は変えていない）、「他 N」の印（`renderUnitMore`）、`getCustomerBreakdown` を足した
- タスク22: `inventory-order-alert-list.js` に `renderCustomerBreakdown`（得意先が 2 社以上なら見出しに「得意先 N 社」）
- タスク23: `static/css/app.css` に「他 N」の印・内訳の表
- **テスト設計の誤り（V-004）**: CSV は絞り込みを反映せず常に全件を出す仕様（design.md §6.3 既存）だったため、V-004 は「サマリ API を代表でない得意先で絞る」に改めた
- タスク24（全テスト 2,505 件が通った。アーキテクチャテストを含む）:
  - **実装の不具合を 1 つ直した**: 1 行だけの照合単位までまとめ直していたため、旧スナップショットで `mari_stock_qty`・`shipment_trend` のキーを新しく作って「未取得」の区別を消し、推移の並び順も変えていた（`test_summary_storage.py` 3 件・`test_snapshot_patch.py`・`test_confirmation_save_result.py` 2 件が検出）。1 行の単位は元の行をそのまま使い、2 行以上でもどの行にもないキーは作らないようにした
  - 期待値を改めた既存テスト: `test_domain_confirmation.py::test_load_confirmation_map_includes_memo_history`（確認記録の辞書のキーが得意先品番になった）、`test_inventory_order_alert_views.py`（10 件。テストデータの複数行が同じ仕入先品番を共有して 1 つの照合単位にまとまったため、ファイル内の保存関数で行ごとに仕入先品番を分け、件数・並び替え・ページ送りの意図を保った。期待値そのものは変えていない）
  - タスク6 の追加分（`apply_list_filters`）は前回レポートのとおり
- 懸念事項: 画面の見た目（「他 N」の印・内訳の表）はテストでは文字列しか確かめていない。タスク25 で実際に開いて確かめる
--------------------

--------------------
### タスク25 実行レポート（2026/11/25 18:06・進行中）

開発 DB に migration 0017 を適用した（確認記録 1 件 → 1 件・確認メモ 1 件 → 1 件）。タスク0 と同じ取込（ID 34・2026/11/25 15:48）で確かめた。

| TC | 結果 |
|---|---|
| R-001 | ✅ 一覧 1,726 行（照合単位の数と一致）。`total_count` も 1,726 |
| R-002 | ✅ `90361-18001` は 1 行。代表 104 トヨタ紡織、得意先 104・176 |
| R-003 | ✅ サマリ API を 104・176 のどちらで絞っても出る |
| R-004 | ✅ 得意先別内訳 2 件（104 出荷数合計 27,000・176 は 0） |
| R-005 | ✅ 配信したグラフの材料で 2026/12/10 に 0 を下回り、在庫切れ日と一致 |
| R-006 | ✅ 要対応 192（発注遅れ 37・納期確認 93・要発注 59・要監視 3）。アラート帯も 37・59・93 で一致 |
| R-007 | ✅ CSV 1,726 行。複数の得意先は「、」で連結 |
| R-008 | 未実施（自動テスト I-006・D-031〜033 で担保。実地の再取込は利用者の確認待ち） |
| R-009 | ✅ 移行の前後で確認記録・メモの件数が変わらない（開発環境は 1 件ずつ） |
| R-010 | ✅ 照合単位 1,726 件すべてで対応区分・在庫切れ日・発注期限が変更前と一致 |
| R-011 | ⚠️ 配信データ 20,254,152 → 20,635,327 バイト（+381,175・+1.9%）。目安（上回らない）を超えた |

- 流動区分（照合単位行で判定）: 通常流動品 828・低流動品（入荷なし）216・在庫死蔵品 305・打ち切り候補 251・欠品 71・欠品（入荷なし）47・低流動品（出荷なし）8
- 懸念事項: R-011。得意先別内訳の月次系列と一覧キーが増えた分。行が減っても行の全キーを写す作りのため相殺しきれない。減らすなら得意先別内訳を詳細ダイアログを開いたときの別 API に移す（design §6.1 の案）
- 残り: 画面の見た目（「他 N」の印・得意先別内訳の表）の目視確認、再取込後の確認状態（R-008）
--------------------

--------------------
### タスク26 実行レポート（2026/11/25 18:06）

- 機能仕様書 rev 13.0（REQ-F-018・保存キー・§8.1／§8.3／§8.5／§8.6・変更履歴）、テスト仕様書 rev 8.0（TC-IOA-RUR-001〜003・変更履歴）、用語集（E-201 の保存キー）を改訂した
- design.md に §10「実装時の改訂」（配信キー名・1 行の単位はそのまま・関数の置き場所・`apply_list_filters`・データ量）、test-design.md に §6（D-053・D-040b・V-004・I-020〜025 の方式）を追記した
--------------------

--------------------
### R-011 の判断（2026/11/25 18:10）

配信データ量の増加（+1.9%・20,635,327 バイト）は**このまま受け入れる**（Hashizume 判断）。得意先別内訳を別 API に移す対応は行わない。
--------------------

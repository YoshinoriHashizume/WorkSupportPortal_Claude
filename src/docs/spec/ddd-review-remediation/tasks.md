# DDD レビュー指摘 是正タスク

| 項目 | 内容 |
|---|---|
| 文書ID | TASK-DDD-REVIEW-REMEDIATION-2026-001 |
| 作成日 | 2026/08/25 |
| 更新日 | 2026/08/25 |
| 対応文書 | `docs/strategic_design.md`（SD-WORK-SUPPORT-PORTAL-2026-001） |
| 起点 | 2026/08/25 実施の DDD 設計レビュー（指摘 D-1〜D-9 / S-1〜S-4） |

---

## 1. 方針（ユーザー確定事項 2026/08/25）

| 決定事項 | 選択 |
|---|---|
| 共通VO（prefix_filter / code_sort / dependent_cust_filter / list_table）の置き場 | **`application/shared/` を新設して移設** |
| Oracle 例外（OracleNotConfiguredError / OracleQueryError）の置き場 | **`application/sales/` へ移設** |
| portal → inventory_order_alert の双方向依存 | **wiring（合成ルート）は許可・infrastructure からの参照は除去** |
| D-2（dict 主役データ）/ D-6（表示関心事の domain 混入）| **今回は対象外。Issue 起票して別途 SDD フローで対応** |

---

## 2. スコープ

### 今回実施する指摘

| 指摘 | 概要 | 対応 |
|---|---|---|
| S-1 | 共有カーネル外の相互参照 | shared 新設 + sales へ例外移設 |
| S-2 | portal ↔ inventory_order_alert 双方向依存 | infra 側の直参照を除去、wiring は文書で正式に許可 |
| S-3 | `application/identity/` が戦略的設計書に無い | 文書へコンテキスト I として追記（コードは現状維持） |
| S-4 | コンテキスト境界を守るテストが無い | `test_clean_architecture.py` にホワイトリスト方式の境界テストを追加 |
| D-3 | VO が不変条件を守っていない | `AppSettings.__post_init__` 追加、リポジトリ側もクランプ |
| D-4 | `ComparisonRow` が VO ではなくエンティティ | `domain/entities/` へ移設 |
| D-7 | ポートがドメインの語彙を持たない | `object` 型エイリアスを実型へ |
| D-8 | 業務ルールがユースケース層にある（3重複） | domain へ集約 |
| D-1 | エンティティ 0 個 | D-4 により receipt_comparison で部分解消。残りは Issue |

### 今回実施しない指摘（Issue 起票）

| 指摘 | 理由 |
|---|---|
| D-1（残） | D-2 と不可分。コア文脈から段階的に対応 |
| D-2 | 全域 126 箇所。summary / snapshot / CSV / テンプレートまで波及 |
| D-6 | display 系 VO 十数本の移設。影響範囲が大きい |
| （追加）`portal/domain/value_objects/constants.py` が `RECEIPT_COMPARISON_PATH` 等コア文脈Aの知識を持つ | D-6 と同種。Issue に含める |

---

## 3. タスク一覧

### Phase 1: 戦略的設計の是正（S-1 / S-2 / S-3 / S-4）

| # | タスク | 対象ファイル | 種別 |
|---|---|---|---|
| T-1 | `application/shared/` パッケージ新設 | `shared/__init__.py`, `shared/domain/__init__.py`, `shared/domain/value_objects/__init__.py`, `shared/tests/__init__.py` | 新規4 |
| T-2 | 共通VO 4本を shared へ移設 | `shared/domain/value_objects/{prefix_filter,code_sort,dependent_cust_filter,list_table}.py` | 新規4 |
| T-3 | portal から旧4本を削除 | `portal/domain/value_objects/{prefix_filter,code_sort,dependent_cust_filter,list_table}.py` | **削除4** |
| T-4 | 参照元の import を shared へ変更 | `asset_inventory/domain/value_objects/list_filter.py`<br>`inventory_order_alert/domain/value_objects/code_sort.py`<br>`inventory_order_alert/domain/value_objects/list_filter.py`<br>`shipment_trend/domain/value_objects/list_filter.py`<br>`shipment_trend/domain/value_objects/table_display.py`<br>`shipment_trend/use_cases/list_page.py` | 修正6 |
| T-5 | 該当テストを shared へ移設 | `portal/tests/{test_prefix_filter,test_code_sort,test_dependent_cust_filter,test_list_table}.py` → `shared/tests/` | 移動4 |
| T-6 | sales に Oracle 例外を新設 | `sales/domain/__init__.py`, `sales/domain/value_objects/__init__.py`, `sales/domain/value_objects/errors.py` | 新規3 |
| T-7 | gonenkukumi の errors から例外定義を削除 | `gonenkukumi/domain/value_objects/errors.py`（`NAISAK_NOT_FOUND` と `oracle_error_message` は残す） | 修正1（**定義削除**） |
| T-8 | gonenkukumi 側の import を sales へ | `gonenkukumi/infrastructure/oracle/client.py`<br>`gonenkukumi/infrastructure/oracle/customers.py`<br>`gonenkukumi/use_cases/search_page.py`<br>`gonenkukumi/interfaces/views.py`<br>`gonenkukumi/tests/{test_gonenkukumi_application,test_gonenkukumi_domain_errors,test_gonenkukumi_views}.py` | 修正7 |
| T-9 | receipt_comparison 側の import を sales へ（コアA→支援C の逆依存を解消） | `receipt_comparison/infrastructure/oracle/receipt_choices.py`<br>`receipt_comparison/infrastructure/oracle/vendors.py`<br>`receipt_comparison/use_cases/compare.py`<br>`receipt_comparison/use_cases/register.py` | 修正4 |
| T-10 | sales 自身の import を自前へ | `sales/infrastructure/oracle/client.py` | 修正1 |
| T-11 | portal infra からの他文脈モデル直参照を除去 | `portal/infrastructure/persistence/user_bootstrap_repository.py`（`_ensure_ioa_settings_row` **削除**・呼び出し2箇所削除） | 修正1（**関数削除**） |
| T-12 | コンテキスト境界テストを追加 | `config/tests/test_clean_architecture.py` | 修正1 |

### Phase 2: 戦術的設計の局所是正（D-3 / D-4 / D-7 / D-8）

| # | タスク | 対象ファイル | 種別 |
|---|---|---|---|
| T-13 | 在庫鮮度判定を domain へ集約 | `inventory_order_alert/domain/value_objects/dates.py` に `is_stock_stale()` 追加 | 修正1 |
| T-14 | 3重複したユースケース内実装を置換 | `inventory_order_alert/use_cases/list_page.py`（`_is_stock_stale` **削除**）<br>`inventory_order_alert/use_cases/summary_api.py`（`_is_stale` **削除**）<br>`inventory_order_alert/use_cases/portal_dashboard.py`（インライン式を置換） | 修正3 |
| T-15 | `AppSettings` に不変条件を持たせる | `inventory_order_alert/domain/value_objects/app_settings.py`（`__post_init__` 追加） | 修正1 |
| T-16 | リポジトリ側も全項目クランプ | `inventory_order_alert/infrastructure/persistence/settings_repository.py` | 修正1 |
| T-17 | shipment_trend の `AppSettings` も同様 | `shipment_trend/domain/value_objects/app_settings.py` | 修正1 |
| T-18 | `ComparisonRow` をエンティティへ移設 | `receipt_comparison/domain/entities/comparison_row.py` | 新規1 |
| T-19 | 参照元の import を entities へ変更 | `receipt_comparison/domain/value_objects/comparison.py`（定義**削除**）<br>`domain/value_objects/comparison_display.py`<br>`domain/repositories/ports.py`<br>`infrastructure/oracle/client.py`<br>`infrastructure/persistence/comparison_result_repository.py`<br>`infrastructure/session/pending_comparison_session.py`<br>`infrastructure/session/pending_comparison_store.py`<br>`use_cases/compare.py`<br>`tests/{test_receipt_comparison,test_receipt_comparison_pending}.py` | 修正10 |
| T-20 | shipment_trend のポートに実型を付ける | `shipment_trend/domain/repositories/ports.py` | 修正1 |
| T-21 | inventory_order_alert のポートに実型を付ける | `inventory_order_alert/domain/repositories/ports.py` | 修正1 |

### Phase 3: 文書更新と Issue 起票

| # | タスク | 対象ファイル | 種別 |
|---|---|---|---|
| T-22 | 戦略的設計書を更新 | `docs/strategic_design.md`<br>・§3 にコンテキスト I（アイデンティティ）を追加<br>・§3.1 共有カーネルを刷新（shared / sales Oracle 例外 / identity desknet ACL / favorites 公開関数）<br>・§4 に「wiring は合成ルートとして例外的に全文脈を参照してよい」を明記<br>・改訂履歴に追記 | 修正1 |
| T-23 | 残指摘を Issue 起票 | `manage-issue` スキルで D-1（残）/ D-2 / D-6 / portal constants を起票 | 新規 |

---

## 4. 影響範囲

| 区分 | 件数 |
|---|---|
| 新規ファイル | 12 |
| 削除ファイル | 4（portal 共通VO） |
| 移動ファイル | 4（portal テスト → shared テスト） |
| 修正ファイル | 40 |
| 既存コードの削除 | `_ensure_ioa_settings_row`（portal）/ `_is_stock_stale`（list_page）/ `_is_stale`（summary_api）/ `ComparisonRow` 定義（comparison.py）/ `OracleNotConfiguredError`・`OracleQueryError` 定義（gonenkukumi errors.py） |

**振る舞いへの影響**: 原則なし（移設・型付け・重複排除が中心）。ただし次の2点は挙動が変わりうる。

1. **T-11**: `_ensure_ioa_settings_row` 削除により、ブートストラップ時点では在庫発注アラートの設定行が作られなくなる。`load_app_settings()` が `get_or_create(pk=1)` するため初回アクセス時に自動生成される（既存動作と等価）。
2. **T-15 / T-16 / T-17**: 範囲外の設定値が DB に入っている場合、これまでそのまま返っていたものがクランプされる。仕様（§13.1・§8.10）の範囲に収束させる意図的な変更。

**テスト**: 現行 1038 passed / clean-architecture 58 passed を基準とし、各 Phase 完了時に全件実行する。

---

## 5. 実行順序

Phase 1 → 全件テスト → Phase 2 → 全件テスト → Phase 3 → 全件テスト。
Phase 1 の T-12（境界テスト）は T-1〜T-11 の完了後に追加する（先に入れると既存違反で失敗するため）。

---

## 6. 実行レポート

実施日: 2026/08/25

### 6.1 結果

| Phase | 内容 | テスト |
|---|---|---|
| Phase 1 | T-1〜T-12 完了 | 全件 1050 passed / clean-architecture 69 passed |
| Phase 2 | T-13〜T-21 完了 | 全件 1050 passed |
| Phase 3 | T-22・T-23 完了 | 全件 1050 passed |

テスト件数は 1038 → 1050（+12）。境界テストは 58 → 69（+11）。
差分はすべて新規追加分で、既存テストの削除・スキップは無い。

### 6.2 計画からの差分

| # | 差分 | 対応 |
|---|---|---|
| 1 | T-8 の `sed` が一部ファイルで空振りした。原因は CRLF 改行（`.gitattributes` 正規化コミットの残り） | 既存の改行コードを保持する Python スクリプトへ切り替えて再実行 |
| 2 | T-19 で `comparison.py` の `ReceiptFlag` import を巻き添えで削除しかけた（同ファイル内で使用中） | import を復活。未使用となった `dataclass` は AST で確認してから削除 |
| 3 | T-21 の実施中、ポート定義がユースケース層（`use_cases/save_alert_settings.py`）にあることを発見 | `SaveWarningMonthSettings` を `domain/repositories/ports.py` へ移し、Protocol として定義 |
| 4 | `sales/infrastructure/oracle/client.py` が gonenkukumi の 978 行のクライアントを re-export しているだけと判明 | 承認スコープ外のため接続プリミティブの移設は見送り。`KNOWN_CONTEXT_LEAKS` に登録し、ISSUE-GNK-IMP-2026-001 として起票 |
| 5 | T-22 で、コンテキスト F の責務が identity 新設により実態とずれていることが判明 | F を「アクセス管理」に限定し、認証を新コンテキスト I として分離（strategic_design.md 1.1） |

### 6.3 起票した Issue（T-23）

| 文書ID | 対象 | 内容 | 優先度 |
|---|---|---|---|
| [ISSUE-IOA-IMP-2026-001](../../../application/inventory_order_alert/docs/issues/ISSUE-0001-dict-centric-domain-model.md) | 在庫発注アラート（横断） | D-1（残）＋ D-2。`dict[str, object]` 中心のドメインモデル | 中 |
| [ISSUE-IOA-IMP-2026-002](../../../application/inventory_order_alert/docs/issues/ISSUE-0002-presentation-concerns-in-domain.md) | 在庫発注アラート（横断） | D-6 ＋ `portal/domain/value_objects/constants.py` のコンテキストA依存 | 低 |
| [ISSUE-GNK-IMP-2026-001](../../../application/gonenkukumi/docs/issues/ISSUE-0001-oracle-primitives-not-in-sales.md) | 5年9組 | Oracle 接続プリミティブが共有カーネル（sales）に無い | 中 |

### 6.4 未対応として残したもの

- `application/*/use_cases/` に残る 11 本の `Callable` 型エイリアス（`asset_inventory/use_cases/fetch_attachment.py`、`inventory_order_alert/use_cases/` の 8 本、`portal/use_cases/bootstrap_*.py` の 2 本）。
  D-7 と同種だが、今回の承認変更対象リストに含まれないため手を付けていない。
  → **2026/08/25 に追加承認を受け、§7 の Phase 4 として実施済み（残 0 本）。**


---

## 7. 追加スコープ: Phase 4（D-7 残件 — ユースケース層のポート定義移設）

**承認**: 2026/08/25（「対応して」）。名前衝突の解消方針はユーザー選択により
**ユースケースクラスをリネームする**（ポート名 `SaveConfirmation` をドメインに残す）。

### 7.1 方針

- ポート（依存の抽象）はドメインの持ち物。`use_cases/` に定義された `Callable` 型エイリアスは
  該当アプリの `domain/repositories/ports.py` へ移し、`typing.Protocol` として再定義する
- `Callable[..., X]` の `...` は引数を検査しない。実装側の実シグネチャに合わせてキーワード引数まで記述する
- 実行時の振る舞いは変えない（Protocol は構造的部分型。`isinstance` 判定には使わない）

### 7.2 タスク一覧

| ID | 対象ファイル | 内容 |
|---|---|---|
| T-24 | `asset_inventory/domain/repositories/ports.py` | `FetchAttachmentFn` を Protocol で**追加**（`*, source_url, access_key, timeout` → `tuple[bytes, str]`） |
| T-25 | `asset_inventory/use_cases/fetch_attachment.py` | エイリアス `FetchAttachmentFn` を**削除**し ports から import |
| T-26 | `inventory_order_alert/domain/repositories/ports.py` | 8 本のポートを**追加**（下表 7.3） |
| T-27 | `inventory_order_alert/use_cases/import_stock.py` | `StockImporter` を**削除**。戻り値を `Any` → `StockImportInfo` に是正 |
| T-28 | `inventory_order_alert/use_cases/confirmation_memos.py` | `ListConfirmationMemos` / `AddConfirmationMemo` / `ResolveUserDisplayNames` を**削除** |
| T-29 | `inventory_order_alert/use_cases/patch_snapshot_row.py` | `ReconcileConfirmationsAfterImport` を**削除** |
| T-30 | `inventory_order_alert/use_cases/list_page.py` | `HasResettableConfirmations` を**削除** |
| T-31 | `inventory_order_alert/use_cases/reset_confirmations.py` | `ResetAllConfirmations` を**削除** |
| T-32 | `inventory_order_alert/use_cases/save_confirmation.py` | `SaveConfirmation` エイリアスを**削除**。ユースケースクラスを `SaveConfirmationUseCase` に**改名** |
| T-33 | `inventory_order_alert/interfaces/wiring.py` | 改名したユースケースクラスの参照を追随 |
| T-34 | `portal/domain/repositories/ports.py` | `BootstrapLocalDevRunner` / `BootstrapProductionAdminRunner` を Protocol で**追加** |
| T-35 | `portal/use_cases/bootstrap_local_dev.py` / `bootstrap_production_admin.py` | エイリアスを**削除**し ports から import |

### 7.3 在庫発注アラートのポート定義（T-26）

| ポート名 | 実装 | シグネチャ |
|---|---|---|
| `StockImporter` | `slims_stock_repository.import_slims_csv_text` | `(text: str, *, user, file_name) -> StockImportInfo` |
| `HasResettableConfirmations` | `confirmation_repository.has_resettable_confirmations` | `() -> bool` |
| `SaveConfirmation` | `confirmation_repository.save_confirmation` | `(input_data, *, confirmed_by, alert_level) -> ConfirmationRecord` |
| `ListConfirmationMemos` | `confirmation_repository.list_confirmation_memos` | `(*, cust_code, item_cd) -> list[dict[str, str]]` |
| `AddConfirmationMemo` | `confirmation_repository.add_confirmation_memo` | `(*, cust_code, item_cd, content, created_by) -> MemoEntryRecord` |
| `ResolveUserDisplayNames` | `user_display_repository.resolve_user_display_names` | `(usernames: set[str]) -> dict[str, str]` |
| `ReconcileConfirmationsAfterImport` | `confirmation_repository.reconcile_confirmations_after_import` | `(rows: list[dict[str, object]]) -> int` |
| `ResetAllConfirmations` | `confirmation_repository.reset_all_confirmations` | `() -> int` |

### 7.4 併せて是正する型の誤り

| # | 箇所 | 誤り | 是正 |
|---|---|---|---|
| 1 | `save_confirmation.py:17` / `:64` | ポート型エイリアス `SaveConfirmation` が同名のユースケースクラスに上書きされ、`__init__` の引数注釈が自クラスを指す自己参照になっていた | ポートをドメインへ移設し、クラスを `SaveConfirmationUseCase` に改名 |
| 2 | `save_confirmation.py:17` | 戻り値 `None`。実装は `ConfirmationRecord` を返す | ポート定義で `ConfirmationRecord` に是正 |
| 3 | `import_stock.py:8` | 戻り値 `Any`。実装は `StockImportInfo` を返す | ポート定義とユースケースの `execute` を `StockImportInfo` に是正 |

### 7.5 検証

- `pytest`（全件）が 1050 passed を維持すること
- `config/tests/test_clean_architecture.py` が 69 passed を維持すること
- `application/*/use_cases/` に `Callable` 型エイリアスのポート定義が残っていないこと

### 7.6 実行レポート（2026/08/25）

| 項目 | 結果 |
|---|---|
| T-24〜T-35 | 全て完了（12 ファイル） |
| `pytest`（全件） | **1050 passed**（Phase 3 時点と同数。増減なし） |
| `application/*/use_cases/` の `Callable` 型エイリアス | **0 本**（11 本すべて移設） |

**計画からの差分**

| # | 差分 | 対応 |
|---|---|---|
| 1 | 実行時に `application/asset_inventory/tests/test_asp_import.py` と `test_usecase_export_asp_import.py` が収集エラー（`use_cases.export_asp_import` が存在しない）。いずれも本タスク開始後に別途追加された未追跡ファイルで、Phase 4 の変更対象外 | 2 ファイルを `--ignore` して計測。本件のスコープ外として未対応のまま残す |
| 2 | `patch_snapshot_row.py` / `list_page.py` / `reset_confirmations.py` は `Callable` の用途がポート定義のみだったため、`collections.abc.Callable` の import も併せて削除 | AST で未使用を確認してから削除 |
| 3 | `asset_inventory/use_cases/fetch_attachment.py` の `__all__` が `FetchAttachmentFn` を公開している | ports からの import に切り替えたうえで `__all__` はそのまま維持（再エクスポートとして機能） |

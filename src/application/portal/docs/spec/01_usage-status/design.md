# 機能設計書: 利用状況

文書ID: DESIGN-USAGE-STATUS-2026-001
作成日: 2026/08/27
更新日: 2026/08/27
対応文書: [requirements.md](./requirements.md)（REQ-USAGE-STATUS-2026-001）／[ubiquitous_language.md](../../ubiquitous_language.md)（UL-PORTAL-2026-001）／[ubiquitous_language_core.md](../../../../../docs/ubiquitous_language_core.md)（UL-CORE-2026-001）／[strategic_design.md](../../../../../docs/strategic_design.md)（SD-WORK-SUPPORT-PORTAL-2026-001 v1.3）
アーキテクチャreference: django-clean-architecture version 1.0

---

## 1. 設計の目的

要件定義書 REQ-USAGE-STATUS-2026-001 が求める次の 2 つを、`application/portal/` の内部だけで実現する。

| # | 実現すること | 対応要件 |
|---|---|---|
| 1 | **利用記録（A-601）** — ポータルの画面表示と出力操作を、メニュー利用ログ（E-601）として自動的に 1 件ずつ記録する | REQ-F-001〜REQ-F-004 |
| 2 | **利用状況（T-601）画面** — 管理者が集計期間（V-602）を指定して、メニュー別・ユーザー別の利用状況と出力操作の記録を確認する | REQ-F-005〜REQ-F-016 |

技術的な要点は次の 4 点である。

1. **記録は横断的関心事としてミドルウェアで捕捉する。** 各業務コンテキストの view に記録処理を書き加えない（REQ-NF-006）。
2. **記録対象の判別はドメインの純関数に置く。** パス → メニューキー（V-601）の対応と出力エンドポイント一覧を `domain/value_objects/` に定義し、テストで固定する（REQ-NF-008）。
3. **記録の失敗は業務操作を止めない。** ミドルウェアはレスポンス確定後に記録し、例外を捕捉して握りつぶす（REQ-F-004）。
4. **無期限に増え続けるログを、集計期間の必須指定と複合索引で捌く。** 全期間を走査する経路を作らない（REQ-NF-002・REQ-NF-004）。

---

## 2. 対象コンテキスト

`docs/strategic_design.md`（v1.3）に基づく位置づけ。

| 項目 | 内容 |
|---|---|
| 境界コンテキスト | **G: ポータル基盤**（`application/portal/`） |
| サブドメイン分類 | **汎用サブドメイン** |
| 責務（v1.3 で追記済み） | メニュー提示、お気に入り、お知らせ、データベース管理画面に加え、**メニュー利用ログの記録と利用状況の集計**（`docs/strategic_design.md` §3 と同一表記） |
| 他コンテキストとの関係 | `docs/strategic_design.md` §4.1 のとおり **G が上流・A〜E が下流の順応者（Conformist）**。メニュー利用ログの記録は G が一括して担い、各アプリは記録処理を持たない（REQ-NF-006）。出力エンドポイントの把握（§4.4(b)）では G が各アプリの URL 構成を読み取るが、**各アプリに変更を要求しない**ことでこの上流／下流の向きを保つ |

### 2.1 コンテキスト境界の守り方

- 記録するのは **メニューキー・利用種別・ユーザー・利用日時の 4 項目のみ**（REQ-F-001・REQ-NF-005）。業務データ（絞り込み条件・出力件数・出力内容）は記録しないため、業務コンテキストのドメインが portal に漏れない。
- portal は他コンテキストのモジュールを import しない。**パス文字列とメニュー定義（`domain/value_objects/menu.py`）だけを手がかりに判別する。**
- 他コンテキストからも portal を import させない。5 つの業務アプリのコードは **1 行も変更しない**（REQ-NF-006・REQ-F-003）。
- 一覧の並び替え・ページングは共有カーネル `application/shared/domain/value_objects/list_table.py` を用いる（`config/tests/test_clean_architecture.py` の `SHARED_KERNEL_PREFIXES` に登録済み）。

---

## 3. アーキテクチャ概要

### 3.1 レイヤー構成

```
interfaces/
  usage_logging.py      UsageLoggingMiddleware（記録の捕捉）
  views.py              usage_status_page / usage_status_export_csv
  urls.py               /app/management/usage-status[.export.csv]
  wiring.py             組み立て（唯一の組み立て地点）
        │
        ▼
use_cases/
  record_usage.py       RecordUsage（利用記録・A-601）
  usage_status.py       UsageStatus（画面・CSV）
        │
        ▼
domain/
  entities/menu_usage_log.py            MenuUsageLog（E-601）
  value_objects/usage_record.py         UsageType / 記録対象の判別 / 出力エンドポイント一覧
  value_objects/usage_period.py         AggregationPeriod（V-602）
  value_objects/usage_status_display.py 集計結果の行 VO とファーストクラスコレクション
  repositories/ports.py                 MenuUsageLogRepository / UsageStatusRepository（追記）
        ▲
        │
infrastructure/persistence/
  menu_usage_log_repository.py   DjangoMenuUsageLogRepository（書き込み）
  usage_status_repository.py     DjangoUsageStatusRepository（集計の読み取り）
models.py                        MenuUsageLog ORM モデル
```

依存方向は `interfaces → use_cases → domain ← infrastructure`。`domain/` と `use_cases/` に `import django` を書かない。

### 3.2 設計上の判断とその理由

| # | 判断 | 理由 |
|---|---|---|
| 1 | 記録は **ミドルウェア**（`interfaces/usage_logging.py`）で行う | 全画面・全出力を 1 箇所で捕捉でき、他コンテキストを変更しない（REQ-NF-006）。既存の `AccessApprovalMiddleware` が同じ責務範囲（`/app`・`/api/`）を既に横断しており、実績のある方式 |
| 2 | ミドルウェアの登録位置は **`AccessApprovalMiddleware` の直後** | アクセスを許可されていないメニューグループ（core V-002）へのアクセスは `AccessApprovalMiddleware` が 403 で短絡するため、直後に置けば拒否されたリクエストが利用記録ミドルウェアに届かない。REQ-F-003「拒否されたリクエストは記録しない」を **コードの分岐ではなく登録順で** 満たせる |
| 3 | 記録は **レスポンス確定後**（`process_response` 相当）に行う | ステータスコードを見て成否を判定できる。出力失敗・0 件時に記録しない（REQ-F-002）ための唯一の手段 |
| 4 | 記録対象の判別は **domain の純関数**（`usage_record.py`） | Django に依存しないため単体テストが速く、REQ-NF-008 の「記録対象・対象外の判別を固定するテスト」がフレームワーク無しで書ける |
| 5 | メニュー利用ログの user は **`on_delete=SET_NULL`** | ユーザーを物理削除してもログが連鎖削除されない（REQ-F-018・REQ-NF-004）。社員番号のスナップショットは **持たない** — REQ-F-018 が削除後を「ユーザーを特定できない記録として残す」と定めており、スナップショットはこれに反する |
| 6 | 集計は **infrastructure で GROUP BY**、判断（未利用・休眠・廃止メニューの注記）は **domain** | ログ件数がアプリケーションメモリに載らない規模（年 50 万件、§6.1）になるため、件数の圧縮は SQL で行う。一方、業務ルールは domain に置く |
| 7 | テンプレートは **`templates/portal/usage_status.html`**（スネークケース） | reference の命名規則はケバブケースだが、`application/portal/` の既存テンプレート（`user_management.html` / `access_requests.html` 等）が全てスネークケースであり、1 ファイルだけ流儀を変えると保守しづらい。**既存アプリの慣習を優先する（意図的な逸脱）** |

---

## 4. ドメインモデル

### 4.1 エンティティ

#### MenuUsageLog（メニュー利用ログ・E-601）

`application/portal/domain/entities/menu_usage_log.py`

| 属性 | 型 | 内容 |
|---|---|---|
| `log_id` | `int \| None` | 識別子。永続化前は `None` |
| `user_id` | `int \| None` | 利用したユーザー。物理削除後は `None`（REQ-F-018） |
| `menu_key` | `str` | メニューキー（V-601） |
| `usage_type` | `str` | 利用種別（S-601）。`VIEW` / `EXPORT` |
| `used_at` | `datetime` | 利用日時 |

- **追記のみ**のエンティティ。生成後に状態が変化するメソッドを持たない（REQ-F-017・REQ-F-018）。
- 識別子で同一性を判断するためエンティティとする。ただしライフサイクルは「生成 → 永続化 → 参照」のみで、更新・論理削除は設けない。
- 生成時に `usage_type` が `UsageType`（S-601）の 2 値のいずれかであることを検証し、外れる場合は `ValueError` を送出する（エンティティ固有のバリデーションはエンティティ自身に置く）。

### 4.2 バリューオブジェクト

`application/portal/domain/value_objects/usage_record.py` — **記録側**

| 名前 | 種別 | 内容 |
|---|---|---|
| `UsageType` | 定数 | `VIEW = "VIEW"` / `EXPORT = "EXPORT"`（S-601）。`USAGE_TYPE_LABELS` に表示名（表示／出力） |
| `ExportEndpoint` | frozen dataclass | `path: str` / `menu_key: str`。出力エンドポイントとメニューキーの対応 1 件 |
| `ExportEndpoints` | **ファーストクラスコレクション** | `ExportEndpoint` の集合。`menu_key_for(path, comparison_type)` を持つ。`EXPORT_ENDPOINTS` として単一のインスタンスを公開 |
| `UsageRecordTarget` | frozen dataclass | `menu_key: str` / `usage_type: str`。記録すべき 1 件の判別結果 |
| `resolve_menu_key(path: str, comparison_type: str) -> str \| None` | 関数 | パスに対応するメニューキー（V-601）を返す。`menu.MENU_ITEMS` を走査し、`menu_access.is_menu_path_active` と同一の一致規則で判定する。既存の `menu_access.py` には存在せず、本設計で新設する（§7.1 の新規ファイルに含む） |

判別の純関数（ドメインサービス相当。詳細は §4.4）:

```
resolve_usage_record_target(
    *, path: str, comparison_type: str, status_code: int,
    content_type: str, is_attachment: bool
) -> UsageRecordTarget | None
```

---

`application/portal/domain/value_objects/usage_period.py` — **集計期間**

| 名前 | 種別 | 内容 |
|---|---|---|
| `AggregationPeriod` | frozen dataclass | 集計期間（V-602）。`start_date: date` / `end_date: date`。両端を含む。**`__post_init__` で検証規則 3・4 を検査し、違反時は `AggregationPeriodError` を送出する**（不正な値のインスタンスを生成できない） |
| `AggregationPeriodError` | 例外 | 不正な集計期間。`message` に画面表示用の文言を持つ |
| `DEFAULT_AGGREGATION_DAYS` | 定数 | `30`（既定は当日を終了日とする直近 30 日。開始日＝当日の 29 日前） |
| `MAX_AGGREGATION_DAYS` | 定数 | `366`（REQ-F-006） |

| 関数 | 役割 |
|---|---|
| `default_aggregation_period(today: date) -> AggregationPeriod` | 既定値の生成。現在日時は引数で受け取り、domain 内で `date.today()` を呼ばない（テスト可能性のため） |
| `parse_aggregation_period(start: str, end: str, *, today: date) -> AggregationPeriod` | 画面入力の**文字列解釈**を担う（検証規則 1・2 と既定値の適用）。日付として解釈できたら `AggregationPeriod` を生成し、規則 3・4 の検査はコンストラクタに委ねる。いずれの違反も `AggregationPeriodError` |

検証規則（REQ-F-006）:

| # | 規則 | 違反時の文言 |
|---|---|---|
| 1 | 開始日・終了日はいずれも必須（両方空なら既定値、片方だけ空はエラー） | 「開始日と終了日の両方を指定してください。」 |
| 2 | `yyyy-mm-dd` として解釈できること | 「日付の形式が正しくありません。」 |
| 3 | 開始日 ≤ 終了日 | 「開始日は終了日以前を指定してください。」 |
| 4 | `(end_date - start_date).days + 1 <= 366` | 「集計期間は最大 366 日です。期間を短くしてください。」 |
| 5 | 未来日の終了日は **受け付ける**（該当ログが 0 件になるだけ） | — |

規則 1・2 は `parse_aggregation_period`（文字列 → 日付）が、**規則 3・4 は `AggregationPeriod.__post_init__`** が実施する（バリューオブジェクトの制約は VO のコンストラクタに置く）。規則 5 は制約を課さないことの明示であり、実装上の分岐を持たない。

`AggregationPeriod` は日付境界の解釈を担わない。`Asia/Tokyo` での 00:00:00〜23:59:59 への変換は infrastructure が行う（§5.3）。

---

`application/portal/domain/value_objects/usage_status_display.py` — **画面側**

集計結果の行と、そのファーストクラスコレクション（reference「ファーストクラスコレクション必須」）。
行 VO はすべて `@dataclass(frozen=True)` とし、生成後に状態が変化しない。コレクションも内部のリストを再代入せず、絞り込み・並び替えは**新しいインスタンスを返す**。

| 行 VO | コレクション | 対応要件 | 主な属性 |
|---|---|---|---|
| `UsageSummary`（全体集計・V-609） | （単一のため無し） | REQ-F-007 | `active_user_count`（V-604）／`usage_count`（V-603）／`export_count`（V-608）／`unused_user_count`（S-602）／`dormant_user_count`（S-605） |
| `MenuUsageRow` | `MenuUsageRows` | REQ-F-008 | `group_title`／`menu_title`／`view_count`（V-607）／`export_count`／`user_count`／`last_used_on`（V-605）／`is_retired` |
| `UserUsageRow` | `UserUsageRows` | REQ-F-009 | `username`（core V-001）／`display_name`／`role`（core R-003）／`menu_group_titles`／`usage_count`／`export_count`／`most_used_menu_title`（V-610）／`last_used_on`／`last_login_at`（V-606） |
| `UnusedMenuGroupGrantRow` | `UnusedMenuGroupGrantRows` | REQ-F-010 | `username`／`display_name`／`group_title`／`last_used_on`／`granted_on`（V-613）。未利用のメニューグループ付与（V-612）1 件 |
| `ExportLogRow` | `ExportLogRows` | REQ-F-011 | `used_at`／`username`／`display_name`／`group_title`／`menu_title` |
| `DailyUsagePoint` | `DailyUsageTrend` | REQ-F-012 | `on: date`／`count: int`。日別推移（V-611）。`DailyUsagePoint` は `DailyUsageTrend` の構成要素であり、単独の業務用語としては UL に登録しない |

各コレクションが持つ振る舞い:

| メソッド | 役割 |
|---|---|
| `sorted_by(specs)` | 共有カーネルの `SortSpec` で並び替え（REQ-NF-007） |
| `filtered_by_group(group_key)` | メニューグループでの絞り込み（REQ-F-013） |
| `csv_rows()` | ヘッダ行＋データ行の `list[list[str]]`（REQ-F-014） |
| `is_empty` | 「該当なし」表示の判定（REQ-F-016） |

その他の定数・関数:

| 名前 | 内容 |
|---|---|
| `USAGE_STATUS_CSV_ROW_LIMIT` | `100_000`（REQ-F-014） |
| `RETIRED_MENU_SUFFIX` | `"（廃止）"`（REQ-F-017） |
| `UNKNOWN_USER_LABEL` | `"（ユーザー不明）"`。物理削除されたユーザーのログを、ユーザーを特定できない記録として表示するラベル（REQ-F-018・§8.2） |
| `USAGE_STATUS_SECTIONS` | CSV 出力の対象区分。`menus` / `users` / `unused-grants` / `exports` |
| `*_SORT_LABELS` | 各一覧の列ラベル（既存の `USER_MANAGEMENT_SORT_LABELS` と同じ流儀） |
| `USAGE_STATUS_PURPOSE_NOTE` | 画面に常時表示する利用目的の注記（REQ-NF-005）。「この画面はメニューの改廃・定着（T-602）支援・権限棚卸（A-603）・データ持ち出しの確認のために用います。個人の勤務時間の把握や勤務評価には用いません。」 |
| `most_used_menu_key(entries)` | 1 ユーザーの `(menu_key, count)` から最多利用メニュー（V-610）を選ぶ。同数の場合は**メニューキーの昇順**で先頭を採る（REQ-F-009） |
| `build_daily_trend(counts, period)` | 日付の欠落を 0 で埋める（REQ-F-012） |
| `unused_user_count(entries, used_user_ids)` | 未利用ユーザー数（S-602）。母集団は **利用申請が許可（core S-001 `APPROVED`）かつ有効（S-604）** なユーザーで、集計期間内の利用回数が 0 のもの |
| `dormant_user_count(entries, period)` | 休眠ユーザー数（S-605）。母集団は上と同じで、**最終ログイン日時（V-606）が集計期間の開始日より前**のもの。一度もログインしていないユーザー（未ログイン・S-603）も含める |
| `menu_display_title(menu_key)` | 現行定義にあれば表示名、無ければ `"{menu_key}（廃止）"`（REQ-F-017） |
| `aggregation_target_menu_keys()` | 行として並べるメニューキー（`href` が空の親メニューを除外。REQ-F-008） |
| `unused_menu_group_grant_rows(grants, *, used_group_keys_by_user, last_used_on_by_user=None)` | 付与済みメニューグループ − 期間内に利用したメニューグループ の差分（REQ-F-010）。社員番号・メニューグループ名の昇順で並べる |
| `is_retired_menu(menu_key)` | 現行定義に無い（廃止された）メニューキーかどうか（REQ-F-017） |
| `menu_group_title(menu_key)` | 現行定義にあればメニューグループ名、無ければ `UNKNOWN_GROUP_LABEL`（REQ-F-017） |
| `UNKNOWN_GROUP_LABEL` | `"—"`。廃止メニューのメニューグループ表示（REQ-F-017） |
| `UserAggregationEntry` | 未利用ユーザー数・休眠ユーザー数の集計入力となる frozen な VO。`user_id`／`is_approved`（core S-001）／`is_active`（S-604）／`last_login_at`（V-606）。`unused_user_count` / `dormant_user_count` の引数 `entries` の要素 |
| `MenuGroupGrantEntry` | 未利用のメニューグループ付与（V-612）の集計入力となる frozen な VO。`user_id`／`username`（core V-001）／`display_name`／`group_key`／`granted_on`（V-613）。`unused_menu_group_grant_rows` の引数 `grants` の要素 |

### 4.3 集約

| 集約 | ルート | 境界 | 他集約との関係 |
|---|---|---|---|
| メニュー利用ログ | `MenuUsageLog` | ログ 1 件のみ。極小に保つ | ユーザーは `user_id`（ID 参照）。メニューは `menu_key`（ID 参照）。オブジェクト参照を持たない |

- 集約をログ 1 件に閉じることで、書き込み時に他の集約をロックしない。REQ-NF-003「利用記録どうしが待ち合わせない」を構造で満たす。
- 集計結果の VO（§4.2）は **集約ではなく読み取りモデル**。永続化されず、リクエストごとに infrastructure が組み立てる。
- メニュー項目・メニューグループは code 上の定数（`menu.py`）であり集約を成さない。ログはそれらへの外部キーを持たないため、メニュー定義の変更がログに影響しない（REQ-F-017）。

### 4.4 ドメインサービス

ドメインサービスは、既存の `menu_access.py` と同じく **モジュールレベルの純関数** として実現する（クラス化しない）。

#### (a) 記録対象の判別 — `usage_record.resolve_usage_record_target`

```
入力: path（クエリ文字列を含まない）／comparison_type（?type= の値）／
      status_code／content_type／is_attachment（Content-Disposition が attachment か）
出力: UsageRecordTarget | None（None は「記録しない」）
```

判定順序:

| 順 | 条件 | 結果 |
|---|---|---|
| 1 | `status_code != 200` | `None`（リダイレクト・エラー・403 は記録しない。REQ-F-002・REQ-F-003） |
| 2 | `path` が `EXPORT_ENDPOINTS` のいずれかに完全一致し、かつ `is_attachment` | `UsageRecordTarget(menu_key=対応表の値, usage_type=EXPORT)` |
| 2' | `path` が `EXPORT_ENDPOINTS` に一致するが `is_attachment` でない | `None`（ファイルが生成されていない。REQ-F-002） |
| 3 | `content_type` が `text/html` で始まらない | `None`（JSON の非同期問い合わせ・添付ファイル中継を除外。REQ-F-003） |
| 4 | `resolve_menu_key(path, comparison_type)` がメニューキーを返す | `UsageRecordTarget(menu_key=..., usage_type=VIEW)` |
| 5 | 上記以外 | `None`（ポータルトップ `portal:dashboard`・利用申請状況など、メニューキーに対応づかない画面。REQ-F-003） |

`resolve_menu_key` は既存の `menu_access.is_menu_path_active` と **同一の一致規則**（完全一致または `"{href_path}/"` 前方一致、`receipt-comparison` は `type` で分岐）を用いる。判定規則を二重に持たないよう、`is_menu_path_active` が使うパス正規化を `usage_record.py` から再利用する（`menu_access.py` → `usage_record.py` の domain 内 import）。

- 記録するメニューキーは `href` を持つメニュー項目のみ。子メニューを束ねるだけの親（`receipt-comparison`）は `href` が空のため一致しない（REQ-F-008）。
- `/app/production/receipt-comparison/settings` のように `type` を伴わない配下のパスは、既存の `receipt_comparison_type_from_path` と同じ既定（`finished-product`）に従う。
- 検収書比較の旧 URL（`/app/production/receipt-comparison/<slug>/...`）はリダイレクト（302）を返すため条件 1 で除外され、遷移先の 200 が 1 件だけ記録される（二重記録しない）。
- **出力成否の判定根拠**: 既存の出力 view は 5 つとも、失敗時に 400 / 404 / 502 / 503 を `Content-Disposition` 無しで返し、成功時のみ 200 と `Content-Disposition: attachment` を設定している（`application/*/interfaces/views.py`）。したがって「200 かつ attachment」がファイル生成の成否と一致する。0 件でもヘッダ行のみのファイルが生成される場合は出力操作（A-602）が成立しているため記録する。

#### (b) 出力エンドポイント一覧 — `EXPORT_ENDPOINTS`

REQ-F-002・REQ-NF-008 に基づき、記録対象の出力エンドポイントを **定数として固定する**。

| # | パス | メニューキー | 形式 |
|---|---|---|---|
| 1 | `/api/asset-inventory/export.csv` | `asset-inventory` | CSV |
| 2 | `/api/asset-inventory/asp-import.csv` | `asset-inventory` | CSV |
| 3 | `/api/gonenkukumi/export` | `five-year-nine` | Excel |
| 4 | `/app/production/inventory-order-alert/export.csv` | `inventory-order-alert` | CSV |
| 5 | `/api/inventory-order-alert/export.csv` | `inventory-order-alert` | CSV |
| 6 | `/app/production/receipt-comparison/export` | `receipt-comparison-finished-product` / `receipt-comparison-supplied-parts`（`?type=` で分岐） | CSV |
| 7 | `/app/sales/shipment-trend/export.csv` | `shipment-trend-list` | CSV |
| 8 | `/api/shipment-trend/export.csv` | `shipment-trend-list` | CSV |
| 9 | `/app/management/usage-status/export.csv` | `usage-status` | CSV（本機能自身。REQ-F-014・REQ-F-015） |

**対象外とするもの（明示）**:

| パス | 対象外の理由 |
|---|---|
| `/api/asset-inventory/attachment` | desknet's NEO の添付ファイルを中継する経路であり、CSV／Excel の出力操作（A-602）ではない。画面内で個別の添付を開く操作であり、記録すると出力回数（V-608）が持ち出しの実態から乖離する |
| `/api/gonenkukumi/search` ほかの `/api/` 群 | 画面内の非同期問い合わせ（REQ-F-003） |

**REQ-NF-008 の担保**: `application/portal/tests/test_usage_record_target.py` に、全アプリの `urlpatterns` を走査して「パスに `export` を含むルート」を列挙し、上表の一覧と一致することを検証するテストを置く。出力エンドポイントが追加・改称されるとこのテストが失敗し、記録漏れに気づける。

#### (c) 集計期間の検証 — `usage_period.parse_aggregation_period`

§4.2 の検証規則 1〜5 を実施する。

---

## 5. データモデル

### 5.1 追加テーブル: `portal_menuusagelog`

ORM モデルは既存の慣習に従い `application/portal/models.py` に置く（portal は `infrastructure/django/models/` を使っていない）。テーブル名は既存の 4 モデルと同じく **`db_table` を指定せず Django の既定命名に従う**。索引には既存モデルと同様に明示的な名前を付ける。

```python
class MenuUsageLog(models.Model):
    """メニュー利用ログ（E-601）。追記のみ。"""

    class UsageType(models.TextChoices):
        VIEW = "VIEW", "表示"
        EXPORT = "EXPORT", "出力"

    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,   # ユーザー削除でログを消さない（REQ-F-018・REQ-NF-004）
        null=True,
        blank=True,
        related_name="portal_menu_usage_logs",
    )
    menu_key = models.CharField(max_length=80)
    usage_type = models.CharField(max_length=10, choices=UsageType.choices)
    used_at = models.DateTimeField()

    class Meta:
        ordering = ["-used_at"]
        indexes = [
            models.Index(fields=["used_at"], name="menu_usage_used_at_idx"),
            models.Index(fields=["menu_key", "-used_at"], name="menu_usage_menu_key_idx"),
            models.Index(fields=["user", "-used_at"], name="menu_usage_user_idx"),
            models.Index(fields=["usage_type", "-used_at"], name="menu_usage_type_idx"),
        ]
```

| 列 | 型 | NULL | 内容 |
|---|---|---|---|
| `id` | bigint | × | 代理キー |
| `user_id` | integer FK | ○ | 利用したユーザー。削除時は NULL（REQ-F-018） |
| `menu_key` | varchar(80) | × | メニューキー（V-601）。既存 `UserFavoriteMenu.menu_key` と同じ長さに揃える |
| `usage_type` | varchar(10) | × | `VIEW` / `EXPORT`（S-601） |
| `used_at` | timestamptz | × | 利用日時。`timezone.now()` を infrastructure が設定する |

- **メニューへの外部キーを持たない。** メニューは code 上の定数であり、削除・改称してもログは影響を受けない（REQ-F-017）。
- **更新・削除の経路をアプリケーションに設けない。** リポジトリは `record()` と読み取りのみを公開する（REQ-NF-004）。
- 記録する項目はこの 4 つに限る。IP アドレス・ユーザーエージェント・操作対象データの列を作らない（REQ-NF-005）。
- **メニューキーが空文字の場合は記録しない。** リポジトリの `record()` が早期 return する（例外にすると記録の失敗が画面に波及するため）。判別（`resolve_usage_record_target`）が空のキーを返さない前提の二重の防御であり、TC-INF-006 で固定する（2026/08/27 追記）。

### 5.2 索引（REQ-NF-002 #3）

| # | 索引 | 解決する参照 |
|---|---|---|
| 1 | `(used_at)` | 集計期間での絞り込み・日別推移（REQ-F-012）・全体集計（REQ-F-007） |
| 2 | `(menu_key, used_at DESC)` | メニュー別集計（REQ-F-008）・メニュー単位の最終利用日 |
| 3 | `(user_id, used_at DESC)` | ユーザー別集計（REQ-F-009）・ユーザー単位の最終利用日・将来のパージ（REQ-NF-004） |
| 4 | `(usage_type, used_at DESC)` | 出力操作の記録（REQ-F-011）・出力回数（V-608） |

索引 4 本は挿入コストを増やすが、1 行あたり 4 項目の小さな行であり、REQ-NF-003 の 50ms に対して十分に収まる。挿入は追記のみで更新が無いため、索引の肥大（bloat）も生じにくい。

**最終利用日（V-605）の取得方法**（REQ-F-008・REQ-F-009 は集計期間外も含む全期間が対象）:

全期間を GROUP BY で走査すると REQ-NF-002 #1 に反するため、**キーごとに `ORDER BY used_at DESC LIMIT 1` を発行**し、索引 2・3 の先頭 1 行だけを読む。メニューキーは十数件、対象ユーザーは 100 名程度（§6.1）であり、走査行数はキー数に比例した定数に収まる。

### 5.3 日付境界の扱い（REQ-F-006）

- `USE_TZ = True` / `TIME_ZONE = "Asia/Tokyo"`（`config/settings/base.py`）。`used_at` は UTC で保存される。
- 集計は infrastructure で `AggregationPeriod`（`date`）を `Asia/Tokyo` の aware な datetime に変換し、`used_at__gte=開始日 00:00:00` / `used_at__lt=終了日の翌日 00:00:00` で絞り込む。`__lte 23:59:59` ではなく `__lt 翌日 00:00` を用いる（秒未満の値を取りこぼさないため）。
- 日別推移の日付は `TruncDate("used_at")`（現在のタイムゾーンで解釈される）で求める。

### 5.4 既存テーブルとの関係

| テーブル | 関係 |
|---|---|
| `auth_user` | `user_id` で参照（SET_NULL）。最終ログイン日時（V-606）＝ `last_login`、社員番号（core V-001）＝ `username`、有効状態（S-604）＝ `is_active` |
| `portal_user_access_request` | 集計対象ユーザーの母集団の判定（`status = APPROVED`。REQ-F-009） |
| `portal_menu_group_access` | 付与メニューグループと付与日（V-613 ＝ `created_at`）。REQ-F-010 |
| `portal_user_favorite_menu` | 関係なし |

### 5.5 マイグレーション

`application/portal/migrations/0007_menu_usage_log.py` を 1 本追加する（既存の最新は `0006_normalize_menu_group_access_keys`）。テーブル作成と索引 4 本の作成のみで、既存データの変換は無い。

### 5.6 容量の見込み（REQ-NF-004）

§6.1 の前提（1 日約 2,000 件・年約 50 万件）に対し、**年間およそ 100MB 前後**の増加を見込む。PostgreSQL の容量監視の対象に加える（運用手順は `Document/本番環境デプロイ手順.md` に記載する）。

実測値（2026/08/27・PostgreSQL 16 のテスト DB に `portal_menu_usage_log` を 50 万件投入して `pg_total_relation_size` 等で計測）:

| 区分 | 実測 | 1 行あたり |
|------|------|-----------|
| 本体（heap） | 36.5MB | 76.6 バイト |
| 索引 4 本 | 60.9MB | 127.7 バイト |
| 合計 | **97.4MB** | **204.3 バイト** |

索引 4 本の合計が本体を上回るため、容量は索引が支配的である。当初の見積り（1 行 130 バイト前後・年 70MB 前後）は実測で約 1.4 倍となったが、REQ-NF-004 が求める「容量の見積りを行い監視対象に加える」ことは満たしている。

---

## 6. API / インターフェース設計

### 6.1 メニュー項目の追加（REQ-F-005）

`application/portal/domain/value_objects/menu.py` の `MENU_ITEMS` に 1 件追加する。

```python
PortalMenuItem(
    key="usage-status",
    title="利用状況",
    href="/app/management/usage-status",
    group_key="management",
)
```

管理メニューグループ（`management`）に属するため、既存の `can_access_menu_group` が管理者以外を弾く（REQ-NF-001）。新たな認可の仕組みを作らない。

**このメニュー項目を追加することで、利用状況画面自身の表示も `usage-status` の `VIEW` として自動的に記録される**（§4.4(a) の判定順 4 に一致するため。REQ-F-015）。記録のための個別の処理を view に書かない。

### 6.2 URL

`application/portal/interfaces/urls.py` に 2 件追加する。`app/management/<str:slug>` のプレースホルダより **前** に置く（先勝ちのため）。

| メソッド | パス | view | 名前 |
|---|---|---|---|
| GET | `/app/management/usage-status` | `usage_status_page` | `usage_status` |
| GET | `/app/management/usage-status/export.csv` | `usage_status_export_csv` | `usage_status_export_csv` |

### 6.3 クエリパラメータ

| 名前 | 既定 | 内容 |
|---|---|---|
| `start` | 当日の 29 日前 | 集計期間の開始日（`yyyy-mm-dd`） |
| `end` | 当日 | 集計期間の終了日（`yyyy-mm-dd`） |
| `group` | 空（全メニューグループ） | メニューグループでの絞り込み（REQ-F-013） |
| `sort` | 一覧ごとの既定 | 並び替え（共有カーネル `parse_sort_specs` の書式。REQ-NF-007） |
| `dir` | `asc` | 並び順 |
| `page` / `size` | `1` / 既定件数 | ページング（共有カーネル `paginate_rows`） |
| `section` | — | CSV 出力のみ。`menus` / `users` / `unused-grants` / `exports`（REQ-F-014） |

### 6.4 画面（`templates/portal/usage_status.html`）

上から次の順に配置する。既存の管理メニューと同じ構成（絞り込みパネル → 一覧 → フッタ）に揃える（REQ-NF-007）。

| # | 区画 | 内容 | 対応要件 |
|---|---|---|---|
| 0 | 利用目的の注記 | `USAGE_STATUS_PURPOSE_NOTE` を常時表示 | REQ-NF-005 |
| 1 | 絞り込みパネル | 開始日・終了日・メニューグループ。集計期間はサーバ再問い合わせを伴うため送信操作を持つ | REQ-F-006・REQ-F-013 |
| 2 | 全体集計（V-609） | 利用ユーザー数／延べ利用回数／出力回数／未利用ユーザー数／休眠ユーザー数 | REQ-F-007 |
| 3 | 日別推移 | 日付昇順の横棒。**外部ライブラリを使わず** 最大値に対する比率を CSS の `width` で表現する | REQ-F-012・§6.3 制約 2 |
| 4 | メニュー別 利用状況 | 一覧＋列並び替え＋CSV 出力 | REQ-F-008 |
| 5 | ユーザー別 利用状況 | 同上 | REQ-F-009 |
| 6 | メニューグループ付与済み × 未利用 | 同上 | REQ-F-010 |
| 7 | 出力操作の記録 | 利用日時の降順。`yyyy/mm/dd hh:mm` | REQ-F-011 |

- 各一覧は 0 件のとき「該当なし」を表示する（REQ-F-016）。
- 集計期間が不正なときは、エラー文言を絞り込みパネル直下に表示し、**一覧を描画しない**（REQ-F-006）。
- 並び替え・ページングは既存の `portal-list-core.js` / `portal-list-sort-dialog.js` を用い、画面別の設定だけを `static/js/usage-status-list-client.js` に置く（既存の `shipment-trend-list-client.js` 等と同じ役割。`ポータル一覧表_共通仕様.md`）。
- **補足**: 既存の管理系画面（`user_management.html` / `notices.html`）はこの共通エンジンを使わずサーバー側の並び替えのみで作られている。本画面は REQ-NF-007 が `ポータル一覧表_共通仕様.md` への準拠を求めているため、**共通エンジン側に合わせる**。
- **行データの持ち方**: 共通エンジンの既定は行データを `json_script` で埋め込むクライアント側ページングだが、本画面は 4 つの一覧を 1 画面に並べるため、埋め込み payload が 4 一覧分の合計になる。とくに「出力操作の記録」は行数が集計期間に比例して増える（他の 3 つはメニュー数・ユーザー数に上限がある）。そのため本画面は **最初からサーバー側ページング**を採る。ユースケース `page_context` が `paginate_rows` で切り出した行だけをテンプレートが描画し（SSR）、`json_script` による全行の埋め込みは行わない。`usage-status-list-client.js` は並び替えダイアログの操作・ページ送り操作・URL 同期（`history.replaceState`）を担当し、`sort` / `dir` / `page` / `size` を付けてサーバーへ再問い合わせする。

### 6.5 CSV 出力（REQ-F-014）

- `GET /app/management/usage-status/export.csv?section=...&start=...&end=...&group=...&sort=...`
- 画面と同じ集計期間・絞り込み・並び替えを反映する。
- 文字コード・改行・ファイル名の規約は既存の CSV 出力に揃える。
- 行数が `USAGE_STATUS_CSV_ROW_LIMIT`（10 万行）を超える場合は **出力せず**、画面へ戻して「出力対象が 10 万行を超えました。集計期間または絞り込みを狭めてください。」と表示する。
- この出力自身も `usage-status` の `EXPORT` として記録される（§4.4(b) の #9）。

### 6.6 ミドルウェア（REQ-F-001〜REQ-F-004）

`application/portal/interfaces/usage_logging.py`

```python
class UsageLoggingMiddleware:
    def __init__(self, get_response): ...
    def __call__(self, request):
        response = self.get_response(request)
        try:
            self._record(request, response)
        except Exception:              # 記録の失敗で業務操作を止めない（REQ-F-004）
            logger.warning(...)        # ユーザーには表示しない
        return response
```

`_record` の流れ:

1. `request.user` が未認証なら何もしない（REQ-F-003）。
2. `resolve_usage_record_target(...)` を呼ぶ。`None` なら何もしない。

   ```python
   target = resolve_usage_record_target(
       path=request.path,
       comparison_type=request.GET.get("type", ""),
       status_code=response.status_code,
       content_type=response.headers.get("Content-Type", ""),
       is_attachment="attachment" in response.headers.get("Content-Disposition", ""),
   )
   ```
3. `wiring.record_usage_usecase()` に `user` と判別結果を渡す。

登録位置（`config/settings/base.py` の `MIDDLEWARE`）:

```
AuthenticationMiddleware
application.portal.interfaces.middleware.AccessApprovalMiddleware
application.portal.interfaces.usage_logging.UsageLoggingMiddleware   ← 追加
MessageMiddleware
```

`AccessApprovalMiddleware` の **直後**に置くことで、メニューグループ（core V-002）を持たない等の理由で 403 に短絡したリクエストは本ミドルウェアに到達しない（§3.2 #2）。

### 6.7 ユースケース

#### `use_cases/record_usage.py` — `RecordUsage`

```
record(*, user: object, target: UsageRecordTarget) -> None
```
リポジトリの `record()` を呼ぶだけの薄い層。判別は domain、永続化は infrastructure が担う。

#### `use_cases/usage_status.py` — `UsageStatus`

| メソッド | 役割 |
|---|---|
| `page_context(*, start, end, group_key, sort_key, sort_direction, page, page_size, today)` | 集計期間を解釈し、リポジトリから集計を取得し、domain の VO を組み立ててテンプレート用の辞書を返す。`AggregationPeriodError` は捕捉して `error_message` としてコンテキストに載せ、一覧は空にする |
| `csv_payload(*, section, ...)` | 指定区画の CSV 行を返す。上限超過時は `(rows=None, error_message=...)` を返す |

#### リポジトリのポート（`domain/repositories/ports.py` に追記）

既存の流儀に合わせ `typing.Protocol` で定義する。

```python
class MenuUsageLogRepository(Protocol):
    def record(self, *, user: object, menu_key: str, usage_type: str) -> None: ...


class UsageStatusRepository(Protocol):
    def overall_counts(self, *, start_at, end_at) -> dict[str, int]: ...
    def menu_counts(self, *, start_at, end_at) -> list[dict[str, object]]: ...
    def last_used_at_by_menu_key(self) -> dict[str, object]: ...
    def user_counts(self, *, start_at, end_at) -> list[dict[str, object]]: ...
    def last_used_at_by_user(self) -> dict[int, object]: ...
    def menu_counts_by_user(self, *, start_at, end_at) -> list[dict[str, object]]: ...
    def used_menu_keys_by_user(self, *, start_at, end_at) -> dict[int, set[str]]: ...
    def daily_counts(self, *, start_at, end_at) -> list[dict[str, object]]: ...
    def export_entries(self, *, start_at, end_at) -> list[dict[str, object]]: ...
    def approved_user_entries(self) -> list[dict[str, object]]: ...
    def menu_group_grants(self) -> list[dict[str, object]]: ...
```

- 集計期間は **aware な datetime**（`start_at` / `end_at`）で渡す。`date` → datetime の変換は `UsageStatus` が行うが、タイムゾーンは `wiring` が `django.utils.timezone.get_current_timezone()` から渡した `tzinfo` を用いる（`UsageStatus(repository, tzinfo=...)`）。`use_cases` が Django のタイムゾーン API を直接呼ばないための受け渡しであり、テストでは任意の `tzinfo` を与えられる。範囲は半開区間で、`start_at` = 開始日 00:00、`end_at` = **終了日の翌日** 00:00 とする。
- 「今日」は view が `django.utils.timezone.localdate()` で求め、`today` として `page_context` に渡す。`domain` / `use_cases` の中で現在日時を取得しない（テストで任意の日付を与えられるようにするため）。
- `approved_user_entries()` は 1 ユーザーにつき `user_id` / `username` / `display_name` / `role` / `is_active`（S-604）/ `last_login`（V-606）を返す。未利用ユーザー数（S-602）・休眠ユーザー数（S-605）の母集団の判定材料は domain 側で揃う。
- `menu_counts_by_user()` は `user_id` / `menu_key` / `count` の一覧を返すだけで、最多の判定は行わない。**最多利用メニュー（V-610）の判定と、同数の場合の順序（メニューキーの昇順）は domain の `usage_status_display.most_used_menu_key(entries)` が担う**（REQ-F-009 が design.md での定義を求めている箇所）。集計ルールを infrastructure に置かないための分担であり、行数はユーザー数 × 利用したメニュー数にとどまるため §3.2 #6 の「集計は DB 側で圧縮する」方針とも両立する。

#### リポジトリの戻り値のキー

`UsageStatusRepository` の各メソッドが返す辞書のキーを次のとおり定める（`use_cases` はこのキー名だけに依存する）。

| メソッド | 戻り値のキー |
|---|---|
| `overall_counts()` | `usage_count`（延べ利用回数 V-607）/ `export_count`（出力回数）/ `active_user_count`（利用ユーザー数 S-601） |
| `menu_counts()` | `menu_key` / `view_count` / `export_count` / `user_count` |
| `last_used_at_by_menu_key()` | `menu_key` → 利用日時（V-605、全期間） |
| `user_counts()` | `user_id` / `usage_count` / `export_count` |
| `last_used_at_by_user()` | `user_id` → 利用日時（全期間） |
| `menu_counts_by_user()` | `user_id` / `menu_key` / `count` |
| `used_menu_keys_by_user()` | `user_id` → 期間内に利用したメニューキーの集合 |
| `daily_counts()` | `on`（日付）/ `count` |
| `export_entries()` | `used_at` / `user_id` / `username` / `display_name` / `menu_key` |
| `approved_user_entries()` | `user_id` / `username` / `display_name` / `role` / `is_active` / `last_login` |
| `menu_group_grants()` | `user_id` / `username` / `display_name` / `group_key` / `granted_on` |

- `user_id` が `NULL` のログ（REQ-F-018）は `user_counts()` / `used_menu_keys_by_user()` / `menu_counts_by_user()` に含めない。`overall_counts()` / `menu_counts()` / `daily_counts()` / `export_entries()` には含める（§8.2）。
- メニューグループ（core V-002）・メニュー名は `menu_key` から domain 側で解決する。infrastructure は `menu_key` を返すだけで、表示名を組み立てない。

#### `page_context()` の戻り値のキー

| キー | 型 | 内容 |
|---|---|---|
| `purpose_note` | `str` | `USAGE_STATUS_PURPOSE_NOTE`（エラー時も必ず載せる。REQ-NF-005） |
| `error_message` | `str \| None` | 集計期間が不正なときの文言（§8.2） |
| `period` | `AggregationPeriod \| None` | 解釈済みの集計期間。不正なときは `None` |
| `start` / `end` | `str` | 絞り込みパネルに戻す `yyyy-mm-dd`。不正なときは入力値をそのまま返す |
| `group_key` | `str` | 絞り込み中のメニューグループ（空文字は全件） |
| `sort_key` / `sort_direction` | `str` | 並び替えの状態 |
| `summary` | `UsageSummary` | 全体集計（V-609）。不正・0 件のときは 5 値とも 0 |
| `daily_trend` | `DailyUsageTrend` | 日別推移（V-608） |
| `menu_usage_rows` / `user_usage_rows` / `unused_grant_rows` / `export_log_rows` | 各ファーストクラスコレクション | 絞り込み・並び替え済みの全行（「該当なし」の判定は `is_empty` を使う） |
| `menu_usage_page` / `user_usage_page` / `unused_grant_page` / `export_log_page` | `PaginatedRows` | 共有カーネル `paginate_rows` の戻り値をそのまま載せる（総ページ数を含む） |
| `sort_labels` | `dict[str, dict[str, str]]` | 区分（`menus` / `users` / `unused-grants` / `exports`）ごとの列ラベル |

- 集計期間が不正なときは 4 つのコレクションを空にし、リポジトリを **1 度も呼ばない**。
- ページングの `page` / `page_size` は 4 つの一覧に同じ値を適用する。最終ページを超える `page` は共有カーネル `paginate_rows` の規約どおり最終ページに丸める。
- `sort_key` が空のときは並び替えを行わず、リポジトリが返した順（domain が組み立てた順）のままとする。

#### `csv_payload()` の戻り値

```python
@dataclass(frozen=True)
class CsvPayload:
    rows: list[list[str]] | None      # 1 行目はヘッダ
    error_message: str | None
```

`section` が `USAGE_STATUS_SECTIONS` にない場合・集計期間が不正な場合・行数が `USAGE_STATUS_CSV_ROW_LIMIT` を超える場合は `rows=None` と文言を返す（例外にしない）。

#### `interfaces/wiring.py` に追記

```python
def get_menu_usage_log_repository() -> MenuUsageLogRepository: ...
def get_usage_status_repository() -> UsageStatusRepository: ...
def record_usage_usecase() -> RecordUsage: ...
def usage_status_usecase() -> UsageStatus: ...
```

`composition.py` および `services/` は新設しない。

---

## 7. 既存コードへの変更点

### 7.1 新規ファイル

| # | ファイル | 内容 |
|---|---|---|
| 1 | `application/portal/domain/entities/menu_usage_log.py` | `MenuUsageLog`（E-601） |
| 2 | `application/portal/domain/value_objects/usage_record.py` | `UsageType` / `ExportEndpoints` / `resolve_usage_record_target` |
| 3 | `application/portal/domain/value_objects/usage_period.py` | `AggregationPeriod` / 検証 |
| 4 | `application/portal/domain/value_objects/usage_status_display.py` | 行 VO・ファーストクラスコレクション・列ラベル・CSV 行 |
| 5 | `application/portal/use_cases/record_usage.py` | `RecordUsage` |
| 6 | `application/portal/use_cases/usage_status.py` | `UsageStatus` |
| 7 | `application/portal/infrastructure/persistence/menu_usage_log_repository.py` | `DjangoMenuUsageLogRepository` |
| 8 | `application/portal/infrastructure/persistence/usage_status_repository.py` | `DjangoUsageStatusRepository` |
| 9 | `application/portal/interfaces/usage_logging.py` | `UsageLoggingMiddleware` |
| 10 | `application/portal/migrations/0007_menu_usage_log.py` | テーブル・索引の追加 |
| 11 | `templates/portal/usage_status.html` | 画面 |
| 12 | `static/js/usage-status-list-client.js` | 一覧の画面別設定 |
| 13 | `application/portal/tests/test_usage_record_target.py` | 記録対象の判別・出力エンドポイント一覧（REQ-NF-008） |
| 14 | `application/portal/tests/test_usage_logging_middleware.py` | 記録・非記録・失敗時の非中断（REQ-F-001〜004） |
| 15 | `application/portal/tests/test_usage_period.py` | 集計期間の境界（REQ-F-006） |
| 16 | `application/portal/tests/test_usage_status_page.py` | 認可・0 件・廃止メニュー・無効化／削除ユーザー（REQ-NF-001・REQ-F-016〜018） |
| 17 | `application/portal/tests/test_menu_usage_log.py` | エンティティの生成・値域検証（REQ-F-001） |
| 18 | `application/portal/tests/test_usage_status_display.py` | 行 VO・ファーストクラスコレクション・集計関数（REQ-F-007〜012・017・018） |
| 19 | `application/portal/tests/test_usecase_record_usage.py` | `RecordUsage` の振る舞い（REQ-F-001〜004） |
| 20 | `application/portal/tests/test_usecase_usage_status.py` | `UsageStatus` の集計・CSV 行・エラー時（REQ-F-006〜014） |
| 21 | `application/portal/tests/test_usage_status_repository.py` | リポジトリの保存・集計・日付境界（REQ-F-001・006〜011・REQ-NF-004） |

※ #17〜#21 は test-design.md（TEST-USAGE-STATUS-2026-001）§1.5 の設計により追加した（2026/08/27）。

### 7.2 変更ファイル

| # | ファイル | 変更概要 | 削除 |
|---|---|---|---|
| 1 | `application/portal/models.py` | `MenuUsageLog` モデルを追加 | 無し |
| 2 | `application/portal/domain/value_objects/menu.py` | `MENU_ITEMS` に `usage-status` を 1 件追加 | 無し |
| 3 | `application/portal/domain/repositories/ports.py` | `MenuUsageLogRepository` / `UsageStatusRepository` を追加 | 無し |
| 4 | `application/portal/interfaces/urls.py` | ルート 2 件を `app/management/<str:slug>` より前に追加 | 無し |
| 5 | `application/portal/interfaces/views.py` | `usage_status_page` / `usage_status_export_csv` を追加 | 無し |
| 6 | `application/portal/interfaces/wiring.py` | ファクトリ 4 件を追加 | 無し |
| 7 | `config/settings/base.py` | `MIDDLEWARE` に `UsageLoggingMiddleware` を 1 行追加 | 無し |

**既存コードの削除は行わない。** 他の 5 つの業務コンテキスト（`asset_inventory` / `gonenkukumi` / `inventory_order_alert` / `receipt_comparison` / `shipment_trend`）のファイルは **1 つも変更しない**（REQ-NF-006）。

### 7.3 アーキテクチャ検証への適合

`config/tests/test_clean_architecture.py` の各検証に対して:

| 検証 | 適合 |
|---|---|
| `views` が `use_cases` / `infrastructure` / `models` を直 import しない | 新しい view は `wiring` のファクトリのみを呼ぶ |
| `use_cases` に `import django` / 自 infrastructure / models を書かない | `UsageStatus` はポート経由。日時変換は infrastructure 側 |
| `domain` に `import django` / 外側レイヤーを書かない | 3 つの VO モジュールと 1 つのエンティティは標準ライブラリと `application.shared.domain` のみに依存 |
| `composition.py` を作らない・DI コンテナを使わない | `wiring.py` に関数を追加するのみ |
| 境界コンテキスト間の import | portal から他コンテキストへの import は無い。`application.shared.domain` は共有カーネルとして許可済み |

---

## 8. エラーハンドリング方針

### 8.1 利用記録側（REQ-F-004・REQ-NF-003）

| 事象 | 振る舞い |
|---|---|
| メニューキーを解決できない | 記録せず、正常終了（エラーではない） |
| DB への書き込みに失敗（接続断・制約違反） | 例外を捕捉し、`logging` に `warning` を出力。**レスポンスはそのまま返す**。ユーザーに何も表示しない |
| 記録処理が予期せぬ例外を投げる | 同上。`except Exception` で包括的に捕捉する。ここは「握りつぶすことが仕様」である稀な箇所であり、その旨をコード上のコメントに残す |
| 未認証・匿名ユーザー | 記録しない（REQ-F-003） |

記録は **レスポンス生成後**に行うため、記録の遅延がレンダリングを待たせない。1 リクエストにつき 1 行の INSERT のみで、トランザクションを跨いだロックを取らない（REQ-NF-003）。

### 8.2 利用状況画面側

| 事象 | 振る舞い | 対応要件 |
|---|---|---|
| 一般ユーザーが URL を直接指定 | 既存の管理メニューと同じ 403 応答 | REQ-NF-001 |
| 未ログイン | 既存どおりログイン画面へ | — |
| 開始日 > 終了日 / 形式不正 / 366 日超過 | 画面にエラー文言を表示し、集計を行わない（HTTP 200） | REQ-F-006 |
| 集計期間内のログが 0 件 | エラーとせず「該当なし」。全体集計は 0 | REQ-F-016 |
| 現行のメニュー定義に無い `menu_key` | メニュー名に「（廃止）」を付けて表示。メニューグループは「—」 | REQ-F-017 |
| `user_id` が NULL のログ（物理削除されたユーザー） | 全体集計・メニュー別・日別推移・出力操作の記録に含める。ユーザー名は `UNKNOWN_USER_LABEL` を表示する。ユーザー別・メニューグループ付与済み × 未利用の一覧には出さない | REQ-F-018 |
| 無効化されたユーザー | ユーザー別・未利用付与の一覧から除外。集計・メニュー別・出力記録には含める | REQ-F-018 |
| CSV が 10 万行超過 | 出力せず画面に文言を表示 | REQ-F-014 |

---

## 9. リスクと対策

| # | リスク | 影響 | 対策 |
|---|---|---|---|
| 1 | 全リクエストに記録処理が挟まり、応答が遅くなる | 全画面の体感低下（REQ-NF-003 の 50ms 超過） | レスポンス確定後に 1 行 INSERT のみ。判別はメモリ上の辞書引き。Phase 5 で実測し、50ms を超える場合は非同期化（`transaction.on_commit` ないしキュー）を検討する |
| 2 | 索引 4 本により書き込みが重くなる | 同上 | 追記のみ・4 列の小さな行であり影響は限定的。Phase 5 の実測で判断する |
| 3 | ログの単調増加でテーブルが肥大化する | 将来の性能劣化・容量逼迫（REQ-NF-004） | 集計期間の必須指定で走査範囲を限定。`(user_id, used_at)` 索引によりパージ可能な構造を確保。容量監視を運用手順に加える |
| 4 | 最終利用日（V-605）が全期間参照であり、REQ-NF-002 #1 と緊張する | 表示の遅延 | キーごとの `ORDER BY used_at DESC LIMIT 1`（索引の先頭 1 行）に限定し、全件走査を発生させない（§5.2） |
| 5 | ユーザー別の最終利用日をユーザー数分のクエリで取る | ユーザー増加時に問い合わせ回数が増える | 現状 100 名程度（§6.1）で問題にならない。数百名規模になった場合は LATERAL 結合 1 クエリへ置き換える |
| 6 | 出力エンドポイントの追加・改称に記録が追随しない | 出力操作の追跡（目的③）の欠落 | `EXPORT_ENDPOINTS` を単一の定義とし、URLConf を走査して一覧との一致を検証するテストを置く（§4.4(b)・REQ-NF-008） |
| 7 | パスの前方一致による誤ったメニューキー割り当て | 集計値の誤り | 既存の `is_menu_path_active` と同一規則を再利用し、規則を二重に持たない。判別はテストで固定する（REQ-NF-008） |
| 8 | 記録が「監視されている」と受け取られる | ユーザーの心理的抵抗 | 画面に利用目的の限定を常時表示（REQ-NF-005）。記録項目を 4 つに限り、時刻単位の行動履歴を一覧できる画面を設けない |
| 9 | リリース直後はログが無く、画面が空のまま | 「壊れている」と誤解される | 0 件時は「該当なし」＋記録の開始日を案内する文言を表示（REQ-F-016） |
| 10 | ミドルウェアの登録位置が将来変更され、拒否されたリクエストまで記録される | 利用回数（V-603）の過大計上（REQ-F-003 違反） | 登録順に依存することを本書と `usage_logging.py` のコメントに明記し、403 が記録されないことをテストで固定する |
| 11 | 定量値（366 日・10 万行・50 ユーザー・50 万件）が実測に基づかない | 実運用で過大／過小になる | 要件定義書の L3 再レビュー指摘 L3R-1・L3R-2 として継続課題に登録済み。Phase 5 の実測後に requirements.md を先に更新し、本書を追随させる |
| 12 | 「出力操作の記録」の行数が集計期間に比例して増える | 画面の初期表示が遅くなる | 集計期間の上限（366 日）で頭打ちになる。加えて §6.4 のとおり 4 一覧ともサーバー側ページング（SSR）とし、1 ページ分の行だけを描画する |
| 13 | `ポータル一覧表_共通仕様.md` §2.1 が共通 primitives の置き場所を `application/portal/domain/list_table.py` と記しているが、実体は `application/shared/domain/value_objects/list_table.py` にある | 実装時に存在しないモジュールを参照する | 本書では実体のパスを正とする（§2.1）。共通仕様書の記述は別途 Issue として更新する |

---

## 10. レビュー履歴

<!-- design-review-l1 / l2 が追記する -->

### Design-L1レビュー (2026/08/27 17:18)

**アーキテクチャreference**: django-clean-architecture version 1.0（make-design / design-review-l1 / implement-review-l1 で一致）

**観点別サマリー**:

| 観点 | OK | 警告 | NG |
|------|-----|------|-----|
| 1. 戦略的設計との整合性 | 4件 | 1件 | 1件 |
| 2. ドメインモデルの妥当性 | 5件 | 3件 | 0件 |
| 3. ビジネスルールの配置 | 5件 | 2件 | 1件 |
| 4. ユビキタス言語との整合性 | 4件 | 3件 | 1件 |

**総合判定**: CONDITIONAL PASS（NG 3件）

**指摘事項**:

| # | 観点 | 重要度 | 該当箇所 | 指摘内容 | 対応 |
|---|------|--------|---------|---------|------|
| 1 | 観点1 | NG | §2 | 「A〜E に対して順応者」が strategic_design.md §4.1（F・G が上流、A〜E が順応者）と逆向き | 修正済み（G を上流と明記。出力エンドポイント把握の例外を注記） |
| 2 | 観点3 | NG | §6.7 | 最多利用メニュー（V-610）の同数時タイブレークがリポジトリ（infrastructure）に埋め込まれていた | 修正済み（ポートを `menu_counts_by_user()` に変更し、判定を domain の `most_used_menu_key()` へ） |
| 3 | 観点4 | NG | §3.2 #2 / §6.6 | 「権限を持たないメニュー」「権限不足」が core R-003 の適用範囲（メニュー・画面・API の利用可否には「権限」を使わない）に違反 | 修正済み（メニューグループ core V-002 に言い換え） |
| 4 | 観点1 | 警告 | §2 | 責務欄が strategic_design.md §3 の文言と不一致 | 修正済み（SD の文言に統一） |
| 5 | 観点2 | 警告 | §4.2 / §4.4(a) | `resolve_usage_record_target` の署名が §4.2 で `is_attachment` を欠き文書内不整合 | 修正済み |
| 6 | 観点2 | 警告 | §4.2 | 行 VO の不変性（frozen）が明記されていない | 修正済み |
| 7 | 観点2 | 警告 | §4.2 / §4.4(a) | `resolve_menu_key` の定義場所・署名が未記載（既存 `menu_access.py` にも無い） | 修正済み（`usage_record.py` の新設関数として定義） |
| 8 | 観点3 | 警告 | §4.2 | `AggregationPeriod` の制約が `parse_aggregation_period` にのみあり、不正値のインスタンスを生成できた | 修正済み（`__post_init__` で規則3・4を検証） |
| 9 | 観点3 | 警告 | §4.1 | エンティティ `MenuUsageLog` に `usage_type`（S-601）の値域検証が無い | 修正済み |
| 10 | 観点4 | 警告 | §4.2 / §6.5 / §7 | モデル名が UL 英語名と不一致（`OverallSummary` / `UnusedGrantRow` / `top_menu_*` / `RecordMenuUsage`） | 修正済み（`UsageSummary` / `UnusedMenuGroupGrantRow` / `most_used_menu_*` / `RecordUsage`） |
| 11 | 観点4 | 警告 | §8.2 | 表示ラベル「（削除済み）」が S-604 の「使用しない表現」に抵触 | 修正済み（`UNKNOWN_USER_LABEL = "（ユーザー不明）"`） |
| 12 | 観点4 | 警告 | §4.2 | `DailyUsagePoint` が UL 未定義 | 修正済み（V-611 の構成要素として単独登録しない旨を注記） |

**誤検出として除外**: 「最終ログイン日時」（V-606 の正式名称）／「概要」（構造見出し）／「ダッシュボード」（実在の view 名 `portal:dashboard` を指す技術識別子。可読性のため「ポータルトップ」に言い換え）／`usage_record.py` の `value_objects/` 配置（既存 `menu_access.py` と同じ慣習）。

**未解決の指摘**: 0件（NG: 0件 / 警告: 0件）

**次のアクション**: 指摘12件を反映済み。テスト設計書（test-design.md）の作成へ進む。Design-L2（Codex クロスレビュー）は Codex CLI 未導入のため保留。


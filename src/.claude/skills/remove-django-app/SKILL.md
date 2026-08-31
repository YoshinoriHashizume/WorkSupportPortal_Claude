---
name: remove-app
description: |
  既存の Django アプリを Clean Architecture 構成ごと安全に削除する。
  add-app で作成したアプリの逆操作。ユーザーがアプリ名（と任意で配置先ディレクトリ）を
  指定すると、他アプリからの参照走査・影響分析を先に行い、承認を得てから
  INSTALLED_APPS 登録解除・config/urls.py の include 削除・マイグレーション巻き戻し（テーブル削除）・
  アプリディレクトリ削除・manage.py check までを実施する。
  ユーザーが「アプリを削除して」「〇〇アプリを消して」「作ったアプリを撤去して」
  「不要になったアプリを削除して」などと依頼したときに使用する。
argument-hint: "<app_name(snake_case)> [配置先ディレクトリ 例: application]"
allowed-tools: Read, Edit, Glob, Grep, Bash(python manage.py:*), Bash(rm:*), Bash(ls:*), Bash(test:*), Bash(grep:*), Bash(find:*)
---

# アプリ削除スキル

あなたは Django + Clean Architecture の基盤保守担当です。
既存アプリを安全に撤去します。**削除は不可逆な破壊的操作**（DB テーブル・マイグレーション履歴・コードが失われる）のため、
add-app スキルと違い **必ず影響分析を提示し、ユーザーの承認を得てから実行**してください。

## 前提・重要ルール

- 依存方向: `interfaces → use_cases → domain ← infrastructure`
- ORM Model は `infrastructure/django/models/` に置き、`models.py` でリエクスポートされている
- **このスキルは承認ゲートを設ける。** 影響分析（削除対象一覧＋参照元＋DB 影響）を提示し、明示的な承認を得るまで破壊的操作（ファイル削除・マイグレーション巻き戻し）を実行しない
- 削除は add-app の逆順で行う（DB → ルーティング → 設定 → ファイル）
- 迷う点（他アプリからの参照、残すべき docs 等）が出たら停止してユーザーに確認する

## 入力の解釈

$ARGUMENTS

引数を次のように解釈する:

1. **第1引数 = アプリ名（必須, snake_case）** 例: `inventory_survey`
   - 未指定なら「削除するアプリ名を snake_case で教えてください」と確認して停止する
2. **第2引数 = 配置先ディレクトリ（任意, src からの相対パス）** 例: `application`
   - 未指定なら **`application` をデフォルト**とする

### 派生値の算出（add-app と同一規則）

| 値 | 算出方法 | 例（app=`inventory_survey`, 配置先=`application`） |
|----|----------|------|
| `dotted_path` | `配置先の区切りを . に置換` + `.` + `app_name` | `application.inventory_survey` |
| `ConfigClass` | app_name を PascalCase 化 + `Config` | `InventorySurveyConfig` |
| `url_prefix` | app_name の `_` を `-` に置換（ケバブケース） | `inventory-survey/` |

## 実行フロー

### Phase A: 調査と影響分析（破壊的操作なし）

まず情報を集め、影響分析を提示する。ここではファイルを一切変更しない。

#### Step A0: 対象の存在確認

- 作業ディレクトリを `/django_app/src` とする（絶対パスで操作する）
- `test -d <配置先>/<app_name>` でアプリが存在するか確認する。存在しなければ停止して報告する

#### Step A1: 他アプリからの参照を走査（最重要）

削除するとビルドが壊れる参照が無いかを確認する。以下を grep し、**自分自身（削除対象ディレクトリ内）以外**のヒットを列挙する:

```bash
cd /django_app/src
# dotted_path / app_name への import・include・文字列参照
grep -rn "<dotted_path>" . --include="*.py" | grep -v "<配置先>/<app_name>/"
grep -rn "<app_name>" config/ --include="*.py"
# 他アプリの ORM Model からの ForeignKey / OneToOne / ManyToMany 参照
grep -rn "<app_name>\." . --include="*.py" | grep -iE "ForeignKey|OneToOne|ManyToMany|to=" | grep -v "<配置先>/<app_name>/"
# テンプレート内の URL 逆引き（{% url '<app_name>:... %}）
grep -rn "<app_name>:" . --include="*.html"
```

- 外部からの参照が見つかった場合は、**削除を保留し**、参照元ファイルと行を提示して「先に参照を除去・付け替える必要がある」旨をユーザーに報告する。無断で他アプリのコードを書き換えない
- 参照が自分自身のみなら、安全に削除できると判断する

#### Step A2: マイグレーション／DB 影響の確認

```bash
cd /django_app/src
ls <配置先>/<app_name>/migrations/ 2>/dev/null
python manage.py showmigrations <app_name>
```

- マイグレーションが存在し DB に適用済みなら、削除前に `migrate <app_name> zero`（テーブルを DROP）を実行する必要がある旨を明示する
- **他アプリのテーブルが本アプリのテーブルを FK 参照している場合、zero 移行が失敗しうる**（A1 の結果と突き合わせる）。その場合は依存関係の解消が先であることを報告する

#### Step A3: 影響分析を提示して承認を得る

以下をまとめてユーザーに提示し、**明示的な承認を待つ**:

- 削除対象アプリ・`dotted_path`・`url_prefix`
- **削除するディレクトリ**: `<配置先>/<app_name>/`（配下のファイル数を添える）
- **編集する設定ファイル**: `config/settings/base.py`（INSTALLED_APPS から除外）、`config/urls.py`（include 行を削除）
- **DB への影響**: 巻き戻すマイグレーションの有無、DROP されるテーブル（＝失われるデータ）
- **外部参照の有無**（A1 の結果）
- 残す/消すの判断が要るもの: `docs/spec/` 配下の仕様書（レビュー履歴・要件等が残っている場合は削除の是非を確認する）

> 承認が得られるまで Phase B に進まない。「一部だけ実行」等の指定があればそれに従う。

### Phase B: 削除の実行（承認後のみ）

承認後、add-app の逆順で実行する。各ステップでエラーが出たら停止し、正確に報告してから対処する。

#### Step B1: マイグレーションを巻き戻す（DB あり・適用済みの場合）

```bash
cd /django_app/src
python manage.py migrate <app_name> zero
```

- これで本アプリが作成したテーブルが DROP される。エラー（他テーブルからの FK 依存等）が出たら停止して報告する
- DB を使っていない／マイグレーション未適用ならスキップし、その旨を報告する

#### Step B2: config/urls.py から include を削除

`config/urls.py` の `urlpatterns` から、本アプリの include 行（および直前の日本語コメント行）を削除する（Edit）。

```python
    # <アプリの用途コメント>
    path("<url_prefix>", include("<dotted_path>.interfaces.urls")),
```

#### Step B3: INSTALLED_APPS から登録解除

`config/settings/base.py` の `INSTALLED_APPS` から `"<dotted_path>",`（および直前の日本語コメント行）を削除する（Edit）。

> 補足: ロガーは INSTALLED_APPS の `application.*` から自動生成されるため、ログ設定の手動削除は不要。

#### Step B4: アプリディレクトリを削除

```bash
cd /django_app/src
rm -rf <配置先>/<app_name>
```

> `rm -rf` は不可逆。Phase A で提示したパスと完全一致することを再確認してから実行する。配置先の親ディレクトリ（例: `application`）自体は削除しない。

#### Step B5: 動作確認

```bash
cd /django_app/src
python manage.py check
python manage.py makemigrations --check --dry-run
```

- `check` がエラーなく通ること、削除に伴う未反映のマイグレーション差分が無いことを確認する
- 残存参照によるエラーが出たら内容を報告し、原因（消し漏れた import 等）を修正する

## 完了報告

実行後、以下を簡潔に報告する:

- 削除したアプリと `dotted_path`・`url_prefix`
- 巻き戻したマイグレーション／DROP したテーブル（無ければ「DB 影響なし」）
- 編集したファイル（`config/settings/base.py`, `config/urls.py`）と削除したディレクトリ
- `python manage.py check` の結果
- 残置物の案内: `docs/spec/` を残した場合はその旨。コミット前に `git status` で差分を確認するよう促す

## add-app との対応（逆操作の対照表）

| add-app のステップ | remove-app での逆操作 |
|-------------------|----------------------|
| startapp + 4層/テスト/docs 作成 | ディレクトリ削除（B4） |
| INSTALLED_APPS 登録 | 登録解除（B3） |
| config/urls.py に include 追記 | include 削除（B2） |
| makemigrations/migrate（モデル追加後） | migrate zero でテーブル DROP（B1） |

## 参考

- 追加スキル（対の操作）: `.claude/skills/add-django-app/SKILL.md`
- アーキテクチャ詳細: `.claude/skills/design-review-l1/references/django-clean-architecture.md`

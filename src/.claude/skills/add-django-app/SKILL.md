---
name: add-app
description: |
  Django の新規アプリを Clean Architecture 構成で追加する事前準備を自動実行する。
  ユーザーがアプリ名（と任意で配置先ディレクトリ）を指定すると、startapp から
  apps.py 修正・INSTALLED_APPS 登録・4層ディレクトリ作成・models.py リエクスポート・
  URL ルーティング・テストディレクトリ作成・docs/spec ディレクトリ作成・manage.py check までを一気に実施し、
  すぐに機能実装へ着手できる骨組みを用意する。
  ユーザーが「新しいアプリを作って」「アプリを追加して」「新規アプリの事前準備をして」
  「〇〇アプリのひな形を作って」などと依頼したときに使用する。
argument-hint: "<app_name(snake_case)> [配置先ディレクトリ 例: application]"
allowed-tools: Read, Write, Edit, Glob, Grep, Bash(python manage.py:*), Bash(mkdir:*), Bash(touch:*), Bash(mv:*), Bash(ls:*), Bash(test:*)
---

# 新規アプリ追加スキル

あなたは Django + Clean Architecture の基盤構築担当です。
新規アプリを追加する事前準備を、**確認を挟まず一気通貫で自動実行**してください。

## 前提・重要ルール

- 依存方向: `interfaces → use_cases → domain ← infrastructure`
- `domain/` と `use_cases/` に `import django` を書かない（Django 非依存）
- ORM Model は `infrastructure/django/models/` に置き、`models.py` でリエクスポートする
- Entity と ORM Model は別物（変換はリポジトリが担う）
- **このスキルは承認ゲートを設けない。** アプリ名を受け取ったら最後まで自動実行し、完了後に結果を報告する（ユーザーが明示的に選択した動作）
- 本スキルは「骨組み（ひな形）」を作るところまで。ドメインモデルやユースケースの実装は行わない

## 入力の解釈

$ARGUMENTS

引数を次のように解釈する:

1. **第1引数 = アプリ名（必須, snake_case）** 例: `inventory_survey`
   - 未指定なら「追加するアプリ名を snake_case で教えてください」と確認して停止する
   - snake_case でない（大文字・ハイフン・先頭数字等）場合は指摘し、正しい名前を確認する
2. **第2引数 = 配置先ディレクトリ（任意, src からの相対パス）** 例: `application`
   - 未指定なら **`application` をデフォルト**とする

### 派生値の算出

アプリ名と配置先から以下を機械的に導出し、以後すべてで一貫して使う:

| 値 | 算出方法 | 例（app=`inventory_survey`, 配置先=`application`） |
|----|----------|------|
| `dotted_path` | `配置先.区切りを. に置換` + `.` + `app_name` | `application.inventory_survey` |
| `ConfigClass` | app_name を PascalCase 化 + `Config` | `InventorySurveyConfig` |
| `url_prefix` | app_name の `_` を `-` に置換（ケバブケース） | `inventory-survey/` |

> 配置先が `application` 以外・ネストする場合も、`dotted_path` は必ず「配置先の相対パスをドット区切りにしたもの + アプリ名」で統一する。apps.py の `name`・INSTALLED_APPS・models.py・urls.py の import はすべてこの `dotted_path` を使う。

## 実行フロー（全ステップ自動）

各ステップを順に実行する。途中でエラーが出たら停止し、エラーメッセージを正確に報告してから対処する。

### Step 0: 事前チェック

- 作業ディレクトリを `/django_app/src` とする（絶対パスで操作する）
- 配置先に同名アプリが既に存在しないか確認する（`test -d <配置先>/<app_name>`）。存在する場合は停止して報告する

### Step 1: startapp して配置先へ移動

`startapp <app_name> application` は既存の `application` パッケージと衝突するため、**一度カレントに作ってから移動**する。

```bash
cd /django_app/src
python manage.py startapp <app_name> && mv <app_name> <配置先>/
```

（配置先ディレクトリが未作成なら先に `mkdir -p <配置先>` する）

### Step 2: apps.py の name を修正

`<配置先>/<app_name>/apps.py` の `name` を `dotted_path` に修正する（Edit）。クラス名は startapp 生成のまま（`<ConfigClass>`）で一致するはずだが、異なる場合は `dotted_path` と整合させる。

```python
class <ConfigClass>(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = '<dotted_path>'   # ← 配置先.アプリ名 に修正（デフォルトは app_name のみ）
```

### Step 3: INSTALLED_APPS に登録

`config/settings/base.py` の `INSTALLED_APPS` リスト末尾（`]` の直前）に、日本語コメント + `"<dotted_path>",` を追記する（Edit）。既存アプリと同じスタイルに合わせる:

```python
    # <アプリの用途を1行で>。
    "<dotted_path>",
]
```

> 補足: ロガーは `base.py` が INSTALLED_APPS の `application.*` から自動生成するため、ログ設定の手動追記は不要。

### Step 4: 4層ディレクトリ + テンプレートを作成

```bash
cd /django_app/src/<配置先>/<app_name>
mkdir -p domain/entities domain/value_objects domain/repositories \
         use_cases infrastructure/django/models interfaces templates/<app_name>
touch domain/__init__.py domain/entities/__init__.py domain/value_objects/__init__.py \
      domain/repositories/__init__.py use_cases/__init__.py \
      infrastructure/__init__.py infrastructure/django/__init__.py \
      infrastructure/django/models/__init__.py interfaces/__init__.py
```

### Step 5: models.py をリエクスポートに置換

`<配置先>/<app_name>/models.py` を次の内容で上書きする（Write）:

```python
# Django がマイグレーションで参照する入口。実体は infrastructure に配置する。
from <dotted_path>.infrastructure.django.models import *  # noqa: F401,F403
```

### Step 6: URL ルーティング（interfaces/views.py・urls.py + config/urls.py）

startapp 生成のルート `views.py` は使わず、`interfaces/` に配置する。すぐ疎通確認できるようプレースホルダの index ページを用意する（実装時に差し替える前提）。

`<配置先>/<app_name>/interfaces/views.py`（Write）:
```python
from django.views.generic import TemplateView


class IndexView(TemplateView):
    """プレースホルダ。機能実装時に差し替える。"""
    template_name = "<app_name>/index.html"
```

`<配置先>/<app_name>/interfaces/urls.py`（Write）:
```python
from django.urls import path

from <dotted_path>.interfaces.views import IndexView

app_name = "<app_name>"

urlpatterns = [
    path("", IndexView.as_view(), name="index"),
]
```

`<配置先>/<app_name>/templates/<app_name>/index.html`（Write, 最小プレースホルダ）:
```html
<!DOCTYPE html>
<html lang="ja">
<head><meta charset="utf-8"><title><app_name></title></head>
<body><h1><app_name> index (placeholder)</h1></body>
</html>
```

`config/urls.py` の `urlpatterns` に include を追記（Edit）。既存の書式に合わせ、末尾要素として追加する:
```python
    # <アプリの用途を1行で>。
    path("<url_prefix>", include("<dotted_path>.interfaces.urls")),
```
（`include` が未 import の場合のみ import 行も補う。既存 urls.py は `from django.urls import include, path` 済み）

### Step 7: テストディレクトリを作成（TDD の土台）

```bash
cd /django_app/src/<配置先>/<app_name>
mkdir -p tests/domain tests/use_cases tests/infrastructure tests/interfaces
touch tests/__init__.py tests/domain/__init__.py tests/use_cases/__init__.py \
      tests/infrastructure/__init__.py tests/interfaces/__init__.py
```

配置方針（テスト作成時の指針としてコメント等で残さなくてよいが、報告に含める）:
- `tests/domain/` → DB 不要
- `tests/use_cases/` → DB 不要（InMemory リポジトリ）
- `tests/infrastructure/` → DB 使用
- `tests/interfaces/` → DB 使用 + HTTP

### Step 8: SDD 用の docs ディレクトリを作成

SDD フロー（要件→設計→タスク）の成果物置き場として `docs/spec/` を用意する。
仕様書は機能ごとに `docs/spec/<feature-name>/` に作成されるため、ここでは空の `docs/spec/` まで作る。
git は空ディレクトリを追跡しないため `.gitkeep` を置く。

```bash
cd /django_app/src/<配置先>/<app_name>
mkdir -p docs/spec
touch docs/spec/.gitkeep
```

> 補足: 各機能の `requirements.md` / `design.md` / `test-design.md` / `tasks.md` は
> SDD フローの中で `docs/spec/<feature-name>/` 配下に作成する（本スキルでは作らない）。
> 運用フェーズの `docs/issues/` は manage-issue スキルが必要時に作成する。

### Step 9: 動作確認

```bash
cd /django_app/src
python manage.py check
```

エラーがないことを確認する。エラーが出たら内容を報告し原因を修正する。

> **マイグレーションについて:** ひな形時点では ORM モデルが無いため `makemigrations` は実行しない（変更なし）。モデルを追加した後に別途
> `python manage.py makemigrations <app_name> && python manage.py migrate` を実行する旨を報告に添える。

## 完了報告

実行後、以下を簡潔に報告する:

- 作成したアプリと `dotted_path`・`url_prefix`
- 変更したファイル（`apps.py`, `config/settings/base.py`, `config/urls.py`）と新規作成ファイル一覧（`docs/spec/` を含む）
- `python manage.py check` の結果
- 次アクションの案内: 「ドメインモデル/ユースケースの実装は SDD フロー（要件→設計→タスク→実装）で進める。仕様書は `docs/spec/<feature-name>/` に作成する」「モデル追加後に makemigrations/migrate を実行する」「プレースホルダ view/template/urls は機能実装時に差し替える」

## 命名規則（遵守）

| 種別 | 規則 | 例 |
|------|------|-----|
| アプリ名 | snake_case | `inventory_survey` |
| Entity | PascalCase | `SurveyResponse` |
| ORM Model | PascalCase + `Model` | `SurveyResponseModel` |
| ユースケース | 動詞+名詞 | `CreateSurveyResponse` |
| URL | ケバブケース | `inventory-survey/` |

## 参考

- アーキテクチャ詳細: `.claude/skills/design-review-l1/references/django-clean-architecture.md`
- コーディング規約: `.claude/skills/implement-review-l1/references/django-coding-rules.md`

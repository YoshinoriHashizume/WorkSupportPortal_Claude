---
version: 1.1
updated: 2026-04-25
source-name: django-coding-rules
---

# Django コーディング規約

本ファイルは、Djangoプロジェクトにおけるコーディング規約を定義する。
実装レビュー(implement-review-l1)で実装コードを検証する際の基準として使用する。

## docstring

Googleスタイルで記述する。**全てのモジュール・クラス・メソッド・関数に docstring を記述すること。**

| 対象 | 内容 |
|------|------|
| モジュール | ファイル先頭に1行で目的・責務を記述する |
| クラス | 責務を1-2行で記述する |
| メソッド・関数 | 何をするかを1行で記述する。引数・戻り値が自明でない場合は Args / Returns / Raises も記述する |

### 記述例

```python
"""Userエンティティ関連の定義。"""


class User:
    """業務システムの利用者を表すエンティティ。"""

    def activate(self, actor: "User") -> None:
        """ユーザーをアクティブ化する。

        Args:
            actor: 操作を行う管理者ユーザー

        Raises:
            PermissionDenied: actorが管理者権限を持たない場合
        """
        ...
```

## import規約

- **全てのインポートはモジュールのトップレベルに記述する**
- 関数内でのインポート(遅延インポート)は禁止 (pylint C0415)
- エンティティは各アプリの `domain/entities/__init__.py` を経由してインポートする
  - 新しいエンティティを追加した際は必ず `__init__.py` にエクスポートを追加すること

### 記述例

```python
# Good
from application.user.domain.entities import User


def do_something(user: User) -> None:
    ...


# Bad (遅延インポート)
def do_something(user_id: int) -> None:
    from application.user.domain.entities import User  # pylint: C0415
    ...
```

## コメント

**コード内のコメントや docstring に全角括弧 `（` `）` を使用しないこと。**

- 半角 `(` `)` を使用する
- 全角括弧はリンターエラーの原因となる

```python
# Good
def calc(price: int) -> int:
    """税込価格を計算する(10%想定)。"""
    ...


# Bad (全角括弧)
def calc(price: int) -> int:
    """税込価格を計算する（10%想定）。"""  # リンターエラー
    ...
```

## ログ出力

**infrastructure層の全てのpublicメソッドには、開始・完了・エラーのログを必ず出力すること。**

### ログレベル早見表

| レベル | 用途 |
|--------|------|
| ERROR | API通信失敗(リトライ上限到達)、バリデーションエラー、予期しない例外 |
| WARNING | リトライ発生、HTTP 429受信、スキップされたレコード |
| INFO | 処理開始・完了、各フェーズの開始・完了、処理件数サマリー |
| DEBUG | 個別レコードの送信・成功、APIレスポンス詳細 |

### 記述例

```python
import logging

logger = logging.getLogger(__name__)


class SomeApiClient(BaseAppSuiteApiClient):
    """APIクライアントの実装。"""

    def some_method(self, param: str) -> Result:
        """処理を実行する。"""
        logger.info("処理X開始: param=%s", param)
        try:
            data = self._post(payload)
        except AppSuiteApiError:
            logger.error("処理XでAPIエラー発生: param=%s", param)
            raise
        logger.info("処理X完了: result=%s", data.get("ID"))
        return Result(**data)
```

### ログ設定

- ログ設定は `config/settings/base.py` の `LOGGING` で一元管理する
- `INSTALLED_APPS` の `application.*` エントリから動的にアプリ別ハンドラー/ロガーを生成する
- アプリ別ログ出力先: `application/<app_name>/logs/<app_name>.log`
- Django内部ログ出力先: `logs/django.log`

## ファーストクラスコレクション

アーキテクチャ側 (`django-clean-architecture.md` の「ファーストクラスコレクション」節) に定義あり。

---
version: 1.0
updated: 2026-04-11
source-name: django-pytest
---

# Django + pytest テストパターン

本ファイルは、Djangoプロジェクトにおけるpytestを使ったテストの具体的な
書き方・パターンを定義する。

---

## 1. テスト環境

- フレームワーク: pytest + pytest-django
- 設定: `config/settings/test.py`（pyproject.tomlで指定）
- DB: テスト用PostgreSQL（pytest-djangoが自動管理）

## 2. テストコマンド

```bash
make test-fast    # domain + use_cases のみ（DB不要・高速）。日常はこれ
make test-all     # 全テスト。コミット前に実行
make test-cov     # カバレッジ付き
pytest application/<app_name>/tests/             # 特定アプリのテスト
pytest path/to/test.py::TestClass::test_method   # 単一テスト
```

**日常の開発**: `make test-fast` でdomain + use_casesのテストのみ高速に回す。
**コミット前**: `make test-all` で全テストを実行する。

## 3. テストファイルの配置

```
application/<app_name>/tests/
├── domain/              # DB不要（make test-fast の対象）
│   ├── test_entities.py
│   ├── test_value_objects.py
│   └── test_domain_services.py
├── use_cases/           # DB不要（make test-fast の対象）
│   └── test_{use_case_name}.py
├── infrastructure/      # DB使用
│   ├── test_repositories.py
│   └── test_api_clients.py
└── interfaces/          # DB使用 + HTTP
    └── test_views.py
```

## 4. テストの書き方

### Domain層テスト（DB不要）

```python
"""MaterialTransactionエンティティのテスト。"""

import pytest
from application.material.domain.entities import MaterialTransaction
from application.material.domain.value_objects import MaterialCode


class TestMaterialTransaction:
    """MaterialTransactionエンティティのテスト。"""

    def test_create_with_valid_values(self) -> None:
        """正常な値で生成できること。"""
        # Arrange
        code = MaterialCode("MAT-001")
        quantity = 100

        # Act
        transaction = MaterialTransaction(code=code, quantity=quantity)

        # Assert
        assert transaction.code == code
        assert transaction.quantity == 100

    def test_create_with_negative_quantity_raises_error(self) -> None:
        """負の数量で生成するとバリデーションエラーになること。"""
        with pytest.raises(ValueError, match="数量は0以上"):
            MaterialTransaction(
                code=MaterialCode("MAT-001"),
                quantity=-1,
            )
```

### バリューオブジェクトのテスト（DB不要）

```python
"""MaterialCodeバリューオブジェクトのテスト。"""

import pytest
from application.material.domain.value_objects import MaterialCode


class TestMaterialCode:
    """MaterialCodeバリューオブジェクトのテスト。"""

    def test_create_with_valid_value(self) -> None:
        """正常な値で生成できること。"""
        code = MaterialCode("MAT-001")
        assert code.value == "MAT-001"

    def test_create_with_empty_string_raises_error(self) -> None:
        """空文字で生成するとバリデーションエラーになること。"""
        with pytest.raises(ValueError):
            MaterialCode("")

    def test_equal_values_are_equal(self) -> None:
        """同じ値のMaterialCodeは等しいこと。"""
        a = MaterialCode("MAT-001")
        b = MaterialCode("MAT-001")
        assert a == b

    def test_different_values_are_not_equal(self) -> None:
        """異なる値のMaterialCodeは等しくないこと。"""
        a = MaterialCode("MAT-001")
        b = MaterialCode("MAT-002")
        assert a != b
```

### Application層テスト（DB不要・モック使用）

```python
"""CreateMaterialTransactionユースケースのテスト。"""

from unittest.mock import Mock

from application.material.domain.entities import MaterialTransaction
from application.material.use_cases.create_material_transaction import (
    CreateMaterialTransaction,
    CreateMaterialInput,
)


class TestCreateMaterialTransaction:
    """CreateMaterialTransactionユースケースのテスト。"""

    def test_execute_with_valid_input_creates_transaction(self) -> None:
        """正常な入力でトランザクションが作成されること。"""
        # Arrange
        mock_repo = Mock()
        use_case = CreateMaterialTransaction(repository=mock_repo)
        input_dto = CreateMaterialInput(code="MAT-001", quantity=100)

        # Act
        result = use_case.execute(input_dto)

        # Assert
        mock_repo.save.assert_called_once()
        assert result.code == "MAT-001"
```

### Infrastructure層テスト（DB使用）

```python
"""DjangoMaterialRepositoryのテスト。"""

import pytest

from application.material.domain.entities import MaterialTransaction
from application.material.infrastructure.django.repositories import (
    DjangoMaterialRepository,
)


@pytest.mark.django_db
class TestDjangoMaterialRepository:
    """DjangoMaterialRepositoryの結合テスト。"""

    def test_save_and_find(self) -> None:
        """保存したエンティティを取得できること。"""
        # Arrange
        repo = DjangoMaterialRepository()
        entity = MaterialTransaction(code="MAT-001", quantity=100)

        # Act
        repo.save(entity)
        found = repo.find_by_code("MAT-001")

        # Assert
        assert found is not None
        assert found.quantity == 100
```

## 5. テスト命名規則

```
test_{何を}_{条件}_{期待結果}
```

例:
- `test_create_with_valid_values`
- `test_create_with_negative_quantity_raises_error`
- `test_save_and_find`

## 6. fixture の使い方

```python
@pytest.fixture
def material_code() -> MaterialCode:
    """テスト用のMaterialCode。"""
    return MaterialCode("MAT-001")

@pytest.fixture
def material_transaction(material_code: MaterialCode) -> MaterialTransaction:
    """テスト用のMaterialTransaction。"""
    return MaterialTransaction(code=material_code, quantity=100)
```

## 7. docstring規約

**全てのテストクラス・テストメソッドにdocstringを記述すること。**

- テストクラス: 「{テスト対象}のテスト。」
- テストメソッド: 「{期待される振る舞い}こと。」（「〜こと。」で終わる）

## 8. TDDサイクル

```bash
# 1. Red: 失敗するテストを書く
pytest application/<app>/tests/domain/test_entities.py -x

# 2. Green: テストをパスする最小限の実装
pytest application/<app>/tests/domain/test_entities.py -x

# 3. Refactor: コードをリファクタリング
make test-fast  # リファクタリング後に既存テストが壊れていないか確認
```

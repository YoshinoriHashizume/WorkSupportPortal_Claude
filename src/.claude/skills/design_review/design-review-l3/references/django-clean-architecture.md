---
version: 1.0
updated: 2026-04-11
source-name: django-clean-architecture
---

# Django + Clean Architecture 定義

本ファイルは、Djangoプロジェクトにおける Clean Architecture のレイヤー構成・
依存方向・各レイヤーの責務を定義する。

機能設計書の作成（make-design）および設計レビュー（design-review-l1/l3）で
共通の基準として使用する。

## レイヤー構成

```
src/
├── domain/              # 複数アプリで共有するドメイン概念(任意)
├── config/              # Django設定・URL
└── application/         # 各 Django アプリ
    └── <app_name>/
        ├── domain/          ★ Django非依存。import djangoを書いてはいけない
        │   ├── entities/        # エンティティ + ファーストクラスコレクション
        │   ├── value_objects/   # 値オブジェクト
        │   ├── repositories/    # リポジトリインターフェース(ABC)
        │   └── exceptions.py
        ├── use_cases/       ★ Django非依存。domain/ のみに依存
        │   └── dto.py           # Input / Output
        ├── infrastructure/  Django依存OK。domain/ のインターフェースを実装
        │   ├── api_client/      # 外部API連携
        │   ├── config/          # 環境変数読み込み
        │   ├── django/models/   # ORMモデル(models.pyからリエクスポート)
        │   └── csv/             # CSV処理
        ├── interfaces/      Django依存OK。use_cases/ を呼び出す
        │   ├── views.py
        │   └── urls.py
        ├── tests/
        │   ├── domain/          # DB不要
        │   ├── use_cases/       # DB不要
        │   ├── infrastructure/  # DB使用
        │   └── interfaces/      # DB使用+HTTP
        └── models.py            # infrastructure/django/models/ をリエクスポート
```

## 依存方向

```
interfaces → use_cases → domain ← infrastructure
```

- **外側 → 内側のみ依存可能**
- domain層は他のどの層にも依存しない（最内層）
- infrastructure層はdomain層のABCを実装する（依存逆転の原則）

## 各レイヤーの責務と制約

### domain層

**責務**: ビジネスロジックの核心。エンティティ、バリューオブジェクト、リポジトリインターフェース(ABC)を含む。

**制約（絶対）**:
- `import django` 禁止（django関連の一切のimportを含む）
- 外部フレームワークへの依存は一切不可
- 純粋なPythonのみで記述する

### use_cases層

**責務**: ユースケースの制御フロー。domain層のみに依存する。

**制約（絶対）**:
- `import django` 禁止
- domain層のABC経由でinfrastructure層を利用する

### infrastructure層

**責務**: 外部連携（API、DB、ファイル等）の実装。domain層のABCを実装する。

**制約**: Entity と ORM Model は別物。変換はリポジトリが担う。

### interfaces層

**責務**: HTTPリクエストの受付とレスポンスの返却。use_cases層を呼び出す。

**制約**: ビジネスロジックを書かない。use_casesを呼ぶだけ。

## 命名規則

| 種類 | 規則 | 例 |
|------|------|-----|
| Entity | PascalCase | `MaterialTransaction` |
| ORM Model | PascalCase + Model接尾辞 | `MaterialTransactionModel` |
| Repository ABC | I{Entity}Repository | `IMaterialRepository` |
| Repository実装 | Django{Entity}Repository | `DjangoMaterialRepository` |
| ユースケース | 動詞+名詞 | `CreateMaterialTransaction` |
| DTO | {Action}{Entity}Input / Output | `CreateMaterialInput` |
| テンプレート | kebab-case | `material-list.html` |
| URL | kebab-case | `/material-transaction/` |

## ファーストクラスコレクション

**複数のValue ObjectやEntityを扱う場合、`list[ValueObject]` をそのまま使わず、必ずファーストクラスコレクションとして実装すること。**

```python
@dataclass(frozen=True)
class Users:
    """Userエンティティのファーストクラスコレクション。"""
    _items: tuple[User, ...]

    def active(self) -> "Users":
        """アクティブなユーザーのみを返す。"""
        return Users(tuple(u for u in self._items if u.is_active))
```

- Value Objectのコレクション → `domain/value_objects/` に配置
- Entityのコレクション → `domain/entities/` に配置

## DI方針

- DIコンテナ不使用（ビュー内で手動組み立て）

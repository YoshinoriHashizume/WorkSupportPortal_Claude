---
version: 1.0
updated: 2026-04-11
source-name: swift-clean-architecture
---

# Swift + Clean Architecture 定義

本ファイルは、Swiftプロジェクトにおける Clean Architecture のレイヤー構成・
依存方向・各レイヤーの責務を定義する。

機能設計書の作成（make-design）および設計レビュー（design-review-l1/l3）で
共通の基準として使用する。

## レイヤー構成

```
{ProjectName}/
├── Models/              # Domain層（ビジネスロジックの核心）
│   ├── Entities/            # エンティティ
│   ├── ValueObjects/        # バリューオブジェクト
│   ├── DomainServices/      # ドメインサービス
│   └── Protocols/           # リポジトリインターフェース等
│
├── Application/         # Application層（ユースケース）
│   ├── Services/            # アプリケーションサービス（Fetcher / RegistrationService）
│   └── DTOs/                # Input / Output
│
├── Infrastructure/      # Infrastructure層（外部連携の実装）
│   ├── API/                 # APIクライアント + ApiMapper
│   │   ├── ApiClient/           # API通信
│   │   ├── ApiJson/             # JSONレスポンス型
│   │   ├── ApiMapper/           # JSON → ドメインモデル変換
│   │   └── DemoJson/            # デモ用JSONデータ
│   ├── Realm/               # ローカルDB
│   │   ├── RealmObjects/        # Realm Object
│   │   ├── RealmMapper/         # RealmObject ↔ ドメインモデル変換
│   │   └── RealmRepository/     # リポジトリ実装
│   └── Config/              # 環境設定
│
├── ViewModels/          # Presentation層（ViewModel）
│   └── {Screen}ViewModel
│
└── Views/               # Presentation層（UI）
    ├── ViewControllers/
    └── Storyboards/
```

## 依存方向

```
Views/ViewModels → Application → Models ← Infrastructure
```

- **外側 → 内側のみ依存可能**
- Models層は他のどの層にも依存しない（最内層）
- Infrastructure層はModels層のProtocolを実装する（依存逆転の原則）

## 各レイヤーの責務と制約

### Models層（Domain層）

**責務**: ビジネスロジックの核心。エンティティ、バリューオブジェクト、ドメインサービスを含む。

**制約（絶対）**:
- `import UIKit` 禁止
- `import RealmSwift` 禁止
- `import Alamofire` 禁止
- 外部フレームワークへの依存は一切不可
- 純粋なSwiftのみで記述する

### Application層

**責務**: ユースケースの制御フロー。Models層のみに依存する。

**制約（絶対）**:
- `import UIKit` 禁止
- `import RealmSwift` 禁止
- Models層のProtocol経由でInfrastructure層を利用する

**命名パターン**:
- 取得系: `{Entity}Fetcher`
- 登録系: `{Entity}RegistrationService`

### Infrastructure層

**責務**: 外部連携（API、DB、ファイル等）の実装。Models層のProtocolを実装する。

**パターン（API連携）**: 4ファイル構成
- `{Entity}ApiClient` — API通信
- `{Entity}ApiJson` — JSONレスポンス型
- `{Entity}ApiMapper` — JSON → ドメインモデル変換（腐敗防止層）
- `{Entity}DemoJson` — デモ用JSONデータ

**パターン（Realm永続化）**: 3ファイル構成
- `{Entity}Object` — Realm Object（DBスキーマ）
- `{Entity}RealmMapper` — RealmObject ↔ ドメインモデル変換
- `{Entity}RealmRepository` — リポジトリ実装

**制約**: Entity と RealmObject/ApiJson は別の型。変換はMapper/Repositoryが担う。

### ViewModels層

**責務**: UIに表示するデータの準備。Application層を呼び出す。

**制約**: Infrastructure層を直接呼び出さない。

### Views層

**責務**: UIの表示とユーザー操作の受付。ViewModelを呼び出す。

**制約**: ビジネスロジック、DB操作、API呼び出しを直接記述しない。

## 命名規則

| 種類 | 規則 | 例 |
|------|------|-----|
| Entity | PascalCase | `SurveyResult` |
| ValueObject | PascalCase | `AreaNo` |
| Realm Object | PascalCase + Object接尾辞 | `SurveyResultObject` |
| Repository Protocol | {Entity}Repository | `SurveyResultRepository` |
| Repository実装 | {Entity}RealmRepository | `SurveyResultRealmRepository` |
| AppService（取得） | {Entity}Fetcher | `SurveyResultFetcher` |
| AppService（登録） | {Entity}RegistrationService | `SurveyResultRegistrationService` |
| ViewModel | {Screen}ViewModel | `AreaSelectionViewModel` |
| ViewController | {Screen}ViewController | `AreaSelectionViewController` |
| ApiClient | {Entity}ApiClient | `SurveyResultApiClient` |
| ApiMapper | {Entity}ApiMapper | `SurveyResultApiMapper` |

---
version: 1.0
updated: 2026-04-11
source-name: swift-xctest
---

# Swift + XCTest テストパターン

本ファイルは、SwiftプロジェクトにおけるXCTestを使ったテストの具体的な
書き方・パターンを定義する。

**注意**: Swiftプロジェクトでは現時点でXCTest/XCUITestの導入は将来のロードマップである。
テスト設計書は先に作成し、テスト実装は導入時に行う。

---

## 1. テスト環境

- フレームワーク: XCTest（Xcode標準）
- 将来的にXCUITest（UIテスト）も検討

## 2. テストファイルの配置

```
{ProjectName}Tests/
├── Domain/
│   ├── Entities/
│   │   └── {EntityName}Tests.swift
│   ├── ValueObjects/
│   │   └── {VOName}Tests.swift
│   └── DomainServices/
│       └── {ServiceName}Tests.swift
├── Application/
│   └── {UseCaseName}Tests.swift
└── Infrastructure/
    ├── API/
    │   └── {ApiClient}Tests.swift
    └── Realm/
        └── {Repository}Tests.swift
```

## 3. テストの書き方

### 基本パターン

```swift
import XCTest
@testable import ProjectName

final class AreaNoTests: XCTestCase {

    // MARK: - 正常系

    func test_create_with_valid_value_returns_area_no() {
        // Arrange
        let value = "A-01"

        // Act
        let areaNo = AreaNo(value)

        // Assert
        XCTAssertEqual(areaNo.value, "A-01")
    }

    // MARK: - 異常系

    func test_create_with_empty_string_throws_error() {
        // Arrange & Act & Assert
        XCTAssertThrowsError(try AreaNo("")) { error in
            XCTAssertEqual(error as? DomainError, .invalidAreaNo)
        }
    }

    // MARK: - 等価性

    func test_equal_values_are_equal() {
        let a = AreaNo("A-01")
        let b = AreaNo("A-01")
        XCTAssertEqual(a, b)
    }

    func test_different_values_are_not_equal() {
        let a = AreaNo("A-01")
        let b = AreaNo("B-02")
        XCTAssertNotEqual(a, b)
    }
}
```

### 非同期テスト

```swift
func test_fetch_survey_results_returns_data() async throws {
    // Arrange
    let fetcher = SurveyResultFetcher(repository: MockRepository())

    // Act
    let results = try await fetcher.fetch(areaNo: AreaNo("A-01"))

    // Assert
    XCTAssertFalse(results.isEmpty)
}
```

### モック/スタブ

```swift
final class MockSurveyResultRepository: SurveyResultRepository {
    var stubbedResults: [SurveyResult] = []

    func findByAreaNo(_ areaNo: AreaNo) -> [SurveyResult] {
        return stubbedResults
    }
}
```

## 4. テスト命名規則

```
test_{何を}_{条件}_{期待結果}
```

例:
- `test_create_areaNo_with_valid_value_returns_instance`
- `test_create_areaNo_with_empty_string_throws_error`
- `test_fetch_results_when_area_has_no_data_returns_empty`

## 5. Realmを使うテスト

```swift
// インメモリRealmを使用する
let config = Realm.Configuration(inMemoryIdentifier: "test")
let realm = try! Realm(configuration: config)
```

## 6. os.Loggerのテスト

`os.Logger` のログ出力はXCTestでは直接キャプチャできないため、
ログの検証はプロトコル抽象化またはログレベルの確認で行う。

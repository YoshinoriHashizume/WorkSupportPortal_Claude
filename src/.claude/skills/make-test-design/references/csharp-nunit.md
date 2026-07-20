---
version: 1.0
updated: 2026-04-11
source-name: csharp-nunit
---

# C# + NUnit テストパターン

本ファイルは、C#プロジェクトにおけるNUnitを使ったテストの具体的な
書き方・パターンを定義する。

---

## 1. テスト環境

- フレームワーク: NUnit
- テストデータ: `TestData` フォルダにExcel等の実ファイルを配置（Git管理）

## 2. テストファイルの配置

```
{ProjectName}.Tests/
├── Domain/
│   ├── ValueObjects/
│   │   └── {VOName}Tests.cs
│   └── DomainServices/
│       └── {ServiceName}Tests.cs
├── TestData/                          # テスト用の実ファイル（Git管理）
│   ├── sample_inventory.xlsx
│   └── expected_output.xlsx
└── Infrastructure/
    └── {Repository}Tests.cs
```

## 3. テストの書き方

### バリューオブジェクトのテスト

```csharp
[TestFixture]
public class AreaNoTests
{
    [Test]
    public void Create_WithValidValue_ReturnsAreaNo()
    {
        // Arrange
        var value = "A-01";

        // Act
        var areaNo = new AreaNo(value);

        // Assert
        Assert.That(areaNo.Value, Is.EqualTo("A-01"));
    }

    [Test]
    public void Create_WithEmptyString_ThrowsException()
    {
        // Arrange & Act & Assert
        Assert.Throws<ArgumentException>(() => new AreaNo(""));
    }

    [Test]
    public void Equals_SameValue_ReturnsTrue()
    {
        var a = new AreaNo("A-01");
        var b = new AreaNo("A-01");
        Assert.That(a, Is.EqualTo(b));
    }
}
```

### 実ファイルを使ったテスト

```csharp
[TestFixture]
public class ConsolidateResultTests
{
    private string _testDataPath;

    [SetUp]
    public void SetUp()
    {
        _testDataPath = Path.Combine(
            TestContext.CurrentContext.TestDirectory,
            "TestData"
        );
    }

    [Test]
    public void Consolidate_WithSampleExcel_ReturnsExpectedResult()
    {
        // Arrange
        var inputPath = Path.Combine(_testDataPath, "sample_inventory.xlsx");

        // Act
        var result = ConsolidateService.Execute(inputPath);

        // Assert
        Assert.That(result.TotalCount, Is.EqualTo(150));
    }
}
```

### overload-based output directory injection

テスト時にデスクトップへの書き込みを避けるため、
出力先ディレクトリをオーバーロードで注入する:

```csharp
public class ExportService
{
    // 本番用（デフォルト: デスクトップ）
    public void Export(ConsolidateResult result)
    {
        Export(result, Environment.GetFolderPath(Environment.SpecialFolder.Desktop));
    }

    // テスト用（出力先を注入）
    public void Export(ConsolidateResult result, string outputDirectory)
    {
        // 実際のエクスポート処理
    }
}
```

## 4. テスト命名規則

```
{メソッド名}_{条件}_{期待結果}
```

例:
- `Create_WithValidValue_ReturnsAreaNo`
- `Create_WithEmptyString_ThrowsException`
- `Consolidate_WithSampleExcel_ReturnsExpectedResult`

## 5. バリューオブジェクトのテストパターン（readonly struct）

`readonly struct` + `IEquatable<T>` で実装されたVOに対するテスト:

```csharp
[TestFixture]
public class AreaNoCoverageResultTests
{
    [Test]
    public void IsCovered_WhenAllAreasPresent_ReturnsTrue()
    {
        var expected = new ExpectedAreaNoSet(new[] { "A-01", "A-02" });
        var actual = new[] { new AreaNo("A-01"), new AreaNo("A-02") };

        var result = new AreaNoCoverageResult(expected, actual);

        Assert.That(result.IsCovered, Is.True);
    }

    [Test]
    public void MissingAreas_WhenSomeAreasMissing_ReturnsMissingOnes()
    {
        var expected = new ExpectedAreaNoSet(new[] { "A-01", "A-02", "A-03" });
        var actual = new[] { new AreaNo("A-01") };

        var result = new AreaNoCoverageResult(expected, actual);

        Assert.That(result.MissingAreas, Has.Count.EqualTo(2));
    }
}
```

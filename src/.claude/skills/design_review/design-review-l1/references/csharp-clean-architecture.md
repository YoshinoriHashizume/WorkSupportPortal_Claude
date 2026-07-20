---
version: 1.0
updated: 2026-04-11
source-name: csharp-clean-architecture
---

# C# + Clean Architecture 定義

本ファイルは、C#プロジェクトにおける Clean Architecture のレイヤー構成・
依存方向・各レイヤーの責務を定義する。

機能設計書の作成（make-design）および設計レビュー（design-review-l1/l3）で
共通の基準として使用する。

## レイヤー構成

（プロジェクトの設計が確定した段階で記述する）

## 依存方向

（プロジェクトの設計が確定した段階で記述する）

## 各レイヤーの責務と制約

（プロジェクトの設計が確定した段階で記述する）

## 命名規則

（プロジェクトの設計が確定した段階で記述する）

## DDD戦術的設計パターン

### バリューオブジェクト

`readonly struct` + `IEquatable<T>` で実装する。

```csharp
public readonly struct AreaNo : IEquatable<AreaNo>
{
    public string Value { get; }

    public AreaNo(string value)
    {
        // バリデーション
        Value = value;
    }

    public bool Equals(AreaNo other) => Value == other.Value;
    public override bool Equals(object? obj) => obj is AreaNo other && Equals(other);
    public override int GetHashCode() => Value.GetHashCode();
}
```

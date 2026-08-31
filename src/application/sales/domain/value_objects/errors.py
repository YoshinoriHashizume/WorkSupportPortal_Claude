from __future__ import annotations

"""基幹 Oracle 参照の共有カーネルが送出する例外。

基幹 Oracle（MARI）は参照専用の共有カーネルであり、接続不備・問い合わせ失敗は
利用側のどの境界コンテキストでも同じ意味を持つ。そのため例外の定義はここに置き、
各コンテキストはこのモジュールから import する。
"""


class OracleNotConfiguredError(RuntimeError):
    """基幹 Oracle への接続設定が不足している。"""


class OracleQueryError(RuntimeError):
    """基幹 Oracle への問い合わせが失敗した。"""


__all__ = [
    "OracleNotConfiguredError",
    "OracleQueryError",
]

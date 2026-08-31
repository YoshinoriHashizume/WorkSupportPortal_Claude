"""在庫数の 3 状態（値あり／該当なし／未取得）の表現（design.md §4.2）。

在庫数には次の 3 つの状態があり、取り違えると発注判断を誤らせる。

| 状態 | 意味 | 表示 |
|---|---|---|
| 値あり | 在庫が存在する（0 を含む） | 数値 |
| 該当なし | 突合先にその品番が存在しない | 空 |
| 未取得 | この機能の導入前に作られたスナップショット | `－` |

「未取得」は **行にキーが存在しないこと** で表す。`None` で埋めると
「該当なし」の空と区別できなくなるため、値では表さない。
"""

from __future__ import annotations

from application.inventory_order_alert.domain.value_objects.format_display import format_quantity_display

#: 在庫数が未取得であることを示す標識。既存スナップショットには在庫数のキー自体が無い。
STOCK_NOT_FETCHED = "－"


def is_stock_fetched(row: dict[str, object], key: str) -> bool:
    """行に在庫数のキーが存在するか。

    値が空文字（該当なし）や 0 でも、キーがあれば取得済みとみなす。
    """
    return key in row


def format_stock_quantity(value: object, *, fetched: bool = True) -> str:
    """在庫数を表示用の文字列にする。

    未取得のときは値によらず標識を返す。取得済みなら既存の数量整形に委ね、
    該当なし（空）と 0 を区別したまま返す。
    """
    if not fetched:
        return STOCK_NOT_FETCHED
    return format_quantity_display(value)

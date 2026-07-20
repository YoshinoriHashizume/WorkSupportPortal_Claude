from __future__ import annotations


def numeric_code_sort_key(code: str) -> tuple[int, int | str]:
    """数値のみのコードは数値昇順、それ以外は末尾で文字列昇順。"""
    stripped = str(code).strip()
    if stripped.isdigit():
        return (0, int(stripped))
    return (1, stripped)

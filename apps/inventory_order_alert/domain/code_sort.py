from __future__ import annotations


def numeric_code_sort_key(code: str) -> tuple[int, int | str]:
    stripped = str(code).strip()
    if stripped.isdigit():
        return (0, int(stripped))
    return (1, stripped)

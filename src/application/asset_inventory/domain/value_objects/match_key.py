from __future__ import annotations


def normalize_asset_number(value: str) -> str:
    text = (value or "").strip()
    if text and text[0] in ("L", "l"):
        text = text[1:]
    return text.strip()


def normalize_branch_number(value: str) -> str:
    return (value or "").strip()


def build_match_key(asset_number: str, branch_number: str) -> str:
    return f"{normalize_asset_number(asset_number)}|{normalize_branch_number(branch_number)}"

from __future__ import annotations

from collections.abc import Iterable, Sequence
from typing import Protocol


class CustFilterOption(Protocol):
    value: str
    label: str


CustChrgCustIndex = dict[str, dict[str, str]]


def build_cust_chrg_cust_index(rows: Iterable[dict[str, object]]) -> CustChrgCustIndex:
    index: CustChrgCustIndex = {}
    for row in rows:
        chrg_code = str(row.get("cust_chrg_psn_cd") or "").strip()
        cust_code = str(row.get("cust_code") or "").strip()
        cust_name = str(row.get("cust_name") or "").strip()
        if not chrg_code or not cust_code:
            continue
        bucket = index.setdefault(chrg_code, {})
        if cust_name:
            bucket[cust_code] = cust_name
        else:
            bucket.setdefault(cust_code, "")
    return index


def cust_options_for_chrg_psn(
    all_cust_options: Sequence[CustFilterOption],
    index: CustChrgCustIndex,
    cust_chrg_psn_cd: str,
) -> tuple[CustFilterOption, ...]:
    chrg_code = cust_chrg_psn_cd.strip()
    if not chrg_code:
        return tuple(all_cust_options)
    allowed = index.get(chrg_code, {})
    return tuple(option for option in all_cust_options if option.value in allowed)


def sanitize_cust_code(
    cust_code: str,
    visible_options: Sequence[CustFilterOption],
) -> str:
    code = cust_code.strip()
    if not code:
        return ""
    valid = {option.value for option in visible_options}
    return code if code in valid else ""

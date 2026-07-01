from __future__ import annotations

from collections.abc import Callable

from dataclasses import dataclass

from applications.inventory_order_alert.domain.confirmation import (
    memo_entry_to_dict,
    parse_memo_entry_payload,
)
from applications.inventory_order_alert.domain.confirmation import MemoEntryRecord

ListConfirmationMemos = Callable[..., list[dict[str, str]]]
AddConfirmationMemo = Callable[..., MemoEntryRecord]
ResolveUserDisplayNames = Callable[[set[str]], dict[str, str]]


@dataclass(frozen=True)
class ConfirmationMemosListResult:
    memos: list[dict[str, object]]


@dataclass(frozen=True)
class ConfirmationMemosAddResult:
    memo: dict[str, object]


class ConfirmationMemosUsecase:
    def __init__(
        self,
        list_confirmation_memos: ListConfirmationMemos,
        add_confirmation_memo: AddConfirmationMemo,
        resolve_user_display_names: ResolveUserDisplayNames,
    ) -> None:
        self._list_confirmation_memos = list_confirmation_memos
        self._add_confirmation_memo = add_confirmation_memo
        self._resolve_user_display_names = resolve_user_display_names

    def list_memos(self, *, cust_code: str, item_cd: str) -> ConfirmationMemosListResult:
        if not cust_code or not item_cd:
            raise ValueError("custCode と itemCd は必須です。")
        return ConfirmationMemosListResult(
            memos=self._list_confirmation_memos(cust_code=cust_code, item_cd=item_cd),
        )

    def add_memo(self, payload: dict[str, object], *, created_by: str) -> ConfirmationMemosAddResult:
        input_data = parse_memo_entry_payload(payload)
        entry = self._add_confirmation_memo(
            cust_code=input_data.cust_code,
            item_cd=input_data.item_cd,
            content=input_data.content,
            created_by=created_by,
        )
        author_names = self._resolve_user_display_names({created_by})
        return ConfirmationMemosAddResult(
            memo=memo_entry_to_dict(entry, author_names=author_names),
        )

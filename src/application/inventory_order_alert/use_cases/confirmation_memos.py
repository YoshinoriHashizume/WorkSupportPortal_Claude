from __future__ import annotations

from dataclasses import dataclass

from application.inventory_order_alert.domain.repositories.ports import (
    AddConfirmationMemo,
    ListConfirmationMemos,
    LoadSummary,
    ResolveUserDisplayNames,
)
from application.inventory_order_alert.domain.value_objects.confirmation import (
    memo_entry_to_dict,
    parse_memo_entry_payload,
)
from application.inventory_order_alert.domain.value_objects.reconciliation_unit_row import unit_item_cds_for


@dataclass(frozen=True)
class ConfirmationMemosListResult:
    memos: list[dict[str, object]]


@dataclass(frozen=True)
class ConfirmationMemosAddResult:
    memo: dict[str, object]


class ConfirmationMemos:
    """確認メモを照合単位行（T-213）に対して読み書きする（spec/13 REQ-RUR-F-011・F-012）。

    `load_summary` を渡すと、受け取った（得意先, 得意先品番）を含む照合単位行の得意先品番すべてを対象にする。
    渡さないとき（集計がないときを含む）は受け取った得意先品番だけ。
    """

    def __init__(
        self,
        list_confirmation_memos: ListConfirmationMemos,
        add_confirmation_memo: AddConfirmationMemo,
        resolve_user_display_names: ResolveUserDisplayNames,
        *,
        load_summary: LoadSummary | None = None,
    ) -> None:
        self._list_confirmation_memos = list_confirmation_memos
        self._add_confirmation_memo = add_confirmation_memo
        self._resolve_user_display_names = resolve_user_display_names
        self._load_summary = load_summary

    def _item_cds(self, *, cust_code: str, item_cd: str) -> tuple[str, ...]:
        summary = self._load_summary() if self._load_summary is not None else None
        rows = list(summary.rows) if summary is not None else []
        return unit_item_cds_for(rows, cust_code=cust_code, item_cd=item_cd)

    def list_memos(self, *, cust_code: str, item_cd: str) -> ConfirmationMemosListResult:
        if not cust_code or not item_cd:
            raise ValueError("custCode と itemCd は必須です。")
        return ConfirmationMemosListResult(
            memos=self._list_confirmation_memos(
                cust_code=cust_code,
                item_cd=item_cd,
                item_cds=self._item_cds(cust_code=cust_code, item_cd=item_cd),
            ),
        )

    def add_memo(self, payload: dict[str, object], *, created_by: str) -> ConfirmationMemosAddResult:
        input_data = parse_memo_entry_payload(payload)
        entry = self._add_confirmation_memo(
            cust_code=input_data.cust_code,
            item_cd=input_data.item_cd,
            content=input_data.content,
            created_by=created_by,
            item_cds=self._item_cds(cust_code=input_data.cust_code, item_cd=input_data.item_cd),
        )
        author_names = self._resolve_user_display_names({created_by})
        return ConfirmationMemosAddResult(
            memo=memo_entry_to_dict(entry, author_names=author_names),
        )

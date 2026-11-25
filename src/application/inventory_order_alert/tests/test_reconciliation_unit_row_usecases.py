"""確認状態・確認メモを照合単位行（T-213）に対して書く（spec/13 test-design TC-RUR-A-001〜005）。"""

from __future__ import annotations

from datetime import date, datetime

from application.inventory_order_alert.domain.value_objects.confirmation import ConfirmationRecord, MemoEntryRecord
from application.inventory_order_alert.domain.value_objects.reconciliation_unit_row import build_reconciliation_unit_rows
from application.inventory_order_alert.domain.value_objects.summary import SummaryLoadResult
from application.inventory_order_alert.tests.test_reconciliation_unit_row import (
    _single_s_row,
    _unit_a_rows,
    _unit_b_rows,
)
from application.inventory_order_alert.use_cases.confirmation_memos import ConfirmationMemos
from application.inventory_order_alert.use_cases.save_confirmation import SaveConfirmationUseCase

AS_OF = date(2026, 11, 25)


def _summary() -> SummaryLoadResult:
    rows = build_reconciliation_unit_rows(_unit_a_rows() + _unit_b_rows() + [_single_s_row()])
    return SummaryLoadResult(
        rows=rows,
        stock_info=None,
        as_of_date=AS_OF,
        aggregation_error="",
        total_count=len(rows),
        critical_count=0,
        warning_count=0,
    )


class _FakeSave:
    def __init__(self) -> None:
        self.calls: list[dict[str, object]] = []

    def __call__(self, input_data, *, confirmed_by, flow_quadrant="", item_cds=()):
        self.calls.append({"input": input_data, "item_cds": tuple(item_cds)})
        return ConfirmationRecord(
            cust_code=input_data.cust_code,
            item_cd=input_data.item_cd,
            status=input_data.status,
            memo="",
            confirmed_flow_quadrant=flow_quadrant,
            confirmed_at=None,
            confirmed_by=confirmed_by,
        )


def _save(payload: dict[str, object]) -> tuple[_FakeSave, dict[str, object]]:
    fake = _FakeSave()
    result = SaveConfirmationUseCase(_summary, fake).execute(payload, confirmed_by="u1")
    return fake, result


def test_a001_confirmation_is_saved_to_every_item_of_the_unit():
    fake, _result = _save({"custCode": "308", "itemCd": "Q", "status": "confirmed"})

    assert set(fake.calls[0]["item_cds"]) == {"P", "Q"}


def test_a002_unknown_row_saves_only_the_given_item():
    fake, _result = _save({"custCode": "999", "itemCd": "ZZZ", "status": "confirmed"})

    assert fake.calls[0]["item_cds"] == ("ZZZ",)


def test_a003_counts_are_unit_rows():
    _fake, result = _save({"custCode": "308", "itemCd": "Q", "status": "confirmed"})

    assert sum(result["counts"][key] for key in ("orderOverdue", "deliveryCheck", "orderNeeded", "watch", "noneResponse")) == 3


class _FakeMemos:
    def __init__(self) -> None:
        self.added: list[dict[str, object]] = []
        self.listed: list[dict[str, object]] = []

    def list(self, *, cust_code, item_cd, item_cds=()):
        self.listed.append({"item_cds": tuple(item_cds)})
        return [{"content": "1 件にまとめた結果"}]

    def add(self, *, cust_code, item_cd, content, created_by, item_cds=()):
        self.added.append({"item_cds": tuple(item_cds), "content": content})
        return MemoEntryRecord(created_at=datetime(2026, 11, 25, 9, 0), created_by=created_by, content=content)


def _memos() -> tuple[_FakeMemos, ConfirmationMemos]:
    fake = _FakeMemos()
    use_case = ConfirmationMemos(fake.list, fake.add, lambda names: {}, load_summary=_summary)
    return fake, use_case


def test_a004_memo_is_added_to_every_item_of_the_unit():
    fake, use_case = _memos()

    use_case.add_memo({"custCode": "308", "itemCd": "Q", "content": "仕入先に確認"}, created_by="u1")

    assert set(fake.added[0]["item_cds"]) == {"P", "Q"}


def test_a005_memo_list_is_collected_from_the_unit_items():
    fake, use_case = _memos()

    result = use_case.list_memos(cust_code="308", item_cd="Q")

    assert set(fake.listed[0]["item_cds"]) == {"P", "Q"}
    assert len(result.memos) == 1

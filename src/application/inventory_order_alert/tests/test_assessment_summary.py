"""判定サマリ（T-211）のテスト（test-design.md TC-DDC-S-*）。

詳細ダイアログの先頭で「在庫は切れるのか、切れないのか」に一文で答える。
**新しい判定はせず**、対応区分（S-204）・在庫切れ日（V-232）・発注期限（V-233）を読み替えるだけ（10 design §2.1）。
"""

from __future__ import annotations

from datetime import date

import pytest

from application.inventory_order_alert.domain.value_objects.assessment_summary import (
    NEXT_ACTIONS,
    build_assessment_summary,
)
from application.inventory_order_alert.domain.value_objects.stockout_risk import RESPONSE_CLASSES

AS_OF = date(2026, 9, 18)


def _row(**overrides: object) -> dict[str, object]:
    row: dict[str, object] = {
        "response_class": "対象外",
        "stockout_date": "",
        "order_deadline": "",
        "response_reasons": [],
        "safety_stock": 0.0,
        "overdue_order_qty": 0,
        "overdue_order_count": 0,
    }
    row.update(overrides)
    return row


def _summary(**overrides: object):
    return build_assessment_summary(_row(**overrides), as_of_date=AS_OF)


# --- TC-DDC-S-001〜005: 対応区分ごとの見出し ---


def test_s001_order_overdue_headline():
    summary = _summary(response_class="発注遅れ", stockout_date="2026/09/25", order_deadline="2026/09/15")

    assert summary.headline == "この品番は 2026/09/25 に在庫が切れます。発注期限 2026/09/15 は過ぎています"


def test_s002_order_needed_headline():
    summary = _summary(response_class="要発注", stockout_date="2026/10/10", order_deadline="2026/10/05")

    assert summary.headline == "この品番は 2026/10/10 に在庫が切れます。2026/10/05 までに発注が必要です"


def test_s003_delivery_check_without_a_stockout_date():
    summary = _summary(response_class="納期確認", overdue_order_qty=120, overdue_order_count=3)

    assert summary.headline == "在庫は足ります。ただし納期遅れの発注残 3 件 120 個があります"


def test_s003b_delivery_check_with_a_stockout_date():
    """S-204 では「切れる かつ 納期遅れあり」も納期確認になる。

    2026-09-30: 一律「在庫は足ります」としていたため、実データ 271 行中 216 行で
    見出しが事実と逆になっていた。在庫切れ日の有無で文を分ける。
    """
    summary = _summary(
        response_class="納期確認",
        stockout_date="2026/10/05",
        order_deadline="2026/10/03",
        overdue_order_qty=2400,
        overdue_order_count=1,
    )

    assert summary.headline == (
        "この品番は 2026/10/05 に在庫が切れます。2026/10/03 までに発注が必要です。"
        "あわせて納期遅れの発注残 1 件 2,400 個の納期を確認してください"
    )
    assert summary.deadline_text == "2026/10/03（あと 15 日）"


def test_s004_watch_headline():
    summary = _summary(response_class="要監視", safety_stock=1000)

    assert summary.headline == "在庫は切れませんが、安全在庫 1,000 を下回ります"


def test_s005_none_headline():
    assert _summary().headline == "在庫は切れません"


# --- TC-DDC-S-006: 次にすること ---


def test_s006_next_action_is_defined_for_every_response_class():
    assert set(NEXT_ACTIONS) == set(RESPONSE_CLASSES)
    assert all(NEXT_ACTIONS[label] for label in RESPONSE_CLASSES)


@pytest.mark.parametrize("label", RESPONSE_CLASSES)
def test_s006_summary_carries_the_next_action(label):
    summary = _summary(response_class=label)

    assert summary.next_action == NEXT_ACTIONS[label]
    assert summary.response_class == label


# --- TC-DDC-S-007〜010: 発注期限の残り日数 ---


def test_s007_deadline_shows_days_left():
    summary = _summary(response_class="要発注", stockout_date="2026/10/10", order_deadline="2026/10/05")

    assert summary.deadline_text == "2026/10/05（あと 17 日）"


def test_s008_deadline_today():
    summary = _summary(response_class="発注遅れ", stockout_date="2026/09/23", order_deadline="2026/09/18")

    assert summary.deadline_text == "2026/09/18（本日）"


def test_s009_deadline_already_passed():
    summary = _summary(response_class="発注遅れ", stockout_date="2026/09/25", order_deadline="2026/09/13")

    assert summary.deadline_text == "2026/09/13（5 日超過）"


def test_s010_no_stockout_means_no_deadline_text():
    assert _summary().deadline_text == ""


# --- TC-DDC-S-011/012: 安全側の扱い ---


def test_s011_old_snapshot_without_response_class_is_none():
    summary = build_assessment_summary({"cust_code": "100", "item_cd": "X"}, as_of_date=AS_OF)

    assert summary.response_class == "対象外"
    assert summary.headline == "在庫は切れません"
    assert summary.deadline_text == ""


def test_s012_order_needed_without_a_stockout_date_falls_back():
    """在庫切れ日が無いのに 要発注 になることは定義上ないが、起きたら安全側へ倒す。"""
    summary = _summary(response_class="要発注", stockout_date="", order_deadline="")

    assert summary.headline == "在庫は切れません"


# --- TC-DDC-S-013/014 ---


def test_s013_reasons_are_carried_through():
    reasons = ["在庫切れ 2026/10/10", "発注期限 2026/10/05"]
    summary = _summary(response_class="要発注", stockout_date="2026/10/10", order_deadline="2026/10/05", response_reasons=reasons)

    assert summary.reasons == tuple(reasons)


def test_s014_quantities_use_thousand_separators():
    summary = _summary(response_class="納期確認", overdue_order_qty=12000, overdue_order_count=2)

    assert "12,000 個" in summary.headline


def test_delivery_check_headline_never_claims_enough_stock_when_it_runs_out():
    """在庫切れ日がある納期確認で「在庫は足ります」と言わないこと（回帰防止）。"""
    summary = _summary(response_class="納期確認", stockout_date="2026/10/05", order_deadline="2026/10/03", overdue_order_qty=10, overdue_order_count=1)

    assert "在庫は足ります" not in summary.headline
    assert "在庫が切れます" in summary.headline


def test_no_exception_on_broken_dates():
    summary = _summary(response_class="要発注", stockout_date="おかしな日付", order_deadline="おかしな日付")

    assert summary.headline  # 例外にならない

from __future__ import annotations

from datetime import date

from application.shipment_trend.domain.value_objects.app_settings import AppSettings
from application.shipment_trend.domain.value_objects.summary import SummaryLoadResult
from application.shipment_trend.use_cases.delete_baseline_year import DeleteBaselineYear
from application.shipment_trend.use_cases.refresh_data import RefreshData
from application.shipment_trend.use_cases.save_alert_settings import SaveAlertSettings
from application.shipment_trend.use_cases.save_baseline_year import SaveBaselineYear


def test_save_alert_settings_uses_injected_saver():
    saved: list[tuple[AppSettings, object]] = []

    def save(settings: AppSettings, *, updated_by: object) -> None:
        saved.append((settings, updated_by))

    usecase = SaveAlertSettings(save)
    result = usecase.execute(
        {"decreaseThresholdPct": 10, "increaseThresholdPct": 20},
        updated_by="tester",
    )
    assert result.decrease_threshold_pct == 10.0
    assert result.increase_threshold_pct == 20.0
    assert len(saved) == 1
    assert saved[0][1] == "tester"


def test_refresh_data_uses_injected_create_refresh_record():
    created: list[object] = []

    def create_refresh_record(*, user: object | None) -> object:
        record = {"user": user}
        created.append(record)
        return record

    def run_aggregation(refresh_record: object) -> tuple[str, int]:
        assert refresh_record in created
        return ("", 3)

    usecase = RefreshData(run_aggregation=run_aggregation, create_refresh_record=create_refresh_record)
    result = usecase.execute(user="u1")
    assert result.error == ""
    assert result.row_count == 3
    assert "3" in result.message
    assert created == [{"user": "u1"}]


def test_refresh_data_returns_error_message_on_aggregation_failure():
    usecase = RefreshData(
        run_aggregation=lambda _record: ("boom", 0),
        create_refresh_record=lambda **_: object(),
    )
    result = usecase.execute(user=None)
    assert result.error == "boom"
    assert result.row_count == 0
    assert "エラー" in result.message


def test_save_baseline_year_rejects_unavailable_year():
    summary = SummaryLoadResult(
        rows=[
            {
                "cust_code": "101",
                "item_cd": "ITEM-1",
                "monthly": {"2024-04": 10, "2025-04": 20},
            }
        ],
        as_of_date=date(2025, 6, 1),
        aggregation_error="",
        total_count=1,
        refreshed_at=date(2025, 6, 1),
    )
    saved: list[dict[str, object]] = []

    def save_baseline_year(**kwargs):
        saved.append(kwargs)

    usecase = SaveBaselineYear(load_summary=lambda: summary, save_baseline_year=save_baseline_year)
    try:
        usecase.execute(
            cust_code="101",
            item_cd="ITEM-1",
            baseline_fiscal_year=2099,
            updated_by="u1",
        )
        assert False, "expected ValueError"
    except ValueError as exc:
        assert "候補" in str(exc)
    assert saved == []


def test_save_and_delete_baseline_year_usecases():
    summary = SummaryLoadResult(
        rows=[
            {
                "cust_code": "101",
                "item_cd": "ITEM-1",
                "monthly": {"2023-04": 10, "2024-04": 100, "2025-04": 20},
            }
        ],
        as_of_date=date(2025, 6, 1),
        aggregation_error="",
        total_count=1,
        refreshed_at=date(2025, 6, 1),
    )
    store: dict[tuple[str, str], int] = {}

    def save_baseline_year(*, cust_code, item_cd, baseline_fiscal_year, updated_by):
        store[(cust_code, item_cd)] = baseline_fiscal_year

    def delete_baseline_year(*, cust_code, item_cd):
        return store.pop((cust_code, item_cd), None) is not None

    save_uc = SaveBaselineYear(load_summary=lambda: summary, save_baseline_year=save_baseline_year)
    result = save_uc.execute(
        cust_code="101",
        item_cd="ITEM-1",
        baseline_fiscal_year=2024,
        updated_by="u1",
    )
    assert result.baseline_fiscal_year == 2024
    assert store[("101", "ITEM-1")] == 2024

    delete_uc = DeleteBaselineYear(delete_baseline_year=delete_baseline_year)
    deleted = delete_uc.execute(cust_code="101", item_cd="ITEM-1")
    assert deleted.deleted is True
    assert store == {}

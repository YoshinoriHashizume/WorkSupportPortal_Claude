from __future__ import annotations

from application.shipment_trend.domain.value_objects.app_settings import AppSettings
from application.shipment_trend.use_cases.refresh_data import RefreshData
from application.shipment_trend.use_cases.save_alert_settings import SaveAlertSettings


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

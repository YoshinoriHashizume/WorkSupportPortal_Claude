from __future__ import annotations

from application.shipment_trend.domain.value_objects.least_squares import compute_least_squares_regression


def test_compute_least_squares_perfect_line():
    points = [
        {"yearMonth": "2025-01", "qty": 10},
        {"yearMonth": "2025-02", "qty": 20},
        {"yearMonth": "2025-03", "qty": 30},
    ]
    result = compute_least_squares_regression(points)
    assert result is not None
    assert result["slope"] == 10.0
    assert result["intercept"] == 10.0
    assert result["r_squared"] == 1.0
    assert len(result["regression_points"]) == 3
    assert result["regression_points"][0]["qty"] == 10.0
    assert result["regression_points"][2]["qty"] == 30.0
    assert result["regression_points"][1]["kind"] == "regression"


def test_compute_least_squares_requires_two_points():
    assert compute_least_squares_regression([]) is None
    assert compute_least_squares_regression([{"yearMonth": "2025-01", "qty": 5}]) is None


def test_compute_least_squares_handles_flat_series():
    points = [
        {"yearMonth": "2025-01", "qty": 7},
        {"yearMonth": "2025-02", "qty": 7},
        {"yearMonth": "2025-03", "qty": 7},
    ]
    result = compute_least_squares_regression(points)
    assert result is not None
    assert result["slope"] == 0.0
    assert result["intercept"] == 7.0
    assert result["r_squared"] == 1.0

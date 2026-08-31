from __future__ import annotations


def compute_least_squares_regression(
    points: list[dict[str, object]],
) -> dict[str, object] | None:
    """実績＋予測点に対する線形最小二乗 `y = a + b·x` を計算する。

    横軸は表示系列先頭を 0 とした通番。点が 2 未満、または分散が無い場合は None。
    """
    if len(points) < 2:
        return None

    n = len(points)
    xs = list(range(n))
    ys = [float(point.get("qty") or 0) for point in points]
    sum_x = sum(xs)
    sum_y = sum(ys)
    sum_xx = sum(x * x for x in xs)
    sum_xy = sum(x * y for x, y in zip(xs, ys))
    denom = n * sum_xx - sum_x * sum_x
    if denom == 0:
        return None

    slope = (n * sum_xy - sum_x * sum_y) / denom
    intercept = (sum_y - slope * sum_x) / n
    y_mean = sum_y / n
    ss_tot = sum((y - y_mean) ** 2 for y in ys)
    ss_res = sum((y - (intercept + slope * x)) ** 2 for x, y in zip(xs, ys))
    if ss_tot == 0:
        r_squared = 1.0
    else:
        r_squared = 1.0 - (ss_res / ss_tot)

    regression_points = [
        {
            "yearMonth": str(points[index]["yearMonth"]),
            "qty": intercept + slope * index,
            "kind": "regression",
        }
        for index in xs
    ]
    return {
        "slope": round(slope, 6),
        "intercept": round(intercept, 6),
        "r_squared": round(r_squared, 6),
        "regression_points": regression_points,
    }

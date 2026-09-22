"""需要予測（V-220）・在庫切れ予測月（V-221）・在庫月数（V-222）（05 design §4.6）。

照合単位（T-208）ごとに、内示推移（V-219）を (得意先, 内作品番) の重複を除いて合算する。
内示がなければ「なし」（07 REQ-FQR-F-002。出荷実績の平均による代替は 2026/09/21 に廃止）。
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import date
from typing import Literal

from application.inventory_order_alert.domain.value_objects.dates import add_calendar_months
from application.inventory_order_alert.domain.value_objects.reconciliation_unit import ReconciliationUnits
from application.inventory_order_alert.domain.value_objects.stock_quantity import is_stock_fetched

BASIS_UNCONFIRMED = "内示"
BASIS_NONE = "なし"
DEMAND_FORECAST_BASES = (BASIS_UNCONFIRMED, BASIS_NONE)
DemandForecastBasis = Literal["内示", "なし"]

#: 在庫切れ予測月の上限（この月数を超えても尽きなければ「十分」＝ None）。REQ-SFV-F-018
STOCKOUT_FORECAST_LIMIT_MONTHS = 120

#: 翌月〜翌々々月。
FORECAST_MONTHS = 3


@dataclass(frozen=True)
class DemandForecast:
    basis: DemandForecastBasis
    current_month_remaining: int
    monthly: tuple[int, int, int]
    monthly_average: float

    def __post_init__(self) -> None:
        if self.basis not in DEMAND_FORECAST_BASES:
            raise ValueError(f"需要予測の算出根拠は {DEMAND_FORECAST_BASES} のいずれか: {self.basis!r}")
        object.__setattr__(self, "monthly", tuple(int(qty) for qty in self.monthly))

    @property
    def has_demand(self) -> bool:
        return self.basis != BASIS_NONE and (self.monthly_average > 0 or any(self.monthly) or self.current_month_remaining > 0)


NO_DEMAND = DemandForecast(basis=BASIS_NONE, current_month_remaining=0, monthly=(0, 0, 0), monthly_average=0.0)


def _trend_qtys(trend: object) -> list[int]:
    if not isinstance(trend, list):
        return []
    qtys: list[int] = []
    for point in trend:
        try:
            qtys.append(int((point or {}).get("qty") or 0))
        except (TypeError, ValueError, AttributeError):
            qtys.append(0)
    return qtys


def _month_key(value: date) -> str:
    return f"{value.year:04d}-{value.month:02d}"


def build_demand_forecast(unit_rows: list[dict[str, object]], *, as_of_date: date) -> DemandForecast:
    """照合単位の行から需要予測を作る。

    (cust_code, internal_item_cd) で重複を除いて内示推移を月ごとに合算し、翌月〜翌々々月の合計が 0 なら なし。
    出荷実績は見ない（07 REQ-FQR-F-002）。
    """
    _ = as_of_date
    totals = [0] * (FORECAST_MONTHS + 1)
    seen: set[tuple[str, str]] = set()
    for row in unit_rows:
        key = (str(row.get("cust_code") or "").strip(), str(row.get("internal_item_cd") or "").strip())
        if key in seen:
            continue
        seen.add(key)
        for index, qty in enumerate(_trend_qtys(row.get("unconfirmed_order_trend"))[: FORECAST_MONTHS + 1]):
            totals[index] += max(qty, 0)

    monthly = (totals[1], totals[2], totals[3])
    if sum(monthly) > 0:
        months_with_orders = [qty for qty in monthly if qty > 0]
        return DemandForecast(
            basis=BASIS_UNCONFIRMED,
            current_month_remaining=totals[0],
            monthly=monthly,
            monthly_average=round(sum(months_with_orders) / len(months_with_orders), 4),
        )
    return NO_DEMAND


def _stock_value(row: dict[str, object]) -> float:
    text = str(row.get("stock_qty") or "").replace(",", "").strip()
    if not text:
        return 0.0
    try:
        return float(text)
    except ValueError:
        return 0.0


def stock_total_of(unit_rows: list[dict[str, object]]) -> float | None:
    """単位の在庫合計。該当なし（空）は 0、未取得は 0、全品番が未取得なら None。得意先品番の重複は 1 回だけ数える。"""
    seen: set[str] = set()
    total = 0.0
    fetched_any = False
    for row in unit_rows:
        item_cd = str(row.get("item_cd") or "").strip()
        if item_cd in seen:
            continue
        seen.add(item_cd)
        if not is_stock_fetched(row, "stock_qty"):
            continue
        fetched_any = True
        total += _stock_value(row)
    return total if fetched_any else None


def stockout_forecast_month(stock_total: float | None, forecast: DemandForecast, *, as_of_date: date) -> str | None:
    """在庫切れ予測月（V-221）。当月残を引き、翌月から月別需要（4 か月目以降は平均）を順に引いて初めて負になる月。

    在庫 0 でも需要が出るまでは尽きないので、在庫 0 の照合単位は需要が初めて出る月になる
    （2026/09/21、07 REQ-FQR-F-002。「在庫 0 以下は当月」の特例を廃止）。
    """
    if stock_total is None or not forecast.has_demand:
        return None
    remaining = stock_total - forecast.current_month_remaining
    if remaining < 0:
        return _month_key(as_of_date)
    month_first = date(as_of_date.year, as_of_date.month, 1)
    for offset in range(1, STOCKOUT_FORECAST_LIMIT_MONTHS + 1):
        demand = forecast.monthly[offset - 1] if offset <= FORECAST_MONTHS else forecast.monthly_average
        remaining -= demand
        if remaining < 0:
            return _month_key(add_calendar_months(month_first, offset))
    return None


def months_of_stock(stock_total: float | None, forecast: DemandForecast) -> float | None:
    """在庫月数（V-222）= 在庫合計 ÷ 月平均需要。小数 1 桁。需要なし・平均 0・在庫未取得は None。"""
    if stock_total is None or forecast.basis == BASIS_NONE or forecast.monthly_average <= 0:
        return None
    return round(stock_total / forecast.monthly_average, 1)


def attach_demand_forecast(rows: list[dict[str, object]], as_of_date: date) -> list[dict[str, object]]:
    """全行に照合単位の需要予測を複製して付与する（入力は変更しない。05 design §5.2）。"""
    units = ReconciliationUnits.build(rows)
    cache: dict[str, dict[str, object]] = {}
    enriched: list[dict[str, object]] = []
    for row in rows:
        copied = dict(row)
        unit = units.unit_of(str(row.get("item_cd") or ""))
        if unit is None:
            copied.update(_forecast_fields(None, NO_DEMAND, None, as_of_date=as_of_date))
            enriched.append(copied)
            continue
        if unit.key not in cache:
            unit_rows = units.rows_of(unit, rows)
            forecast = build_demand_forecast(unit_rows, as_of_date=as_of_date)
            stock_total = stock_total_of(unit_rows)
            cache[unit.key] = _forecast_fields(unit.key, forecast, stock_total, as_of_date=as_of_date)
        copied.update(cache[unit.key])
        enriched.append(copied)
    return enriched


def _forecast_fields(unit_key: str | None, forecast: DemandForecast, stock_total: float | None, *, as_of_date: date) -> dict[str, object]:
    return {
        "reconciliation_unit_key": unit_key or "",
        "demand_forecast_basis": forecast.basis,
        "demand_forecast_current_month_remaining": forecast.current_month_remaining,
        "demand_forecast_monthly": list(forecast.monthly),
        "demand_forecast_monthly_average": forecast.monthly_average,
        "demand_forecast_stock_total": stock_total,
        "months_of_stock": months_of_stock(stock_total, forecast),
        "stockout_forecast_month": stockout_forecast_month(stock_total, forecast, as_of_date=as_of_date),
    }

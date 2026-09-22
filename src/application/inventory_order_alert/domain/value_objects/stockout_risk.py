"""在庫切れリスク（S-204）の判定（06 design §4.3）。

目的は「お客さんの納期どおりに納める＝在庫切れを起こさない」。在庫切れ予測月（V-221）に
補充見込み（V-226、発注残）とリードタイム（V-225）を突き合わせ、行ごとに
危険 / 注意 / 監視 / 対象外 と理由を決める。判定は取込時に行い、スナップショットに保存する。

2026/09/21 改訂（目的に照らした判定レビュー）: 危険は「補充見込みが不足数量に満たない」まで広げ、
補充サイクル稼働中の免除は MRP 発注に限り、MRP 発注で発注期限が先・発注残なしの行は対象外にする。
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import date

from application.inventory_order_alert.domain.value_objects.dates import add_calendar_months, parse_optional_ymd
from application.inventory_order_alert.domain.value_objects.demand_forecast import (
    BASIS_NONE,
    BASIS_UNCONFIRMED,
    DEMAND_FORECAST_BASES,
    FORECAST_MONTHS,
    DemandForecast,
    NO_DEMAND,
)
from application.inventory_order_alert.domain.value_objects.flow_facts import row_recent_incoming, row_stock_missing
from application.inventory_order_alert.domain.value_objects.flow_quadrant import (
    DEFAULT_FLOW_THRESHOLDS,
    QUADRANT_DORMANT_STOCK,
    QUADRANT_LOW_FLOW_NO_INCOMING,
    QUADRANT_LOW_FLOW_NO_SHIPMENT,
    QUADRANT_NORMAL_FLOW,
    FlowThresholds,
    normalize_flow_quadrant,
)
from application.inventory_order_alert.domain.value_objects.open_purchase_order import (
    ReplenishmentOutlook,
    build_replenishment_outlook,
    open_purchase_orders_from_rows,
    replenishment_deadline,
)
from application.inventory_order_alert.domain.value_objects.ordering_profile import (
    LEAD_TIME_SOURCE_DEFAULT,
    LEAD_TIME_SOURCE_MASTER,
    ORDERING_MANUAL,
    ORDERING_MRP,
    ORDERING_UNKNOWN,
    resolve_lead_time_days,
)
from application.inventory_order_alert.domain.value_objects.reconciliation_unit import ReconciliationUnits

RISK_DANGER = "危険"
RISK_CAUTION = "注意"
RISK_WATCH = "監視"
RISK_NONE = "対象外"
STOCKOUT_RISKS = (RISK_DANGER, RISK_CAUTION, RISK_WATCH, RISK_NONE)
STOCKOUT_RISK_RANK = {RISK_DANGER: 0, RISK_CAUTION: 1, RISK_WATCH: 2, RISK_NONE: 3}
#: CSS キー・URL 値。
STOCKOUT_RISK_KEYS = {RISK_DANGER: "danger", RISK_CAUTION: "caution", RISK_WATCH: "watch", RISK_NONE: "none"}
STOCKOUT_RISK_LABELS = {key: label for label, key in STOCKOUT_RISK_KEYS.items()}

#: 理由（F-006）。表示文言そのもの。
REASON_SUPPLIER_CHECK_FIRST = "仕入先の生産可否を先に確認"
REASON_MAYBE_FORGOTTEN = "発注忘れの可能性"
REASON_WITHIN_LEAD_TIME = "リードタイム内"
REASON_OVERDUE = "納期遅れ"
REASON_QTY_SHORT = "数量不足"
REASON_RAMP_UP = "立ち上がり品"
REASON_LEAD_TIME_DEFAULT = "リードタイム未設定"
REASON_LEVEL1_UNRESOLVED = "仕入先未解決"
REASON_REPLENISHMENT_UNKNOWN = "発注残を取得できませんでした"
REASON_RECENT_INCOMING = "直近に入荷あり"
#: 欠品（T-209）の行に付く理由（07 design §2.6）。危険・注意の先頭に置く
REASON_STOCK_MISSING = "在庫なし"
REASON_SUPPLY_DELAY = "供給遅延（入荷即出荷）"
REASON_UPSTREAM_ORDER = "上流工程に発注残あり"
REASON_UPSTREAM_OVERDUE = "上流工程で納期遅れ"


def _require_range(value: int, *, label: str, minimum: int, maximum: int) -> None:
    if not isinstance(value, int) or isinstance(value, bool) or not minimum <= value <= maximum:
        raise ValueError(f"{label}は {minimum}〜{maximum} の整数で指定してください: {value!r}")


@dataclass(frozen=True)
class StockoutRiskSettings:
    safety_days: int = 14
    default_lead_time_days: int = 5
    watch_months: int = 6

    def __post_init__(self) -> None:
        _require_range(self.safety_days, label="安全日数", minimum=1, maximum=60)
        _require_range(self.default_lead_time_days, label="既定リードタイム（日）", minimum=1, maximum=60)
        _require_range(self.watch_months, label="監視期間（か月）", minimum=1, maximum=12)


@dataclass(frozen=True)
class OrderingProfile:
    lead_time_days: int
    lead_time_source: str
    ordering_method: str


@dataclass(frozen=True)
class StockoutRiskAssessment:
    risk: str
    reasons: tuple[str, ...]
    days_until_stockout: int | None
    shortage_qty: int | None
    outlook: ReplenishmentOutlook
    profile: OrderingProfile

    @property
    def key(self) -> str:
        return STOCKOUT_RISK_KEYS[self.risk]


def _month_first(month: str) -> date:
    year, mon = (int(part) for part in month.split("-"))
    return date(year, mon, 1)


def _month_key(value: date) -> str:
    return f"{value.year:04d}-{value.month:02d}"


def days_until_stockout(as_of_date: date, stockout_month: str | None) -> int | None:
    """猶予日数（V-228）: 基準日から在庫切れ予測月の 1 日まで。当月なら 0。"""
    if not stockout_month:
        return None
    return max((_month_first(stockout_month) - as_of_date).days, 0)


def demand_until_month(forecast: DemandForecast, *, as_of_date: date, stockout_month: str) -> int:
    """当月残 ＋ 翌月から在庫切れ予測月までの月別需要（4 か月目以降は月平均）。"""
    total = float(forecast.current_month_remaining)
    month_first = date(as_of_date.year, as_of_date.month, 1)
    offset = 1
    while _month_key(add_calendar_months(month_first, offset)) <= stockout_month and offset <= 120:
        total += forecast.monthly[offset - 1] if offset <= FORECAST_MONTHS else forecast.monthly_average
        offset += 1
    return int(round(total))


def shortage_qty(demand: int, stock_total: float | None) -> int | None:
    """不足数量: 在庫切れ予測月までの需要 − 在庫合計（0 未満は 0）。在庫未取得は None。"""
    if stock_total is None:
        return None
    return max(int(round(demand - stock_total)), 0)


def chain_lead_time(process_chain: list[dict[str, object]], *, default_days: int) -> tuple[int, str]:
    """工程の連鎖のリードタイム（日）。BOM の階層（`level`）ごとに最大値を取って足す（並列の工程は同時に進む前提）。

    `level` がない工程は直列とみなして各々を足す。1 工程でも既定値なら出所は default。連鎖が空なら (0, default)。
    """
    per_level: dict[object, int] = {}
    serial_total = 0
    source = LEAD_TIME_SOURCE_MASTER if process_chain else LEAD_TIME_SOURCE_DEFAULT
    for index, stage in enumerate(process_chain):
        days, stage_source = resolve_lead_time_days(stage.get("lead_time_days"), default_days=default_days)
        if stage.get("lead_time_source") == LEAD_TIME_SOURCE_DEFAULT or stage_source == LEAD_TIME_SOURCE_DEFAULT:
            source = LEAD_TIME_SOURCE_DEFAULT
        level = stage.get("level")
        if level is None:
            serial_total += days
        else:
            per_level[level] = max(per_level.get(level, 0), days)
    return serial_total + sum(per_level.values()), source


def assess_stockout_risk(
    *,
    forecast: DemandForecast,
    stock_total: float | None,
    stockout_month: str | None,
    outlook: ReplenishmentOutlook,
    profile: OrderingProfile,
    flow_quadrant: str,
    level1_resolved: bool,
    settings: StockoutRiskSettings,
    as_of_date: date,
    last_incoming_date: date | None = None,
    stock_missing: bool = False,
    recent_incoming: bool = False,
) -> StockoutRiskAssessment:
    """F-005 の判定順と F-006 の理由。

    MRP 発注で `last_incoming_date` が「基準日 − (リードタイム + 安全日数)」以降なら補充サイクル稼働中とみなし、
    発注残がなくても危険にしない（2026/09/18 改訂。JIT では発注が起票から数日で検収され発注残が残らないため。
    2026/09/21: 手動発注・不明は「前回は入荷したが次を発注していない」が発注忘れそのものなので免除しない）。

    在庫なし（`stock_missing`、欠品 T-209）の行は 07 で分岐を加えた（07 design §2.6）。
    補充サイクル稼働中の免除と MRP 先送り（対象外）は在庫ありの行に限り、在庫なしは対象外にせず最低でも注意に残す。
    """
    days = days_until_stockout(as_of_date, stockout_month)
    if forecast.basis == BASIS_NONE or not stockout_month or stock_total is None:
        return StockoutRiskAssessment(RISK_WATCH, (), days, None, outlook, profile)
    watch_limit = _month_key(add_calendar_months(date(as_of_date.year, as_of_date.month, 1), settings.watch_months))
    if stockout_month > watch_limit:
        return StockoutRiskAssessment(RISK_WATCH, (), days, None, outlook, profile)

    shortage = shortage_qty(demand_until_month(forecast, as_of_date=as_of_date, stockout_month=stockout_month), stock_total)
    window_days = profile.lead_time_days + settings.safety_days
    within_lead_time = days is not None and days <= window_days
    is_mrp = profile.ordering_method == ORDERING_MRP
    # 補充サイクル稼働中の免除は在庫ありの行のみ（2026/09/21。在庫が切れている行は入荷が間に合っていない）
    replenishment_active = (
        not stock_missing
        and is_mrp
        and last_incoming_date is not None
        and 0 <= (as_of_date - last_incoming_date).days <= window_days
    )
    # 補充見込みが不足を埋めない（0 も含む）。2026/09/21: 危険の条件を qty 0 からここまで広げた
    short = outlook.qty == 0 or outlook.qty < (shortage or 0)

    # 上流工程に納期超過でなく補充期限以前の発注残が 1 件でもあれば流れは止まっていない（納期超過と混在しても）。F-005
    upstream_in_flight = outlook.upstream_pending_qty > 0

    quadrant = normalize_flow_quadrant(flow_quadrant)
    # MRP 先送り: 通常流動品で発注期限がまだ先・所要量計算が起票していないだけの正常状態（F-005、2026/09/21）。
    # 対応要 3 区分は発注前に仕入先の生産可否確認が要るため対象にしない。上流の納期超過も同様
    mrp_deferral = (
        not stock_missing
        and is_mrp
        and quadrant == QUADRANT_NORMAL_FLOW
        and not within_lead_time
        and outlook.qty == 0
        and not outlook.has_overdue
        and not outlook.upstream_overdue
    )

    if outlook.unknown:
        risk = RISK_CAUTION
    elif within_lead_time and short and not replenishment_active and not upstream_in_flight:
        risk = RISK_DANGER
    elif mrp_deferral:
        return StockoutRiskAssessment(RISK_NONE, (), days, shortage, outlook, profile)
    elif short or outlook.has_overdue:
        risk = RISK_CAUTION
    elif stock_missing:
        # 在庫が切れている行は補充が足りていても対象外にしない（07 design §2.6）
        risk = RISK_CAUTION
    else:
        return StockoutRiskAssessment(RISK_NONE, (), days, shortage, outlook, profile)

    reasons: list[str] = []
    if stock_missing:
        reasons.append(REASON_STOCK_MISSING)
        if recent_incoming:
            reasons.append(REASON_SUPPLY_DELAY)
    if quadrant in (QUADRANT_LOW_FLOW_NO_INCOMING, QUADRANT_DORMANT_STOCK):
        reasons.append(REASON_SUPPLIER_CHECK_FIRST)
    if outlook.unknown:
        reasons.append(REASON_REPLENISHMENT_UNKNOWN)
    if replenishment_active:
        reasons.append(REASON_RECENT_INCOMING)
    # 上流工程の理由は独立に付く（混在なら両方。F-006）
    if outlook.upstream_pending_qty > 0:
        reasons.append(REASON_UPSTREAM_ORDER)
    if outlook.upstream_overdue:
        reasons.append(REASON_UPSTREAM_OVERDUE)
    if within_lead_time and not outlook.unknown:
        reasons.append(REASON_WITHIN_LEAD_TIME)
    # 発注忘れは直下の工程に発注残が 1 件もないときのみ（補充期限より後・長期納期超過があれば発注はしている。F-006）
    no_direct_orders = outlook.qty == 0 and outlook.later_qty == 0 and outlook.stale_qty == 0
    if profile.ordering_method == ORDERING_MANUAL and no_direct_orders and not outlook.unknown:
        reasons.append(REASON_MAYBE_FORGOTTEN)
    if outlook.has_overdue:
        reasons.append(REASON_OVERDUE)
    if 0 < outlook.qty < (shortage or 0):
        reasons.append(REASON_QTY_SHORT)
    if quadrant == QUADRANT_LOW_FLOW_NO_SHIPMENT and forecast.basis == BASIS_UNCONFIRMED:
        reasons.append(REASON_RAMP_UP)
    if profile.lead_time_source == LEAD_TIME_SOURCE_DEFAULT:
        reasons.append(REASON_LEAD_TIME_DEFAULT)
    if not level1_resolved:
        reasons.append(REASON_LEVEL1_UNRESOLVED)
    return StockoutRiskAssessment(risk, tuple(reasons), days, shortage, outlook, profile)


def row_stockout_risk(row: dict[str, object]) -> str:
    """行の在庫切れリスク。キーがない旧行・未知の値は「監視」（REQ-SOR-F-013）。"""
    value = str(row.get("stockout_risk") or "").strip()
    if value in STOCKOUT_RISK_RANK:
        return value
    if value in STOCKOUT_RISK_LABELS:
        return STOCKOUT_RISK_LABELS[value]
    return RISK_WATCH


def stockout_risk_sort_rank(row: dict[str, object]) -> int:
    return STOCKOUT_RISK_RANK[row_stockout_risk(row)]


def _row_date(row: dict[str, object], key: str) -> date | None:
    text = str(row.get(key) or "").strip()
    if not text:
        return None
    try:
        return parse_optional_ymd(text)
    except ValueError:
        return None


def _forecast_of(row: dict[str, object]) -> DemandForecast:
    # 現行の算出根拠にない値（廃止した旧スナップショットの根拠）は 需要なし として読む（07 REQ-FQR-F-002）
    basis = str(row.get("demand_forecast_basis") or BASIS_NONE)
    if basis not in DEMAND_FORECAST_BASES or basis == BASIS_NONE:
        return NO_DEMAND
    monthly = row.get("demand_forecast_monthly")
    try:
        monthly_tuple = tuple(int(q) for q in monthly) if isinstance(monthly, list) and len(monthly) == 3 else (0, 0, 0)
        return DemandForecast(
            basis=basis,
            current_month_remaining=int(row.get("demand_forecast_current_month_remaining") or 0),
            monthly=monthly_tuple,
            monthly_average=float(row.get("demand_forecast_monthly_average") or 0.0),
        )
    except (TypeError, ValueError):
        return NO_DEMAND


def _stock_total_of(row: dict[str, object]) -> float | None:
    value = row.get("demand_forecast_stock_total")
    if value is None or value == "":
        return None
    try:
        return float(value)
    except (TypeError, ValueError):
        return None


def _profile_of(row: dict[str, object], settings: StockoutRiskSettings) -> OrderingProfile:
    chain = row.get("process_chain")
    if isinstance(chain, list) and chain:
        # 工程の連鎖があればリードタイムは合計（2026/09/18）
        lead_time, source = chain_lead_time([stage for stage in chain if isinstance(stage, dict)], default_days=settings.default_lead_time_days)
        if lead_time <= 0:
            lead_time, source = settings.default_lead_time_days, LEAD_TIME_SOURCE_DEFAULT
        return OrderingProfile(lead_time_days=lead_time, lead_time_source=source, ordering_method=str(row.get("ordering_method") or ORDERING_UNKNOWN))
    lead_time, source = resolve_lead_time_days(row.get("lead_time_days"), default_days=settings.default_lead_time_days)
    if row.get("lead_time_source") == LEAD_TIME_SOURCE_DEFAULT:
        source = LEAD_TIME_SOURCE_DEFAULT
    return OrderingProfile(
        lead_time_days=lead_time,
        lead_time_source=source,
        ordering_method=str(row.get("ordering_method") or ORDERING_UNKNOWN),
    )


def _assessment_fields(assessment: StockoutRiskAssessment) -> dict[str, object]:
    outlook = assessment.outlook
    return {
        "stockout_risk": assessment.risk,
        "stockout_risk_key": assessment.key,
        "stockout_risk_reasons": list(assessment.reasons),
        "days_until_stockout": assessment.days_until_stockout,
        "shortage_qty": assessment.shortage_qty,
        "replenishment_qty": outlook.qty,
        "replenishment_later_qty": outlook.later_qty,
        "replenishment_stale_qty": outlook.stale_qty,
        "replenishment_earliest_due": outlook.earliest_due.strftime("%Y/%m/%d") if outlook.earliest_due else "",
        "replenishment_has_overdue": outlook.has_overdue,
        "replenishment_unknown": outlook.unknown,
        "upstream_order_qty": outlook.upstream_qty,
        "upstream_order_overdue": outlook.upstream_overdue,
        "upstream_order_earliest_due": outlook.upstream_earliest_due.strftime("%Y/%m/%d") if outlook.upstream_earliest_due else "",
        "lead_time_days": assessment.profile.lead_time_days,
        "lead_time_source": assessment.profile.lead_time_source,
        "ordering_method": assessment.profile.ordering_method,
    }


def attach_stockout_risk(
    rows: list[dict[str, object]],
    as_of_date: date,
    *,
    settings: StockoutRiskSettings,
    thresholds: FlowThresholds = DEFAULT_FLOW_THRESHOLDS,
) -> list[dict[str, object]]:
    """照合単位ごとに補充見込みと判定を 1 回行い、単位内の全行に複製する（入力は変更しない）。

    需要予測・在庫合計・在庫切れ予測月は `attach_demand_forecast` が付けた行の値を使う。
    在庫なし・直近入荷は行から導く（07 design §2.6）。判定は行ごとなので補充見込みのキャッシュとは別に評価する。
    """
    units = ReconciliationUnits.build(rows)
    # 長期納期超過の閾値（リードタイム＋安全日数）は行の工程の連鎖で変わるため、キャッシュは (単位, 閾値) で持つ
    cache: dict[tuple[str, int], ReplenishmentOutlook] = {}
    enriched: list[dict[str, object]] = []

    def outlook_of(
        unit_rows: list[dict[str, object]],
        level1_pairs: frozenset[tuple[str, str]] | None,
        stockout_month: str | None,
        stale_after_days: int,
    ) -> ReplenishmentOutlook:
        if any(bool(r.get("open_purchase_orders_unknown")) for r in unit_rows):
            return ReplenishmentOutlook.unknown_outlook()
        return build_replenishment_outlook(
            open_purchase_orders_from_rows(unit_rows),
            as_of_date=as_of_date,
            stockout_month=stockout_month,
            deadline=replenishment_deadline(as_of_date, stockout_month, safety_days=settings.safety_days),
            stale_after_days=stale_after_days,
            level1_pairs=level1_pairs or None,
        )

    for row in rows:
        copied = dict(row)
        unit = units.unit_of(str(row.get("item_cd") or ""))
        stockout_month = str(row.get("stockout_forecast_month") or "") or None
        profile = _profile_of(row, settings)
        stale_after_days = profile.lead_time_days + settings.safety_days
        if unit is None:
            # 得意先品番が空の行は照合単位に属さない。キャッシュを共有せず行単体で見る
            outlook = outlook_of([row], None, stockout_month, stale_after_days)
        else:
            cache_key = (unit.key, stale_after_days)
            if cache_key not in cache:
                cache[cache_key] = outlook_of(units.rows_of(unit, rows), unit.level1_pairs, stockout_month, stale_after_days)
            outlook = cache[cache_key]
        assessment = assess_stockout_risk(
            forecast=_forecast_of(row),
            stock_total=_stock_total_of(row),
            stockout_month=stockout_month,
            outlook=outlook,
            profile=profile,
            flow_quadrant=str(row.get("flow_quadrant") or ""),
            level1_resolved=bool(str(row.get("level1_item_cd") or "").strip()),
            settings=settings,
            as_of_date=as_of_date,
            last_incoming_date=_row_date(row, "last_incoming_date"),
            stock_missing=row_stock_missing(row),
            recent_incoming=row_recent_incoming(row, as_of_date=as_of_date, days=thresholds.recent_incoming_days),
        )
        copied.update(_assessment_fields(assessment))
        enriched.append(copied)
    return enriched

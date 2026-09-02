from __future__ import annotations

from datetime import date

from application.sales.infrastructure.oracle.client import rows_as_dicts

from application.inventory_order_alert.domain.value_objects.dates import add_calendar_months, to_date
from application.inventory_order_alert.domain.value_objects.internal_item import resolve_cust_code, resolve_internal_item_cd
from application.inventory_order_alert.domain.value_objects.shipment_trend import build_monthly_shipment_trend


def chunked(items: list[str], size: int = 900) -> list[list[str]]:
    return [items[index : index + size] for index in range(0, len(items), size)]


def fetch_customer_names(connection: object) -> dict[str, str]:
    cursor = connection.cursor()
    cursor.execute("SELECT TRIM(CUST_CD) AS CUST_CD, TRIM(CUST_NAME) AS CUST_NAME FROM M_CUST")
    return {str(row["cust_cd"]).strip(): str(row.get("cust_name") or "").strip() for row in rows_as_dicts(cursor)}


def fetch_ship_customer_items(connection: object) -> list[tuple[str, str, str, str]]:
    """Returns (cust_code, cust_item_cd, cust_chrg_psn_cd, internal_item_cd_from_ship)."""
    sql = """
        SELECT TRIM(CUST_CD) AS CUST_CD,
               TRIM(CUST_ITEM_CD) AS CUST_ITEM_CD,
               MAX(TRIM(CUST_CHRG_PSN_CD)) AS CUST_CHRG_PSN_CD,
               MAX(TRIM(ITEM_CD)) AS INTERNAL_ITEM_CD
          FROM T_SHIP
         WHERE DEL_FLG != 1
           AND TRIM(CUST_ITEM_CD) IS NOT NULL
         GROUP BY TRIM(CUST_CD), TRIM(CUST_ITEM_CD)
         ORDER BY CUST_CD, CUST_ITEM_CD
    """
    cursor = connection.cursor()
    cursor.execute(sql)
    return [
        (
            str(row["cust_cd"]).strip(),
            str(row["cust_item_cd"]).strip(),
            str(row.get("cust_chrg_psn_cd") or "").strip(),
            str(row.get("internal_item_cd") or "").strip(),
        )
        for row in rows_as_dicts(cursor)
    ]


def fetch_internal_items_from_m_cust_item(
    connection: object,
    as_of_date: date,
    *,
    cust_item_cds: set[str],
) -> tuple[dict[tuple[str, str], str], dict[str, str]]:
    """Map CUST_ITEM_CD to internal ITEM_CD via M_CUST_ITEM (last row wins)."""
    if not cust_item_cds:
        return {}, {}

    by_pair: dict[tuple[str, str], str] = {}
    by_cust_item: dict[str, str] = {}
    for batch in chunked(sorted(cust_item_cds)):
        placeholders = ", ".join(f":item_{index}" for index, _ in enumerate(batch))
        params = {f"item_{index}": item_cd for index, item_cd in enumerate(batch)}
        params["as_of_date"] = as_of_date
        sql = f"""
            SELECT TRIM(CUST_CD) AS CUST_CD,
                   TRIM(CUST_ITEM_CD) AS CUST_ITEM_CD,
                   TRIM(ITEM_CD) AS ITEM_CD
              FROM M_CUST_ITEM
             WHERE DLV_LOC_CD = '*'
               AND TRIM(CUST_ITEM_CD) IN ({placeholders})
               AND EFF_PHASE_IN_DATE <= :as_of_date
               AND EFF_PHASE_OUT_DATE >= :as_of_date
             ORDER BY CUST_CD, CUST_ITEM_CD, EFF_PHASE_IN_DATE
        """
        cursor = connection.cursor()
        cursor.execute(sql, params)
        for row in rows_as_dicts(cursor):
            cust_code = str(row["cust_cd"]).strip()
            cust_item_cd = str(row["cust_item_cd"]).strip()
            internal_item_cd = str(row["item_cd"]).strip()
            if not cust_item_cd or not internal_item_cd:
                continue
            if cust_code:
                by_pair[(cust_code, cust_item_cd)] = internal_item_cd
            by_cust_item[cust_item_cd] = internal_item_cd
    return by_pair, by_cust_item


def fetch_finished_roots(connection: object, finished_items: set[str]) -> dict[str, set[str]]:
    if not finished_items:
        return {}
    roots_by_finished: dict[str, set[str]] = {item: {item} for item in finished_items}
    for batch in chunked(sorted(finished_items)):
        placeholders = ", ".join(f":item_{index}" for index, _ in enumerate(batch))
        params = {f"item_{index}": item_cd for index, item_cd in enumerate(batch)}
        sql = f"""
            SELECT TRIM(ITEM_CD) AS ITEM_CD,
                   TRIM(SUB_ITEM_CD_01) AS SUB_ITEM_CD_01,
                   TRIM(SUB_ITEM_CD_02) AS SUB_ITEM_CD_02,
                   TRIM(SUB_ITEM_CD_03) AS SUB_ITEM_CD_03,
                   TRIM(SUB_ITEM_CD_04) AS SUB_ITEM_CD_04,
                   TRIM(SUB_ITEM_CD_05) AS SUB_ITEM_CD_05
              FROM M_ITEM
             WHERE TRIM(ITEM_CD) IN ({placeholders})
        """
        cursor = connection.cursor()
        cursor.execute(sql, params)
        for row in rows_as_dicts(cursor):
            finished = str(row["item_cd"]).strip()
            roots = roots_by_finished.setdefault(finished, {finished})
            for key in ("sub_item_cd_01", "sub_item_cd_02", "sub_item_cd_03", "sub_item_cd_04", "sub_item_cd_05"):
                sub_item = str(row.get(key) or "").strip()
                if sub_item:
                    roots.add(sub_item)
    return roots_by_finished


def fetch_bom_level1_by_root(connection: object, roots: set[str], as_of_date: date) -> dict[str, list[str]]:
    if not roots:
        return {}
    level1_by_root: dict[str, list[str]] = {}
    for batch in chunked(sorted(roots)):
        placeholders = ", ".join(f":root_{index}" for index, _ in enumerate(batch))
        params = {f"root_{index}": root for index, root in enumerate(batch)}
        params["as_of_date"] = as_of_date
        sql = f"""
            SELECT CONNECT_BY_ROOT ps.PARENT_ITEM_CD AS ROOT_ITEM,
                   TRIM(ps.COMP_ITEM_CD) AS L1_ITEM_CD
              FROM M_PS ps
              JOIN M_ITEM item
                ON item.ITEM_CD = ps.COMP_ITEM_CD
             WHERE item.OUTSIDE_TYP = '2'
               AND ps.EFF_PHASE_IN_DATE <= :as_of_date
               AND ps.EFF_PHASE_OUT_DATE >= :as_of_date
               AND LEVEL = 1
             START WITH ps.PARENT_ITEM_CD IN ({placeholders})
           CONNECT BY PRIOR ps.COMP_ITEM_CD = ps.PARENT_ITEM_CD
               AND ps.EFF_PHASE_IN_DATE <= :as_of_date
               AND ps.EFF_PHASE_OUT_DATE >= :as_of_date
        """
        cursor = connection.cursor()
        cursor.execute(sql, params)
        for row in rows_as_dicts(cursor):
            root_item = str(row["root_item"]).strip()
            l1_item = str(row["l1_item_cd"]).strip()
            if not root_item or not l1_item:
                continue
            level1_by_root.setdefault(root_item, [])
            if l1_item not in level1_by_root[root_item]:
                level1_by_root[root_item].append(l1_item)
    return level1_by_root


def fetch_mari_stock_totals(connection: object, internal_item_cds: list[str]) -> dict[str, object]:
    """基幹 Oracle(MARI)の在庫数を内作品番単位で合算して返す(design.md §5.3)。

    SLIMS 取込時の集計から 1 回だけ呼ぶ。一覧表示のたびには呼ばない。
    Oracle の IN 句上限を超える場合は既存の chunked() で分割するが、論理的には 1 回の取得として扱う。
    該当在庫が無い品番は戻り値に含めない(呼び出し側で空にする)。
    """
    if not internal_item_cds:
        return {}

    totals: dict[str, object] = {}
    for batch in chunked(sorted({item for item in internal_item_cds if item})):
        placeholders = ", ".join(f":item_{index}" for index, _ in enumerate(batch))
        params = {f"item_{index}": item_cd for index, item_cd in enumerate(batch)}
        sql = f"""
            SELECT TRIM(ITEM_CD) AS ITEM_CD,
                   SUM(NVL(STOCK_ON_HAND_QTY, 0)) AS STOCK_QTY
              FROM T_ITEM_STOCK
             WHERE TRIM(ITEM_CD) IN ({placeholders})
             GROUP BY TRIM(ITEM_CD)
        """
        cursor = connection.cursor()
        cursor.execute(sql, params)
        for row in rows_as_dicts(cursor):
            item_cd = str(row["item_cd"]).strip()
            if item_cd:
                totals[item_cd] = row.get("stock_qty")
    return totals


def fetch_vendor_by_component(connection: object) -> dict[str, tuple[str, str]]:
    sql = """
        SELECT TRIM(cost.ITEM_CD) AS ITEM_CD,
               TRIM(cost.VEND_CD) AS VEND_CD,
               TRIM(vend.VEND_ANAME) AS VEND_NAME
          FROM M_PUCH_UNIT_COST_H cost
          LEFT JOIN M_VEND_CTRL vend
            ON cost.VEND_CD = vend.VEND_CD
    """
    cursor = connection.cursor()
    cursor.execute(sql)
    vendor_by_item: dict[str, tuple[str, str]] = {}
    for row in rows_as_dicts(cursor):
        item_cd = str(row["item_cd"]).strip()
        if item_cd:
            vendor_by_item[item_cd] = (
                str(row.get("vend_cd") or "").strip(),
                str(row.get("vend_name") or "").strip(),
            )
    return vendor_by_item


def fetch_last_incoming_by_item_vend(connection: object) -> dict[tuple[str, str], date]:
    sql = """
        SELECT TRIM(ITEM_CD) AS ITEM_CD,
               TRIM(VEND_CD) AS VEND_CD,
               MAX(ACPT_DATE) AS LAST_INCOMING_DATE
          FROM T_PAST_INSPC_ACPT
         GROUP BY ITEM_CD, VEND_CD
    """
    cursor = connection.cursor()
    cursor.execute(sql)
    result: dict[tuple[str, str], date] = {}
    for row in rows_as_dicts(cursor):
        item_cd = str(row["item_cd"]).strip()
        vend_cd = str(row["vend_cd"]).strip()
        incoming = to_date(row.get("last_incoming_date"))
        if item_cd and vend_cd and incoming:
            result[(item_cd, vend_cd)] = incoming
    return result


def fetch_incoming_receipts(connection: object, window_start: date) -> list[tuple[str, str, date, int]]:
    """(item_cd, vend_cd, acpt_date, qty) の個々の検収明細を window_start 以降に絞って取得する(design.md §3.3)。

    fetch_last_incoming_by_item_vend() は MAX(ACPT_DATE) のみを返すため、
    入荷推移(V-217)の月次集計に必要な個々の明細・数量はここで別途取得する。
    直近 24 か月に絞り込むことで T_PAST_INSPC_ACPT の全件取得を避ける。
    """
    sql = """
        SELECT TRIM(ITEM_CD) AS ITEM_CD,
               TRIM(VEND_CD) AS VEND_CD,
               ACPT_DATE,
               NVL(INSPC_ACPT_QTY, 0) AS QTY
          FROM T_PAST_INSPC_ACPT
         WHERE ACPT_DATE >= :window_start
    """
    cursor = connection.cursor()
    cursor.execute(sql, {"window_start": window_start})
    receipts: list[tuple[str, str, date, int]] = []
    for row in rows_as_dicts(cursor):
        item_cd = str(row["item_cd"]).strip()
        vend_cd = str(row["vend_cd"]).strip()
        acpt_date = to_date(row.get("acpt_date"))
        if item_cd and vend_cd and acpt_date:
            receipts.append((item_cd, vend_cd, acpt_date, int(row.get("qty") or 0)))
    return receipts


def resolve_last_incoming_for_finished(
    finished_item: str,
    roots_by_finished: dict[str, set[str]],
    level1_by_root: dict[str, list[str]],
    vendor_by_component: dict[str, tuple[str, str]],
    incoming_by_item_vend: dict[tuple[str, str], date],
) -> tuple[date | None, str, str, str]:
    best_date: date | None = None
    best_l1 = ""
    best_vend = ""
    best_vend_name = ""
    fallback_l1 = ""
    fallback_vend = ""
    fallback_vend_name = ""

    for root in roots_by_finished.get(finished_item, {finished_item}):
        for l1_item in level1_by_root.get(root, []):
            vend_cd, vend_name = vendor_by_component.get(l1_item, ("", ""))
            if not vend_cd or vend_cd == "?":
                continue
            if not fallback_l1:
                fallback_l1 = l1_item
                fallback_vend = vend_cd
                fallback_vend_name = vend_name
            incoming = incoming_by_item_vend.get((l1_item, vend_cd))
            if incoming is None:
                continue
            if best_date is None or incoming > best_date:
                best_date = incoming
                best_l1 = l1_item
                best_vend = vend_cd
                best_vend_name = vend_name

    if best_l1:
        return best_date, best_l1, best_vend, best_vend_name
    return None, fallback_l1, fallback_vend, fallback_vend_name


def aggregate_shipment_stats(
    shipments: list[tuple[str, str, date, int]],
    cust_code: str,
    cust_item_cd: str,
    last_incoming_date: date | None,
) -> tuple[date | None, int, int]:
    last_ship: date | None = None
    post_count = 0
    post_total_qty = 0
    for ship_cust, ship_item, ship_date, ship_qty in shipments:
        if ship_cust != cust_code or ship_item != cust_item_cd:
            continue
        if last_ship is None or ship_date > last_ship:
            last_ship = ship_date
        if last_incoming_date is not None and ship_date <= last_incoming_date:
            continue
        post_count += 1
        post_total_qty += ship_qty
    return last_ship, post_count, post_total_qty


def fetch_all_shipments(connection: object) -> list[tuple[str, str, date, int]]:
    sql = """
        SELECT TRIM(CUST_CD) AS CUST_CD,
               TRIM(CUST_ITEM_CD) AS CUST_ITEM_CD,
               SHIP_DATE,
               NVL(SHIP_QTY, 0) AS SHIP_QTY
          FROM T_SHIP
         WHERE DEL_FLG != 1
           AND TRIM(CUST_ITEM_CD) IS NOT NULL
    """
    cursor = connection.cursor()
    cursor.execute(sql)
    shipments: list[tuple[str, str, date, int]] = []
    for row in rows_as_dicts(cursor):
        ship_date = to_date(row.get("ship_date"))
        if ship_date is None:
            continue
        shipments.append(
            (
                str(row["cust_cd"]).strip(),
                str(row["cust_item_cd"]).strip(),
                ship_date,
                int(row.get("ship_qty") or 0),
            )
        )
    return shipments


def group_shipments_by_pair(
    shipments: list[tuple[str, str, date, int]],
) -> dict[tuple[str, str], list[tuple[date, int]]]:
    """all_shipments を (cust_code, cust_item_cd) でグループ化する(design.md §6.1)。

    月次出荷推移(V-216)の集計を行あたり O(1) の辞書引きにするための前処理。
    fetch_all_shipments() の戻り値をそのまま渡す想定で、Oracle への追加問い合わせは発生しない。
    """
    grouped: dict[tuple[str, str], list[tuple[date, int]]] = {}
    for cust_code, cust_item_cd, ship_date, ship_qty in shipments:
        grouped.setdefault((cust_code, cust_item_cd), []).append((ship_date, ship_qty))
    return grouped


def build_summary_rows(
    connection: object,
    as_of_date: date,
    *,
    stock_item_cds: set[str] | None = None,
) -> list[dict[str, object]]:
    """Oracle 出荷ペアから一覧サマリ行を組み立てる。

    ``stock_item_cds`` は後方互換のため受け付けるが **無視** する（SLIMS のみ品番は非表示）。
    """
    _ = stock_item_cds
    customer_names = fetch_customer_names(connection)
    ship_pairs = fetch_ship_customer_items(connection)
    shipped_cust_items = {cust_item_cd for _, cust_item_cd, _, _ in ship_pairs}

    m_cust_by_pair, m_cust_by_item = fetch_internal_items_from_m_cust_item(
        connection,
        as_of_date,
        cust_item_cds=shipped_cust_items,
    )
    all_shipments = fetch_all_shipments(connection)

    internal_items: set[str] = set()
    for cust_code, cust_item_cd, _, internal_from_ship in ship_pairs:
        internal_items.add(
            resolve_internal_item_cd(
                cust_item_cd=cust_item_cd,
                internal_from_ship=internal_from_ship,
                internal_from_m_cust_item_pair=m_cust_by_pair.get((cust_code, cust_item_cd), ""),
                internal_from_m_cust_item=m_cust_by_item.get(cust_item_cd, ""),
            )
        )

    roots_by_finished = fetch_finished_roots(connection, internal_items)
    all_roots = {root for roots in roots_by_finished.values() for root in roots}
    level1_by_root = fetch_bom_level1_by_root(connection, all_roots, as_of_date)
    vendor_by_component = fetch_vendor_by_component(connection)
    incoming_by_item_vend = fetch_last_incoming_by_item_vend(connection)
    # MARI 在庫は取込時に 1 回だけ取得する(design.md §3.1)。一覧表示のたびには問い合わせない。
    mari_stock_by_item = fetch_mari_stock_totals(connection, sorted(internal_items))
    # 出荷推移(V-216)は all_shipments を束ね直すだけで、追加の Oracle 問い合わせは発生しない(design.md §3.1)。
    shipments_by_pair = group_shipments_by_pair(all_shipments)
    # 入荷推移(V-217)は level1_item_cd x level1_vend_cd で突合する。直近 24 か月に絞った専用クエリを 1 回だけ発行する(design.md §3.3, §6.1)。
    window_start = add_calendar_months(date(as_of_date.year, as_of_date.month, 1), -23)
    incoming_receipts = fetch_incoming_receipts(connection, window_start)
    incoming_by_pair = group_shipments_by_pair(incoming_receipts)

    incoming_cache: dict[str, tuple[date | None, str, str, str]] = {}
    rows: list[dict[str, object]] = []

    def internal_for(cust_code: str, cust_item_cd: str, internal_from_ship: str = "") -> str:
        return resolve_internal_item_cd(
            cust_item_cd=cust_item_cd,
            internal_from_ship=internal_from_ship,
            internal_from_m_cust_item_pair=m_cust_by_pair.get((cust_code, cust_item_cd), ""),
            internal_from_m_cust_item=m_cust_by_item.get(cust_item_cd, ""),
        )

    def cust_code_for(cust_code: str) -> str:
        resolved = resolve_cust_code(cust_from_ship=cust_code)
        if resolved and resolved in customer_names:
            return resolved
        return ""

    for cust_code, cust_item_cd, cust_chrg_psn_cd, internal_from_ship in ship_pairs:
        resolved_cust_code = cust_code_for(cust_code)
        internal = internal_for(cust_code, cust_item_cd, internal_from_ship)
        if internal not in incoming_cache:
            incoming_cache[internal] = resolve_last_incoming_for_finished(
                internal,
                roots_by_finished,
                level1_by_root,
                vendor_by_component,
                incoming_by_item_vend,
            )
        last_incoming, level1_item, level1_vend, level1_vend_name = incoming_cache[internal]
        last_ship, post_count, post_total_qty = aggregate_shipment_stats(
            all_shipments,
            cust_code,
            cust_item_cd,
            last_incoming,
        )
        shipment_trend = build_monthly_shipment_trend(
            shipments_by_pair.get((cust_code, cust_item_cd), []),
            as_of_date=as_of_date,
        )
        incoming_trend = build_monthly_shipment_trend(
            incoming_by_pair.get((level1_item, level1_vend), []),
            as_of_date=as_of_date,
        )
        rows.append(
            {
                "cust_code": resolved_cust_code,
                "cust_name": customer_names.get(resolved_cust_code, ""),
                "cust_chrg_psn_cd": cust_chrg_psn_cd,
                "item_cd": cust_item_cd,
                "level1_item_cd": level1_item,
                "level1_vend_cd": level1_vend,
                "level1_vend_name": level1_vend_name,
                "last_incoming_date": last_incoming.strftime("%Y/%m/%d") if last_incoming else "",
                "last_ship_date": last_ship.strftime("%Y/%m/%d") if last_ship else "",
                "post_shipment_count": post_count,
                "post_shipment_total_qty": post_total_qty,
                "shipment_trend": shipment_trend,
                "incoming_trend": incoming_trend,
                # 該当在庫が無い場合は空。0(在庫なし)とは区別する(design.md §4.2)
                "mari_stock_qty": mari_stock_by_item.get(internal, ""),
            }
        )

    return rows

from __future__ import annotations

from datetime import date

from applications.gonenkukumi.infrastructure.oracle.client import rows_as_dicts

from applications.inventory_order_alert.domain.dates import to_date


def chunked(items: list[str], size: int = 900) -> list[list[str]]:
    return [items[index : index + size] for index in range(0, len(items), size)]


def fetch_customer_names(connection: object) -> dict[str, str]:
    cursor = connection.cursor()
    cursor.execute("SELECT TRIM(CUST_CD) AS CUST_CD, TRIM(CUST_NAME) AS CUST_NAME FROM M_CUST")
    return {str(row["cust_cd"]).strip(): str(row.get("cust_name") or "").strip() for row in rows_as_dicts(cursor)}


def fetch_ship_customer_items(connection: object) -> list[tuple[str, str, str]]:
    sql = """
        SELECT TRIM(CUST_CD) AS CUST_CD,
               TRIM(ITEM_CD) AS ITEM_CD,
               MAX(TRIM(CUST_CHRG_PSN_CD)) AS CUST_CHRG_PSN_CD
          FROM T_SHIP
         WHERE DEL_FLG != 1
         GROUP BY TRIM(CUST_CD), TRIM(ITEM_CD)
         ORDER BY CUST_CD, ITEM_CD
    """
    cursor = connection.cursor()
    cursor.execute(sql)
    return [
        (
            str(row["cust_cd"]).strip(),
            str(row["item_cd"]).strip(),
            str(row.get("cust_chrg_psn_cd") or "").strip(),
        )
        for row in rows_as_dicts(cursor)
    ]


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
    finished_item: str,
    last_incoming_date: date | None,
) -> tuple[date | None, int, int]:
    last_ship: date | None = None
    post_count = 0
    post_total_qty = 0
    for ship_cust, ship_item, ship_date, ship_qty in shipments:
        if ship_cust != cust_code or ship_item != finished_item:
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
               TRIM(ITEM_CD) AS ITEM_CD,
               SHIP_DATE,
               NVL(SHIP_QTY, 0) AS SHIP_QTY
          FROM T_SHIP
         WHERE DEL_FLG != 1
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
                str(row["item_cd"]).strip(),
                ship_date,
                int(row.get("ship_qty") or 0),
            )
        )
    return shipments


def build_summary_rows(
    connection: object,
    as_of_date: date,
    *,
    stock_item_cds: set[str] | None = None,
) -> list[dict[str, object]]:
    customer_names = fetch_customer_names(connection)
    ship_pairs = fetch_ship_customer_items(connection)
    shipped_items = {item for _, item, _ in ship_pairs}
    finished_items = set(shipped_items)
    if stock_item_cds:
        finished_items |= stock_item_cds
    all_shipments = fetch_all_shipments(connection)

    roots_by_finished = fetch_finished_roots(connection, finished_items)
    all_roots = {root for roots in roots_by_finished.values() for root in roots}
    level1_by_root = fetch_bom_level1_by_root(connection, all_roots, as_of_date)
    vendor_by_component = fetch_vendor_by_component(connection)
    incoming_by_item_vend = fetch_last_incoming_by_item_vend(connection)

    incoming_cache: dict[str, tuple[date | None, str, str, str]] = {}
    rows: list[dict[str, object]] = []

    for cust_code, finished_item, cust_chrg_psn_cd in ship_pairs:
        if finished_item not in incoming_cache:
            incoming_cache[finished_item] = resolve_last_incoming_for_finished(
                finished_item,
                roots_by_finished,
                level1_by_root,
                vendor_by_component,
                incoming_by_item_vend,
            )
        last_incoming, level1_item, level1_vend, level1_vend_name = incoming_cache[finished_item]
        last_ship, post_count, post_total_qty = aggregate_shipment_stats(
            all_shipments,
            cust_code,
            finished_item,
            last_incoming,
        )
        rows.append(
            {
                "cust_code": cust_code,
                "cust_name": customer_names.get(cust_code, ""),
                "cust_chrg_psn_cd": cust_chrg_psn_cd,
                "item_cd": finished_item,
                "level1_item_cd": level1_item,
                "level1_vend_cd": level1_vend,
                "level1_vend_name": level1_vend_name,
                "last_incoming_date": last_incoming.strftime("%Y/%m/%d") if last_incoming else "",
                "last_ship_date": last_ship.strftime("%Y/%m/%d") if last_ship else "",
                "post_shipment_count": post_count,
                "post_shipment_total_qty": post_total_qty,
            }
        )

    extra_items = finished_items - shipped_items
    for finished_item in sorted(extra_items):
        if finished_item not in incoming_cache:
            incoming_cache[finished_item] = resolve_last_incoming_for_finished(
                finished_item,
                roots_by_finished,
                level1_by_root,
                vendor_by_component,
                incoming_by_item_vend,
            )
        last_incoming, level1_item, level1_vend, level1_vend_name = incoming_cache[finished_item]
        if last_incoming is None:
            continue
        rows.append(
            {
                "cust_code": "",
                "cust_name": "",
                "cust_chrg_psn_cd": "",
                "item_cd": finished_item,
                "level1_item_cd": level1_item,
                "level1_vend_cd": level1_vend,
                "level1_vend_name": level1_vend_name,
                "last_incoming_date": last_incoming.strftime("%Y/%m/%d"),
                "last_ship_date": "",
                "post_shipment_count": 0,
                "post_shipment_total_qty": 0,
            }
        )
    return rows

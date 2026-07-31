from __future__ import annotations

from application.sales.infrastructure.oracle.client import rows_as_dicts
from application.shipment_trend.domain.value_objects.trend_builder import MonthlyShipmentRecord


def fetch_customer_names(connection: object) -> dict[str, str]:
    sql = """
        SELECT TRIM(CUST_CD) AS CUST_CD,
               TRIM(CUST_NAME) AS CUST_NAME
          FROM M_CUST
    """
    cursor = connection.cursor()
    cursor.execute(sql)
    return {
        str(row["cust_cd"]).strip(): str(row.get("cust_name") or "").strip()
        for row in rows_as_dicts(cursor)
    }


def fetch_monthly_shipments(connection: object) -> list[MonthlyShipmentRecord]:
    sql = """
        SELECT TRIM(CUST_CD) AS CUST_CD,
               TRIM(ITEM_CD) AS ITEM_CD,
               MAX(TRIM(CUST_CHRG_PSN_CD)) AS CUST_CHRG_PSN_CD,
               TO_CHAR(SHIP_DATE, 'YYYY-MM') AS YEAR_MONTH,
               SUM(NVL(SHIP_QTY, 0)) AS SHIP_QTY
          FROM T_SHIP
         WHERE DEL_FLG != 1
         GROUP BY TRIM(CUST_CD), TRIM(ITEM_CD), TO_CHAR(SHIP_DATE, 'YYYY-MM')
         ORDER BY CUST_CD, ITEM_CD, YEAR_MONTH
    """
    cursor = connection.cursor()
    cursor.execute(sql)
    records: list[MonthlyShipmentRecord] = []
    for row in rows_as_dicts(cursor):
        records.append(
            MonthlyShipmentRecord(
                cust_code=str(row["cust_cd"]).strip(),
                item_cd=str(row["item_cd"]).strip(),
                cust_chrg_psn_cd=str(row.get("cust_chrg_psn_cd") or "").strip(),
                year_month=str(row["year_month"]).strip(),
                ship_qty=int(row.get("ship_qty") or 0),
            )
        )
    return records

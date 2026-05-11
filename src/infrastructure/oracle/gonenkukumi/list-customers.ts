import "server-only";

import oracledb from "oracledb";
import { withOracleReadConnection } from "@/infrastructure/oracle/with-connection";

export type GonenKukumiCustomerOption = {
  custCode: string;
  custName: string;
};

type Row = {
  CUST_CD: string | number | null;
  CUST_ANAME: string | null;
};

/**
 * 得意先マスタ（M_CUST）の一覧。5年9組検索画面のコンボボックス用。
 * 件数は業務上 ~150 件程度を想定し、上限 500 行で打ち切る。
 */
export async function listGonenKukumiCustomers(): Promise<GonenKukumiCustomerOption[]> {
  return withOracleReadConnection<GonenKukumiCustomerOption[]>([], async (conn, { companyCd }) => {
    const sql = `
      SELECT M_CUST.CUST_CD AS "CUST_CD", M_CUST.CUST_ANAME AS "CUST_ANAME"
      FROM M_CUST
      WHERE REGEXP_LIKE(TRIM(TO_CHAR(M_CUST.CUST_CD)), '^[0-9]{3}$')
        AND (:companyCd IS NULL OR M_CUST.COMPANY_CD = :companyCd)
      ORDER BY M_CUST.CUST_CD`;
    const r = await conn.execute<Row>(
      sql,
      { companyCd },
      { outFormat: oracledb.OUT_FORMAT_OBJECT, maxRows: 500 },
    );
    const rows = (r.rows ?? []) as Row[];
    return rows.map((row) => ({
      custCode: String(row.CUST_CD ?? "").trim(),
      custName: String(row.CUST_ANAME ?? "").trim(),
    })).filter((x) => /^\d{3}$/.test(x.custCode));
  });
}

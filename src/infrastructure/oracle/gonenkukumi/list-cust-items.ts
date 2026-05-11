import "server-only";

import oracledb from "oracledb";
import { withOracleReadConnection } from "@/infrastructure/oracle/with-connection";

/**
 * 得意先品目（M_CUST_ITEM.CUST_ITEM_CD）を得意先コードで全件取得。
 * - 対象日付で有効期間を run-search と同様に限定
 * - 入力のたびに DB を叩かないためのプリフェッチ用途
 */
export async function listGonenKukumiCustItems(input: {
  custCode: string;
  asOfDate: string;
}): Promise<string[]> {
  const custCd = input.custCode.trim();
  if (!custCd) return [];

  return withOracleReadConnection<string[]>([], async (conn, { companyCd }) => {
    const sql = `
      SELECT DISTINCT M_CUST_ITEM.CUST_ITEM_CD AS "CUST_ITEM_CD"
      FROM M_CUST_ITEM
      WHERE M_CUST_ITEM.CUST_CD = :custCd
        AND M_CUST_ITEM.DLV_LOC_CD = '*'
        AND (:companyCd IS NULL OR M_CUST_ITEM.COMPANY_CD = :companyCd)
        AND M_CUST_ITEM.EFF_PHASE_IN_DATE <= TO_DATE(:asOf2, 'YYYY/MM/DD')
        AND (M_CUST_ITEM.EFF_PHASE_OUT_DATE IS NULL OR TO_DATE(:asOf, 'YYYY/MM/DD') <= M_CUST_ITEM.EFF_PHASE_OUT_DATE)
      ORDER BY M_CUST_ITEM.CUST_ITEM_CD`;
    const r = await conn.execute<{ CUST_ITEM_CD: string | null }>(
      sql,
      { custCd, asOf: input.asOfDate, asOf2: input.asOfDate, companyCd },
      { outFormat: oracledb.OUT_FORMAT_OBJECT },
    );
    const rows = (r.rows ?? []) as { CUST_ITEM_CD: string | null }[];
    const out: string[] = [];
    const seen = new Set<string>();
    for (const row of rows) {
      const v = String(row.CUST_ITEM_CD ?? "").trim();
      if (!v || seen.has(v)) continue;
      seen.add(v);
      out.push(v);
    }
    return out;
  });
}

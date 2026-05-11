import "server-only";

import oracledb from "oracledb";
import { withOracleReadConnection } from "@/infrastructure/oracle/with-connection";
import { dedupeTrimmedColumn } from "@/infrastructure/oracle/rows-helpers";
import { SQL_CUST_ITEM_EFF_RANGE } from "@/infrastructure/oracle/gonenkukumi/sql-fragments";

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
        AND${SQL_CUST_ITEM_EFF_RANGE}
      ORDER BY M_CUST_ITEM.CUST_ITEM_CD`;
    const r = await conn.execute<{ CUST_ITEM_CD: string | null }>(
      sql,
      { custCd, asOf: input.asOfDate, asOf2: input.asOfDate, companyCd },
      { outFormat: oracledb.OUT_FORMAT_OBJECT },
    );
    return dedupeTrimmedColumn(r.rows, "CUST_ITEM_CD");
  });
}

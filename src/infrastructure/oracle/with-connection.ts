import "server-only";

import oracledb from "oracledb";
import { getMariCompanyCd } from "@/infrastructure/oracle/config";
import { getOraclePool, isOracleConfigured } from "@/infrastructure/oracle/pool";

/**
 * Oracle 接続のお決まりの「`isOracleConfigured` チェック → プールから接続取得 →
 * `companyCd` を解決 → finally で close」を 1 関数に集約する。
 *
 * Oracle 未設定時には `fallback` をそのまま返し、各 list-* / list-suggestions が
 * ガード句を書かなくて済むようにする。
 */
export async function withOracleReadConnection<T>(
  fallback: T,
  fn: (
    conn: oracledb.Connection,
    ctx: { companyCd: string | null },
  ) => Promise<T>,
): Promise<T> {
  if (!isOracleConfigured()) return fallback;
  const pool = await getOraclePool();
  const conn = await pool.getConnection();
  try {
    const companyCd = getMariCompanyCd() ?? null;
    return await fn(conn, { companyCd });
  } finally {
    await conn.close();
  }
}

/**
 * 基幹 Oracle 接続パラメータ（仕様書 §8.2.1）。
 *
 * 既定値（フォールバック）は持たず、すべて環境変数からのみ読み込む。
 * 未設定の項目は `undefined`（数値は `port` のみ `number | undefined`）で返し、
 * 必須チェックは利用側（`pool.ts`）でまとめて行う。
 * 接続情報の値そのものは `.env.local` / シークレットマネージャに集約する方針
 * （リポジトリ内のソース／ドキュメントには記載しない）。
 */
export function getOracleConnectEnv(): {
  host: string | undefined;
  port: number | undefined;
  sid: string | undefined;
  user: string | undefined;
  password: string | undefined;
} {
  const host = process.env.ORACLE_HOST?.trim() || undefined;
  const portRaw = process.env.ORACLE_PORT?.trim();
  const portNum = portRaw ? Number(portRaw) : undefined;
  const port = portNum != null && Number.isFinite(portNum) ? portNum : undefined;
  const sid = process.env.ORACLE_SID?.trim() || undefined;
  const user = process.env.ORACLE_USER?.trim() || undefined;
  const password = process.env.ORACLE_PASSWORD;
  return { host, port, sid, user, password };
}

/**
 * MARI の `COMPANY_CD`（`M_CUST` / `M_CUST_ITEM` 等の主キー先頭）。
 * 同一 DB に複数会社があるときは `.env` で明示すると、得意先コードだけでは曖昧になる行を防げる。
 * 未設定時は Oracle バインド `NULL` で会社条件を付けない（単一会社 DB 向け）。
 */
export function getMariCompanyCd(): string | undefined {
  const v =
    process.env.GONENKUKUMI_COMPANY_CD?.trim() || process.env.MARI_COMPANY_CD?.trim();
  return v ? v : undefined;
}

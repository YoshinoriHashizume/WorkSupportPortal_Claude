import type { GonenKukumiOracleResult } from "@/domains/gonenkukumi/types";

/** 検索結果の「得意先名(得意先コード)」表示・タブタイトル用 */
export function custHeadlineFromOracle(custCode: string, oracle: GonenKukumiOracleResult): string {
  if (!oracle.ok) return custCode;
  const blocks = oracle.customerBlocks;
  if (blocks.length === 0) return custCode;
  const hit = blocks.find((b) => String(b.custCode) === String(custCode));
  const name = (hit?.custName ?? blocks[0]?.custName ?? "").trim();
  return name ? `${name}(${custCode})` : custCode;
}

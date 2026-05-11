import "server-only";

/**
 * Oracle の `execute().rows` から指定列を trim → 重複排除 → 順序保持で取り出す。
 * `list-cust-items` / `list-cust-item-suggestions` のように
 * 「DISTINCT で取った文字列カラムを順序固定で配列化」したい場面で使う。
 */
export function dedupeTrimmedColumn<TRow extends Record<string, unknown>>(
  rows: readonly TRow[] | undefined,
  column: keyof TRow & string,
): string[] {
  const out: string[] = [];
  const seen = new Set<string>();
  if (!rows) return out;
  for (const row of rows) {
    const v = String(row[column] ?? "").trim();
    if (!v || seen.has(v)) continue;
    seen.add(v);
    out.push(v);
  }
  return out;
}

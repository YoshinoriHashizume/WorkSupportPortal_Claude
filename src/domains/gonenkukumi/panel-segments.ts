import type { GonenKukumiOracleSuccess } from "@/domains/gonenkukumi/types";
import { compareGonenKukumiYearMonth, normalizeYearMonth } from "@/domains/gonenkukumi/year-month-nav";

export type GonenPanelSegment =
  | { kind: "cust"; filter?: { custCode: string; custItemCd: string; teban: number } }
  | { kind: "sup"; filter?: { vendCode: string; itemCdWithLevel: string } };

/** openMap / React key 用（ブロック単位で一意） */
export function panelSegmentKey(s: GonenPanelSegment): string {
  if (s.kind === "cust") {
    if (!s.filter) return "cust:__all__";
    const f = s.filter;
    return `cust:${f.custCode}\x1f${f.custItemCd}\x1f${f.teban}`;
  }
  if (!s.filter) return "sup:__all__";
  const f = s.filter;
  return `sup:${f.vendCode}\x1f${f.itemCdWithLevel}`;
}

/**
 * 基準月の並びを保ちつつ、他月にだけ現れるブロックも末尾に追加。
 * 同一階層でも仕入先×品目が違えば別セクションになる。
 */
export function groupSegmentsFromCache(
  cache: Record<string, GonenKukumiOracleSuccess>,
  baseYm: string,
): GonenPanelSegment[] {
  const baseNorm = normalizeYearMonth(baseYm);
  const base = cache[baseNorm];
  if (!base) return [];

  const seen = new Set<string>();
  const out: GonenPanelSegment[] = [];

  const custId = (b: { custCode: string; custItemCd: string; teban: number }) =>
    `c:${b.custCode}\x1f${b.custItemCd}\x1f${b.teban}`;
  const supId = (b: { vendCode: string; itemCdWithLevel: string }) =>
    `s:${b.vendCode}\x1f${b.itemCdWithLevel}`;

  const pushCust = (b: (typeof base.customerBlocks)[number]) => {
    const id = custId(b);
    if (seen.has(id)) return;
    seen.add(id);
    out.push({
      kind: "cust",
      filter: { custCode: b.custCode, custItemCd: b.custItemCd, teban: b.teban },
    });
  };
  const pushSup = (b: (typeof base.supplierBlocks)[number]) => {
    const id = supId(b);
    if (seen.has(id)) return;
    seen.add(id);
    out.push({
      kind: "sup",
      filter: { vendCode: b.vendCode, itemCdWithLevel: b.itemCdWithLevel },
    });
  };

  for (const b of base.customerBlocks) pushCust(b);
  for (const b of base.supplierBlocks) pushSup(b);

  const otherMonths = Object.keys(cache)
    .map(normalizeYearMonth)
    .filter((ym) => ym !== baseNorm)
    .sort(compareGonenKukumiYearMonth);

  for (const ym of otherMonths) {
    const o = cache[ym];
    if (!o) continue;
    for (const b of o.customerBlocks) pushCust(b);
    for (const b of o.supplierBlocks) pushSup(b);
  }

  return out;
}

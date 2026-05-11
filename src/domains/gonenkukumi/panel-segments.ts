import type {
  CustomerShipBlock,
  GonenKukumiOracleSuccess,
  SupplierBlock,
} from "@/domains/gonenkukumi/types";
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

/** 得意先ブロック → 対応するパネルセグメント（filter 付き） */
export function customerBlockToSegment(b: CustomerShipBlock): GonenPanelSegment {
  return {
    kind: "cust",
    filter: { custCode: b.custCode, custItemCd: b.custItemCd, teban: b.teban },
  };
}

/** 仕入先ブロック → 対応するパネルセグメント（filter 付き） */
export function supplierBlockToSegment(b: SupplierBlock): GonenPanelSegment {
  return {
    kind: "sup",
    filter: { vendCode: b.vendCode, itemCdWithLevel: b.itemCdWithLevel },
  };
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

  const pushIfNew = (seg: GonenPanelSegment) => {
    const k = panelSegmentKey(seg);
    if (seen.has(k)) return;
    seen.add(k);
    out.push(seg);
  };

  for (const b of base.customerBlocks) pushIfNew(customerBlockToSegment(b));
  for (const b of base.supplierBlocks) pushIfNew(supplierBlockToSegment(b));

  const otherMonths = Object.keys(cache)
    .map(normalizeYearMonth)
    .filter((ym) => ym !== baseNorm)
    .sort(compareGonenKukumiYearMonth);

  for (const ym of otherMonths) {
    const o = cache[ym];
    if (!o) continue;
    for (const b of o.customerBlocks) pushIfNew(customerBlockToSegment(b));
    for (const b of o.supplierBlocks) pushIfNew(supplierBlockToSegment(b));
  }

  return out;
}

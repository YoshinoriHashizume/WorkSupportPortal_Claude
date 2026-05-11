import { gonenSupplierKaisoFloor } from "@/domains/gonenkukumi/gonen-display-format";
import { findSupplierBlock } from "@/domains/gonenkukumi/block-finders";
import { kaisoColor } from "@/domains/gonenkukumi/kaiso-color";
import type { GonenPanelSegment } from "@/domains/gonenkukumi/panel-segments";
import type { GonenKukumiOracleSuccess, SupplierBlock } from "@/domains/gonenkukumi/types";

/**
 * segment（得意先・仕入先＋filter）から `kaisoColor` / `sectionTheme` に渡す
 * 階層インデックスを決定する。
 * - cust → 1
 * - sup (filter 無し) → 3
 * - sup (filter 有り) → 2 + supplierKaiso（block 解決できなければ 2 + 1）
 */
export function gonenSegmentKaisoIndex(
  segment: GonenPanelSegment,
  banner: GonenKukumiOracleSuccess,
): number {
  if (segment.kind === "cust") return 1;
  if (!segment.filter) return 3;
  const block = findSupplierBlock(banner.supplierBlocks, segment.filter);
  return 2 + gonenSupplierKaisoFloor(block?.kaiso);
}

/** 仕入 block 単体から階層インデックスを決定する（segment を介さない経路用） */
export function gonenSupplierBlockKaisoIndex(block: SupplierBlock): number {
  return 2 + gonenSupplierKaisoFloor(block.kaiso);
}

/** segment から `kaisoColor` のテーマを直接得るショートカット */
export function kaisoColorForSegment(
  segment: GonenPanelSegment,
  banner: GonenKukumiOracleSuccess,
): ReturnType<typeof kaisoColor> {
  return kaisoColor(gonenSegmentKaisoIndex(segment, banner));
}

/** supplier block から `kaisoColor` のテーマを直接得るショートカット */
export function kaisoColorForSupplierBlock(block: SupplierBlock): ReturnType<typeof kaisoColor> {
  return kaisoColor(gonenSupplierBlockKaisoIndex(block));
}
